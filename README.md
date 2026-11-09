# atex (amni-tex) — Native Gold/Helium Edition (v0.4.5)

**A lossless local byte-page memory layer for MCP-capable AI coding assistants. It also stores every conversation turn so earlier facts can be recalled exactly.**
Written in [Gold](https://github.com/Amnibro/gold) and compiled to native [Helium](https://github.com/Amnibro/helium). Local. No embeddings. No cloud. MIT-licensed. Exact-match nonce lookup through an RGBA texture LUT (`index.tex`): a 15 MB knowledge base loads in 22 ms.

## Install (Native Helium — One Line)

Installs the native Helium binary (`~/.local/bin/atex`), runs the self-test, indexes your workspace into `~/.atex`, and auto-wires **Claude Code**, **Claude Desktop**, **Cursor**, **Windsurf**, **Grok Build**, **OpenAI Codex**, and **Gemini CLI**:

```bash
curl -fsSL https://amni-scient.com/atex-install.sh | sh
```

Or directly from GitHub Releases:

```bash
curl -fsSL https://github.com/Amnibro/amnitex/releases/latest/download/install.sh | sh
```

The installer also adds hooks to Claude Code and sets it to compact at about 250K tokens. `atex install --no-compact-window` turns the compact setting off, and `atex uninstall` removes the wiring.

### Install via AI Marketplaces

- **Claude Code Marketplace:**
  ```bash
  /plugin marketplace add Amnibro/amnitex
  /plugin install amnitex@amnitex-marketplace
  ```
- **Claude Desktop (macOS & Linux `.mcpb` Extension):**
  Download [`amnitex.mcpb`](https://github.com/Amnibro/amnitex/releases/latest/download/amnitex.mcpb) and open it in Claude Desktop.
- **Grok Build Marketplace:**
  ```bash
  grok plugin install Amnibro/amnitex --trust
  grok plugin enable amnitex
  ```
- **Gemini CLI / Antigravity:**
  ```bash
  gemini extensions install https://github.com/Amnibro/amnitex
  ```
- **OpenAI Codex / Cursor / Windsurf:**
  Automatically wired by `atex install` (or load `.codex-plugin/plugin.json` / `.cursor-plugin/plugin.json`).

> Marketplace plugin installs register the MCP server as `atex serve`, so the `atex` binary must be on `PATH`. Run the one-line installer first.

---

## What it does

Every AI coding assistant either forgets your project at session boundaries or re-reads the entire growing conversation history on every turn ($O(N^2)$ cumulative token burn), eventually triggering lossy summary compaction that drops exact ports, hashes, and rules.

`atex` targets both problems with a single native Helium binary (`atex_serve.gold` $\rightarrow$ `atex`):
1. **Lossless Byte-Page Store + 2D Spatial `TexGrid`:** Stores project docs, code symbols, and user-taught facts (`manual::*`) in 1 MiB byte-pages (`ATEXKB01`) indexed by a 64-bit FNV-1a 2D spatial texture grid (`TexGrid`). Subword and snake_case tokens are indexed automatically.
2. **Conversation turn store (`conv::*`):** Saves every completed turn into `.atex` (`conv::<id>::turn_<N>` and `conv::latest_state`). Prior turns can be pulled back by keyword through the nonce LUT, without loss.
3. **Bounded context in Claude Code:** Compacts sooner, restores state afterward, and keeps long Bash output on disk with a pointer in context.

## Numbers

### What it saves in real sessions

`atex replay` reads the usage Claude Code logged for each request in your own sessions, shows what fills your context, and models what each setting would have sent, with prompt-cache prices included. It makes no model calls, so it costs nothing to run.

On one person's 20 most recent long sessions (66,241 requests, 18.5B input tokens):

| Setting | Input saved | Cost saved |
|---|---:|---:|
| **Compact at 250K tokens** | 36.6% | 21.2% |
| **That, plus long Bash output kept on disk** | 36.8% | 22.2% |

`atex install` turns on both.

- **This is a model, not a live run.** Run `atex replay` to see your own numbers. It does not count any rework from compacting sooner, and it assumes 30% of hidden Bash output gets read back.
- **Cost** counts input only and uses Claude Opus 5.5 ratios: cache reads at 0.05×, 1-hour cache writes at 2× (what these sessions used), and an 8K-token summary at 5× per compaction. Subscription limits are not published, so your limit may move differently.
- **Compacting sooner keeps context bounded**, so each request stops growing with session length. Claude Code compacts about 33K tokens before its window, so `atex install` sets the window to 283,000.

### Conversation store

Reproducible via `./bench_conv_lut_bin` (`bench_conv_lut.gold`, 200 simulated turns, 20 planted facts):

- **200-turn ingest time:** `2.28 ms` total
- **Single-query `TexGrid` lookup:** `1.66 µs`
- **Exact fact recall at turn 200:** `20/20` (each query shares a keyword with its fact)

### Nonce texture LUT (v0.3.3)

Every unique word, symbol and compound identifier (`snake_case`, `dotted.names`, `kebab-case`, plus their parts) gets a sequential 32-bit nonce. Each nonce's entry list is packed into `index.tex`, an RGBA texture (4096 texels wide, one 32-bit value per texel): an offset table, then a postings table. Lookup is word → nonce → offset texel → postings run, with exact matches and no hash-cell collisions. On startup, atex loads the texture directly and rebuilds it only when the KB changes.

| KB | Unique nonces | Postings | `index.tex` | Cold load | Full rebuild |
|---|---:|---:|---:|---:|---:|
| 15.3 MB, 1,225 entries | 80,420 | 373,558 | 2.9 MB (4096×111 RGBA) | 22 ms | 133 ms |

### Lossless retrieval (v0.3.4)

Every stored byte stays reachable from a search result:

- **Complete enumeration.** `atex_search` ranks every entry containing a query nonce. Confident matches show as snippets; a footer lists every remaining matching key and the `page=N` that returns them. Nothing is dropped by a threshold.
- **Every match location.** Each snippet shows its line range plus `also: L120 L340 (+n)`, the other lines in that entry that match.
- **Line-range recall.** `atex_recall(key, lines="a-b")` returns exactly those lines. Truncated recalls end with the precise remaining range (`rest: lines="58-212"`).
- **Exact mode.** `atex_search(query, exact=true)` scans all stored text for the literal string (case-exact matches first, then case-insensitive) and returns `key:Ln: line` rows, windowed around the match, paged by whole rows.
- **Phrase nonces.** Adjacent query words are joined (`key score` → `key_score`, `keyscore`) and used when that compound exists in the vocabulary.

Ranking: IDF weights over exact nonces, a passage re-rank (query terms found within ±1 line), a bonus for definition lines, plural/`-ies`/`-ed`/`-er` stemming, a code-vocabulary map (directory→dir, environment→env, python→py …), phrase nonces, confidence ordering, line-range snippets, and generated `.amni` files skipped when their `.gold` source is present.

### Find files and lines (v0.3.6)

`atex_where(query)` answers "which files?" with ranked file keys, matching line numbers, and one best line from each. `atex_recall(key, query="...")` then returns only the matching lines in that file.

Results stay current. Folders registered with `atex init <folder>` are checked on each lookup, so edited, new, and deleted files are picked up without re-indexing. A search for an identifier matches the whole identifier; if it exists nowhere, the result says so before listing partial matches.

| Set | `atex_where` + one `atex_recall` | Whole files | Fewer characters |
|---|---:|---:|---:|
| Tuning set (22) | 30,938 | 765,061 | 96% |
| Held-out set (10) | 22,879 | 371,443 | 94% |

Measured with `atex bench <questions.tsv>`, which runs lookups with known answers and no live agent. Counts include a 41-line read at the right spot when the answer has not appeared yet. Results: [`bench/tier_tuning_results.json`](bench/tier_tuning_results.json), [`bench/tier_heldout_results.json`](bench/tier_heldout_results.json).

### Claude Code hooks and settings

`atex install` adds these to `~/.claude/settings.json`, keeping everything else there and saving the old file as `settings.json.atex-backup`. The Claude Code plugin's `hooks/hooks.json` adds the same hooks, but not the compact setting.

- **Stop** → `atex hook stop` saves the turn's prompt, final reply and touched files as `conv::<project>::turn_<N>`, and refreshes `conv::<project>::latest_state`.
- **SessionStart** (on `/clear` or compaction) → `atex hook start` injects `latest_state`, about 1.1K tokens holding the last three turns.
- **PostToolUse** (Bash) → `atex hook tool` keeps a long output on disk. The assistant sees the start, the end, and any error lines, plus a note with the path to the full output. Nothing in the conversation is edited later, so the prompt cache stays valid. Set `ATEX_TOOL_CAP` to change the limit (default 4,200 characters, about 2K tokens), or to `0` to turn this off.
- **`CLAUDE_CODE_AUTO_COMPACT_WINDOW=283000`** → compacts at about 250K tokens. A value you already set is kept. Turn it off with `atex install --no-compact-window`.

### Run a task in small parts

`atex run` keeps context small for one whole task, with no proxy and using your normal Claude Code sign-in:

```bash
atex run --allow-all "Fix the failing tests in src/parser"
```

1. It starts `claude -p` with six tools (`Bash`, `Read`, `Edit`, `Write`, `Grep`, `Glob`) and your `CLAUDE.md` rules, but no MCP servers, plugins, skills or settings hooks.
2. After each tool call it checks how much context has grown. At `--cut` tokens (40,000 by default) it stops the part cleanly.
3. It asks that same session for short notes on what is done, what is left and the next step. The session is resumed from the cache.
4. The next part starts with only the task and those notes. This repeats until the task is finished or `--parts` is reached (30 by default).

| Option | What it does |
|---|---|
| `--cut <tokens>` | Context growth allowed in each part |
| `--parts <n>` | Most parts before stopping (exit code 3) |
| `--allow-all` | Let the agent run any tool without asking (`--dangerously-skip-permissions`). Without it, edits and reads are allowed and everything else, including `Bash`, is refused |
| `-- <flags>` | Passed to `claude`, for example `-- --model sonnet --effort high` |

The final reply goes to standard output, and progress and token counts go to standard error. Each run keeps its prompts, notes and raw logs in `.atex/runs/<id>/`, and saves notes and the result as `run::<id>::part_<n>` and `run::<id>::result`, which `atex_recall` can read later.

A run uses the 5-minute prompt cache. Its cache writes cost 1.25× input instead of the 2× of the 1-hour cache, which is what Claude Code uses on a subscription. Because a run calls the model back to back, the cache stays warm. To choose another lifetime, set `CLAUDE_CODE_PROMPT_CACHE_TTL`.

While a run is going there is no interactive screen and no Remote Control, and nobody can answer the agent's questions. Follow a part with `tail -f` on its log. A cut has a cost: each new part spends calls finding its place again, so a short task costs less with no cuts at all. It needs a POSIX shell, so it does not run on Windows.

`atex doctor` checks the wiring, and `atex uninstall` removes it. Run `/clear` between unrelated tasks. Recent state comes back automatically, and older turns stay available through `atex_recall` / `atex_search`.

## How it differs from other memory layers

|                          | atex | Vector DB (Pinecone / Chroma) | mem0 / basic-memory | "Just paste it"       |
|--------------------------|-----|-------------------------------|---------------------|-----------------------|
| Local                    | yes | no (or self-host)             | yes / hybrid        | yes                   |
| Cost                     | free | $$/mo                         | free / hybrid       | free                  |
| Lossless exact recall    | yes | no (embedding-lossy)          | varies              | yes                   |
| Multi-AI-client (MCP)    | yes | typically one client          | yes                 | every session         |
| Persists across vendors  | yes | per integration               | yes                 | no                    |
| Embedding model required | no  | yes                           | usually yes         | no                    |
| Setup time               | ~10 seconds | hours                         | minutes             | none (but never ends) |

## Tools exposed over MCP

| Tool                          | Use when |
|-------------------------------|-----|
| `atex_search(query, k, max_chars, page, exact)` | Look something up before asking you to re-explain it; `page` walks the full match list, `exact=true` scans raw text |
| `atex_recall(key, max_chars, lines, query)` | Exact key lookup, e.g. `project::src/auth.ts`; `lines="a-b"` returns a line range, `query` returns only the matching lines |
| `atex_remember(key, text)`    | You explicitly tell it "remember that X" |
| `atex_list_keys(prefix, max)` | Discover what is known about an area |
| `atex_stats()`                | Inspect KB size / fill |
| `atex_where(query, k, path)`  | Find which files hold something: file keys, line numbers, one best line each |

Server-side validation: `atex_remember` keys must match `^[a-zA-Z0-9_\-./:(),'—]{1,256}$`, must not contain `..`, text payload capped at 1 MiB.

Several servers and hooks can share one knowledge base. Each write takes a short lock (`write.lock` in the KB folder) and picks up other writers' changes first, so facts are not lost when sessions write at the same moment. A lock left by a crashed process is cleared after 30 seconds. If a write cannot get the lock within 40 seconds, or the folder is read-only, `atex_remember` returns an error instead of reporting success.

## Storage format

Pages only grow for now: each changed file is stored again as a new copy, and the space used by the old copy is not reclaimed. To turn on automatic refresh for a knowledge base made before v0.3.6, run `atex init <folder>` once. Your home folder is never registered, so run it on a project folder.

Lossless byte-page key-value store. Pages are mem-mappable; the index is JSON. No proprietary formats, no embedding indices, no ML dependencies.

- `.atex/pages/page_<idx>.kb.page` — raw byte stream, default 1 MiB per page (configurable via `ATEX_PAGE_W` / `ATEX_PAGE_H`)
- `.atex/index.json` — entry index `{key: {page_idx, offset, length, meta}}`
- `.atex/manual/` — user-taught facts (kept in git for team sharing)
- `.atex/config.json` — project config (kept in git)

## Reproducibility

```bash
git clone https://github.com/Amnibro/amnitex
cd amnitex
sh scripts/build-native.sh ./atex-bin                       # build the native binary
HC_LIB=.helium/hc/lib .helium/build/hc build tests/atex_test.amni -o ./atex-test
./atex-test ./atex-bin .                                    # the Gold test suite
./atex-bin init . --atex-dir ./kb
./atex-bin bench bench/lookup_heldout.tsv --atex-dir ./kb   # lookup numbers above
./atex-bin replay                                           # your own Claude Code sessions
```

## Paper

[`paper/atex.tex`](paper/atex.tex) — arXiv preprint draft, cs.IR + cs.CL, with the full case study of using `atex` to track context while building `atex` (see [`DOGFOOD.md`](DOGFOOD.md)).

## License

MIT — see [LICENSE](LICENSE).

## Citation

```bibtex
@misc{atex2026,
  title  = {atex: A Lossless Byte-Page Memory Layer for MCP-Capable AI Coding Assistants},
  author = {Amni-Scient},
  year   = {2026},
  note   = {arXiv preprint forthcoming}
}
```

## Contributing

Issues and PRs welcome at [github.com/Amnibro/amnitex](https://github.com/Amnibro/amnitex). See [DOGFOOD.md](DOGFOOD.md) for the case study of using atex while building atex (19/19 search hits, 18/18 recall hits across the build).
