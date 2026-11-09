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

_EVENTS = (
    "sessionStart",
    "stop",
    "beforeSubmitPrompt",
    "preCompact",
    "preToolUse",
    "beforeReadFile",
    "postToolUse",
)
_RULE = """---
description: Keep Cursor prompts small with AmniTex
alwaysApply: true
---

Do not reread a whole file or paste a whole tool log. Use atex_search or atex_recall for a line range. A large or repeated read is replaced by a short excerpt before it reaches the model. The session card is the durable state.
"""


def install(home: Optional[str] = None, atex_dir: Optional[str] = None, dry_run: bool = False, command: Optional[str] = None) -> List[str]:
    root = Path(home or os.environ.get("HOME") or str(Path.home()))
    kb = atex_dir or os.environ.get("ATEX_DIR") or str(root / ".atex")
    bin_cmd = command or "python3 -m atex.cli"
    notes: List[str] = []
    script = _write_hook_script(root, bin_cmd, dry_run)
    notes.append(f"  + Cursor hook script ({script})")
    notes.extend(_wire_cursor_hooks(root, script, dry_run))
    notes.extend(_wire_cursor_rule(root, dry_run))
    notes.extend(_wire_cursor_mcp(root, kb, bin_cmd, dry_run))
    notes.extend(_wire_grok(root, kb, bin_cmd, dry_run))
    return notes


def _write_hook_script(root: Path, bin_cmd: str, dry_run: bool) -> str:
    path = root / ".cursor" / "hooks" / "atex-cursor"
    body = "#!/bin/sh\nexec " + " ".join(json.dumps(part) for part in bin_cmd.split()) + " hook cursor\n"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    return str(path)


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


def _wire_cursor_hooks(root: Path, script: str, dry_run: bool) -> List[str]:
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
    for event in _EVENTS:
        changed = _ensure_cmd(hooks, event, script) or changed
    if not changed and path.exists():
        return [f"  = Cursor hooks already wired ({path})"]
    _backup(path, dry_run)
    _write(path, json.dumps(data, indent=2) + "\n", dry_run)
    return [f"  + Cursor hooks ({path})"]


def _wire_cursor_rule(root: Path, dry_run: bool) -> List[str]:
    path = root / ".cursor" / "rules" / "amnitex.mdc"
    if path.exists() and path.read_text(encoding="utf-8") == _RULE:
        return [f"  = Cursor rule already present ({path})"]
    _backup(path, dry_run)
    _write(path, _RULE, dry_run)
    return [f"  + Cursor rule ({path})"]


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


def doctor(home: Optional[str] = None, binary: Optional[str] = None) -> List[str]:
    root = Path(home or os.environ.get("HOME") or str(Path.home()))
    lines = []
    ok = True
    hooks = root / ".cursor" / "hooks.json"
    script = root / ".cursor" / "hooks" / "atex-cursor"
    rule = root / ".cursor" / "rules" / "amnitex.mdc"
    mcp = root / ".cursor" / "mcp.json"
    if script.is_file():
        lines.append(f"ok hook script {script}")
    else:
        ok = False
        lines.append(f"missing hook script {script}")
    if hooks.is_file():
        try:
            data = json.loads(hooks.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            ok = False
            lines.append(f"bad hooks json {hooks}")
            data = {}
        events = data.get("hooks") if isinstance(data, dict) else {}
        for event in _EVENTS:
            rows = events.get(event) if isinstance(events, dict) else None
            cmds = [row.get("command") for row in rows or [] if isinstance(row, dict)]
            if any(str(script) == cmd or "atex-cursor" in str(cmd) for cmd in cmds):
                lines.append(f"ok hook {event}")
            else:
                ok = False
                lines.append(f"missing hook {event}")
    else:
        ok = False
        lines.append(f"missing {hooks}")
    if rule.is_file():
        lines.append(f"ok rule {rule}")
    else:
        ok = False
        lines.append(f"missing rule {rule}")
    if mcp.is_file() and "amnitex" in mcp.read_text(encoding="utf-8"):
        lines.append(f"ok mcp {mcp}")
    else:
        ok = False
        lines.append(f"missing mcp amnitex {mcp}")
    if binary:
        lines.append(f"binary {binary}")
    lines.append("doctor " + ("ok" if ok else "fail"))
    return lines


def uninstall(home: Optional[str] = None, dry_run: bool = False) -> List[str]:
    root = Path(home or os.environ.get("HOME") or str(Path.home()))
    notes = []
    hooks = root / ".cursor" / "hooks.json"
    if hooks.is_file():
        try:
            data = json.loads(hooks.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            notes.append(f"  ! {hooks} is not valid JSON; left unchanged")
            data = None
        if isinstance(data, dict) and isinstance(data.get("hooks"), dict):
            _backup(hooks, dry_run)
            for event, rows in list(data["hooks"].items()):
                if not isinstance(rows, list):
                    continue
                kept = [row for row in rows if not (isinstance(row, dict) and "atex-cursor" in str(row.get("command")))]
                if kept:
                    data["hooks"][event] = kept
                else:
                    del data["hooks"][event]
            _write(hooks, json.dumps(data, indent=2) + "\n", dry_run)
            notes.append(f"  - removed atex-cursor hooks ({hooks})")
    script = root / ".cursor" / "hooks" / "atex-cursor"
    if script.exists() and not dry_run:
        script.unlink()
    if script.exists() or True:
        notes.append(f"  - hook script ({script})")
    rule = root / ".cursor" / "rules" / "amnitex.mdc"
    if rule.exists() and not dry_run:
        rule.unlink()
    notes.append(f"  - rule ({rule})")
    mcp = root / ".cursor" / "mcp.json"
    if mcp.is_file():
        try:
            data = json.loads(mcp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict) and "amnitex" in data["mcpServers"]:
            _backup(mcp, dry_run)
            del data["mcpServers"]["amnitex"]
            _write(mcp, json.dumps(data, indent=2) + "\n", dry_run)
            notes.append(f"  - Cursor MCP amnitex ({mcp})")
    return notes
