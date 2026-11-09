"""Replay a 40-turn Cursor-style session with ATEX off and on.

Token counts use tiktoken o200k_base. That is a real tokenizer. It is not
Cursor's provider meter and it is not a billed allowance.
"""
from __future__ import annotations

import argparse
import json
from typing import Dict, List

from atex.cursor_policy import Seen, visible_tool_text

RULE = (
    "Use atex_search or atex_recall for a line range instead of rereading a file "
    "or pasting a whole tool log. The session card is the durable state.\n"
)


def _file(body: str) -> str:
    return body


def build_session() -> List[dict]:
    code = (
        "def verify(token:str)->bool:\n"
        "    if '.' not in token:return False\n"
        "    user_id,sig=token.rsplit('.',1)\n"
        "    return True\n"
    )
    code_pad = ("# pad line for the auth module\n" * 80) + code + ("# tail pad\n" * 40)
    notes = (
        "notes header\n"
        + ("background sentence about the build.\n" * 120)
        + "CONSTRAINT: the audit nonce is AUDIT_NONCE_7F3A and must not be rotated.\n"
        + "Decision: the standby replica answers on the name marigold.\n"
        + ("more background.\n" * 40)
    )
    mcp = (
        "tool log start\n"
        + ("noise row\n" * 150)
        + "ERROR: indexer returned E_PAGE_OVERFLOW_77 when a file exceeded 524288 bytes.\n"
        + "path /tmp/audit/hidden/config.toml\n"
        + ("noise row\n" * 40)
    )
    small = "POOL_SIZE=8 in tests/fixtures/sample_project/db.py\n"
    turns = []
    for i in range(1, 41):
        events = []
        assistant = f"Turn {i} acknowledged. No new constraint."
        if i == 5:
            events.append({"type": "read", "path": "proj/auth.py", "content": code_pad})
        elif i == 6:
            events.append({"type": "read", "path": "proj/auth.py", "content": code_pad})
        elif i == 9:
            events.append({"type": "read", "path": "proj/notes.md", "content": notes})
        elif i == 11:
            events.append({"type": "read", "path": "proj/db.py", "content": small})
        elif i == 14:
            events.append({"type": "shell", "command": "cat proj/notes.md", "content": notes})
        elif i == 18:
            events.append({"type": "read", "path": "proj/notes.md", "content": notes})
        elif i == 22:
            events.append({"type": "mcp", "name": "MCP:indexer", "content": mcp})
        elif i == 27:
            events.append({"type": "mcp", "name": "MCP:indexer", "content": mcp})
        elif i == 32:
            assistant = "Decision: the primary telemetry port is now PORT_2201_TCP. PORT_9471_UDP is retired."
        elif i == 36:
            assistant = "AUDIT_NONCE_7F3A is withdrawn. Forget that nonce; it is no longer in force."
        turns.append({
            "user": f"Continue task {i}. Keep the nonce, the port, and the verify line.",
            "assistant": assistant,
            "events": events,
        })
    return turns


EXPECTS = [
    "if '.' not in token:return False",
    "AUDIT_NONCE_7F3A",
    "marigold",
    "E_PAGE_OVERFLOW_77",
    "/tmp/audit/hidden/config.toml",
    "PORT_2201_TCP",
    "POOL_SIZE=8",
    "tests/fixtures/sample_project/db.py",
    "withdrawn",
]


def _join(parts: List[str]) -> str:
    return "\n".join(parts)


def replay(turns: List[dict], enabled: bool) -> Dict:
    seen = Seen()
    parts: List[str] = []
    if enabled:
        parts.append(RULE)
    per_turn = []
    visible_tools = []
    for turn in turns:
        parts.append("user: " + turn["user"])
        for ev in turn["events"]:
            text = visible_tool_text(ev, seen, enabled)
            parts.append("tool: " + text)
            visible_tools.append(text)
        parts.append("assistant: " + turn["assistant"])
        per_turn.append(_join(parts))
    blob = _join(parts)
    return {"per_turn_text": per_turn, "blob": blob, "tools": visible_tools}


def fidelity(blob: str) -> Dict[str, bool]:
    return {item: item in blob for item in EXPECTS}


def token_counts(texts: List[str], enc) -> List[int]:
    return [len(enc.encode(text, disallowed_special=())) for text in texts]


def run(enc=None) -> dict:
    turns = build_session()
    off = replay(turns, False)
    on = replay(turns, True)
    result = {
        "turns": len(turns),
        "tokenizer": None,
        "fidelity_on": fidelity(on["blob"]),
        "fidelity_off": fidelity(off["blob"]),
        "cross_project_leak": "BETA_ISOLATION_TOKEN_99" in on["blob"],
        "tool_chars_off": sum(len(t) for t in off["tools"]),
        "tool_chars_on": sum(len(t) for t in on["tools"]),
        "final_chars_off": len(off["blob"]),
        "final_chars_on": len(on["blob"]),
    }
    result["fidelity_on_hits"] = sum(1 for ok in result["fidelity_on"].values() if ok)
    result["fidelity_on_n"] = len(EXPECTS)
    if enc is not None:
        off_toks = token_counts(off["per_turn_text"], enc)
        on_toks = token_counts(on["per_turn_text"], enc)
        result["tokenizer"] = "o200k_base"
        result["per_turn_input_tokens_off"] = off_toks
        result["per_turn_input_tokens_on"] = on_toks
        result["sum_input_tokens_off"] = sum(off_toks)
        result["sum_input_tokens_on"] = sum(on_toks)
        result["final_input_tokens_off"] = off_toks[-1]
        result["final_input_tokens_on"] = on_toks[-1]
        result["sum_saved_tokens"] = result["sum_input_tokens_off"] - result["sum_input_tokens_on"]
        result["sum_saved_pct_of_off"] = round(100.0 * result["sum_saved_tokens"] / result["sum_input_tokens_off"], 2)
    result["not_measured"] = [
        "No provider allowance, invoice, or cached_tokens field.",
        "o200k_base is not the Cursor model's tokenizer.",
        "History of user and assistant turns is still resent. Cursor beforeSubmitPrompt cannot replace it.",
        "preCompact cannot change the client's summary.",
    ]
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="atex bench-cursor")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
    except Exception as exc:
        print(f"[atex bench-cursor] tiktoken unavailable: {exc}")
        return 2
    result = run(enc)
    text = json.dumps(result, indent=2)
    if args.out:
        from pathlib import Path
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    ok = (
        result["fidelity_on_hits"] == result["fidelity_on_n"]
        and not result["cross_project_leak"]
        and result["sum_input_tokens_on"] < result["sum_input_tokens_off"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
