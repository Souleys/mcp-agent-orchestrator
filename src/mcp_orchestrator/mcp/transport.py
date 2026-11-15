"""MCP Transport layer - stdio and SSE implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool


class MCPTransport(ABC):
    """Abstract protocol for MCP transport."""

    @abstractmethod
    async def connect(self) -> ClientSession:
        """Connect to the MCP server and return the session."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        ...

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        ...

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        ...

    @property
    @abstractmethod
    def session(self) -> ClientSession | None:
        """Get the underlying MCP session."""
        ...


class StdioTransport(MCPTransport):
    """STDIO transport for MCP servers."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._session: ClientSession | None = None
        self._stdio_context: Any = None
        self._read_stream: Any = None
        self._write_stream: Any = None

    async def connect(self) -> ClientSession:
        """Connect to the MCP server via stdio."""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )

        self._stdio_context = stdio_client(server_params)
        self._read_stream, self._write_stream = await self._stdio_context.__aenter__()

        self._session = ClientSession(self._read_stream, self._write_stream)
        await self._session.__aenter__()
        await self._session.initialize()

        return self._session

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None

        if self._stdio_context:
            await self._stdio_context.__aexit__(None, None, None)
            self._stdio_context = None

        self._read_stream = None
        self._write_stream = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server")

        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
                "required_capabilities": self._extract_capabilities(tool),
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server")

        result = await self._session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(f"Tool call failed: {result.content}")

        return {"result": result.content}

    @property
    def session(self) -> ClientSession | None:
        """Get the underlying MCP session."""
        return self._session

    def _extract_capabilities(self, tool: Tool) -> dict[str, bool]:
        """Extract required capabilities from tool schema."""
        return {"tools": True}


class SSETransport(MCPTransport):
    """SSE transport for MCP servers."""

    def __init__(self, url: str, headers: dict[str, str] | None = None) -> None:
        self.url = url
        self.headers = headers or {}
        self._session: ClientSession | None = None
        self._sse_context: Any = None
        self._read_stream: Any = None
        self._write_stream: Any = None

    async def connect(self) -> ClientSession:
        """Connect to the MCP server via SSE."""
        self._sse_context = sse_client(self.url, headers=self.headers)
        self._read_stream, self._write_stream = await self._sse_context.__aenter__()

        self._session = ClientSession(self._read_stream, self._write_stream)
        await self._session.__aenter__()
        await self._session.initialize()

        return self._session

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None

        if self._sse_context:
            await self._sse_context.__aexit__(None, None, None)
            self._sse_context = None

        self._read_stream = None
        self._write_stream = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server")

        result = await self._session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema,
                "required_capabilities": self._extract_capabilities(tool),
            }
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        if not self._session:
            raise RuntimeError("Not connected to MCP server")

        result = await self._session.call_tool(name, arguments)

        if result.isError:
            raise RuntimeError(f"Tool call failed: {result.content}")

        return {"result": result.content}

    @property
    def session(self) -> ClientSession | None:
        """Get the underlying MCP session."""
        return self._session

    def _extract_capabilities(self, tool: Tool) -> dict[str, bool]:
        """Extract required capabilities from tool schema."""
        return {"tools": True}
