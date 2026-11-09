"""Wire Cursor and Grok to the local atex memory layer.

Cursor gets a user-level hooks file that saves the transcript on stop and
injects the restored card on sessionStart. Grok gets an MCP server entry.
Existing client files are backed up before they are changed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

_HOOK_STOP = "python3 -m atex.cli hook stop"
_HOOK_START = "python3 -m atex.cli hook session-start"


def install(home: Optional[str] = None, atex_dir: Optional[str] = None, dry_run: bool = False, command: Optional[str] = None) -> List[str]:
    root = Path(home or os.environ.get("HOME") or str(Path.home()))
    kb = atex_dir or os.environ.get("ATEX_DIR") or str(root / ".atex")
    bin_cmd = command or "python3 -m atex.cli"
    notes: List[str] = []
    notes.extend(_wire_cursor_hooks(root, dry_run))
    notes.extend(_wire_cursor_mcp(root, kb, bin_cmd, dry_run))
    notes.extend(_wire_grok(root, kb, bin_cmd, dry_run))
    return notes


def _backup(path: Path, dry_run: bool) -> None:
    if not path.exists() or dry_run:
        return
    dest = path.with_name(path.name + ".atex-backup")
    dest.write_bytes(path.read_bytes())


def _write(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _wire_cursor_hooks(root: Path, dry_run: bool) -> List[str]:
    path = root / ".cursor" / "hooks.json"
    data = {"version": 1, "hooks": {}}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"  ! {path} is not valid JSON; left unchanged"]
        if isinstance(loaded, dict):
            data = loaded
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return [f"  ! {path} hooks field is not an object; left unchanged"]
    changed = False
    changed = _ensure_cmd(hooks, "stop", _HOOK_STOP) or changed
    changed = _ensure_cmd(hooks, "sessionStart", _HOOK_START) or changed
    if not changed and path.exists():
        return [f"  = Cursor hooks already wired ({path})"]
    _backup(path, dry_run)
    _write(path, json.dumps(data, indent=2) + "\n", dry_run)
    return [f"  + Cursor hooks ({path})"]


def _ensure_cmd(hooks: dict, event: str, command: str) -> bool:
    rows = hooks.get(event)
    if not isinstance(rows, list):
        rows = []
    for row in rows:
        if isinstance(row, dict) and row.get("command") == command:
            hooks[event] = rows
            return False
    rows.append({"command": command})
    hooks[event] = rows
    return True


def _mcp_entry(kb: str, bin_cmd: str) -> dict:
    parts = bin_cmd.split()
    return {"command": parts[0], "args": parts[1:] + ["serve", "--atex-dir", kb]}


def _wire_cursor_mcp(root: Path, kb: str, bin_cmd: str, dry_run: bool) -> List[str]:
    path = root / ".cursor" / "mcp.json"
    data = {"mcpServers": {}}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return [f"  ! {path} is not valid JSON; left unchanged"]
        if isinstance(loaded, dict):
            data = loaded
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        return [f"  ! {path} mcpServers is not an object; left unchanged"]
    if "amnitex" in servers:
        return [f"  = Cursor MCP already wired ({path})"]
    servers["amnitex"] = _mcp_entry(kb, bin_cmd)
    _backup(path, dry_run)
    _write(path, json.dumps(data, indent=2) + "\n", dry_run)
    return [f"  + Cursor MCP ({path})"]


def _wire_grok(root: Path, kb: str, bin_cmd: str, dry_run: bool) -> List[str]:
    path = root / ".grok" / "config.toml"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if "mcp_servers.amnitex" in existing or "[mcp_servers.amnitex]" in existing:
        return [f"  = Grok MCP already wired ({path})"]
    parts = bin_cmd.split()
    command = parts[0]
    args = parts[1:] + ["serve", "--atex-dir", kb]
    args_toml = ", ".join(json.dumps(a) for a in args)
    block = f'\n[mcp_servers.amnitex]\ncommand = {json.dumps(command)}\nargs = [{args_toml}]\n'
    _backup(path, dry_run)
    _write(path, existing + block, dry_run)
    return [f"  + Grok MCP ({path})"]
