"""Provider registry for managing multiple model providers."""

import logging
from typing import Dict, List, Optional, Type
from mcp_orchestrator.config import ProviderConfig
from mcp_orchestrator.providers.base import BaseProvider
from mcp_orchestrator.providers.darkrouter import DarkRouterProvider
from mcp_orchestrator.providers.openai_compat import OpenAICompatibleProvider, AnthropicProvider, OllamaProvider
from mcp_orchestrator.providers.models import ModelInfo


# Map of provider type to provider class
PROVIDER_CLASSES: Dict[str, Type[BaseProvider]] = {
    "darkrouter": DarkRouterProvider,
    "openai": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openai_compatible": OpenAICompatibleProvider,
}


logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for creating and managing provider instances."""

    def __init__(self, configs: List[ProviderConfig]):
        self._configs = {config.name: config for config in configs}
        self._providers: Dict[str, BaseProvider] = {}
        self._model_cache: Dict[str, List[ModelInfo]] = {}

    def get(self, name: str) -> Optional[BaseProvider]:
        """Get a provider by name, creating it lazily if needed."""
        if name in self._providers:
            return self._providers[name]

        config = self._configs.get(name)
        if config is None:
            return None

        provider_class = PROVIDER_CLASSES.get(config.type)
        if provider_class is None:
            raise ValueError(f"Unknown provider type: {config.type}")

        provider = provider_class(config)
        self._providers[name] = provider
        return provider

    def get_all(self) -> List[BaseProvider]:
        """Get all configured providers, skipping any that fail to initialize."""
        providers = []
        for name in self._configs:
            try:
                provider = self.get(name)
                if provider is not None:
                    providers.append(provider)
            except Exception as e:
                # Log the error but continue with other providers
                logger.warning("Failed to initialize provider '%s': %s", name, e)
        return providers

    def discover_models(self) -> Dict[str, List[ModelInfo]]:
        """Discover models from all providers and cache capabilities."""
        for name, config in self._configs.items():
            provider = self.get(name)
            if provider:
                try:
                    models = provider.list_models()
                    self._model_cache[name] = models
                except Exception as e:
                    # Log the error but continue with other providers
                    logger.warning("Failed to discover models for provider '%s': %s", name, e)
                    self._model_cache[name] = []
        return self._model_cache

    def get_models(self, provider_name: str) -> List[ModelInfo]:
        """Get cached models for a provider."""
        if provider_name not in self._model_cache:
            self.discover_models()
        return self._model_cache.get(provider_name, [])