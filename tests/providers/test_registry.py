# tests/providers/test_registry.py
import pytest
from mcp_orchestrator.config import ProviderConfig


def test_registry_creates_providers():
    from mcp_orchestrator.providers.registry import ProviderRegistry
    configs = [
        ProviderConfig(name="dr", type="darkrouter", base_url="http://localhost:5080/api/v1", api_key="t"),
        ProviderConfig(name="openai", type="openai", base_url="https://api.openai.com/v1", api_key="sk"),
    ]
    registry = ProviderRegistry(configs)
    assert registry.get("dr") is not None
    assert registry.get("openai") is not None
    assert registry.get("nonexistent") is None