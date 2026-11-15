"""Tests for WorkflowEngine."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_orchestrator.core.engine import WorkflowEngine
from mcp_orchestrator.core.events import EventBus
from mcp_orchestrator.core.models import (
    AgentConfig,
    AgentNode,
    Edge,
    Run,
    RunStatus,
    Workflow,
    WorkflowMetadata,
)
from mcp_orchestrator.core.store import StateStore
from mcp_orchestrator.mcp.models import Tool
from mcp_orchestrator.mcp.registry import MCPToolRegistry
from mcp_orchestrator.providers.base import Provider
from mcp_orchestrator.providers.registry import ProviderRegistry


class MockProvider(Provider):
    """Mock provider for testing."""

    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0

    async def chat_completion(self, model, messages, tools, temperature, max_tokens):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Provider error")
        return MagicMock(choices=[MagicMock(message=MagicMock(content="Test response"))])

    async def stream_chat(self, model, messages, tools, temperature, max_tokens):
        self.call_count += 1
        if self.should_fail:
            raise Exception("Provider error")
        for token in ["Test ", "response"]:
            yield token

    async def list_models(self):
        return [MagicMock(id="test-model", capabilities=MagicMock(tools=True, vision=False, reasoning=False))]

    async def tokenize(self, text):
        return MagicMock(tokens=len(text.split()))

    async def upload_file(self, file):
        return MagicMock(id="file-1")

    async def health_check(self):
        return not self.should_fail


class MockMCPRegistry:
    """Mock MCP tool registry."""

    def __init__(self):
        self.tools = []

    def register_server(self, name, tools):
        self.tools.extend(tools)

    def get_available_tools(self, capabilities):
        return self.tools


def create_test_workflow():
    """Create a simple linear workflow A -> B -> C."""
    nodes = [
        AgentNode(id="A", type="agent", label="Node A", config=AgentConfig(provider="openai", model="gpt-4")),
        AgentNode(id="B", type="agent", label="Node B", config=AgentConfig(provider="openai", model="gpt-4")),
        AgentNode(id="C", type="agent", label="Node C", config=AgentConfig(provider="openai", model="gpt-4")),
    ]
    edges = [
        Edge(id="e1", source="A", target="B"),
        Edge(id="e2", source="B", target="C"),
    ]
    return Workflow(
        id="test-workflow",
        version="1.0",
        metadata=WorkflowMetadata(name="Test Workflow"),
        nodes=nodes,
        edges=edges,
    )


def create_parallel_workflow():
    """Create a workflow with parallel branches: A -> (B, C) -> D."""
    nodes = [
        AgentNode(id="A", type="agent", label="Node A", config=AgentConfig(provider="openai", model="gpt-4")),
        AgentNode(id="B", type="agent", label="Node B", config=AgentConfig(provider="openai", model="gpt-4")),
        AgentNode(id="C", type="agent", label="Node C", config=AgentConfig(provider="openai", model="gpt-4")),
        AgentNode(id="D", type="agent", label="Node D", config=AgentConfig(provider="openai", model="gpt-4")),
    ]
    edges = [
        Edge(id="e1", source="A", target="B"),
        Edge(id="e2", source="A", target="C"),
        Edge(id="e3", source="B", target="D"),
        Edge(id="e4", source="C", target="D"),
    ]
    return Workflow(
        id="parallel-workflow",
        version="1.0",
        metadata=WorkflowMetadata(name="Parallel Workflow"),
        nodes=nodes,
        edges=edges,
    )


@pytest.fixture
def mock_store(tmp_path):
    """Create a mock state store."""
    store = MagicMock(spec=StateStore)
    store.load_workflow = MagicMock()
    store.save_run = MagicMock()
    store.load_run = MagicMock()
    store.load_conversation = MagicMock(return_value=None)
    return store


@pytest.fixture
def mock_provider_registry():
    """Create a mock provider registry."""
    registry = MagicMock(spec=ProviderRegistry)
    provider = MockProvider("openai")
    registry.get = MagicMock(return_value=provider)
    registry.get_all = MagicMock(return_value=[provider])
    return registry


@pytest.fixture
def mock_mcp_registry():
    """Create a mock MCP registry."""
    return MockMCPRegistry()


@pytest.fixture
def event_bus():
    """Create an event bus."""
    return EventBus()


@pytest.fixture
def engine(mock_store, mock_provider_registry, mock_mcp_registry, event_bus):
    """Create a workflow engine with mocks."""
    return WorkflowEngine(
        store=mock_store,
        provider_registry=mock_provider_registry,
        mcp_registry=mock_mcp_registry,
        event_bus=event_bus,
    )


@pytest.mark.asyncio
async def test_engine_executes_linear_workflow(engine, mock_store):
    """Test linear workflow A -> B -> C execution order."""
    workflow = create_test_workflow()
    mock_store.load_workflow.return_value = workflow

    events = []
    async for event in engine.execute("test-workflow", "Hello"):
        events.append(event)

    node_starts = [e for e in events if e.type == "node_start"]
    assert len(node_starts) == 3
    assert node_starts[0].node_id == "A"
    assert node_starts[1].node_id == "B"
    assert node_starts[2].node_id == "C"

    node_completes = [e for e in events if e.type == "node_complete"]
    assert len(node_completes) == 3

    workflow_completes = [e for e in events if e.type == "workflow_complete"]
    assert len(workflow_completes) == 1

    assert mock_store.save_run.call_count >= 4


@pytest.mark.asyncio
async def test_engine_parallel_branches(engine, mock_store):
    """Test parallel execution A -> (B, C) -> D."""
    workflow = create_parallel_workflow()
    mock_store.load_workflow.return_value = workflow

    events = []
    async for event in engine.execute("parallel-workflow", "Hello"):
        events.append(event)

    node_starts = [e for e in events if e.type == "node_start"]
    assert node_starts[0].node_id == "A"

    b_start_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "B")
    c_start_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "C")
    d_start_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "D")

    assert b_start_idx > 0
    assert c_start_idx > 0
    assert d_start_idx > b_start_idx
    assert d_start_idx > c_start_idx

    node_completes = [e for e in events if e.type == "node_complete"]
    assert len(node_completes) == 4


@pytest.mark.asyncio
async def test_engine_error_handling(engine, mock_store, mock_provider_registry):
    """Test NodeError emitted on provider failure."""
    workflow = create_test_workflow()
    mock_store.load_workflow.return_value = workflow

    failing_provider = MockProvider("openai", should_fail=True)
    mock_provider_registry.get = MagicMock(side_effect=lambda name: failing_provider if name == "openai" else None)

    events = []
    async for event in engine.execute("test-workflow", "Hello"):
        events.append(event)

    node_errors = [e for e in events if e.type == "node_error"]
    assert len(node_errors) == 1
    assert "Provider error" in node_errors[0].data["error"]

    saved_run = mock_store.save_run.call_args_list[-1][0][0]
    assert saved_run.status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_engine_checkpoint_resume(engine, mock_store):
    """Test resume from checkpoint."""
    workflow = create_test_workflow()
    mock_store.load_workflow.return_value = workflow

    run = Run(
        id="test-run",
        workflow_id="test-workflow",
        status=RunStatus.RUNNING,
        input_message="Hello",
        current_node="A",
        context={"A": {"output": "Node A output", "error": None}},
        created_at=1000.0,
        updated_at=1000.0,
    )
    mock_store.load_run.return_value = run

    events = []
    async for event in engine.resume("test-run"):
        events.append(event)

    node_starts = [e for e in events if e.type == "node_start"]
    assert any(e.node_id == "B" for e in node_starts)


@pytest.mark.asyncio
async def test_topological_sort():
    """Test topological sort groups nodes by depth."""
    from mcp_orchestrator.core.engine import WorkflowEngine
    from mcp_orchestrator.core.models import WorkflowMetadata

    engine = WorkflowEngine(
        store=MagicMock(),
        provider_registry=MagicMock(),
        mcp_registry=MagicMock(),
        event_bus=EventBus(),
    )

    workflow = create_test_workflow()
    groups = engine._topological_sort(workflow)
    assert len(groups) == 3
    assert len(groups[0]) == 1 and groups[0][0].id == "A"
    assert len(groups[1]) == 1 and groups[1][0].id == "B"
    assert len(groups[2]) == 1 and groups[2][0].id == "C"

    workflow = create_parallel_workflow()
    groups = engine._topological_sort(workflow)
    assert len(groups) == 3
    assert len(groups[0]) == 1 and groups[0][0].id == "A"
    assert len(groups[1]) == 2
    assert {n.id for n in groups[1]} == {"B", "C"}
    assert len(groups[2]) == 1 and groups[2][0].id == "D"


@pytest.mark.asyncio
async def test_engine_with_conversation_history(engine, mock_store):
    """Test engine includes conversation history when share_conversation enabled."""
    workflow = create_test_workflow()
    workflow.nodes[0].config.share_conversation = True
    workflow.nodes[0].config.conversation_id = "conv-1"
    mock_store.load_workflow.return_value = workflow

    from mcp_orchestrator.core.models import Conversation, Message
    conv = Conversation(
        id="conv-1",
        provider="openai",
        model="gpt-4",
        messages=[
            Message(role="user", content="Previous message"),
            Message(role="assistant", content="Previous response"),
        ],
        created_at=1000.0,
        updated_at=1000.0,
    )
    mock_store.load_conversation.return_value = conv

    events = []
    async for event in engine.execute("test-workflow", "Hello"):
        events.append(event)

    assert mock_store.load_conversation.called