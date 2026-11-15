"""Tests for TUI app."""

from __future__ import annotations

import pytest

from mcp_orchestrator.ui.app import OrchestratorApp


@pytest.mark.asyncio
async def test_app_startup():
    """Test that the app starts without errors."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        assert pilot.app.screen is not None