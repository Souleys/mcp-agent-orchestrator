"""Tests for Tor Transport."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import subprocess


class TestTorTransport:
    """Tests for TorTransport."""

    def test_tor_transport_starts_socat(self, monkeypatch):
        """Test that TorTransport starts socat process."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen = MagicMock(return_value=mock_process)

        with patch("mcp_orchestrator.transport.tor.subprocess.Popen", mock_popen):
            with patch("mcp_orchestrator.transport.tor.time.sleep"):  # Don't sleep in tests
                transport.ensure_tunnel()

        assert transport.is_healthy() is True
        mock_popen.assert_called_once()

    def test_tor_transport_get_base_url(self):
        """Test that get_base_url returns correct URL."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        assert transport.get_base_url() == "http://127.0.0.1:5080/api/v1"

    def test_tor_transport_disabled_returns_none(self):
        """Test that disabled TorTransport returns None for base URL."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=False, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        assert transport.get_base_url() is None

    @pytest.mark.asyncio
    async def test_tor_transport_health_check(self):
        """Test TorTransport health check."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        # Mock the HTTP request - patch AsyncClient (which is used as async context manager)
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        # Mock process as running
        transport._process = MagicMock()
        transport._process.poll.return_value = None

        with patch("mcp_orchestrator.transport.tor.httpx.AsyncClient", return_value=mock_client):
            result = await transport.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_tor_transport_health_check_failure(self):
        """Test TorTransport health check failure."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection refused")

        transport._process = MagicMock()
        transport._process.poll.return_value = None

        with patch("mcp_orchestrator.transport.tor.httpx.AsyncClient", return_value=mock_client):
            result = await transport.health_check()
            assert result is False

    def test_tor_transport_shutdown(self):
        """Test TorTransport shutdown kills socat process."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        transport._process = mock_process

        transport.shutdown()

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_tor_transport_shutdown_force_kill(self):
        """Test TorTransport shutdown force kills on timeout."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        # Use subprocess.TimeoutExpired which is what the code catches
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("wait", 5), None]
        transport._process = mock_process

        transport.shutdown()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_process.wait.call_count == 2

    @pytest.mark.asyncio
    async def test_tor_transport_auto_restart(self):
        """Test TorTransport auto-restart on process failure."""
        from mcp_orchestrator.transport.tor import TorTransport
        from mcp_orchestrator.config import TorConfig

        cfg = TorConfig(enabled=True, socks_port=9050, tunnel_port=5080)
        transport = TorTransport(cfg)

        # Start with a running process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        transport._process = mock_process

        # Simulate process dying
        mock_process.poll.return_value = 1  # Process exited

        with patch("mcp_orchestrator.transport.tor.subprocess.Popen") as mock_popen:
            new_process = MagicMock()
            new_process.poll.return_value = None
            mock_popen.return_value = new_process

            # Also mock health_check to return True
            with patch.object(transport, "health_check", new_callable=AsyncMock) as mock_health:
                mock_health.return_value = True
                with patch("mcp_orchestrator.transport.tor.time.sleep"):
                    await transport.ensure_tunnel_async()

        assert transport._process is new_process
        mock_popen.assert_called_once()
