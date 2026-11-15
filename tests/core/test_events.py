"""Tests for Event Bus."""

import pytest
import asyncio
from mcp_orchestrator.core.events import (
    EventBus, Event, NodeStart, TokenStream, ToolCall, ToolResult,
    NodeComplete, NodeError, WorkflowComplete, get_event_bus
)


class TestEventBus:
    """Tests for EventBus pub/sub functionality."""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh event bus for each test."""
        return EventBus()

    @pytest.mark.asyncio
    async def test_event_bus_pub_sub(self, event_bus):
        """Test basic pub/sub with typed events."""
        # Subscribe to node_start events
        queue = await event_bus.subscribe("node_start")

        # Publish a NodeStart event
        event = NodeStart(run_id="run1", node_id="node1", data={"test": "data"})
        await event_bus.publish(event)

        # Receive the event
        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.type == "node_start"
        assert received.run_id == "run1"
        assert received.node_id == "node1"
        assert received.data == {"test": "data"}

    @pytest.mark.asyncio
    async def test_event_bus_multiple_subscribers(self, event_bus):
        """Test multiple subscribers receive the same event."""
        queue1 = await event_bus.subscribe("token_stream")
        queue2 = await event_bus.subscribe("token_stream")

        event = TokenStream(run_id="run1", node_id="node1", token="hello")
        await event_bus.publish(event)

        received1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
        received2 = await asyncio.wait_for(queue2.get(), timeout=1.0)

        assert received1.data["token"] == "hello"
        assert received2.data["token"] == "hello"

    @pytest.mark.asyncio
    async def test_event_bus_unsubscribe(self, event_bus):
        """Test unsubscribing stops receiving events."""
        queue = await event_bus.subscribe("tool_call")
        await event_bus.unsubscribe("tool_call", queue)

        event = ToolCall(run_id="run1", node_id="node1", tool_name="test_tool", arguments={})
        await event_bus.publish(event)

        # Queue should be empty
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_event_bus_different_event_types(self, event_bus):
        """Test events of different types go to different subscribers."""
        node_start_queue = await event_bus.subscribe("node_start")
        token_queue = await event_bus.subscribe("token_stream")

        await event_bus.publish(NodeStart(run_id="run1", node_id="node1"))
        await event_bus.publish(TokenStream(run_id="run1", node_id="node1", token="test"))

        node_event = await asyncio.wait_for(node_start_queue.get(), timeout=1.0)
        token_event = await asyncio.wait_for(token_queue.get(), timeout=1.0)

        assert node_event.type == "node_start"
        assert token_event.type == "token_stream"

    @pytest.mark.asyncio
    async def test_event_types_creation(self):
        """Test all event types can be created correctly."""
        run_id = "run1"
        node_id = "node1"

        events = [
            NodeStart(run_id=run_id, node_id=node_id),
            TokenStream(run_id=run_id, node_id=node_id, token="test"),
            ToolCall(run_id=run_id, node_id=node_id, tool_name="tool1", arguments={"arg": "value"}),
            ToolResult(run_id=run_id, node_id=node_id, tool_name="tool1", result="success"),
            NodeComplete(run_id=run_id, node_id=node_id, output="done"),
            NodeError(run_id=run_id, node_id=node_id, error="failed"),
            WorkflowComplete(run_id=run_id, output="complete"),
        ]

        for event in events:
            assert event.run_id == run_id
            if event.type != "workflow_complete":
                assert event.node_id == node_id
            else:
                assert event.node_id is None

    @pytest.mark.asyncio
    async def test_global_event_bus(self):
        """Test global event bus singleton."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2


class TestEventDataClasses:
    """Tests for event data class structure."""

    def test_node_start_fields(self):
        event = NodeStart(run_id="run1", node_id="node1", data={"key": "value"})
        assert event.type == "node_start"
        assert event.run_id == "run1"
        assert event.node_id == "node1"
        assert event.data == {"key": "value"}

    def test_token_stream_fields(self):
        event = TokenStream(run_id="run1", node_id="node1", token="hello", data={"extra": "data"})
        assert event.type == "token_stream"
        assert event.data["token"] == "hello"
        assert event.data["extra"] == "data"

    def test_tool_call_fields(self):
        event = ToolCall(run_id="run1", node_id="node1", tool_name="my_tool", arguments={"a": 1})
        assert event.type == "tool_call"
        assert event.data["tool_name"] == "my_tool"
        assert event.data["arguments"] == {"a": 1}

    def test_tool_result_fields(self):
        event = ToolResult(run_id="run1", node_id="node1", tool_name="my_tool", result="output", is_error=False)
        assert event.type == "tool_result"
        assert event.data["tool_name"] == "my_tool"
        assert event.data["result"] == "output"
        assert event.data["is_error"] is False

        event_error = ToolResult(run_id="run1", node_id="node1", tool_name="my_tool", result=None, is_error=True, error_message="failed")
        assert event_error.data["is_error"] is True
        assert event_error.data["error_message"] == "failed"

    def test_node_complete_fields(self):
        event = NodeComplete(run_id="run1", node_id="node1", output="completed")
        assert event.type == "node_complete"
        assert event.data["output"] == "completed"

    def test_node_error_fields(self):
        event = NodeError(run_id="run1", node_id="node1", error="something went wrong")
        assert event.type == "node_error"
        assert event.data["error"] == "something went wrong"

    def test_workflow_complete_fields(self):
        event = WorkflowComplete(run_id="run1", output="all done")
        assert event.type == "workflow_complete"
        assert event.node_id is None
        assert event.data["output"] == "all done"
