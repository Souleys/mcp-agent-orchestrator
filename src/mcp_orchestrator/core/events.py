"""Event Bus for the orchestrator - pub/sub system for workflow events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import asyncio
import time
import uuid


@dataclass
class Event:
    """Base event class for all workflow events."""
    type: str
    timestamp: float = field(default_factory=time.time)
    data: Any = None
    run_id: str = ""
    node_id: str | None = None


@dataclass
class NodeStart(Event):
    """Event emitted when a node starts execution."""
    def __init__(self, run_id: str, node_id: str, data: Any = None):
        super().__init__(type="node_start", run_id=run_id, node_id=node_id, data=data)


@dataclass
class TokenStream(Event):
    """Event emitted for each token in a streaming response."""
    def __init__(self, run_id: str, node_id: str, token: str, data: Any = None):
        super().__init__(type="token_stream", run_id=run_id, node_id=node_id, data={"token": token, **(data or {})})


@dataclass
class ToolCall(Event):
    """Event emitted when a tool is called."""
    def __init__(self, run_id: str, node_id: str, tool_name: str, arguments: dict, data: Any = None):
        super().__init__(type="tool_call", run_id=run_id, node_id=node_id, data={"tool_name": tool_name, "arguments": arguments, **(data or {})})


@dataclass
class ToolResult(Event):
    """Event emitted when a tool returns a result."""
    def __init__(self, run_id: str, node_id: str, tool_name: str, result: Any, is_error: bool = False, error_message: str | None = None, data: Any = None):
        super().__init__(type="tool_result", run_id=run_id, node_id=node_id, data={"tool_name": tool_name, "result": result, "is_error": is_error, "error_message": error_message, **(data or {})})


@dataclass
class NodeComplete(Event):
    """Event emitted when a node completes successfully."""
    def __init__(self, run_id: str, node_id: str, output: Any, data: Any = None):
        super().__init__(type="node_complete", run_id=run_id, node_id=node_id, data={"output": output, **(data or {})})


@dataclass
class NodeError(Event):
    """Event emitted when a node encounters an error."""
    def __init__(self, run_id: str, node_id: str, error: str, data: Any = None):
        super().__init__(type="node_error", run_id=run_id, node_id=node_id, data={"error": error, **(data or {})})


@dataclass
class WorkflowComplete(Event):
    """Event emitted when the entire workflow completes."""
    def __init__(self, run_id: str, output: Any, data: Any = None):
        super().__init__(type="workflow_complete", run_id=run_id, node_id=None, data={"output": output, **(data or {})})


class EventBus:
    """Async pub/sub event bus for workflow events."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str) -> asyncio.Queue:
        """Subscribe to events of a specific type. Returns a queue for receiving events."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(queue)
        return queue

    async def unsubscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from events of a specific type."""
        async with self._lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(queue)
                except ValueError:
                    pass

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of its type."""
        async with self._lock:
            queues = self._subscribers.get(event.type, []).copy()

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop event if queue is full
                pass

    async def publish_all(self, events: list[Event]) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)

    async def subscribe_all(self, event_types: list[str]) -> dict[str, asyncio.Queue]:
        """Subscribe to multiple event types at once."""
        return {et: await self.subscribe(et) for et in event_types}


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def set_event_bus(bus: EventBus) -> None:
    """Set the global event bus instance."""
    global _event_bus
    _event_bus = bus
