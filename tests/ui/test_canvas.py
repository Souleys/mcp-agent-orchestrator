"""Tests for Canvas widget."""

from __future__ import annotations

import pytest

from mcp_orchestrator.ui.app import OrchestratorApp
from mcp_orchestrator.ui.canvas import Canvas, NodeData
from mcp_orchestrator.ui.palette import Palette


@pytest.mark.asyncio
async def test_canvas_add_node():
    """Test adding a node to the canvas."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        canvas = app.query_one(Canvas)
        palette = app.query_one(Palette)

        # Post a node add request from palette
        palette.post_message(Palette.NodeAddRequested("agent", "Test Agent"))

        # Wait for the event to be processed
        await pilot.pause()

        # Check that node was added
        assert len(canvas.nodes) == 1
        node = list(canvas.nodes.values())[0]
        assert node.node_type == "agent"
        assert node.label == "Test Agent"


@pytest.mark.asyncio
async def test_canvas_node_selection():
    """Test selecting a node on the canvas."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        canvas = app.query_one(Canvas)
        palette = app.query_one(Palette)

        # Add a node
        palette.post_message(Palette.NodeAddRequested("agent", "Test Agent"))
        await pilot.pause()

        node_id = list(canvas.nodes.keys())[0]

        # Click on the node widget to select it
        node_widget = canvas.query_one(f"#node-{node_id}")
        node_widget.post_message(node_widget.NodeSelected(node_id))
        await pilot.pause()

        # Check that node is selected
        assert canvas._selected_node == node_id


@pytest.mark.asyncio
async def test_canvas_delete_node():
    """Test deleting a node from the canvas."""
    app = OrchestratorApp()
    async with app.run_test() as pilot:
        canvas = app.query_one(Canvas)
        palette = app.query_one(Palette)

        # Add a node
        palette.post_message(Palette.NodeAddRequested("agent", "Test Agent"))
        await pilot.pause()

        node_id = list(canvas.nodes.keys())[0]

        # Select the node
        node_widget = canvas.query_one(f"#node-{node_id}")
        node_widget.post_message(node_widget.NodeSelected(node_id))
        await pilot.pause()

        # Delete the node (simulate Delete key)
        canvas.delete_node(node_id)
        await pilot.pause()

        # Check that node was deleted
        assert len(canvas.nodes) == 0


@pytest.mark.asyncio
async def test_canvas_workflow_data():
    """Test exporting workflow data from canvas."""
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

        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2