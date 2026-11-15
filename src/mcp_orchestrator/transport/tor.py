"""Tor Transport - manages socat tunnel for DarkRouter .onion access."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from typing import Optional

import httpx

from mcp_orchestrator.config import TorConfig

logger = logging.getLogger(__name__)


class TorTransport:
    """Manages socat tunnel for Tor hidden service access."""

    DARKROUTER_ONION = "drgmxvch5rr22rrqn54bszno2tvclnv4eu34gqz6vwl6ngcjyzbxz5ad.onion"

    def __init__(self, config: TorConfig) -> None:
        self.config = config
        self._process: Optional[subprocess.Popen] = None
        self._tunnel_port = config.tunnel_port
        self._socks_port = config.socks_port

    def ensure_tunnel(self) -> None:
        """Ensure socat tunnel is running, start if needed."""
        if not self.config.enabled:
            logger.info("Tor transport disabled, skipping tunnel creation")
            return

        if self._process and self._process.poll() is None:
            logger.debug("Tunnel already running")
            return

        logger.info(f"Starting socat tunnel on port {self._tunnel_port} -> {self.DARKROUTER_ONION}:80")

        # socat command: TCP4-LISTEN:5080,bind=127.0.0.1,reuseaddr,fork SOCKS4A:127.0.0.1:darkrouter.onion:80,socksport=9050
        cmd = [
            "socat",
            f"TCP4-LISTEN:{self._tunnel_port},bind=127.0.0.1,reuseaddr,fork",
            f"SOCKS4A:127.0.0.1:{self.DARKROUTER_ONION}:80,socksport={self._socks_port}",
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            # Wait a moment for socat to start
            time.sleep(1)

            if self._process.poll() is not None:
                raise RuntimeError(f"socat process exited immediately with code {self._process.poll()}")

            logger.info(f"Socat tunnel started on port {self._tunnel_port} (PID: {self._process.pid})")

        except FileNotFoundError:
            raise RuntimeError("socat not found in PATH. Please install socat to use Tor transport.")
        except Exception as e:
            logger.error(f"Failed to start socat tunnel: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if tunnel is healthy by hitting the health endpoint."""
        if not self.config.enabled:
            return True

        if not self._process or self._process.poll() is not None:
            logger.warning("Tunnel process not running")
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://127.0.0.1:{self._tunnel_port}/health")
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def get_base_url(self) -> Optional[str]:
        """Get the base URL for DarkRouter API via tunnel."""
        if not self.config.enabled:
            return None
        return f"http://127.0.0.1:{self._tunnel_port}/api/v1"

    def is_healthy(self) -> bool:
        """Synchronous health check - returns True if process is running."""
        return self._process is not None and self._process.poll() is None

    def shutdown(self) -> None:
        """Shutdown the socat tunnel gracefully."""
        if self._process and self._process.poll() is None:
            logger.info(f"Shutting down socat tunnel (PID: {self._process.pid})")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Socat did not terminate gracefully, force killing")
                self._process.kill()
                self._process.wait()
            self._process = None
            logger.info("Socat tunnel stopped")

    async def ensure_tunnel_async(self) -> None:
        """Async wrapper for ensure_tunnel with auto-restart on failure."""
        if not self.config.enabled:
            return

        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                self.ensure_tunnel()
                # Verify tunnel is actually working
                healthy = await self.health_check()
                if healthy:
                    return
                else:
                    logger.warning(f"Tunnel started but health check failed (attempt {attempt + 1})")
                    self.shutdown()
            except Exception as e:
                logger.warning(f"Tunnel start attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying tunnel start in {delay}s...")
                await asyncio.sleep(delay)
            else:
                raise RuntimeError(f"Failed to establish Tor tunnel after {max_retries} attempts")
