# Usage Guide

## Quick Start

### Prerequisites

1. **Tor**: Install and run Tor daemon
   ```bash
   # Linux
   sudo apt-get install tor
   sudo systemctl start tor
   
   # macOS
   brew install tor
   brew services start tor
   
   # Windows
   # Download from https://www.torproject.org/download/
   ```

2. **socat**: For Tor tunnel
   ```bash
   # Linux
   sudo apt-get install socat
   
   # macOS
   brew install socat
   
   # Windows
   # Use WSL or install from https://github.com/openssl/openssl/wiki/Binaries
   ```

### Installation

```bash
# From source
git clone <repo>
cd mcp-agent-orchestrator
pip install -e .

# Or use the pre-built binary
# Download from releases page
```

### Configuration

Create `~/.config/mcp-orchestrator/config.yaml`:

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
    api_key: "${DARKROUTER_API_KEY}"
    models: ["darkrouter-model"]
    tor_required: true
    timeout: 60
    max_retries: 3
    concurrency_limit: 5

  - name: "openai"
    type: "openai_compat"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    models: ["gpt-4", "gpt-3.5-turbo"]
    tor_required: false

mcp_servers:
  - name: "filesystem"
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem"]
    args: ["~/projects"]
    transport: "stdio"
  
  - name: "github"
    command: ["npx", "-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
    transport: "stdio"
```

### Running

```bash
# Start TUI
mcp-orchestrator

# With custom config
mcp-orchestrator --config /path/to/config.yaml

# Debug mode
mcp-orchestrator --debug
```

## TUI Interface

### Panels

1. **Palette (Left)**: Available node types
   - Drag nodes to canvas
   - Agent, Tool, Input, Output types

2. **Canvas (Center)**: Visual workflow editor
   - Click to select nodes
   - Drag to reposition
   - Connect nodes by dragging from output to input
   - Delete with Del key

3. **Inspector (Right)**: Node configuration
   - Edit node properties
   - Provider, model, system prompt
   - Tool selection
   - Temperature, max tokens

4. **Console (Bottom)**: Execution logs
   - Real-time event stream
   - Color-coded by level
   - Filter by node

4. **Providers (Toggle with Ctrl+E)**: Provider status
   - Health checks
   - Available models
   - Connection status

### Key Bindings

| Key | Action |
|-----|--------|
| Ctrl+E | Toggle Providers panel |
| Ctrl+Q | Quit |
| Ctrl+S | Save workflow |
| Ctrl+O | Load workflow |
| Ctrl+R | Run workflow |
| Del | Delete selected node/edge |
| Esc | Deselect |

### Workflow Creation

1. **Add Nodes**: Drag from Palette to Canvas
2. **Configure**: Click node, edit in Inspector
3. **Connect**: Drag from output port to input port
4. **Save**: Ctrl+S to save workflow
5. **Run**: Ctrl+R to execute

## CLI Commands

```bash
# Help
mcp-orchestrator --help

# Version
mcp-orchestrator --version

# Run with config
mcp-orchestrator --config ~/.config/mcp-orchestrator/config.yaml

# Debug
mcp-orchestrator --debug
```

## Workflow Examples

### Simple Agent

```yaml
# Saved workflow (JSON)
{
  "id": "simple-agent",
  "version": "1.0",
  "metadata": {"name": "Simple Agent"},
  "nodes": [{
    "id": "agent-1",
    "type": "agent",
    "label": "Assistant",
    "config": {
      "provider": "darkrouter",
      "model": "darkrouter-model",
      "system_prompt": "You are a helpful assistant."
    }
  }],
  "edges": []
}
```

### Multi-Agent Pipeline

```json
{
  "id": "pipeline",
  "version": "1.0",
  "metadata": {"name": "Research Pipeline"},
  "nodes": [
    {
      "id": "planner",
      "type": "agent",
      "label": "Planner",
      "config": {
        "provider": "darkrouter",
        "model": "darkrouter-model",
        "system_prompt": "Create a research plan."
      }
    },
    {
      "id": "researcher",
      "type": "agent",
      "label": "Researcher",
      "config": {
        "provider": "darkrouter",
        "model": "darkrouter-model",
        "system_prompt": "Execute research using tools.",
        "tools": ["web_search", "fetch_content"]
      }
    },
    {
      "id": "writer",
      "type": "agent",
      "label": "Writer",
      "config": {
        "provider": "darkrouter",
        "model": "darkrouter-model",
        "system_prompt": "Write final report."
      }
    }
  ],
  "edges": [
    {"id": "e1", "source": "planner", "target": "researcher"},
    {"id": "e2", "source": "researcher", "target": "writer"}
  ]
}
```

### Parallel Branches

```json
{
  "id": "parallel",
  "version": "1.0",
  "metadata": {"name": "Parallel Development"},
  "nodes": [
    {"id": "planner", "type": "agent", "label": "Planner", "config": {"provider": "darkrouter", "model": "darkrouter-model", "system_prompt": "Plan features."}},
    {"id": "frontend", "type": "agent", "label": "Frontend", "config": {"provider": "darkrouter", "model": "darkrouter-model", "system_prompt": "Write frontend code."}},
    {"id": "backend", "type": "agent", "label": "Backend", "config": {"provider": "darkrouter", "model": "darkrouter-model", "system_prompt": "Write backend code."}},
    {"id": "reviewer", "type": "agent", "label": "Reviewer", "config": {"provider": "darkrouter", "model": "darkrouter-model", "system_prompt": "Review code."}}
  ],
  "edges": [
    {"id": "e1", "source": "planner", "target": "frontend"},
    {"id": "e2", "source": "planner", "target": "backend"},
    {"id": "e3", "source": "frontend", "target": "reviewer"},
    {"id": "e4", "source": "backend", "target": "reviewer"}
  ]
}
```

## MCP Server Setup

### Filesystem Server

```bash
npx -y @modelcontextprotocol/server-filesystem ~/projects
```

Config:
```yaml
mcp_servers:
  - name: "filesystem"
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem"]
    args: ["~/projects"]
    transport: "stdio"
```

### GitHub Server

```bash
export GITHUB_TOKEN=your_token
npx -y @modelcontextprotocol/server-github
```

Config:
```yaml
mcp_servers:
  - name: "github"
    command: ["npx", "-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
    transport: "stdio"
```

## Troubleshooting

### Tor Connection Issues

1. Check Tor is running:
   ```bash
   curl --socks5 127.0.0.1:9050 https://check.torproject.org
   ```

2. Check socat tunnel:
   ```bash
   socat TCP-LISTEN:5080,fork SOCKS4A:127.0.0.1:darkrouter.onion:9050,socksport=9050
   ```

3. Verify tunnel:
   ```bash
   curl http://127.0.0.1:5080/api/v1/models \
     -H "X-Token: your-api-key"
   ```

### Provider Errors

- Check API key in config
- Verify base_url is correct
- Check tor_required matches Tor availability

### MCP Server Issues

- Verify command exists in PATH
- Check server logs in Console panel
- Ensure transport type matches server (stdio vs SSE)

### Binary Issues

- Run from terminal to see errors
- Check antivirus isn't blocking
- Try `--debug` flag for verbose output

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DARKROUTER_API_KEY` | DarkRouter API token |
| `OPENAI_API_KEY` | OpenAI API key |
| `GITHUB_TOKEN` | GitHub personal access token |
| `MCP_ORCHESTRATOR_CONFIG` | Config file path |

## Data Directory

Default: `~/.local/share/mcp-orchestrator/`

Contains:
- `workflows.db` - SQLite database
- `logs/` - Execution logs
- `cache/` - Model/tool caches