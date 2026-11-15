"""Providers/MCP panel for managing connections."""

from __future__ import annotations

from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button, DataTable, TabbedContent, TabPane, Label
from textual.message import Message
from textual.reactive import reactive


class ProvidersPanel(Vertical):
    """Panel for managing provider and MCP server connections."""

    DEFAULT_CSS = """
    ProvidersPanel {
        background: $surface;
        border: solid $primary;
        padding: 1;
        overflow: auto;
    }
    .status-connected {
        color: $success;
    }
    .status-disconnected {
        color: $error;
    }
    .status-connecting {
        color: $warning;
    }
    .action-buttons {
        height: 3;
        margin-top: 1;
    }
    .action-buttons Button {
        margin-right: 1;
    }
    """

    providers_data: reactive[list[dict]] = reactive([])
    mcp_servers_data: reactive[list[dict]] = reactive([])

    class RefreshProvidersRequested(Message):
        """Event sent when provider refresh is requested."""
        pass

    class RefreshMCPRequested(Message):
        """Event sent when MCP refresh is requested."""
        pass

    class TestProviderRequested(Message):
        """Event sent when provider test is requested."""
        def __init__(self, provider_name: str) -> None:
            self.provider_name = provider_name
            super().__init__()

    class ReconnectMCPRequested(Message):
        """Event sent when MCP reconnect is requested."""
        def __init__(self, server_name: str) -> None:
            self.server_name = server_name
            super().__init__()

    class ViewToolsRequested(Message):
        """Event sent when view tools is requested."""
        def __init__(self, server_name: str) -> None:
            self.server_name = server_name
            super().__init__()

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Providers", id="tab-providers"):
                yield DataTable(id="providers-table", cursor_type="row")
                with Horizontal(classes="action-buttons"):
                    yield Button("Refresh", id="btn-refresh-providers", variant="primary")
                    yield Button("Test Connection", id="btn-test-provider", variant="default")

            with TabPane("MCP Servers", id="tab-mcp"):
                yield DataTable(id="mcp-table", cursor_type="row")
                with Horizontal(classes="action-buttons"):
                    yield Button("Refresh", id="btn-refresh-mcp", variant="primary")
                    yield Button("Reconnect", id="btn-reconnect-mcp", variant="default")
                    yield Button("View Tools", id="btn-view-tools", variant="default")

    def on_mount(self) -> None:
        """Initialize tables."""
        providers_table = self.query_one("#providers-table", DataTable)
        providers_table.add_columns("Name", "Type", "Status", "Models", "Actions")

        mcp_table = self.query_one("#mcp-table", DataTable)
        mcp_table.add_columns("Name", "Transport", "Status", "Tools", "Actions")

        self._refresh_providers_table()
        self._refresh_mcp_table()

    def watch_providers_data(self, data: list[dict]) -> None:
        """Update providers table when data changes."""
        self._refresh_providers_table()

    def watch_mcp_servers_data(self, data: list[dict]) -> None:
        """Update MCP table when data changes."""
        self._refresh_mcp_table()

    def _refresh_providers_table(self) -> None:
        """Refresh the providers table."""
        try:
            table = self.query_one("#providers-table", DataTable)
            table.clear()
            for provider in self.providers_data:
                status_text = "● Connected" if provider.get("healthy") else "○ Disconnected"
                models_count = len(provider.get("models", []))
                table.add_row(
                    provider.get("name", ""),
                    provider.get("type", ""),
                    status_text,
                    str(models_count),
                    "Test",
                    key=provider.get("name", "")
                )
        except Exception:
            pass  # Table not ready yet

    def _refresh_mcp_table(self) -> None:
        """Refresh the MCP servers table."""
        try:
            table = self.query_one("#mcp-table", DataTable)
            table.clear()
            for server in self.mcp_servers_data:
                status_text = "● Connected" if server.get("connected") else "○ Disconnected"
                tools_count = len(server.get("tools", []))
                table.add_row(
                    server.get("name", ""),
                    server.get("transport", ""),
                    status_text,
                    str(tools_count),
                    "Reconnect",
                    key=server.get("name", "")
                )
        except Exception:
            pass  # Table not ready yet

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-refresh-providers":
            self.post_message(self.RefreshProvidersRequested())
        elif event.button.id == "btn-test-provider":
            table = self.query_one("#providers-table", DataTable)
            if table.cursor_row >= 0:
                row_key = table.get_row_at(table.cursor_row).key
                self.post_message(self.TestProviderRequested(str(row_key)))
        elif event.button.id == "btn-refresh-mcp":
            self.post_message(self.RefreshMCPRequested())
        elif event.button.id == "btn-reconnect-mcp":
            table = self.query_one("#mcp-table", DataTable)
            if table.cursor_row >= 0:
                row_key = table.get_row_at(table.cursor_row).key
                self.post_message(self.ReconnectMCPRequested(str(row_key)))
        elif event.button.id == "btn-view-tools":
            table = self.query_one("#mcp-table", DataTable)
            if table.cursor_row >= 0:
                row_key = table.get_row_at(table.cursor_row).key
                self.post_message(self.ViewToolsRequested(str(row_key)))

    def update_providers(self, providers: list[dict]) -> None:
        """Update providers data."""
        self.providers_data = providers

    def update_mcp_servers(self, servers: list[dict]) -> None:
        """Update MCP servers data."""
        self.mcp_servers_data = servers