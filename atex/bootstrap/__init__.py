"""atex.bootstrap: detect MCP-capable AI clients and offer to wire atex into their config (with consent + backup)."""
from atex.bootstrap.detect import detect_all,ClientStatus
from atex.bootstrap.configs import wire_client,wire_all
from atex.bootstrap.demo import run_demo
__all__=["detect_all","ClientStatus","wire_client","wire_all","run_demo"]
