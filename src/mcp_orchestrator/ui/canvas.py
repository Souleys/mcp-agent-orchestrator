"""Canvas panel for visual workflow editing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from textual.containers import Container
from textual.widgets import Static
from textual.message import Message
from textual.reactive import reactive


@dataclass
class NodeData:
    """Data for a node on the canvas."""
    id: str
    node_type: str
    label: str
    x: int = 100
    y: int = 100
    config: dict = field(default_factory=dict)


class NodeWidget(Static):
    """A node widget on the canvas."""

    DEFAULT_CSS = """
    NodeWidget {
        width: 20;
        height: 7;
        border: solid $primary;
        background: $surface;
        padding: 1;
        margin: 1;
    }
    NodeWidget:hover {
        border: solid $accent;
    }
    NodeWidget.selected {
        border: double $accent;
        background: $boost;
    }
    .node-header {
        text-style: bold;
        text-align: center;
        color: $primary;
    }
    .node-type {
        text-align: center;
        color: $text-muted;
        text-style: dim;
    }
    """

    def __init__(self, node_data: NodeData) -> None:
        super().__init__(id=f"node-{node_data.id}")
        self.node_data = node_data
        self.selected = False

    def compose(self) -> ComposeResult:
        yield Static(self.node_data.label, classes="node-header")
        yield Static(self.node_data.node_type.upper(), classes="node-type")

    def on_click(self, event) -> None:
        """Select this node on click."""
        self.post_message(self.NodeSelected(self.node_data.id))

    class NodeSelected(Message):
        """Event sent when a node is selected."""
        def __init__(self, node_id: str) -> None:
            self.node_id = node_id
            super().__init__()


class Canvas(Container):
    """Canvas widget for visual workflow editing."""

    DEFAULT_CSS = """
    Canvas {
        background: $surface-darken-1;
        border: solid $primary;
        overflow: auto;
    }
    Canvas:focus {
        border: solid $accent;
    }
    """

    nodes: reactive[dict[str, NodeData]] = reactive({}, repaint=True)
    edges: reactive[list[tuple[str, str]]] = reactive([], repaint=True)

    class NodeAdded(Message):
        """Event sent when a node is added to the canvas."""
        def __init__(self, node_data: NodeData) -> None:
            self.node_data = node_data
            super().__init__()

    class NodeMoved(Message):
        """Event sent when a node is moved."""
        def __init__(self, node_id: str, x: int, y: int) -> None:
            self.node_id = node_id
            self.x = x
            self.y = y
            super().__init__()

    class NodeDeleted(Message):
        """Event sent when a node is deleted."""
        def __init__(self, node_id: str) -> None:
            self.node_id = node_id
            super().__init__()

    class EdgeAdded(Message):
        """Event sent when an edge is added."""
        def __init__(self, source: str, target: str) -> None:
            self.source = source
            self.target = target
            super().__init__()

    class NodeSelected(Message):
        """Event sent when a node is selected."""
        def __init__(self, node_id: str) -> None:
            self.node_id = node_id
            super().__init__()

    def __init__(self, id: str | None = None) -> None:
        super().__init__(id=id)
        self._node_widgets: dict[str, NodeWidget] = {}
        self._selected_node: str | None = None
        self._connecting_from: str | None = None
        self._next_position = (100, 100)

    def compose(self) -> ComposeResult:
        yield Static(id="canvas-area")

    def on_mount(self) -> None:
        """Set up the canvas."""
        self.can_focus = True

    def watch_nodes(self, nodes: dict[str, NodeData]) -> None:
        """Update node widgets when nodes change."""
        # Remove widgets for deleted nodes
        for node_id in list(self._node_widgets.keys()):
            if node_id not in nodes:
                widget = self._node_widgets.pop(node_id)
                widget.remove()

        # Add or update widgets
        for node_id, node_data in nodes.items():
            if node_id in self._node_widgets:
                widget = self._node_widgets[node_id]
                widget.node_data = node_data
                widget.styles.offset = (node_data.x, node_data.y)
                # Update label
                header = widget.query_one(".node-header", Static)
                header.update(node_data.label)
            else:
                widget = NodeWidget(node_data)
                widget.styles.offset = (node_data.x, node_data.y)
                self._node_widgets[node_id] = widget
                self.mount(widget)

    def on_palette_node_add_requested(self, event: "Palette.NodeAddRequested") -> None:
        """Handle node add request from palette."""
        node_type = event.node_type
        label = event.label
        node_id = f"{node_type}-{len(self.nodes)}"

        x, y = self._next_position
        self._next_position = (x + 250, y)

        node_data = NodeData(
            id=node_id,
            node_type=node_type,
            label=label,
            x=x,
            y=y,
        )

        self.nodes = {**self.nodes, node_id: node_data}
        self.post_message(self.NodeAdded(node_data))

    def on_key(self, event) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "delete" and self._selected_node:
            self.delete_node(self._selected_node)
        elif event.key == "escape":
            self._selected_node = None
            self._connecting_from = None
            # Update selection visuals
            for widget in self._node_widgets.values():
                widget.selected = False
                widget.refresh()

    def on_node_widget_node_selected(self, event: NodeWidget.NodeSelected) -> None:
        """Handle node selection."""
        self._selected_node = event.node_id
        # Update visuals
        for nid, widget in self._node_widgets.items():
            widget.selected = (nid == event.node_id)
            widget.refresh()
        self.post_message(self.NodeSelected(event.node_id))

    def delete_node(self, node_id: str) -> None:
        """Delete a node and its edges."""
        if node_id in self.nodes:
            new_nodes = {k: v for k, v in self.nodes.items() if k != node_id}
            self.nodes = new_nodes
            new_edges = [(s, t) for s, t in self.edges if s != node_id and t != node_id]
            self.edges = new_edges
            self.post_message(self.NodeDeleted(node_id))

    def add_edge(self, source: str, target: str) -> None:
        """Add an edge between two nodes."""
        if source != target and (source, target) not in self.edges:
            self.edges = [*self.edges, (source, target)]
            self.post_message(self.EdgeAdded(source, target))

    def get_workflow_data(self) -> dict[str, Any]:
        """Export workflow data for saving."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.node_type,
                    "label": node.label,
                    "x": node.x,
                    "y": node.y,
                    "config": node.config,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {"source": s, "target": t}
                for s, t in self.edges
            ],
        }