"""MCP Client - wraps transport and handles MCP protocol."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp_orchestrator.mcp.transport import MCPTransport
from mcp_orchestrator.mcp.models import Tool, ToolResult

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client that wraps a transport and handles the MCP protocol."""

    def __init__(self, transport: MCPTransport) -> None:
        self.transport = transport
        self._connected = False
        self._tools: list[Tool] = []

    async def connect(self) -> Any:
        """Connect to the MCP server via transport."""
        if self._connected:
            return self.transport.session

        session = await self.transport.connect()
        self._connected = True
        await self._refresh_tools()
        logger.info("Connected to MCP server successfully")
        return session

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._connected:
            await self.transport.disconnect()
            self._connected = False
            self._tools = []
            logger.info("Disconnected from MCP server")

    def list_tools(self) -> list[Tool]:
        """List available tools from the connected server (cached after connect)."""
        if not self._connected:
            raise RuntimeError("Not connected to MCP server. Call connect() first.")
        return self._tools.copy()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Call a tool on the MCP server."""
        if not self._connected or not self.transport.session:
            raise RuntimeError("Not connected to MCP server")

        result = await self.transport.session.call_tool(name, arguments)

        content = []
        for c in result.content:
            if hasattr(c, 'text'):
                content.append({"type": c.type, "text": c.text})
            elif hasattr(c, 'data'):
                content.append({"type": c.type, "data": c.data})
            else:
                content.append({"type": "text", "text": str(c)})

        return ToolResult(
            content=content,
            is_error=result.isError,
            error_message=getattr(result, 'error', None) if result.isError else None
        )

    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self.transport.session is not None

    async def _refresh_tools(self) -> None:
        """Refresh the tools cache from the server."""
        if not self.transport.session:
            self._tools = []
            return

        try:
            result = await self.transport.session.list_tools()
            self._tools = [
                Tool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema,
                    server_name=getattr(self.transport, 'server_name', 'unknown')
                )
                for tool in result.tools
            ]
        except Exception:
            self._tools = []

    async def __aenter__(self) -> MCPClient:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
