"""Persist conversation turns and build a bounded restored-state card.

The card is what a client may inject at session start. Full turns, including
tool results, stay in the knowledge base for exact recall. Retired and
withdrawn identifiers are dropped from earlier lines and kept on the line
that retires them.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from atex.kb import KnowledgeBase, KnowledgeBaseError

_ID_RE = re.compile(r"\b[A-Z][A-Z0-9_]{5,}\b")
_RETIRE_RE = re.compile(r"\b(?i:retired|withdrawn|forget)\b")
_CRUCIAL_RE = re.compile(
    r"\b(?i:error|constraint|decision|withdrawn|forget|retired|must not)\b"
    r"|`[^`\n]{4,}`"
    r"|/[A-Za-z0-9_./-]{8,}"
    r"|\b[A-Z][A-Z0-9_]{5,}\b"
)
_CODE_HEAD_RE = re.compile(r"^\s*(def|fn|class|struct|function)\b")
_SKIP_USER_PREFIXES = ("<command", "<local-command", "Caveat:", "<system-reminder")
_SPAN = 240
_LABELS = {"CONSTRAINT", "DECISION", "ERROR", "TOOL", "ASSISTANT", "USER"}


def project_slug(cwd: str) -> str:
    raw = (cwd or "")[-48:].lower()
    out: List[str] = []
    dash = False
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
            dash = False
        elif out and not dash:
            out.append("-")
            dash = True
    while out and out[-1] == "-":
        out.pop()
    return "".join(out) or "root"


def _text_from_content(content) -> Tuple[str, str, bool]:
    """Return (user_or_assistant_text, tool_text, saw_tool_result)."""
    if isinstance(content, str):
        return content, "", False
    if not isinstance(content, list):
        return "", "", False
    texts: List[str] = []
    tools: List[str] = []
    saw_tool = False
    for block in content:
        if isinstance(block, str):
            texts.append(block)
            continue
        if not isinstance(block, dict):
            continue
        kind = block.get("type") or ""
        if kind == "tool_result":
            saw_tool = True
            tools.append(_tool_body(block.get("content")))
        elif kind == "text" and isinstance(block.get("text"), str):
            texts.append(block["text"])
        elif kind == "tool_use":
            path = ""
            inp = block.get("input") if isinstance(block.get("input"), dict) else {}
            if isinstance(inp.get("file_path"), str):
                path = inp["file_path"]
            elif isinstance(inp.get("notebook_path"), str):
                path = inp["notebook_path"]
            if path:
                tools.append(f"file {path}")
    return "\n".join(t for t in texts if t), "\n".join(t for t in tools if t), saw_tool


def _tool_body(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    if content is None:
        return ""
    return str(content)


def _skip_user(text: str) -> bool:
    stripped = text.strip()
    return (not stripped) or stripped.startswith(_SKIP_USER_PREFIXES)


def parse_transcript(raw: str) -> List[dict]:
    """Group a JSONL transcript into turns. Accepts compact or spaced JSON."""
    turns: List[dict] = []
    current: Optional[dict] = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        if rec.get("isSidechain") or rec.get("isMeta"):
            continue
        kind = rec.get("type")
        message = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        content = message.get("content")
        text, tool, saw_tool = _text_from_content(content)
        if kind == "user":
            if saw_tool and current is not None:
                if tool.strip():
                    current["tools"].append(tool)
                continue
            if _skip_user(text):
                continue
            current = {"user": text.strip(), "tools": [], "assistant": []}
            turns.append(current)
        elif kind == "assistant" and current is not None:
            if text.strip():
                current["assistant"].append(text.strip())
            if tool.strip():
                current["tools"].append(tool)
    return turns


def render_turn(turn: dict) -> str:
    parts = [f"User: {turn['user']}"]
    tool = "\n".join(t for t in turn.get("tools") or [] if t.strip())
    if tool:
        parts.append("Tool:\n" + tool)
    assistant = "\n".join(turn.get("assistant") or []).strip()
    parts.append("Assistant: " + assistant)
    return "\n".join(parts).rstrip() + "\n"


def _windows(line: str) -> List[str]:
    if not _CRUCIAL_RE.search(line):
        return []
    stripped = line.strip()
    if len(stripped) <= 500:
        return [stripped]
    spans = []
    for match in _CRUCIAL_RE.finditer(stripped):
        a = max(0, match.start() - 80)
        b = min(len(stripped), match.end() + _SPAN)
        span = re.sub(r"(.)\1{19,}", "", stripped[a:b]).strip()
        spans.append(span)
    # Merge overlapping windows so one long tool line does not explode.
    uniq = []
    for span in spans:
        if span and span not in uniq:
            uniq.append(span)
    return uniq[:4]


def crucial_pieces(text: str) -> List[str]:
    lines = text.splitlines()
    pieces: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _CODE_HEAD_RE.match(line):
            block = [line]
            j = i + 1
            while j < len(lines) and (lines[j].startswith((" ", "\t")) or lines[j].strip() == ""):
                if lines[j].strip() == "":
                    nxt = lines[j + 1] if j + 1 < len(lines) else ""
                    if not nxt.startswith((" ", "\t")):
                        break
                block.append(lines[j])
                j += 1
                if sum(len(x) + 1 for x in block) > 1200:
                    break
            pieces.append("\n".join(block).rstrip())
            i = j
            continue
        pieces.extend(_windows(line))
        i += 1
    return pieces


def restored_card(turns: Iterable[Tuple[int, str]], slug: str) -> str:
    indexed = list(turns)
    found: List[Tuple[int, int, str]] = []
    for n, text in indexed:
        for piece in crucial_pieces(text):
            found.append((n, len(found), piece))
    retired_at = {}
    for idx, (_n, _ord, piece) in enumerate(found):
        if _RETIRE_RE.search(piece):
            for ident in _ID_RE.findall(piece):
                retired_at[ident] = idx
    kept: List[Tuple[int, str]] = []
    seen = set()
    for idx, (n, _ord, piece) in enumerate(found):
        idents = [ident for ident in _ID_RE.findall(piece) if ident not in _LABELS]
        if idents and not _RETIRE_RE.search(piece) and all(retired_at.get(i, -1) > idx for i in idents):
            continue
        key = piece.strip()
        if key in seen:
            continue
        seen.add(key)
        kept.append((n, key))
    n_turns = len(indexed)
    lines = [
        f"[atex] Restored working state for this project ({n_turns} saved turns).",
        f"Older turns: atex_recall key conv::{slug}::turn_<n>. Tool output is on that turn.",
    ]
    if kept:
        lines.append("Crucial lines:")
        for n, piece in kept:
            lines.append(f"- turn {n}: {piece}")
    if indexed:
        last_n, _last_text = indexed[-1]
        lines.append(f"Latest turn {last_n} is stored in full at conv::{slug}::turn_{last_n}.")
    card = "\n".join(lines).rstrip() + "\n"
    if len(card) <= 8000:
        return card
    # Keep the header and the newest crucial lines when a session is huge.
    head = lines[:2]
    tail = [ln for ln in lines if ln.startswith("- turn ") or ln.startswith("Latest turn") or ln.startswith("Crucial")]
    body = "\n".join(head + tail[-40:])
    return body[:8000].rstrip() + "\n"


def _base(slug: str) -> str:
    return f"conv::{slug}::"


def save_turns(kb: KnowledgeBase, slug: str, turns: List[dict]) -> str:
    base = _base(slug)
    rendered = []
    for i, turn in enumerate(turns, start=1):
        text = render_turn(turn)
        rendered.append((i, text))
        kb.add(f"{base}turn_{i}", text, meta={"kind": "turn"}, allow_overwrite=True)
    kb.add(f"{base}count", str(len(turns)), meta={"kind": "count"}, allow_overwrite=True)
    card = restored_card(rendered, slug) if turns else ""
    if card:
        kb.add(f"{base}latest_state", card, meta={"kind": "state"}, allow_overwrite=True)
    kb.flush()
    return card


def load_transcript_path(path: str) -> str:
    file = Path(path)
    if not file.is_file():
        return ""
    return file.read_text(encoding="utf-8", errors="replace")


def transcript_path_from(payload: dict) -> str:
    for key in ("transcript_path", "transcriptPath"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for env_key in ("CURSOR_TRANSCRIPT_PATH", "CLAUDE_TRANSCRIPT_PATH", "GROK_TRANSCRIPT_PATH"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    return ""


def cwd_from(payload: dict) -> str:
    for key in ("cwd", "workspace_root"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    roots = payload.get("workspace_roots")
    if isinstance(roots, list) and roots and isinstance(roots[0], str):
        return roots[0]
    for env_key in ("CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "PWD"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    return os.getcwd()


def read_stdin_payload(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        val = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return val if isinstance(val, dict) else {}


def ingest_transcript(kb: KnowledgeBase, transcript: str, cwd: str) -> str:
    turns = parse_transcript(transcript)
    if not turns:
        return ""
    return save_turns(kb, project_slug(cwd), turns)


def hook_output(kind: str, card: str) -> str:
    """Client-shaped stdout. Empty when there is nothing to inject."""
    if kind in ("stop", "pre-compact", "precompact"):
        return ""
    if not card.strip():
        return ""
    if kind in ("start", "session-start", "sessionstart"):
        body = {
            "additional_context": card,
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": card},
        }
        return json.dumps(body, ensure_ascii=False) + "\n"
    return ""


def open_kb(atex_dir: str) -> KnowledgeBase:
    root = Path(atex_dir)
    index = root / "index.json"
    if index.exists():
        try:
            payload = json.loads(index.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise KnowledgeBaseError(f"corrupt index.json: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("entries"), dict):
            raise KnowledgeBaseError("corrupt index.json: missing entries object")
    return KnowledgeBase(root)


def default_atex_dir() -> str:
    env = os.environ.get("ATEX_DIR", "").strip()
    if env:
        return env
    local = Path(".atex")
    if local.is_dir():
        return str(local.resolve())
    home = Path.home()
    ai = home / "ai" / ".atex"
    if ai.is_dir():
        return str(ai)
    return str(home / ".atex")
