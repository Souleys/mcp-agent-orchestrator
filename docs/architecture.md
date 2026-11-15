# Architecture Documentation

## Overview

MCP Agent Orchestrator is a modular, plugin-based system for orchestrating multi-agent workflows with MCP (Model Context Protocol) support, Tor routing, and DarkRouter integration.

## System Components

### 1. Core Engine (`src/mcp_orchestrator/core/engine.py`)
- **WorkflowEngine**: Main orchestration class
- Topological sort (Kahn's algorithm) for execution order
- Parallel branch execution by depth
- Checkpoint/resume capability
- Event-driven execution with EventBus

### 2. Event System (`src/mcp_orchestrator/core/events.py`)
- **EventBus**: Pub/sub event system
- Event types: NodeStart, NodeComplete, NodeError, TokenStream, ToolCall, ToolResult, WorkflowComplete

### 3. State Store (`src/mcp_orchestrator/core/store.py`)
- **StateStore**: SQLite-based persistence
- Workflows, Runs, Conversations
- JSON serialization for complex data

### 4. Data Models (`src/mcp_orchestrator/core/models.py`)
- **Workflow**: Nodes, edges, metadata
- **AgentNode**: Agent configuration (provider, model, system prompt, tools)
- **Edge**: Directed connections between nodes
- **Run**: Execution state with checkpoints
- **AgentConfig**: Provider, model, temperature, max_tokens, tools

### 5. Provider Abstraction (`src/mcp_orchestrator/providers/`)
- **Base Provider** (`base.py`): Abstract interface
  - `chat_completion`: Non-streaming completion
  - `stream_chat`: Streaming completion
  - `list_models`: Available models
  - `tokenize`: Token counting
  - `upload_file`: File upload
  - `health_check`: Health check

- **DarkRouter Provider** (`darkrouter.py`): OpenAI-compatible API via Tor tunnel
  - Routes through local socat tunnel (port 5080)
  - X-Token authentication header
  - Automatic model listing

- **OpenAI Compatible** (`openai_compat.py`): Generic OpenAI-compatible provider
  - Configurable base URL
  - Standard OpenAI API format

- **Registry** (`registry.py`): Provider registration and discovery
  - Lazy initialization
  - Fallback model support

### 6. MCP Client (`src/mcp_orchestrator/mcp/`)
- **Client** (`client.py`): High-level MCP client
  - Tool calling with retry logic
  - Resource reading
  - Prompt templates

- **Transports** (`transport.py`): 
  - **StdioTransport**: Local process communication
  - **SSETransport**: Server-Sent Events for remote servers

- **Registry** (`registry.py`): Tool discovery and capability filtering
  - Tool schemas with required capabilities
  - Server-specific tool namespaces

- **Models** (`models.py`): Pydantic models for MCP protocol
  - Tool, ToolResult, Resource, Prompt

### 7. Tor Transport (`src/mcp_orchestrator/transport/tor.py`)
- **TorTransport**: Manages socat tunnel to Tor
  - Automatic tunnel startup
  - Health checks against onion service
  - Graceful shutdown with force-kill fallback
  - Auto-restart on process death

### 8. TUI (`src/mcp_orchestrator/ui/`)
- **App** (`app.py`): Main Textual application
  - 4-panel layout: Palette, Canvas, Inspector, Console
  - Collapsible Providers panel
  - Key bindings for common actions

- **Palette** (`palette.py`): Draggable node palette
  - Agent, Tool, Input, Output node types
  - Drag-and-drop to canvas

- **Canvas** (`canvas.py`): Visual workflow editor
  - Node positioning
  - Edge drawing
  - Selection and deletion

- **Inspector** (`inspector.py`): Node/edge property editor
  - Form-based configuration
  - Validation

- **Console** (`console.py`): Log output panel
  - Event streaming display
  - Color-coded log levels

- **Providers Panel** (`providers_panel.py`): Provider status
  - Health indicators
  - Available models
  - Connection status

## Data Flow

```
User Input → CLI → OrchestratorApp → WorkflowEngine
                                    ↓
                            Topological Sort
                                    ↓
                            Parallel Execution Groups
                                    ↓
                            Provider Registry → Provider
                                    ↓
                            MCP Registry → MCP Tools
                                    ↓
                            EventBus → UI / Store
                                    ↓
                            SQLite Persistence
```

## Configuration

Loaded from YAML with environment variable expansion:
- App settings (data_dir, log_level)
- Tor settings (enabled, ports)
- Provider configurations
- MCP server definitions

## Security Considerations

- API keys stored in config (expandable from env vars)
- Tor routing for DarkRouter traffic
- Local-only socat tunnel (no external exposure)
- SQLite with local file permissions

## Extensibility Points

1. **Custom Providers**: Implement `Provider` protocol
2. **Custom MCP Transports**: Implement `MCPTransport` protocol
3. **Custom Node Types**: Extend `AgentNode` with new `type` values
4. **Event Handlers**: Subscribe to `EventBus` for custom logging/monitoring