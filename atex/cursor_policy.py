"""Per-turn Cursor hook policy.

Mirrors the native `atex hook cursor` decisions.
Cursor's documented hooks can deny a file read and replace an MCP tool
result. They cannot rewrite the chat transcript on beforeSubmitPrompt
or change preCompact's summary. Those limits are enforced here: submit
returns only continue=true, and preCompact returns an empty object.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LARGE_FILE = 1500
LARGE_MCP = 800


def line_keep(ln: str) -> bool:
    if "CONSTRAINT" in ln or "Decision" in ln or "ERROR" in ln or "def " in ln or "return False" in ln:
        return True
    if "/" in ln and len(ln) > 8:
        return True
    run = 0
    for ch in ln:
        if "A" <= ch <= "Z":
            run += 1
        elif ch == "_" or ch.isdigit():
            pass
        else:
            if run >= 6:
                return True
            run = 0
    return run >= 6


def excerpt_keep(raw: str) -> str:
    kept: List[str] = []
    size = 0
    for ln in raw.split("\n"):
        if not line_keep(ln):
            continue
        piece = ln[:240]
        kept.append(piece)
        size += len(piece) + 1
        if size > 700 or len(kept) >= 12:
            break
    if not kept:
        return raw[:400]
    return "\n".join(kept)


def shrink_message(path: str, raw: str, duplicate: bool) -> str:
    if duplicate:
        head = f"ATEX duplicate. Already sent this session. Do not read {path} again.\n"
    else:
        head = f"ATEX kept {len(raw)} chars off the prompt for {path}.\n"
    return head + excerpt_keep(raw)


class Seen:
    def __init__(self) -> None:
        self.paths = set()

    def already(self, path: str) -> bool:
        return path in self.paths

    def mark(self, path: str) -> None:
        if path:
            self.paths.add(path)


def load_seen(atex_dir: str, conv: str) -> Seen:
    seen = Seen()
    path = Path(atex_dir) / f"cursor-seen-{_safe_conv(conv)}"
    if not path.is_file():
        return seen
    text = path.read_text(encoding="utf-8", errors="replace")
    for ln in text.splitlines():
        if ln.strip():
            seen.mark(ln.strip())
    return seen


def save_seen(atex_dir: str, conv: str, seen: Seen) -> None:
    root = Path(atex_dir)
    root.mkdir(parents=True, exist_ok=True)
    body = "\n".join(sorted(seen.paths))
    if body:
        body += "\n"
    (root / f"cursor-seen-{_safe_conv(conv)}").write_text(body, encoding="utf-8")


def _safe_conv(conv: str) -> str:
    out = []
    for ch in (conv or "default")[:64]:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
    return "".join(out) or "default"


def conversation_id(payload: dict) -> str:
    for key in ("conversation_id", "session_id"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return "default"


def _tool_input(payload: dict) -> dict:
    raw = payload.get("tool_input")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            val = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return val if isinstance(val, dict) else {}
    return {}


def tool_path(payload: dict) -> str:
    src = _tool_input(payload)
    for key in ("path", "file_path", "target_file"):
        val = src.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    val = payload.get("file_path")
    if isinstance(val, str):
        return val.strip()
    return ""


def shell_target(command: str) -> str:
    cmd = command.strip()
    if cmd.startswith("cat "):
        rest = cmd[4:].strip()
    elif cmd.startswith("type "):
        rest = cmd[5:].strip()
    else:
        return ""
    if len(rest) >= 2 and rest[0] == '"' and rest[-1] == '"':
        rest = rest[1:-1]
    return rest.split(" ", 1)[0]


def read_body(path: str, inline: str = "") -> Optional[str]:
    if inline:
        return inline
    if not path:
        return None
    file = Path(path)
    if not file.is_file():
        return None
    return file.read_text(encoding="utf-8", errors="replace")


def consider_path(path: str, raw: Optional[str], seen: Seen) -> Optional[str]:
    """Return the replacement text when the read must stay off the prompt."""
    if not path or raw is None:
        return None
    dup = seen.already(path)
    if not dup and len(raw) <= LARGE_FILE:
        seen.mark(path)
        return None
    msg = shrink_message(path, raw, dup)
    if not dup:
        seen.mark(path)
    return msg


def handle(payload: dict, seen: Optional[Seen] = None) -> dict:
    event = str(payload.get("hook_event_name") or "")
    seen = seen if seen is not None else Seen()
    if event in ("beforeSubmitPrompt", "UserPromptSubmit"):
        return {"continue": True}
    if event in ("preCompact", "PreCompact"):
        return {}
    if event in ("sessionStart", "SessionStart", "start"):
        card = str(payload.get("_card") or "")
        return {
            "additional_context": card,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": card},
        }
    if event in ("stop", "Stop"):
        return {}
    if event == "beforeReadFile":
        path = tool_path(payload)
        raw = payload.get("content") if isinstance(payload.get("content"), str) else read_body(path)
        msg = consider_path(path, raw if isinstance(raw, str) else None, seen)
        if msg is None:
            return {"permission": "allow"}
        return {"permission": "deny", "user_message": msg}
    if event == "preToolUse":
        name = str(payload.get("tool_name") or "")
        if name in ("Read", "read_file", "ReadFile"):
            path = tool_path(payload)
            msg = consider_path(path, read_body(path), seen)
            if msg is None:
                return {"permission": "allow"}
            return {"permission": "deny", "agent_message": msg, "user_message": msg}
        if name in ("Shell", "shell"):
            cmd = str(_tool_input(payload).get("command") or "")
            target = shell_target(cmd)
            msg = consider_path(target, read_body(target), seen) if target else None
            if msg is None:
                return {"permission": "allow"}
            return {"permission": "deny", "agent_message": msg, "user_message": msg}
        return {"permission": "allow"}
    if event == "postToolUse":
        name = str(payload.get("tool_name") or "")
        mcp = payload.get("mcp_server_name")
        output = payload.get("tool_output")
        is_mcp = (isinstance(mcp, str) and mcp) or name.startswith("MCP:")
        if is_mcp and isinstance(output, str) and len(output) > LARGE_MCP:
            text = f"ATEX trimmed MCP output from {len(output)} chars.\n" + excerpt_keep(output)
            return {"updated_mcp_tool_output": {"text": text}}
        return {}
    return {}


def visible_tool_text(event: dict, seen: Seen, enabled: bool) -> str:
    """What this tool result contributes to the model transcript."""
    kind = event["type"]
    if not enabled:
        return event.get("content") or ""
    if kind == "read":
        msg = consider_path(event["path"], event["content"], seen)
        return event["content"] if msg is None else msg
    if kind == "shell":
        target = shell_target(event.get("command") or "")
        msg = consider_path(target, event.get("content"), seen) if target else None
        return event["content"] if msg is None else msg
    if kind == "mcp":
        output = event.get("content") or ""
        if len(output) > LARGE_MCP:
            return f"ATEX trimmed MCP output from {len(output)} chars.\n" + excerpt_keep(output)
        return output
    return event.get("content") or ""
