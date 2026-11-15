"""Configuration models and loader for MCP Agent Orchestrator."""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    """Application configuration."""
    data_dir: str = "~/.local/share/mcp-orchestrator"
    log_level: str = "INFO"


class TorConfig(BaseModel):
    """Tor configuration."""
    enabled: bool = True
    socks_port: int = 9050
    tunnel_port: int = 5080


class ProviderConfig(BaseModel):
    """Provider configuration."""
    name: str
    type: str
    base_url: str
    api_key: str
    tor_required: bool = False


class MCPServerConfig(BaseModel):
    """MCP Server configuration."""
    name: str
    command: List[str]
    args: List[str] = Field(default_factory=list)
    env: dict = Field(default_factory=dict)
    transport: str = "stdio"


class Config(BaseSettings):
    """Main configuration class."""
    app: AppConfig = Field(default_factory=AppConfig)
    tor: TorConfig = Field(default_factory=TorConfig)
    providers: List[ProviderConfig] = Field(default_factory=list)
    mcp_servers: List[MCPServerConfig] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file with environment variable expansion."""
        import yaml
        import os

        def expand_env_vars(obj):
            """Recursively expand environment variables in config."""
            if isinstance(obj, str):
                return os.path.expandvars(obj)
            elif isinstance(obj, dict):
                return {k: expand_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [expand_env_vars(item) for item in obj]
            return obj

        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)

        if raw_config is None:
            raw_config = {}

        expanded_config = expand_env_vars(raw_config)
        return cls(**expanded_config)
