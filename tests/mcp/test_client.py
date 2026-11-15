"""Tests for MCP Client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


class TestMCPClient:
    """Tests for MCPClient."""

    @pytest.mark.asyncio
    async def test_mcp_client_lists_tools(self):
        """Test that MCPClient can list tools from a connected server."""
        from mcp_orchestrator.mcp.client import MCPClient
        from mcp_orchestrator.mcp.transport import StdioTransport

        transport = StdioTransport(command="echo", args=["hello"])
        client = MCPClient(transport)

        with patch.object(transport, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_init_result = MagicMock()
            mock_connect.return_value = mock_init_result

            # Mock the session property
            mock_session = AsyncMock()

            # Create proper mock tools
            tool1 = MagicMock()
            tool1.name = "read_file"
            tool1.description = "Read a file"
            tool1.inputSchema = {"type": "object"}

            tool2 = MagicMock()
            tool2.name = "write_file"
            tool2.description = "Write a file"
            tool2.inputSchema = {"type": "object"}

            mock_session.list_tools.return_value = MagicMock(tools=[tool1, tool2])

            # Manually patch and restore the session property
            original_session = StdioTransport.__dict__.get('session')
            mock_session_prop = PropertyMock(return_value=mock_session)
            StdioTransport.session = mock_session_prop
            try:
                # Connect first
                await client.connect()

                tools = client.list_tools()  # Not async

                assert isinstance(tools, list)
                assert len(tools) == 2
                assert tools[0].name == "read_file"
                assert tools[1].name == "write_file"
            finally:
                # Restore original property
                if original_session is not None:
                    StdioTransport.session = original_session
                else:
                    del StdioTransport.session

    @pytest.mark.asyncio
    async def test_mcp_client_calls_tool(self):
        """Test that MCPClient can call a tool."""
        from mcp_orchestrator.mcp.client import MCPClient
        from mcp_orchestrator.mcp.transport import StdioTransport

        transport = StdioTransport(command="echo", args=["hello"])
        client = MCPClient(transport)

        with patch.object(transport, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = MagicMock()

            mock_session = AsyncMock()

            # Create proper mock result
            mock_content = MagicMock()
            mock_content.text = "File content"
            mock_content.type = "text"

            mock_result = MagicMock()
            mock_result.content = [mock_content]
            mock_result.isError = False
            mock_result.error = None

            mock_session.call_tool.return_value = mock_result

            # Manually patch and restore the session property
            original_session = StdioTransport.__dict__.get('session')
            mock_session_prop = PropertyMock(return_value=mock_session)
            StdioTransport.session = mock_session_prop
            try:
                # Connect first
                await client.connect()

                result = await client.call_tool("read_file", {"path": "/test.txt"})

                assert result is not None
                mock_session.call_tool.assert_awaited_once_with("read_file", {"path": "/test.txt"})
            finally:
                # Restore original property
                if original_session is not None:
                    StdioTransport.session = original_session
                else:
                    del StdioTransport.session

    @pytest.mark.asyncio
    async def test_mcp_client_connect_disconnect(self):
        """Test MCPClient connect and disconnect."""
        from mcp_orchestrator.mcp.client import MCPClient
        from mcp_orchestrator.mcp.transport import StdioTransport

        transport = StdioTransport(command="echo", args=["hello"])
        client = MCPClient(transport)

        with patch.object(transport, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(transport, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
                mock_connect.return_value = MagicMock()

                await client.connect()
                mock_connect.assert_awaited_once()

                await client.disconnect()
                mock_disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mcp_client_context_manager(self):
        """Test MCPClient as async context manager."""
        from mcp_orchestrator.mcp.client import MCPClient
        from mcp_orchestrator.mcp.transport import StdioTransport

        transport = StdioTransport(command="echo", args=["hello"])

        with patch.object(transport, 'connect', new_callable=AsyncMock) as mock_connect:
            with patch.object(transport, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
                mock_connect.return_value = MagicMock()

                async with MCPClient(transport) as client:
                    assert client.transport is transport

                mock_connect.assert_awaited_once()
                mock_disconnect.assert_awaited_once()
