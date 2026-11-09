"""Restored-state card, transcript parsing, corrupt index, and client wiring."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from atex.kb import KnowledgeBase, KnowledgeBaseError
from atex.retriever import KBRetriever
from atex.session import ingest_transcript, open_kb, project_slug, restored_card
from atex.wire import install

_REPO = Path(__file__).resolve().parents[1]


def _line(obj) -> str:
    return json.dumps(obj)


def _user(text: str) -> str:
    return _line({"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": text}]}})


def _tool(text: str) -> str:
    return _line({"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": text}]}})


def _asst(text: str) -> str:
    return _line({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}})


def _fixture_transcript() -> str:
    rows = []
    for i in range(1, 41):
        user = f"Status check {i}. Summarize module_{i} without dropping earlier constraints."
        asst = f"Refactored module_{i} state machine and verified zero allocations across hot loop iteration {i * 17}."
        extra = []
        if i == 4:
            asst = "Decision: the standby replica answers on the name marigold. Keep that name exact."
        elif i == 8:
            asst = "CONSTRAINT: the audit nonce is AUDIT_NONCE_7F3A and must not be rotated."
        elif i == 12:
            asst = "Exact code from tests/fixtures/sample_project/auth.py verify:\ndef verify(token:str)->bool:\n    if '.' not in token:return False\n"
        elif i == 16:
            extra.append(_tool(("lorem " * 400) + " spare spool is called marigold-tool and path /tmp/audit/hidden/config.toml end."))
            asst = "Indexer command finished. I did not repeat the tool stdout."
        elif i == 18:
            asst = "ERROR: indexer returned E_PAGE_OVERFLOW_77 when a file exceeded 524288 bytes."
        elif i == 20:
            asst = "Decision: the primary telemetry port is PORT_9471_UDP."
        elif i == 28:
            asst = "The sample pool constant is POOL_SIZE=8 in tests/fixtures/sample_project/db.py. Do not change the fixture."
        elif i == 32:
            asst = "Decision: the primary telemetry port is now PORT_2201_TCP. PORT_9471_UDP is retired."
        elif i == 36:
            asst = "AUDIT_NONCE_7F3A is withdrawn. Forget that nonce; it is no longer in force."
        elif i == 38:
            asst = ("x" * 1200) + " CLIP_FACT_BEYOND_900 is the detail past the older-turn clip."
        elif i == 40:
            asst = ("y" * 2600) + " CLIP_FACT_BEYOND_2400 is the detail past the latest-turn clip."
        rows.append(_user(user))
        rows.extend(extra)
        rows.append(_asst(asst))
    return "\n".join(rows) + "\n"


class TestRestoredCard(unittest.TestCase):
    def test_spaced_transcript_keeps_crucial_details_and_drops_retired_claims(self):
        raw = _fixture_transcript()
        self.assertIn('"type": "user"', raw)
        tmp = Path(tempfile.mkdtemp(prefix="atex_sess_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        kb = KnowledgeBase(tmp / "kb")
        card = ingest_transcript(kb, raw, "/tmp/atex-audit/proj-alpha")
        expects = [
            "marigold",
            "AUDIT_NONCE_7F3A",
            "if '.' not in token:return False",
            "/tmp/audit/hidden/config.toml",
            "marigold-tool",
            "E_PAGE_OVERFLOW_77",
            "PORT_2201_TCP",
            "POOL_SIZE=8",
            "tests/fixtures/sample_project/db.py",
            "CLIP_FACT_BEYOND_900",
            "CLIP_FACT_BEYOND_2400",
            "withdrawn",
        ]
        for item in expects:
            self.assertIn(item, card, item)
        self.assertNotIn("must not be rotated", card)
        self.assertNotIn("the primary telemetry port is PORT_9471_UDP.", card)
        self.assertIn("retired", card)
        self.assertLess(len(card), len(raw) // 2)
        slug = project_slug("/tmp/atex-audit/proj-alpha")
        stored = kb.lookup(f"conv::{slug}::turn_16")
        self.assertIn("/tmp/audit/hidden/config.toml", stored)
        self.assertIn("lorem", stored)

    def test_projects_stay_isolated(self):
        tmp = Path(tempfile.mkdtemp(prefix="atex_iso_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        kb = KnowledgeBase(tmp / "kb")
        alpha = ingest_transcript(kb, _user("hi") + "\n" + _asst("CONSTRAINT: AUDIT_NONCE_7F3A stays here.") + "\n", "/tmp/proj-alpha")
        beta = ingest_transcript(kb, _user("hi") + "\n" + _asst("BETA_ISOLATION_TOKEN_99 belongs only to beta.") + "\n", "/tmp/proj-beta-isolation")
        self.assertIn("AUDIT_NONCE_7F3A", alpha)
        self.assertNotIn("BETA_ISOLATION_TOKEN_99", alpha)
        self.assertIn("BETA_ISOLATION_TOKEN_99", beta)
        self.assertNotIn("AUDIT_NONCE_7F3A", beta)

    def test_compact_json_parses(self):
        raw = json.dumps({"type": "user", "message": {"content": [{"type": "text", "text": "ping"}]}}, separators=(",", ":"))
        raw += "\n" + json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Decision: keep COMPACT_TOKEN_77."}]}}, separators=(",", ":"))
        card = restored_card([(1, "User: ping\nAssistant: Decision: keep COMPACT_TOKEN_77.\n")], "root")
        self.assertIn("COMPACT_TOKEN_77", card)
        tmp = Path(tempfile.mkdtemp(prefix="atex_compact_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        kb = KnowledgeBase(tmp / "kb")
        saved = ingest_transcript(kb, raw + "\n", "/tmp/compact-proj")
        self.assertIn("COMPACT_TOKEN_77", saved)


class TestHookCli(unittest.TestCase):
    def test_stop_then_session_start_and_startup_is_silent(self):
        tmp = Path(tempfile.mkdtemp(prefix="atex_hook_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        transcript = tmp / "t.jsonl"
        transcript.write_text(_user("ping") + "\n" + _asst("Decision: the marker is HOOK_MARKER_42.") + "\n", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(_REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env["HOME"] = str(tmp / "home")
        stop = subprocess.run(
            [sys.executable, "-m", "atex.cli", "hook", "stop", "--atex-dir", str(tmp / "kb")],
            input=json.dumps({"transcript_path": str(transcript), "cwd": str(tmp / "proj")}),
            capture_output=True, text=True, env=env, cwd=str(_REPO),
        )
        self.assertEqual(stop.returncode, 0, stop.stderr)
        self.assertEqual(stop.stdout, "")
        start = subprocess.run(
            [sys.executable, "-m", "atex.cli", "hook", "session-start", "--atex-dir", str(tmp / "kb")],
            input=json.dumps({"session_id": "s1", "composer_mode": "agent", "cwd": str(tmp / "proj")}),
            capture_output=True, text=True, env=env, cwd=str(_REPO),
        )
        self.assertEqual(start.returncode, 0, start.stderr)
        payload = json.loads(start.stdout)
        self.assertIn("HOOK_MARKER_42", payload["additional_context"])
        self.assertIn("HOOK_MARKER_42", payload["hookSpecificOutput"]["additionalContext"])
        startup = subprocess.run(
            [sys.executable, "-m", "atex.cli", "hook", "start", "--atex-dir", str(tmp / "kb")],
            input=json.dumps({"source": "startup", "cwd": str(tmp / "proj")}),
            capture_output=True, text=True, env=env, cwd=str(_REPO),
        )
        self.assertEqual(startup.returncode, 0, startup.stderr)
        self.assertEqual(startup.stdout, "")


class TestCorruptIndex(unittest.TestCase):
    def test_stats_exits_on_truncated_index(self):
        tmp = Path(tempfile.mkdtemp(prefix="atex_bad_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        kb = KnowledgeBase(tmp / "kb")
        kb.add("manual::ok", "hello")
        kb.flush()
        kb.close()
        index = tmp / "kb" / "index.json"
        original = index.read_bytes()
        index.write_bytes(original[:40])
        with self.assertRaises(KnowledgeBaseError):
            open_kb(str(tmp / "kb"))
        env = os.environ.copy()
        env["PYTHONPATH"] = str(_REPO) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "atex.cli", "stats", "--atex-dir", str(tmp / "kb")],
            capture_output=True, text=True, env=env, cwd=str(_REPO),
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("corrupt index.json", proc.stderr)


class TestSearchWindow(unittest.TestCase):
    def test_match_past_the_prefix_is_returned(self):
        tmp = Path(tempfile.mkdtemp(prefix="atex_win_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        kb = KnowledgeBase(tmp / "kb")
        kb.add("manual::tail", ("head word " * 300) + "\nTAIL_SENTINEL_8841 is at the end of the entry.\n")
        kb.flush()
        hit = KBRetriever(str(tmp / "kb")).retrieve("TAIL_SENTINEL_8841", k=1, max_chars_per=400)
        self.assertEqual(len(hit), 1)
        self.assertIn("TAIL_SENTINEL_8841", hit[0][1])
        self.assertLess(len(hit[0][1]), 500)


class TestWire(unittest.TestCase):
    def test_install_writes_cursor_and_grok_without_clobbering(self):
        tmp = Path(tempfile.mkdtemp(prefix="atex_wire_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        cursor = tmp / ".cursor"
        cursor.mkdir()
        (cursor / "hooks.json").write_text(json.dumps({"version": 1, "hooks": {"stop": [{"command": "other-hook"}]}}) + "\n", encoding="utf-8")
        (cursor / "mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "other"}}}) + "\n", encoding="utf-8")
        notes = install(home=str(tmp), atex_dir=str(tmp / "kb"), dry_run=False)
        self.assertTrue(any("Cursor hooks" in n for n in notes))
        self.assertTrue(any("Grok MCP" in n for n in notes))
        hooks = json.loads((cursor / "hooks.json").read_text(encoding="utf-8"))
        commands = [row["command"] for row in hooks["hooks"]["stop"]]
        self.assertIn("other-hook", commands)
        self.assertIn("python3 -m atex.cli hook stop", commands)
        self.assertIn("python3 -m atex.cli hook session-start", [row["command"] for row in hooks["hooks"]["sessionStart"]])
        mcp = json.loads((cursor / "mcp.json").read_text(encoding="utf-8"))
        self.assertIn("other", mcp["mcpServers"])
        self.assertEqual(mcp["mcpServers"]["amnitex"]["args"][-1], str(tmp / "kb"))
        grok = (tmp / ".grok" / "config.toml").read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.amnitex]", grok)
        self.assertIn(str(tmp / "kb"), grok)
        again = install(home=str(tmp), atex_dir=str(tmp / "kb"))
        self.assertTrue(any("already wired" in n for n in again))
        self.assertIn("other-hook", (cursor / "hooks.json").read_text(encoding="utf-8"))
