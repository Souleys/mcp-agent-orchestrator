"""Tests for MCP Tool Registry."""

import pytest
from unittest.mock import MagicMock


class TestMCPToolRegistry:
    """Tests for MCPToolRegistry."""

    def test_registry_filters_by_capabilities(self):
        """Test that registry filters tools by model capabilities."""
        from mcp_orchestrator.mcp.registry import MCPToolRegistry
        from mcp_orchestrator.providers.models import ModelCapabilities

        registry = MCPToolRegistry()

        # tool1 requires tools capability, tool2 requires vision capability
        tool1 = {
            "name": "tool1",
            "description": "Tool requiring tools",
            "inputSchema": {},
            "required_capabilities": {"tools": True}
        }
        tool2 = {
            "name": "tool2",
            "description": "Tool requiring vision",
            "inputSchema": {},
            "required_capabilities": {"vision": True}
        }

        registry.register_server("fs", [tool1, tool2])

        caps = ModelCapabilities(tools=True, vision=False, reasoning=False)
        available = registry.get_available_tools(caps)

        available_names = {t["name"] for t in available}
        assert "tool1" in available_names
        assert "tool2" not in available_names

    def test_registry_aggregates_tools_from_multiple_servers(self):
        """Test that registry aggregates tools from all connected servers."""
        from mcp_orchestrator.mcp.registry import MCPToolRegistry
        from mcp_orchestrator.providers.models import ModelCapabilities

        registry = MCPToolRegistry()

        tool1 = {"name": "tool1", "description": "Tool 1", "inputSchema": {}, "required_capabilities": {}}
        tool2 = {"name": "tool2", "description": "Tool 2", "inputSchema": {}, "required_capabilities": {}}
        tool3 = {"name": "tool3", "description": "Tool 3", "inputSchema": {}, "required_capabilities": {}}

        registry.register_server("server1", [tool1, tool2])
        registry.register_server("server2", [tool3])

        caps = ModelCapabilities()
        available = registry.get_available_tools(caps)

        assert len(available) == 3
        tool_names = {t["name"] for t in available}
        assert tool_names == {"tool1", "tool2", "tool3"}

    def test_registry_returns_empty_for_no_capabilities(self):
        """Test that registry returns empty list when no capabilities match."""
        from mcp_orchestrator.mcp.registry import MCPToolRegistry
        from mcp_orchestrator.providers.models import ModelCapabilities

        registry = MCPToolRegistry()

        tool1 = {
            "name": "tool1",
            "description": "Tool requiring tools",
            "inputSchema": {},
            "required_capabilities": {"tools": True}
        }

        registry.register_server("fs", [tool1])

        caps = ModelCapabilities(tools=False, vision=False, reasoning=False)
        available = registry.get_available_tools(caps)

        assert available == []

    def test_registry_unregister_server(self):
        """Test that registry can unregister a server."""
        from mcp_orchestrator.mcp.registry import MCPToolRegistry
        from mcp_orchestrator.providers.models import ModelCapabilities

        registry = MCPToolRegistry()

        tool1 = {"name": "tool1", "description": "Tool 1", "inputSchema": {}, "required_capabilities": {}}
        tool2 = {"name": "tool2", "description": "Tool 2", "inputSchema": {}, "required_capabilities": {}}

        registry.register_server("server1", [tool1])
        registry.register_server("server2", [tool2])

        caps = ModelCapabilities()
        available = registry.get_available_tools(caps)
        assert len(available) == 2

        registry.unregister_server("server1")
        available = registry.get_available_tools(caps)
        assert len(available) == 1
        assert available[0]["name"] == "tool2"

    def test_registry_get_server_tools(self):
        """Test getting tools for a specific server."""
        from mcp_orchestrator.mcp.registry import MCPToolRegistry

        registry = MCPToolRegistry()

        tool1 = {"name": "tool1", "description": "Tool 1", "inputSchema": {}, "required_capabilities": {}}
        tool2 = {"name": "tool2", "description": "Tool 2", "inputSchema": {}, "required_capabilities": {}}

        registry.register_server("server1", [tool1])
        registry.register_server("server2", [tool2])

        server1_tools = registry.get_server_tools("server1")
        assert len(server1_tools) == 1
        assert server1_tools[0]["name"] == "tool1"

        server2_tools = registry.get_server_tools("server2")
        assert len(server2_tools) == 1
        assert server2_tools[0]["name"] == "tool2"

        # Non-existent server
        assert registry.get_server_tools("nonexistent") == []

    def test_registry_tool_schema_includes_required_capabilities(self):
        """Test that tool schema includes required capabilities field."""
        from mcp_orchestrator.mcp.registry import MCPToolRegistry
        from mcp_orchestrator.providers.models import ModelCapabilities

        registry = MCPToolRegistry()

        tool = {
            "name": "test_tool",
            "description": "Test tool",
            "inputSchema": {"type": "object", "properties": {}},
            "required_capabilities": {"tools": True, "vision": True}
        }

        registry.register_server("test", [tool])
        caps = ModelCapabilities(tools=True, vision=True, reasoning=False)
        available = registry.get_available_tools(caps)

        assert len(available) == 1
        assert available[0]["required_capabilities"] == {"tools": True, "vision": True}
