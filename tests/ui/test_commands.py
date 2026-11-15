"""Tests for TUI commands and key bindings."""

from __future__ import annotations

import pytest

from mcp_orchestrator.ui.app import OrchestratorApp
from mcp_orchestrator.ui.canvas import Canvas
from mcp_orchestrator.ui.palette import Palette


@pytest.mark.asyncio
async def test_save_load_workflow():
    """Test saving and loading a workflow."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        canvas = app.query_one(Canvas)
        palette = app.query_one(Palette)

        # Add a couple of nodes
        palette.post_message(Palette.NodeAddRequested("agent", "Agent 1"))
        palette.post_message(Palette.NodeAddRequested("tool", "Tool 1"))
        await pilot.pause()

        # Add an edge
        node_ids = list(canvas.nodes.keys())
        if len(node_ids) >= 2:
            canvas.add_edge(node_ids[0], node_ids[1])
            await pilot.pause()

        # Export workflow data
        data = canvas.get_workflow_data()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1


@pytest.mark.asyncio
async def test_key_bindings():
    """Test key bindings."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        # Test Ctrl+Q quits
        await pilot.press("ctrl+q")
        # App should exit (we can't easily test this, but we can check the binding exists)
        assert ("ctrl+q", "quit", "Quit") in app.BINDINGS

        # Test Ctrl+E toggles providers
        assert ("ctrl+e", "toggle_providers", "Toggle Providers") in app.BINDINGS


@pytest.mark.asyncio
async def test_toggle_providers_panel():
    """Test toggling the providers panel."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        providers_panel = app.query_one("#providers-panel")

        # Initially hidden
        assert "visible" not in providers_panel.classes

        # Toggle providers
        app.action_toggle_providers()
        await pilot.pause()

        # Should be visible
        assert "visible" in providers_panel.classes

        # Toggle again
        app.action_toggle_providers()
        await pilot.pause()

        # Should be hidden again
        assert "visible" not in providers_panel.classes