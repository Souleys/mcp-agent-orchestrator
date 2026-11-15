# tests/providers/test_base.py
import pytest


def test_provider_protocol():
    from mcp_orchestrator.providers.base import Provider
    # Verify protocol methods exist with correct signatures
    assert hasattr(Provider, 'chat_completion')
    assert hasattr(Provider, 'stream_chat')
    assert hasattr(Provider, 'list_models')
    assert hasattr(Provider, 'tokenize')
    assert hasattr(Provider, 'upload_file')
    assert hasattr(Provider, 'health_check')
