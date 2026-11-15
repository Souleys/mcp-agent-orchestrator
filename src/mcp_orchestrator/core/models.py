"""Core models for the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import json


class RunStatus(str, Enum):
    """Status of a workflow run."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowMetadata:
    """Metadata for a workflow."""
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class AgentConfig:
    """Configuration for an agent node."""
    provider: str
    model: str
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: list[str] = field(default_factory=list)
    builtin_tools: list[str] = field(default_factory=list)
    fallback_model: str | None = None
    conversation_id: str | None = None
    share_conversation: bool = False


@dataclass
class AgentNode:
    """A node in the workflow graph representing an agent."""
    id: str
    type: str = "agent"
    label: str = ""
    config: AgentConfig = field(default_factory=AgentConfig)
    position: dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})


@dataclass
class Edge:
    """An edge connecting two nodes in the workflow."""
    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None
    type: str = "default"


@dataclass
class Workflow:
    """A workflow definition."""
    id: str
    version: str
    metadata: WorkflowMetadata
    nodes: list[AgentNode] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize workflow to JSON."""
        return json.dumps({
            "id": self.id,
            "version": self.version,
            "metadata": {
                "name": self.metadata.name,
                "description": self.metadata.description,
                "tags": self.metadata.tags,
                "created_at": self.metadata.created_at,
                "updated_at": self.metadata.updated_at,
            },
            "nodes": [
                {
                    "id": n.id,
                    "type": n.type,
                    "label": n.label,
                    "config": {
                        "provider": n.config.provider,
                        "model": n.config.model,
                        "system_prompt": n.config.system_prompt,
                        "temperature": n.config.temperature,
                        "max_tokens": n.config.max_tokens,
                        "tools": n.config.tools,
                        "builtin_tools": n.config.builtin_tools,
                        "fallback_model": n.config.fallback_model,
                        "conversation_id": n.config.conversation_id,
                        "share_conversation": n.config.share_conversation,
                    },
                    "position": n.position,
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "source_handle": e.source_handle,
                    "target_handle": e.target_handle,
                    "type": e.type,
                }
                for e in self.edges
            ],
        })

    @classmethod
    def from_json(cls, json_str: str) -> Workflow:
        """Deserialize workflow from JSON."""
        data = json.loads(json_str)
        metadata = WorkflowMetadata(
            name=data["metadata"]["name"],
            description=data["metadata"].get("description", ""),
            tags=data["metadata"].get("tags", []),
            created_at=data["metadata"].get("created_at", datetime.now().timestamp()),
            updated_at=data["metadata"].get("updated_at", datetime.now().timestamp()),
        )
        nodes = []
        for n in data.get("nodes", []):
            config = AgentConfig(
                provider=n["config"]["provider"],
                model=n["config"]["model"],
                system_prompt=n["config"].get("system_prompt", ""),
                temperature=n["config"].get("temperature", 0.7),
                max_tokens=n["config"].get("max_tokens", 4096),
                tools=n["config"].get("tools", []),
                builtin_tools=n["config"].get("builtin_tools", []),
                fallback_model=n["config"].get("fallback_model"),
                conversation_id=n["config"].get("conversation_id"),
                share_conversation=n["config"].get("share_conversation", False),
            )
            nodes.append(AgentNode(
                id=n["id"],
                type=n.get("type", "agent"),
                label=n.get("label", ""),
                config=config,
                position=n.get("position", {"x": 0, "y": 0}),
            ))
        edges = []
        for e in data.get("edges", []):
            edges.append(Edge(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                source_handle=e.get("source_handle"),
                target_handle=e.get("target_handle"),
                type=e.get("type", "default"),
            ))
        return cls(
            id=data["id"],
            version=data["version"],
            metadata=metadata,
            nodes=nodes,
            edges=edges,
        )


@dataclass
class Run:
    """A workflow execution run."""
    id: str
    workflow_id: str
    status: RunStatus
    input_message: str
    current_node: str | None
    context: dict[str, Any]
    created_at: float
    updated_at: float
    completed_at: float | None = None
    error_message: str | None = None


@dataclass
class Message:
    """A message in a conversation."""
    role: str
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class Conversation:
    """A conversation with a model."""
    id: str
    provider: str
    model: str
    messages: list[Message]
    created_at: float
    updated_at: float
