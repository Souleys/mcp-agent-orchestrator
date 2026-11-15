"""Integration tests for multi-agent workflows."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from mcp_orchestrator.core.engine import WorkflowEngine
from mcp_orchestrator.core.events import EventBus
from mcp_orchestrator.core.models import (
    AgentConfig, AgentNode, Edge, Run, RunStatus, Workflow, WorkflowMetadata
)
from mcp_orchestrator.core.store import StateStore
from mcp_orchestrator.mcp.registry import MCPToolRegistry
from mcp_orchestrator.providers.base import Provider
from mcp_orchestrator.providers.registry import ProviderRegistry
from mcp_orchestrator.providers.models import ModelCapabilities


class MockProvider(Provider):
    """Mock provider for testing."""

    def __init__(self, name: str, response: str = "Test response", should_fail: bool = False):
        self.name = name
        self.response = response
        self.should_fail = should_fail
        self.call_count = 0

    async def chat_completion(self, model, messages, tools, temperature, max_tokens):
        self.call_count += 1
        if self.should_fail:
            raise Exception(f"{self.name} error")
        return MagicMock(choices=[MagicMock(message=MagicMock(content=self.response))])

    async def stream_chat(self, model, messages, tools, temperature, max_tokens):
        self.call_count += 1
        if self.should_fail:
            raise Exception(f"{self.name} error")
        for token in [self.response]:
            yield token

    async def list_models(self):
        return [MagicMock(id=f"{self.name}-model", capabilities=MagicMock(tools=True, vision=False, reasoning=False))]

    async def tokenize(self, text):
        return MagicMock(tokens=len(text.split()))

    async def upload_file(self, file):
        return MagicMock(id="file-1")

    async def health_check(self):
        return not self.should_fail


class MockMCPRegistry(MCPToolRegistry):
    """Mock MCP tool registry."""

    def __init__(self):
        super().__init__()
        self._tools = []

    def get_available_tools(self, capabilities):
        return self._tools


@pytest.fixture
def mock_store(tmp_path):
    """Create a state store."""
    store = StateStore(tmp_path / "test.db")
    store.init_db()
    return store


@pytest.fixture
def mock_provider_registry():
    """Create a mock provider registry with multiple providers."""
    registry = MagicMock(spec=ProviderRegistry)
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


def create_planner_frontend_backend_reviewer_workflow():
    """Create a 4-agent workflow: Planner -> (Frontend, Backend) -> Reviewer."""
    nodes = [
        AgentNode(
            id="planner",
            type="agent",
            label="Planner",
            config=AgentConfig(provider="planner-provider", model="planner-model", system_prompt="Plan the task.")
        ),
        AgentNode(
            id="frontend",
            type="agent",
            label="Frontend Developer",
            config=AgentConfig(provider="dev-provider", model="dev-model", system_prompt="Write frontend code.")
        ),
        AgentNode(
            id="backend",
            type="agent",
            label="Backend Developer",
            config=AgentConfig(provider="dev-provider", model="dev-model", system_prompt="Write backend code.")
        ),
        AgentNode(
            id="reviewer",
            type="agent",
            label="Code Reviewer",
            config=AgentConfig(provider="reviewer-provider", model="reviewer-model", system_prompt="Review the code.")
        ),
    ]
    edges = [
        Edge(id="e1", source="planner", target="frontend"),
        Edge(id="e2", source="planner", target="backend"),
        Edge(id="e3", source="frontend", target="reviewer"),
        Edge(id="e4", source="backend", target="reviewer"),
    ]
    return Workflow(
        id="multi-agent-workflow",
        version="1.0",
        metadata=WorkflowMetadata(name="Planner-Frontend-Backend-Reviewer"),
        nodes=nodes,
        edges=edges,
    )


@pytest.mark.asyncio
async def test_planner_frontend_backend_reviewer(engine, mock_store, mock_provider_registry):
    """Test 4-agent parallel workflow execution."""
    from unittest.mock import MagicMock

    workflow = create_planner_frontend_backend_reviewer_workflow()
    mock_store.save_workflow(workflow)

    # Set up providers for each node
    providers = {
        "planner-provider": MockProvider("planner-provider", "Plan: Create API and UI"),
        "dev-provider": MockProvider("dev-provider", "Implementation complete"),
        "reviewer-provider": MockProvider("reviewer-provider", "Code looks good"),
    }

    def get_provider(name):
        return providers.get(name)

    mock_provider_registry.get = MagicMock(side_effect=get_provider)

    events = []
    async for event in engine.execute("multi-agent-workflow", "Build a todo app"):
        events.append(event)

    # Verify execution order: planner first, then frontend/backend in parallel, then reviewer
    node_starts = [e for e in events if e.type == "node_start"]
    assert len(node_starts) == 4

    # Planner should start first
    assert node_starts[0].node_id == "planner"

    # Frontend and backend should start after planner (order between them doesn't matter)
    frontend_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "frontend")
    backend_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "backend")
    reviewer_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "reviewer")

    assert frontend_idx > 0
    assert backend_idx > 0
    assert reviewer_idx > frontend_idx
    assert reviewer_idx > backend_idx

    # Verify all nodes completed
    node_completes = [e for e in events if e.type == "node_complete"]
    assert len(node_completes) == 4

    # Verify workflow completed
    workflow_completes = [e for e in events if e.type == "workflow_complete"]
    assert len(workflow_completes) == 1


@pytest.mark.asyncio
async def test_parallel_branches_execution(engine, mock_store, mock_provider_registry):
    """Test that parallel branches execute concurrently."""
    from unittest.mock import MagicMock

    # Create workflow: A -> (B, C) -> D
    nodes = [
        AgentNode(id="A", type="agent", label="Node A", config=AgentConfig(provider="p1", model="m1")),
        AgentNode(id="B", type="agent", label="Node B", config=AgentConfig(provider="p2", model="m2")),
        AgentNode(id="C", type="agent", label="Node C", config=AgentConfig(provider="p3", model="m3")),
        AgentNode(id="D", type="agent", label="Node D", config=AgentConfig(provider="p4", model="m4")),
    ]
    edges = [
        Edge(id="e1", source="A", target="B"),
        Edge(id="e2", source="A", target="C"),
        Edge(id="e3", source="B", target="D"),
        Edge(id="e4", source="C", target="D"),
    ]
    workflow = Workflow(
        id="parallel-workflow",
        version="1.0",
        metadata=WorkflowMetadata(name="Parallel Workflow"),
        nodes=nodes,
        edges=edges,
    )
    mock_store.save_workflow(workflow)

    providers = {
        "p1": MockProvider("p1", "A done"),
        "p2": MockProvider("p2", "B done"),
        "p3": MockProvider("p3", "C done"),
        "p4": MockProvider("p4", "D done"),
    }

    mock_provider_registry.get = MagicMock(side_effect=lambda n: providers.get(n))

    events = []
    async for event in engine.execute("parallel-workflow", "Test"):
        events.append(event)

    # Verify parallel execution: A first, then B and C (order between them doesn't matter), then D
    node_starts = [e for e in events if e.type == "node_start"]
    assert len(node_starts) == 4
    assert node_starts[0].node_id == "A"

    # B and C should start after A
    b_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "B")
    c_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "C")
    d_idx = next(i for i, e in enumerate(node_starts) if e.node_id == "D")

    assert b_idx > 0
    assert c_idx > 0
    assert d_idx > b_idx
    assert d_idx > c_idx

    # Verify all nodes completed
    node_completes = [e for e in events if e.type == "node_complete"]
    assert len(node_completes) == 4

    # Verify workflow completed
    workflow_completes = [e for e in events if e.type == "workflow_complete"]
    assert len(workflow_completes) == 1