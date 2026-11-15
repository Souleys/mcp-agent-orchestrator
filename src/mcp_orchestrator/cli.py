"""CLI entry point for MCP Orchestrator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp_orchestrator.ui.app import OrchestratorApp


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="mcp-orchestrator",
        description="MCP Agent Orchestrator - Multi-agent orchestration with MCP, Tor, and DarkRouter",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="mcp-orchestrator 0.1.0",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )

    args = parser.parse_args()

    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    app = OrchestratorApp()
    app.run()

    return 0


if __name__ == "__main__":
    sys.exit(main())