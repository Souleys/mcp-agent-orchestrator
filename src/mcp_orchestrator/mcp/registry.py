"""MCP Tool Registry - aggregates tools from all servers with capability filtering."""

from __future__ import annotations

from typing import Any

from mcp_orchestrator.providers.models import ModelCapabilities


class MCPToolRegistry:
    """Registry that aggregates tools from all connected MCP servers and filters by capabilities."""

    def __init__(self) -> None:
        self._servers: dict[str, list[dict[str, Any]]] = {}

    def register_server(self, server_name: str, tools: list[dict[str, Any]]) -> None:
        """Register tools from a server."""
        self._servers[server_name] = tools

    def unregister_server(self, server_name: str) -> None:
        """Unregister a server and its tools."""
        self._servers.pop(server_name, None)

    def get_server_tools(self, server_name: str) -> list[dict[str, Any]]:
        """Get all tools for a specific server."""
        return self._servers.get(server_name, [])

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Get all tools from all servers (unfiltered)."""
        all_tools = []
        for tools in self._servers.values():
            all_tools.extend(tools)
        return all_tools

    def get_available_tools(self, capabilities: ModelCapabilities) -> list[dict[str, Any]]:
        """Get tools that are available for the given model capabilities."""
        all_tools = self.get_all_tools()
        available = []

        for tool in all_tools:
            required = tool.get("required_capabilities", {})

            # Check if model has all required capabilities
            if self._capabilities_match(capabilities, required):
                available.append(tool)

        return available

    def _capabilities_match(
        self, model_caps: ModelCapabilities, required: dict[str, bool]
    ) -> bool:
        """Check if model capabilities satisfy tool requirements."""
        for cap_name, required_value in required.items():
            if required_value:
                model_value = getattr(model_caps, cap_name, False)
                if not model_value:
                    return False
        return True

    def get_server_names(self) -> list[str]:
        """Get list of registered server names."""
        return list(self._servers.keys())

    def clear(self) -> None:
        """Clear all registered servers and tools."""
        self._servers.clear()
