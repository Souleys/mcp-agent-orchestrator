"""MCP models for the orchestrator."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass


@dataclass
class Tool:
    """Represents an MCP tool with its metadata."""
    name: str
    description: str
    input_schema: dict[str, Any]
    server_name: str = "unknown"


@dataclass
class ToolResult:
    """Result of a tool call."""
    content: list[dict[str, Any]]
    is_error: bool
    error_message: str | None = None


class MCPTool:
    """MCP Tool model with capability requirements."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        required_capabilities: dict[str, bool] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.required_capabilities = required_capabilities or {}

    @property
    def inputSchema(self) -> dict[str, Any]:
        return self.input_schema
