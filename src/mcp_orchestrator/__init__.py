"""MCP Agent Orchestrator - Multi-agent orchestration with MCP, Tor, and DarkRouter."""

from .config import (
    AppConfig,
    Config,
    MCPServerConfig,
    ProviderConfig,
    TorConfig,
)
from .constants import (
    DB_FILE_NAME,
    DEFAULT_CONFIG_PATH,
    DEFAULT_LOG_LEVEL,
    DEFAULT_TOR_SOCKS_PORT,
    DEFAULT_TOR_TUNNEL_PORT,
    DARKROUTER_ONION,
    HEALTH_ENDPOINT,
)

__version__ = "0.1.0"

__all__ = [
    # Config
    "Config",
    "AppConfig",
    "TorConfig",
    "ProviderConfig",
    "MCPServerConfig",
    # Constants
    "DEFAULT_CONFIG_PATH",
    "DARKROUTER_ONION",
    "HEALTH_ENDPOINT",
    "DEFAULT_TOR_SOCKS_PORT",
    "DEFAULT_TOR_TUNNEL_PORT",
    "DB_FILE_NAME",
    "DEFAULT_LOG_LEVEL",
    # Version
    "__version__",
]
