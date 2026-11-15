"""Constants for MCP Agent Orchestrator."""

from pathlib import Path

# Default configuration file path
DEFAULT_CONFIG_PATH = Path("~/.config/mcp-orchestrator/config.yaml").expanduser()

# DarkRouter onion address (placeholder - actual address from DarkRouter docs)
DARKROUTER_ONION = "http://darkrouter7l4j6m4h.onion"

# Health check endpoint
HEALTH_ENDPOINT = "/health"

# Default ports
DEFAULT_TOR_SOCKS_PORT = 9050
DEFAULT_TOR_TUNNEL_PORT = 5080

# Database file name
DB_FILE_NAME = "orchestrator.db"

# Default log level
DEFAULT_LOG_LEVEL = "INFO"
