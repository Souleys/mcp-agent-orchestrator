"""Inspector panel for node configuration."""

from __future__ import annotations

from textual.containers import Vertical, Horizontal
from textual.widgets import (
    Static, Input, TextArea, Select, Checkbox, Button, Label
)
from textual.message import Message
from textual.reactive import reactive


class Inspector(Vertical):
    """Inspector widget for editing node properties."""

    DEFAULT_CSS = """
    Inspector {
        background: $surface;
        border: solid $primary;
        padding: 1;
        overflow: auto;
    }
    .form-row {
        height: auto;
        margin-bottom: 1;
    }
    .form-label {
        width: 14;
        text-align: right;
        padding-right: 1;
        color: $text;
    }
    .form-input {
        width: 1fr;
    }
    .section-title {
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }
    """

    current_node_id: reactive[str | None] = reactive(None)
    node_config: reactive[dict] = reactive({})

    class ConfigChanged(Message):
        """Event sent when node configuration changes."""
        def __init__(self, node_id: str, config: dict) -> None:
            self.node_id = node_id
            self.config = config
            super().__init__()

    class NodeDeleteRequested(Message):
        """Event sent when node deletion is requested."""
        def __init__(self, node_id: str) -> None:
            self.node_id = node_id
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("No node selected", id="no-selection", classes="section-title")

        # Node identity
        with Horizontal(classes="form-row", id="row-id"):
            yield Label("Node ID:", classes="form-label")
            yield Input(placeholder="Auto-generated", id="input-id", disabled=True, classes="form-input")

        with Horizontal(classes="form-row", id="row-label"):
            yield Label("Label:", classes="form-label")
            yield Input(placeholder="Node label", id="input-label", classes="form-input")

        with Horizontal(classes="form-row", id="row-type"):
            yield Label("Type:", classes="form-label")
            yield Input(placeholder="Node type", id="input-type", disabled=True, classes="form-input")

        # Model configuration
        yield Static("Model Configuration", classes="section-title")

        with Horizontal(classes="form-row", id="row-provider"):
            yield Label("Provider:", classes="form-label")
            yield Select([], id="select-provider", classes="form-input", allow_blank=True)

        with Horizontal(classes="form-row", id="row-model"):
            yield Label("Model:", classes="form-label")
            yield Select([], id="select-model", classes="form-input", allow_blank=True)

        with Horizontal(classes="form-row", id="row-fallback"):
            yield Label("Fallback:", classes="form-label")
            yield Select([], id="select-fallback", classes="form-input", allow_blank=True)

        with Horizontal(classes="form-row", id="row-temperature"):
            yield Label("Temperature:", classes="form-label")
            yield Input(placeholder="0.7", id="input-temperature", classes="form-input")
            yield Static("(0.0-2.0)", id="temp-hint", classes="form-label")

        with Horizontal(classes="form-row", id="row-max-tokens"):
            yield Label("Max Tokens:", classes="form-label")
            yield Input(placeholder="4096", id="input-max-tokens", classes="form-input")

        # System prompt
        yield Static("System Prompt", classes="section-title")
        yield TextArea(id="textarea-system-prompt", classes="form-input")

        # Tools
        yield Static("Tools", classes="section-title")
        with Horizontal(classes="form-row"):
            yield Label("MCP Tools:", classes="form-label")
            yield Static("Select from available tools", id="tools-info", classes="form-input")

        yield Checkbox("Enable Tools", id="checkbox-tools", value=True)
        yield Checkbox("Enable Vision", id="checkbox-vision", value=False)
        yield Checkbox("Enable Reasoning", id="checkbox-reasoning", value=False)

        # Conversation
        yield Static("Conversation", classes="section-title")
        with Horizontal(classes="form-row", id="row-conv-id"):
            yield Label("Conv. ID:", classes="form-label")
            yield Input(placeholder="Optional: share conversation", id="input-conv-id", classes="form-input")

        yield Checkbox("Share Conversation", id="checkbox-share-conv", value=False)

        # Actions
        yield Static("", classes="form-row")
        yield Button("Save", id="btn-save", variant="primary")
        yield Button("Delete Node", id="btn-delete", variant="error")

    def on_mount(self) -> None:
        """Initialize the inspector."""
        self._update_visibility(False)

    def watch_current_node_id(self, node_id: str | None) -> None:
        """Update inspector when node selection changes."""
        self._update_visibility(node_id is not None)
        if node_id:
            self.query_one("#no-selection", Static).update(f"Editing: {node_id}")
        else:
            self.query_one("#no-selection", Static).update("No node selected")

    def _update_visibility(self, visible: bool) -> None:
        """Show/hide form fields based on node selection."""
        for widget_id in [
            "row-id", "row-label", "row-type",
            "row-provider", "row-model", "row-fallback",
            "row-temperature", "row-max-tokens",
            "textarea-system-prompt", "tools-info",
            "checkbox-tools", "checkbox-vision", "checkbox-reasoning",
            "row-conv-id", "checkbox-share-conv",
            "btn-save", "btn-delete",
        ]:
            widget = self.query_one(f"#{widget_id}")
            widget.display = visible

    def watch_node_config(self, config: dict) -> None:
        """Update form fields when config changes."""
        if not config:
            return

        self.query_one("#input-id", Input).value = config.get("id", "")
        self.query_one("#input-label", Input).value = config.get("label", "")
        self.query_one("#input-type", Input).value = config.get("type", "")

        provider = config.get("provider", "")
        if provider:
            self.query_one("#select-provider", Select).value = provider

        model = config.get("model", "")
        if model:
            self.query_one("#select-model", Select).value = model

        fallback = config.get("fallback_model", "")
        if fallback:
            self.query_one("#select-fallback", Select).value = fallback

        temp = config.get("temperature", 0.7)
        self.query_one("#input-temperature", Input).value = str(temp)

        self.query_one("#input-max-tokens", Input).value = str(config.get("max_tokens", 4096))
        self.query_one("#textarea-system-prompt", TextArea).text = config.get("system_prompt", "")
        self.query_one("#checkbox-tools", Checkbox).value = config.get("tools_enabled", True)
        self.query_one("#checkbox-vision", Checkbox).value = config.get("vision_enabled", False)
        self.query_one("#checkbox-reasoning", Checkbox).value = config.get("reasoning_enabled", False)
        self.query_one("#input-conv-id", Input).value = config.get("conversation_id", "")
        self.query_one("#checkbox-share-conv", Checkbox).value = config.get("share_conversation", False)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "input-temperature":
            try:
                temp = float(event.value)
                if 0.0 <= temp <= 2.0:
                    self.query_one("#temp-hint", Static).update(f"(✓ {temp:.1f})")
                else:
                    self.query_one("#temp-hint", Static).update("(0.0-2.0)")
            except ValueError:
                self.query_one("#temp-hint", Static).update("(0.0-2.0)")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            self._save_config()
        elif event.button.id == "btn-delete":
            self._delete_node()

    def _save_config(self) -> None:
        """Collect form data and emit config changed event."""
        if not self.current_node_id:
            return

        try:
            temperature = float(self.query_one("#input-temperature", Input).value or "0.7")
        except ValueError:
            temperature = 0.7

        config = {
            "id": self.current_node_id,
            "label": self.query_one("#input-label", Input).value,
            "type": self.query_one("#input-type", Input).value,
            "provider": self.query_one("#select-provider", Select).value or "",
            "model": self.query_one("#select-model", Select).value or "",
            "fallback_model": self.query_one("#select-fallback", Select).value or "",
            "temperature": temperature,
            "max_tokens": int(self.query_one("#input-max-tokens", Input).value or "4096"),
            "system_prompt": self.query_one("#textarea-system-prompt", TextArea).text,
            "tools_enabled": self.query_one("#checkbox-tools", Checkbox).value,
            "vision_enabled": self.query_one("#checkbox-vision", Checkbox).value,
            "reasoning_enabled": self.query_one("#checkbox-reasoning", Checkbox).value,
            "conversation_id": self.query_one("#input-conv-id", Input).value or None,
            "share_conversation": self.query_one("#checkbox-share-conv", Checkbox).value,
        }

        self.post_message(self.ConfigChanged(self.current_node_id, config))

    def _delete_node(self) -> None:
        """Request node deletion."""
        if self.current_node_id:
            self.post_message(self.NodeDeleteRequested(self.current_node_id))

    def set_providers(self, providers: list[str]) -> None:
        """Update provider select options."""
        select = self.query_one("#select-provider", Select)
        select.set_options([(p, p) for p in providers])

    def set_models(self, models: list[str]) -> None:
        """Update model select options."""
        select = self.query_one("#select-model", Select)
        select.set_options([(m, m) for m in models])

    def set_fallback_models(self, models: list[str]) -> None:
        """Update fallback model select options."""
        select = self.query_one("#select-fallback", Select)
        select.set_options([("", "None")] + [(m, m) for m in models])