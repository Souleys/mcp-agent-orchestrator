# tests/providers/test_darkrouter.py
import pytest
import httpx
import respx


def test_darkrouter_provider_health_check(respx_mock):
    from mcp_orchestrator.providers.darkrouter import DarkRouterProvider
    from mcp_orchestrator.config import ProviderConfig

    # Mock the health endpoint
    respx_mock.get("http://127.0.0.1:5080/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))

    # Create a test client that uses respx
    test_client = httpx.Client(base_url="http://127.0.0.1:5080", transport=respx_mock)

    provider = DarkRouterProvider(
        ProviderConfig(name="dr", type="darkrouter", base_url="http://127.0.0.1:5080/api/v1", api_key="test"),
        client=test_client
    )
    assert provider.health_check().healthy is True