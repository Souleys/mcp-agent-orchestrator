"""Palette panel for node types (click to add)."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Button, Static
from textual.message import Message


class Palette(Vertical):
    """Palette widget with clickable node type buttons."""

    class NodeAddRequested(Message):
        """Event sent when a node type is requested to be added."""

        def __init__(self, node_type: str, label: str) -> None:
            self.node_type = node_type
            self.label = label
            super().__init__()

    NODE_TYPES = [
        ("agent", "Agent", "AI agent node"),
        ("tool", "Tool", "MCP tool call node"),
        ("conditional", "Conditional", "Branch based on condition"),
        ("human", "Human Input", "Wait for human input"),
        ("transform", "Transform", "Data transformation"),
    ]

    def compose(self) -> ComposeResult:
        for node_type, label, description in self.NODE_TYPES:
            btn = Button(f"{label}\n{description}", id=f"palette-{node_type}", classes="palette-item")
            btn.tooltip = f"Click to add {label} node"
            yield btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press - request node addition."""
        if event.button.id and event.button.id.startswith("palette-"):
            node_type = event.button.id.replace("palette-", "")
            label = next((lbl for typ, lbl, _ in self.NODE_TYPES if typ == node_type), node_type)
            self.post_message(self.NodeAddRequested(node_type, label))