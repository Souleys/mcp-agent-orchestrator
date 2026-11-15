"""Provider abstraction layer for MCP Agent Orchestrator."""

from mcp_orchestrator.providers.base import Provider, BaseProvider
from mcp_orchestrator.providers.models import (
    ModelInfo,
    ModelCapabilities,
    ChatMessage,
    ChatCompletionResult,
    StreamChunk,
    TokenizeResult,
    UploadResult,
    HealthCheckResult,
)
from mcp_orchestrator.providers.registry import ProviderRegistry
from mcp_orchestrator.providers.darkrouter import DarkRouterProvider
from mcp_orchestrator.providers.openai_compat import OpenAICompatibleProvider, AnthropicProvider, OllamaProvider

__all__ = [
    "Provider",
    "BaseProvider",
    "ProviderRegistry",
    "DarkRouterProvider",
    "OpenAICompatibleProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "ModelInfo",
    "ModelCapabilities",
    "ChatMessage",
    "ChatCompletionResult",
    "StreamChunk",
    "TokenizeResult",
    "UploadResult",
    "HealthCheckResult",
]