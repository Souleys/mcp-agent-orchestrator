"""Workflow engine for executing multi-agent workflows."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from mcp_orchestrator.core.events import (
    Event,
    EventBus,
    NodeComplete,
    NodeError,
    NodeStart,
    ToolCall,
    ToolResult,
    TokenStream,
    WorkflowComplete,
)
from mcp_orchestrator.core.models import (
    AgentConfig,
    AgentNode,
    Edge,
    Run,
    RunStatus,
    Workflow,
)
from mcp_orchestrator.core.store import StateStore
from mcp_orchestrator.mcp.models import Tool
from mcp_orchestrator.mcp.registry import MCPToolRegistry
from mcp_orchestrator.providers.base import Provider
from mcp_orchestrator.providers.registry import ProviderRegistry


@dataclass
class NodeContext:
    """Execution context for a single node."""

    node: AgentNode
    messages: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    output: str = ""
    error: str | None = None


class WorkflowEngine:
    """Executes workflows with topological sort, parallel branches, and checkpointing."""

    def __init__(
        self,
        store: StateStore,
        provider_registry: ProviderRegistry,
        mcp_registry: MCPToolRegistry,
        event_bus: EventBus,
        provider_semaphores: dict[str, asyncio.Semaphore] | None = None,
    ) -> None:
        self.store = store
        self.provider_registry = provider_registry
        self.mcp_registry = mcp_registry
        self.event_bus = event_bus
        self.provider_semaphores = provider_semaphores or {}

    def _topological_sort(self, workflow: Workflow) -> list[list[AgentNode]]:
        """Return nodes grouped by execution depth (parallelizable groups)."""
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = defaultdict(int)

        for edge in workflow.edges:
            adj[edge.source].append(edge.target)
            in_degree[edge.target] += 1
            if edge.source not in in_degree:
                in_degree[edge.source] = 0

        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        depth: dict[str, int] = {nid: 0 for nid in in_degree if in_degree[nid] == 0}
        max_depth = 0

        while queue:
            current = queue.popleft()
            current_depth = depth[current]
            max_depth = max(max_depth, current_depth)

            for neighbor in adj[current]:
                in_degree[neighbor] -= 1
                depth[neighbor] = max(depth.get(neighbor, 0), current_depth + 1)
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        groups: list[list[AgentNode]] = [[] for _ in range(max_depth + 1)]
        for node in workflow.nodes:
            d = depth.get(node.id, 0)
            groups[d].append(node)

        return groups

    def _build_messages(
        self,
        node: AgentNode,
        input_message: str,
        context: dict[str, NodeContext],
        run: Run,
    ) -> list[dict]:
        """Build message list for a node, including conversation history if shared."""
        messages = []

        if node.config.system_prompt:
            messages.append({"role": "system", "content": node.config.system_prompt})

        if node.config.share_conversation and node.config.conversation_id:
            conv = self.store.load_conversation(node.config.conversation_id)
            if conv:
                for msg in conv.messages:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content,
                        "name": msg.name,
                    })

        for edge in run.workflow.edges if hasattr(run, 'workflow') and hasattr(run.workflow, 'edges') else []:
            if edge.target == node.id and edge.source in context:
                pred_output = context[edge.source].output
                if pred_output:
                    messages.append({
                        "role": "assistant",
                        "content": pred_output,
                        "name": edge.source,
                    })

        if not messages or messages[-1].get("role") != "user":
            messages.append({"role": "user", "content": input_message})

        return messages

    def _get_provider(self, node: AgentNode) -> Provider | None:
        """Get provider for a node, with fallback support."""
        provider = self.provider_registry.get(node.config.provider)
        if provider is None and node.config.fallback_model:
            for prov in self.provider_registry.get_all():
                models = asyncio.run(prov.list_models()) if hasattr(prov, 'list_models') else []
                if any(m.id == node.config.fallback_model for m in models):
                    return prov
        return provider

    def _get_available_tools(self, node: AgentNode) -> list[Tool]:
        """Get tools available to this node based on model capabilities."""
        provider = self._get_provider(node)
        if not provider:
            return []

        from mcp_orchestrator.providers.models import ModelCapabilities
        capabilities = ModelCapabilities(tools=True, vision=False, reasoning=False)
        return self.mcp_registry.get_available_tools(capabilities)

    async def execute(
        self,
        workflow_id: str,
        input_message: str,
        run_id: str | None = None,
    ) -> AsyncGenerator[Event, None]:
        """Execute a workflow and yield events."""
        workflow = self.store.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        run_id = run_id or str(uuid.uuid4())
        run = Run(
            id=run_id,
            workflow_id=workflow_id,
            status=RunStatus.RUNNING,
            input_message=input_message,
            current_node=None,
            context={},
            created_at=time.time(),
            updated_at=time.time(),
        )
        self.store.save_run(run)

        default_semaphore = asyncio.Semaphore(6)
        semaphores: dict[str, asyncio.Semaphore] = defaultdict(lambda: default_semaphore)
        semaphores.update(self.provider_semaphores)

        groups = self._topological_sort(workflow)
        context: dict[str, NodeContext] = {}

        try:
            for depth, nodes in enumerate(groups):
                if not nodes:
                    continue

                # Execute nodes in parallel within the same depth
                for node in nodes:
                    sem = semaphores.get(node.config.provider, default_semaphore)

                    # Yield node_start event
                    yield NodeStart(
                        run_id=run.id,
                        node_id=node.id,
                        data={"label": node.label, "provider": node.config.provider, "model": node.config.model}
                    )

                    # Execute node and yield its token_stream events
                    node_ctx = NodeContext(node=node)

                    provider = self._get_provider(node)
                    if not provider:
                        node_ctx.error = f"Provider not found: {node.config.provider}"
                    else:
                        tools = self._get_available_tools(node)
                        tool_schemas = [{"type": "function", "function": t.to_openai_schema()} for t in tools] if tools else None
                        messages = self._build_messages(node, input_message, context, run)

                        async with sem:
                            try:
                                async for token in provider.stream_chat(
                                    model=node.config.model,
                                    messages=messages,
                                    tools=tool_schemas,
                                    temperature=node.config.temperature,
                                    max_tokens=node.config.max_tokens,
                                ):
                                    if token:
                                        node_ctx.output += token
                                        yield TokenStream(
                                            run_id=run.id,
                                            node_id=node.id,
                                            token=token
                                        )
                            except Exception as e:
                                node_ctx.error = str(e)

                    context[node.id] = node_ctx

                    run.current_node = node.id
                    run.context = {nid: {"output": ctx.output, "error": ctx.error} for nid, ctx in context.items()}
                    run.updated_at = time.time()
                    self.store.save_run(run)

                    if node_ctx.error:
                        # Yield node_error event
                        yield NodeError(
                            run_id=run.id,
                            node_id=node.id,
                            error=node_ctx.error
                        )
                        run.status = RunStatus.FAILED
                        run.error_message = node_ctx.error
                        run.completed_at = time.time()
                        self.store.save_run(run)
                        return

                    # Yield node_complete event
                    yield NodeComplete(
                        run_id=run.id,
                        node_id=node.id,
                        output=node_ctx.output
                    )

            run.status = RunStatus.COMPLETED
            run.completed_at = time.time()
            run.context = {nid: {"output": ctx.output, "error": ctx.error} for nid, ctx in context.items()}
            self.store.save_run(run)

            # Yield workflow_complete event
            yield WorkflowComplete(
                run_id=run_id,
                output=context.get(groups[-1][-1].id, NodeContext(node=groups[-1][-1])).output if groups else ""
            )

        except Exception as e:
            run.status = RunStatus.FAILED
            run.error_message = str(e)
            run.completed_at = time.time()
            self.store.save_run(run)
            raise

    async def resume(self, run_id: str) -> AsyncGenerator[Event, None]:
        """Resume a workflow from a checkpoint."""
        run = self.store.load_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        workflow = self.store.load_workflow(run.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {run.workflow_id}")

        context: dict[str, NodeContext] = {}
        for node_id, node_data in run.context.items():
            node = next((n for n in workflow.nodes if n.id == node_id), None)
            if node:
                context[node_id] = NodeContext(
                    node=node,
                    output=node_data.get("output", ""),
                    error=node_data.get("error"),
                )

        completed_nodes = set(context.keys())
        all_nodes = {n.id for n in workflow.nodes}
        remaining_nodes = all_nodes - completed_nodes

        async for event in self.execute(run.workflow_id, run.input_message, run_id):
            yield event


def create_workflow_engine(
    store: StateStore,
    provider_registry: ProviderRegistry,
    mcp_registry: MCPToolRegistry,
    event_bus: EventBus | None = None,
    provider_semaphores: dict[str, asyncio.Semaphore] | None = None,
) -> WorkflowEngine:
    """Factory function to create a WorkflowEngine with default event bus if not provided."""
    if event_bus is None:
        event_bus = EventBus()
    return WorkflowEngine(
        store=store,
        provider_registry=provider_registry,
        mcp_registry=mcp_registry,
        event_bus=event_bus,
        provider_semaphores=provider_semaphores,
    )