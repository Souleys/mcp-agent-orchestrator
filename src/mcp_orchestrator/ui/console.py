"""Console panel for streaming logs and output."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog, Button, Static
from textual.message import Message
from textual.reactive import reactive


class Console(Vertical):
    """Console widget for streaming output with color-coded messages."""

    DEFAULT_CSS = """
    Console {
        background: $surface-darken-2;
        border: solid $primary;
        padding: 0;
    }
    #log {
        height: 1fr;
        border: none;
        background: transparent;
    }
    .controls {
        height: 3;
        dock: bottom;
        padding: 0 1;
    }
    .controls Button {
        margin-right: 1;
    }
    """

    paused: reactive[bool] = reactive(False)
    auto_scroll: reactive[bool] = reactive(True)

    class ClearRequested(Message):
        """Event sent when clear is requested."""
        pass

    class PauseToggled(Message):
        """Event sent when pause state changes."""
        def __init__(self, paused: bool) -> None:
            self.paused = paused
            super().__init__()

    def compose(self) -> ComposeResult:
        yield RichLog(id="log", markup=True, highlight=True, auto_scroll=True)
        with Static(classes="controls"):
            yield Button("Pause", id="btn-pause", variant="default")
            yield Button("Clear", id="btn-clear", variant="default")
            yield Button("Auto-scroll", id="btn-autoscroll", variant="default")

    def on_mount(self) -> None:
        """Initialize the console."""
        self.log_widget = self.query_one("#log", RichLog)

    def write_token(self, token: str, node_id: str = "") -> None:
        """Write a streaming token (dimmed)."""
        if not self.paused:
            prefix = f"[dim]{node_id} ›[/dim] " if node_id else ""
            self.log_widget.write(f"{prefix}[dim]{token}[/dim]")

    def write_tool_call(self, tool_name: str, args: str, node_id: str = "") -> None:
        """Write a tool call (yellow)."""
        if not self.paused:
            prefix = f"[yellow]{node_id} ›[/yellow] " if node_id else "[yellow]›[/yellow] "
            self.log_widget.write(f"{prefix}[bold yellow]Tool Call:[/bold yellow] {tool_name}({args})")

    def write_tool_result(self, tool_name: str, result: str, node_id: str = "") -> None:
        """Write a tool result (green)."""
        if not self.paused:
            prefix = f"[green]{node_id} ›[/green] " if node_id else "[green]›[/green] "
            display_result = result[:500] + ("..." if len(result) > 500 else "")
            self.log_widget.write(f"{prefix}[bold green]Tool Result:[/bold green] {tool_name} → {display_result}")

    def write_node_start(self, node_id: str, label: str, provider: str, model: str) -> None:
        """Write node start message."""
        if not self.paused:
            self.log_widget.write(f"[bold cyan]▶ Node Started:[/bold cyan] {label} ({node_id}) via {provider}/{model}")

    def write_node_complete(self, node_id: str, label: str, output: str) -> None:
        """Write node completion message."""
        if not self.paused:
            display_output = output[:200] + ("..." if len(output) > 200 else "")
            self.log_widget.write(f"[bold green]✓ Node Complete:[/bold green] {label} ({node_id}) → {display_output}")

    def write_node_error(self, node_id: str, label: str, error: str) -> None:
        """Write node error message."""
        if not self.paused:
            self.log_widget.write(f"[bold red]✗ Node Error:[/bold red] {label} ({node_id}) → {error}")

    def write_workflow_complete(self, output: str) -> None:
        """Write workflow completion message."""
        if not self.paused:
            display_output = output[:300] + ("..." if len(output) > 300 else "")
            self.log_widget.write(f"[bold magenta]✓ Workflow Complete:[/bold magenta] {display_output}")

    def write_info(self, message: str) -> None:
        """Write an info message."""
        if not self.paused:
            self.log_widget.write(f"[blue]ℹ[/blue] {message}")

    def write_warning(self, message: str) -> None:
        """Write a warning message."""
        if not self.paused:
            self.log_widget.write(f"[yellow]⚠[/yellow] {message}")

    def write_error(self, message: str) -> None:
        """Write an error message."""
        if not self.paused:
            self.log_widget.write(f"[red]✗[/red] {message}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-pause":
            self.paused = not self.paused
            event.button.label = "Resume" if self.paused else "Pause"
            self.post_message(self.PauseToggled(self.paused))
        elif event.button.id == "btn-clear":
            self.log_widget.clear()
            self.post_message(self.ClearRequested())
        elif event.button.id == "btn-autoscroll":
            self.auto_scroll = not self.auto_scroll
            self.log_widget.auto_scroll = self.auto_scroll
            event.button.label = "Auto-scroll: ON" if self.auto_scroll else "Auto-scroll: OFF"

    def clear(self) -> None:
        """Clear the console."""
        self.log_widget.clear()