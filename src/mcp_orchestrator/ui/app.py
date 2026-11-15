"""Main TUI application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static

from mcp_orchestrator.ui.palette import Palette
from mcp_orchestrator.ui.canvas import Canvas
from mcp_orchestrator.ui.inspector import Inspector
from mcp_orchestrator.ui.console import Console
from mcp_orchestrator.ui.providers_panel import ProvidersPanel


class OrchestratorApp(App):
    """Main orchestrator TUI application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #left-panel {
        width: 30;
        border: solid $primary;
        padding: 1;
    }

    #center-panel {
        width: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #right-panel {
        width: 40;
        border: solid $primary;
        padding: 1;
    }

    #console-panel {
        height: 20;
        border: solid $primary;
        padding: 1;
    }

    #providers-panel {
        width: 50;
        border: solid $primary;
        padding: 1;
        display: none;
    }

    #providers-panel.visible {
        display: block;
    }

    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("ctrl+e", "toggle_providers", "Toggle Providers"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._providers_visible = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            # Left panel - Palette
            with Vertical(id="left-panel"):
                yield Static("Palette", classes="panel-title")
                yield Palette(id="palette")

            # Center panel - Canvas
            with Vertical(id="center-panel"):
                yield Static("Canvas", classes="panel-title")
                yield Canvas(id="canvas")

            # Right panel - Inspector
            with Vertical(id="right-panel"):
                yield Static("Inspector", classes="panel-title")
                yield Inspector(id="inspector")

            # Providers panel (collapsible, on far right)
            with Vertical(id="providers-panel"):
                yield Static("Providers / MCP", classes="panel-title")
                yield ProvidersPanel(id="providers")

        # Bottom panel - Console
        with Container(id="console-panel"):
            yield Static("Console", classes="panel-title")
            yield Console(id="console")

        yield Footer()

    def action_toggle_providers(self) -> None:
        """Toggle the providers panel visibility."""
        self._providers_visible = not self._providers_visible
        providers_panel = self.query_one("#providers-panel")
        if self._providers_visible:
            providers_panel.add_class("visible")
        else:
            providers_panel.remove_class("visible")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def on_palette_node_add_requested(self, event: Palette.NodeAddRequested) -> None:
        """Forward palette node add requests to the canvas."""
        canvas = self.query_one(Canvas)
        canvas.post_message(event)
