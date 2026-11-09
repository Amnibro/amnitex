"""Per-turn shrink decisions and the 40-turn tokenizer benchmark."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from atex.bench.cursor_session import EXPECTS, build_session, fidelity, replay, run
from atex.cursor_policy import Seen, handle, visible_tool_text

_BIN = os.environ.get("ATEX_HELIUM_BIN", "/tmp/atex-audit/atex-helium")


class TestPolicy(unittest.TestCase):
    def test_submit_and_precompact_do_not_rewrite_the_prompt(self):
        submit = handle({"hook_event_name": "beforeSubmitPrompt", "prompt": "hello"})
        self.assertEqual(submit, {"continue": True})
        self.assertNotIn("additional_context", submit)
        compact = handle({"hook_event_name": "preCompact", "context_tokens": 120000})
        self.assertEqual(compact, {})

    def test_large_read_and_duplicate_are_shorter_and_keep_the_constraint(self):
        body = "head\n" + ("lorem " * 400) + "\nCONSTRAINT: the audit nonce is AUDIT_NONCE_7F3A and must not be rotated.\n"
        seen = Seen()
        first = visible_tool_text({"type": "read", "path": "notes.md", "content": body}, seen, True)
        second = visible_tool_text({"type": "read", "path": "notes.md", "content": body}, seen, False)
        shrunk = visible_tool_text({"type": "read", "path": "notes.md", "content": body}, seen, True)
        self.assertLess(len(first), len(body))
        self.assertIn("AUDIT_NONCE_7F3A", first)
        self.assertEqual(second, body)
        self.assertIn("duplicate", shrunk)
        self.assertLess(len(shrunk), len(body))

    def test_small_file_is_sent_once(self):
        seen = Seen()
        body = "POOL_SIZE=8 in tests/fixtures/sample_project/db.py\n"
        first = visible_tool_text({"type": "read", "path": "db.py", "content": body}, seen, True)
        second = visible_tool_text({"type": "read", "path": "db.py", "content": body}, seen, True)
        self.assertEqual(first, body)
        self.assertIn("duplicate", second)


class TestBenchmark(unittest.TestCase):
    def test_forty_turns_save_tokens_and_keep_facts(self):
        try:
            import tiktoken
        except ImportError:
            self.skipTest("tiktoken is not installed")
        enc = tiktoken.get_encoding("o200k_base")
        result = run(enc)
        self.assertEqual(result["turns"], 40)
        self.assertEqual(result["fidelity_on_hits"], result["fidelity_on_n"])
        self.assertFalse(result["cross_project_leak"])
        self.assertLess(result["sum_input_tokens_on"], result["sum_input_tokens_off"])
        self.assertLess(result["tool_chars_on"], result["tool_chars_off"] / 2)
        missing = [item for item, ok in result["fidelity_on"].items() if not ok]
        self.assertEqual(missing, [], missing)
        for item in EXPECTS:
            self.assertIn(item, result["fidelity_on"])


class TestNativeHook(unittest.TestCase):
    def test_binary_matches_the_shrink_decision(self):
        binary = Path(_BIN)
        if not binary.is_file():
            self.skipTest(f"native binary not built at {binary}")
        tmp = Path(tempfile.mkdtemp(prefix="atex_native_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        notes = tmp / "notes.txt"
        notes.write_text("head\n" + ("lorem " * 400) + "\nCONSTRAINT: keep NATIVE_NONCE_4455 exact.\n", encoding="utf-8")
        kb = tmp / "kb"
        subprocess.run([str(binary), "init", str(tmp), "--atex-dir", str(kb)], check=True, capture_output=True, text=True)
        payload = json.dumps({
            "hook_event_name": "preToolUse",
            "conversation_id": "native-1",
            "tool_name": "Read",
            "tool_input": {"path": str(notes)},
        })
        proc = subprocess.run([str(binary), "hook", "cursor", "--atex-dir", str(kb)], input=payload, capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        self.assertEqual(out["permission"], "deny")
        self.assertIn("NATIVE_NONCE_4455", out["agent_message"])
        self.assertLess(len(out["agent_message"]), notes.stat().st_size)
        submit = subprocess.run(
            [str(binary), "hook", "cursor", "--atex-dir", str(kb)],
            input=json.dumps({"hook_event_name": "beforeSubmitPrompt", "prompt": "x"}),
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(submit.stdout), {"continue": True})
        tools = subprocess.run(
            [str(binary), "serve", "--atex-dir", str(kb)],
            input='{"jsonrpc":"2.0","id":1,"method":"initialize"}\n{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n',
            capture_output=True, text=True, check=True,
        )
        second = tools.stdout.splitlines()[1]
        parsed = json.loads(second)
        self.assertIn("tools", parsed["result"])


class TestReplayShape(unittest.TestCase):
    def test_session_has_forty_turns(self):
        turns = build_session()
        self.assertEqual(len(turns), 40)
        on = replay(turns, True)
        off = replay(turns, False)
        self.assertLess(len(on["blob"]), len(off["blob"]))
        hits = fidelity(on["blob"])
        self.assertTrue(all(hits.values()), hits)
