# MCP Agent Orchestrator

Multi-agent orchestration with MCP, Tor, and DarkRouter.

## Overview

MCP Agent Orchestrator is a framework for orchestrating multiple AI agents that communicate via the Model Context Protocol (MCP), with optional Tor routing and DarkRouter integration for privacy-preserving agent communication.

## Features

- **MCP Client**: Connect to and manage MCP servers
- **Provider Abstraction**: Support for multiple LLM providers (DarkRouter, etc.)
- **Tor Transport**: Route traffic through Tor for anonymity
- **DarkRouter Integration**: Access LLM models via DarkRouter onion service
- **State Persistence**: SQLite-based storage for workflows, conversations, and runs
- **TUI Interface**: Terminal user interface for monitoring and control

## Installation

```bash
pip install -e .
```

## Configuration

Create a configuration file at `~/.config/mcp-orchestrator/config.yaml`:

```yaml
app:
  data_dir: "~/.local/share/mcp-orchestrator"
  log_level: "INFO"
tor:
  enabled: true
  socks_port: 9050
  tunnel_port: 5080
providers:
  - name: "darkrouter"
    type: "darkrouter"
    base_url: "http://127.0.0.1:5080/api/v1"
    api_key: "your-api-key"
    tor_required: true
mcp_servers: []
```

## Usage

```bash
# Run the orchestrator
mcp-orchestrator

# Run with custom config
mcp-orchestrator --config /path/to/config.yaml
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Type check
mypy src/
```

## Architecture

- **Task 1**: Project scaffolding & configuration (this task)
- **Task 2**: Provider abstraction layer
- **Task 3**: MCP client implementation
- **Task 4**: Tor transport layer
- **Task 5**: State store (SQLite)
- **Task 6**: DarkRouter integration
- **Task 7**: Agent orchestration engine
- **Task 8**: TUI interface
- **Task 9**: CLI commands
- **Task 10**: PyInstaller packaging

## License

MIT
