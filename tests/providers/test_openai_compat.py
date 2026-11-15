# tests/providers/test_openai_compat.py
import pytest
import httpx
import respx


def test_openai_provider_chat_completion():
    from mcp_orchestrator.providers.openai_compat import OpenAICompatibleProvider
    from mcp_orchestrator.config import ProviderConfig
    from mcp_orchestrator.providers.models import ChatMessage

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(return_value=httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "Hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }))

        test_client = httpx.Client(base_url="https://api.openai.com/v1")

        provider = OpenAICompatibleProvider(
            ProviderConfig(name="openai", type="openai", base_url="https://api.openai.com/v1", api_key="sk-test"),
            client=test_client
        )
        result = provider.chat_completion(model="gpt-4o", messages=[ChatMessage(role="user", content="Hi")])
        assert result.choices[0].message.content == "Hello"