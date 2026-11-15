"""Tests for MCP transport layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestStdioTransport:
    """Tests for StdioTransport."""

    @pytest.mark.asyncio
    async def test_stdio_transport_connects(self):
        """Test that StdioTransport can connect."""
        from mcp_orchestrator.mcp.transport import StdioTransport
        transport = StdioTransport(command="echo", args=["hello"])

        with patch("mcp_orchestrator.mcp.transport.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            with patch("mcp_orchestrator.mcp.transport.ClientSession", return_value=mock_session):
                session = await transport.connect()
                assert session is mock_session
                assert transport.session is mock_session
                mock_session.initialize.assert_awaited_once()
                await transport.disconnect()
                mock_session.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stdio_transport_initializes_session(self):
        """Test that StdioTransport initializes MCP session."""
        from mcp_orchestrator.mcp.transport import StdioTransport
        transport = StdioTransport(command="python", args=["-m", "mcp.server.test"])

        with patch("mcp_orchestrator.mcp.transport.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            with patch("mcp_orchestrator.mcp.transport.ClientSession", return_value=mock_session):
                session = await transport.connect()
                assert session is mock_session
                mock_session.initialize.assert_awaited_once()
                await transport.disconnect()

    @pytest.mark.asyncio
    async def test_stdio_transport_disconnects(self):
        """Test that StdioTransport can disconnect."""
        from mcp_orchestrator.mcp.transport import StdioTransport
        transport = StdioTransport(command="echo", args=["hello"])

        with patch("mcp_orchestrator.mcp.transport.stdio_client") as mock_stdio:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            with patch("mcp_orchestrator.mcp.transport.ClientSession", return_value=mock_session):
                await transport.connect()
                await transport.disconnect()
                mock_session.__aexit__.assert_awaited_once()


class TestSSETransport:
    """Tests for SSETransport."""

    @pytest.mark.asyncio
    async def test_sse_transport_connects(self):
        """Test that SSETransport can connect."""
        from mcp_orchestrator.mcp.transport import SSETransport
        transport = SSETransport(url="http://localhost:8080/sse")

        with patch("mcp_orchestrator.mcp.transport.sse_client") as mock_sse:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_sse.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            with patch("mcp_orchestrator.mcp.transport.ClientSession", return_value=mock_session):
                session = await transport.connect()
                assert session is mock_session
                assert transport.session is mock_session
                mock_session.initialize.assert_awaited_once()
                await transport.disconnect()
                mock_session.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sse_transport_disconnects(self):
        """Test that SSETransport can disconnect."""
        from mcp_orchestrator.mcp.transport import SSETransport
        transport = SSETransport(url="http://localhost:8080/sse")

        with patch("mcp_orchestrator.mcp.transport.sse_client") as mock_sse:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_sse.return_value.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock(return_value=None)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            with patch("mcp_orchestrator.mcp.transport.ClientSession", return_value=mock_session):
                await transport.connect()
                await transport.disconnect()
                mock_session.__aexit__.assert_awaited_once()


class TestMCPTransportProtocol:
    """Tests for MCPTransport protocol compliance."""

    def test_transport_protocol_exists(self):
        """Test that MCPTransport protocol is defined."""
        from mcp_orchestrator.mcp.transport import MCPTransport
        assert hasattr(MCPTransport, "connect")
        assert hasattr(MCPTransport, "disconnect")
        assert hasattr(MCPTransport, "list_tools")
        assert hasattr(MCPTransport, "call_tool")
        assert hasattr(MCPTransport, "session")
