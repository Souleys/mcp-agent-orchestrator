# MCP Agent Orchestrator Implementation Plan

**Goal:** Build a Python TUI application for orchestrating multi-agent workflows with DarkRouter (.onion via Tor), OpenAI-compatible providers, and local MCP servers, featuring a visual drag-and-drop flow builder.

**Architecture:** Modular plugin architecture with 5 independent components (TUI, Orchestrator Core, Model Registry, MCP Client, Tor Transport) communicating via well-defined interfaces. SQLite for persistence, textual for TUI, asyncio throughout.

**Tech Stack:** Python 3.11+, textual (TUI), pydantic (models), httpx (async HTTP), mcp (MCP client), sqlite3 (persistence), pytest (testing), respx (mocking), pytest-textual-snapshot (TUI tests)

**Spec:** docs/superpowers/specs/2026-11-14-mcp-agent-orchestrator-design.md

## Global Constraints

- Python 3.11+ (ExceptionGroup, tomllib, typing.Self)
- Single binary distribution via PyInstaller
- Sub-100ms TUI frame latency
- External Tor + socat tunnel for DarkRouter (port 5080)
- Env vars for secrets (no keyring)
- No telemetry
- SQLite for state persistence (workflows, conversations, runs)
- Per-agent option to share or isolate DarkRouter conversation IDs

## Review Focus

1. Tor tunnel failure: socat process dies -> TUI shows degraded status, auto-reconnect with backoff, queued requests flush on recovery
2. Model capability mismatch: Agent configured with tools but model lacks capabilities.tools -> validation error at workflow save, not runtime
3. Context overflow: DarkRouter returns 413 context_too_long -> auto-summarize conversation, retry with truncated history, max 3 retries
4. MCP server crash mid-run: stdio process exits -> mark tools unavailable, emit NodeError event, attempt reconnect every 5s, resume if workflow paused
5. Concurrent provider limits: 6 requests/token/worker (DarkRouter) -> semaphore per provider, queue with priority, emit RateLimitWarning event

### Task 1: Project Scaffolding & Configuration

Files: pyproject.toml, src/mcp_orchestrator/__init__.py, src/mcp_orchestrator/config.py, src/mcp_orchestrator/constants.py, tests/test_config.py, .gitignore, README.md

Interfaces: Produces Config class with load() method, ProviderConfig, MCPServerConfig, TorConfig, AppConfig models

### Task 2: Provider Abstraction Layer

Files: src/mcp_orchestrator/providers/__init__.py, base.py, darkrouter.py, openai_compat.py, registry.py, models.py, tests/providers/*

Interfaces: Consumes ProviderConfig, Produces Provider protocol, ProviderRegistry

### Task 3: MCP Client

Files: src/mcp_orchestrator/mcp/__init__.py, transport.py, client.py, registry.py, models.py, tests/mcp/*

Interfaces: Consumes MCPServerConfig, Produces MCPTransport protocol, MCPClient, MCPToolRegistry

### Task 4: Tor Transport Layer

Files: src/mcp_orchestrator/transport/__init__.py, tor.py, tests/transport/test_tor.py

Interfaces: Consumes TorConfig, Produces TorTransport with ensure_tunnel, health_check, get_base_url, shutdown

### Task 5: Orchestrator Core - State Store

Files: src/mcp_orchestrator/core/__init__.py, store.py, models.py, tests/core/test_store.py

Interfaces: Produces StateStore with init_db, save_workflow, load_workflow, list_workflows, save_run, load_run, save_conversation, load_conversation, get_conversation_history

### Task 6: Orchestrator Core - Event Bus & Workflow Engine

Files: src/mcp_orchestrator/core/events.py, engine.py, tests/core/test_events.py, test_engine.py

Interfaces: Consumes StateStore, ProviderRegistry, MCPToolRegistry, Produces EventBus, WorkflowEngine

### Task 7: TUI - Layout & Panels

Files: src/mcp_orchestrator/ui/__init__.py, app.py, layout.py, palette.py, canvas.py, inspector.py, console.py, providers_panel.py, tests/ui/*

Interfaces: Consumes WorkflowEngine, ProviderRegistry, MCPToolRegistry, StateStore, Config, Produces OrchestratorApp

### Task 8: TUI - Workflow Actions & Key Bindings

Files: src/mcp_orchestrator/ui/app.py, canvas.py, inspector.py, commands.py, tests/ui/test_commands.py

Interfaces: Consumes OrchestratorApp, StateStore, WorkflowEngine, Produces Command palette, key bindings, workflow save/load/run/stop

### Task 9: Integration & E2E Tests

Files: tests/integration/test_darkrouter_flow.py, test_multi_agent.py, test_mcp_tools.py, test_tor_resilience.py

### Task 10: Packaging & Distribution

Files: src/mcp_orchestrator/__main__.py, pyproject.toml, build.spec, .github/workflows/build.yml

### Task 11: Documentation & Polish

Files: README.md, docs/usage.md, docs/configuration.md, docs/architecture.md, CHANGELOG.md

## Execution Recommendation

Subagent-driven execution recommended because: 11 tasks with complex interdependencies benefit from independent review at each stage. TUI and orchestrator logic are high-risk areas. Tasks 1-4 can run in parallel.
