# tests/test_config.py
import pytest
from pathlib import Path


def test_load_config_from_yaml(tmp_path):
    config_yaml = tmp_path / "config.yaml"
    config_yaml.write_text("""
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
    api_key: "test-token"
    tor_required: true
mcp_servers: []
""")
    from mcp_orchestrator.config import Config
    cfg = Config.load(config_yaml)
    assert cfg.app.data_dir == "~/.local/share/mcp-orchestrator"
    assert cfg.tor.enabled is True
    assert cfg.tor.tunnel_port == 5080
    assert len(cfg.providers) == 1
    assert cfg.providers[0].name == "darkrouter"
    assert cfg.providers[0].tor_required is True
