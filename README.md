# atex (amni-tex) — Native Gold/Helium Edition (v0.3.2)

**A lossless local byte-page memory layer for MCP-capable AI coding assistants. It also stores every conversation turn so earlier facts can be recalled exactly.**
Written in [Gold](https://github.com/Amnibro/gold) and compiled to native [Helium](https://github.com/Amnibro/helium). Local. No embeddings. No cloud. MIT-licensed. **1.66 µs** keyword lookup through a spatial `TexGrid`. Building the grid plus running 3 searches is `17.5×` faster than the earlier Python version, and the process uses `5.2 MB` RSS.

## Install (Native Helium — One Line)

Installs the native Helium binary (`~/.local/bin/atex`), runs the self-test, indexes your workspace into `~/.atex`, and auto-wires **Claude Code**, **Claude Desktop**, **Cursor**, **Windsurf**, **Grok Build**, **OpenAI Codex**, and **Gemini CLI**:

```bash
curl -fsSL https://amni-scient.com/atex-install.sh | sh
```

Or directly from GitHub Releases:

```bash
curl -fsSL https://github.com/Amnibro/amnitex/releases/latest/download/install.sh | sh
```

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
2. **Conversation turn store (`conv::*`):** Saves every completed turn into `.atex` (`conv::<id>::turn_<N>` and `conv::latest_state`). Prior turns can be pulled back by keyword in **1.66 µs** without loss. The longer-term goal is a "fresh-turn" client that sends only a small fixed window each turn and recalls the rest from atex. **No current assistant client works this way yet**, so the token figures below are projections, not measured savings.

## Numbers

### Projected: fresh-turn window vs. full history & lossy compaction (simulation, not measured)

Reproducible via `./bench_conv_lut_bin` (`bench_conv_lut.gold`, 200 simulated turns, 20 planted ground-truth facts). Every number below is copied from [`conv_lut_bench_results.json`](conv_lut_bench_results.json).

> **What is measured and what is assumed.** Measured: lookup latency, ingest time, and exact recall of the 20 planted facts (each query shares a keyword with its fact). Assumed: all token counts. They come from fixed constants in `bench_conv_lut.gold`: 4,850 tokens per raw turn, 1,750 per discarded turn, a 4,500-token summary block, and a 1,752-token fresh-turn window. The fresh-turn window leaves out the system prompt and tool schemas. The full-history baseline ignores prompt caching, which in practice cuts the cost of repeated prefixes a lot. The `2/20` recall for lossy summaries is a modeled rule, not a run against a real summarizer. A live A/B harness that uses API-reported token usage is in progress.

| Turn | Full history (cumulative input) | Rolling window + lossy summary every 7 turns | **Fresh-turn window (hypothetical)** | **Projected saving vs. full history** |
|-----:|--------------------------------:|---------------------------------------------:|---------------------------:|---------------------------:|
| 5 | 170,970 tok | 29,110 tok | **8,760 tok** | **94.88%** |
| 10 | 463,190 tok | 79,860 tok | **17,520 tok** | **96.22%** |
| 20 | 1,411,380 tok | 211,910 tok | **35,040 tok** | **97.52%** |
| 50 | 7,165,950 tok | 625,370 tok | **87,600 tok** | **98.78%** |
| 100 | 26,456,900 tok | 1,419,650 tok | **175,200 tok** | **99.34%** |
| 200 | 101,413,800 tok | 3,420,440 tok | **350,400 tok** | **99.65%** |

- **200-turn ingest time:** `2.28 ms` total
- **Single-query `TexGrid` lookup:** `1.66 µs`
- **Exact fact recall at turn 200:** `20/20` measured from the atex store (keyword-overlap queries). The `2/20` for lossy summaries is modeled, not measured
- Interactive charts & full writeup: **[amni-scient.com/amnitex-lut.html](https://amni-scient.com/amnitex-lut.html)**

### Measured: lookup benchmark (v0.3.2)

`atex bench bench/lookup_questions.tsv` runs 22 lookups whose answer strings are known. For each one it checks whether the answer text shows up in `atex_search`'s default output (k=3, max_chars=600) and counts the chars returned. The comparison is reading the whole file that holds the answer (capped at 46,080 chars, the size of one `view_file` page) or a 41-line window around it. Results are in [`lookup_bench_results.json`](lookup_bench_results.json).

| Method | Answer in output | Chars returned (22 lookups) |
|---|---:|---:|
| atex v0.3.1 search, repo KB (114 entries) | 5/22 | 43,582 |
| **atex v0.3.2 search, repo KB** | **15/22** | **35,067** |
| atex v0.3.1 search, author's working KB (~1,000 entries) | 3/22 | 43,673 |
| **atex v0.3.2 search, author's working KB** | **14/22** | **35,529** |
| Read the whole file holding the answer | 22/22 | 604,655 |
| Read ±20 lines around the answer (requires already knowing where it is) | 22/22 | 48,010 |

Caveats: the author wrote these questions and tuned the ranker against them, so treat them as a smoke test, not a held-out evaluation. "Answer in output" means the text appears in the output; it does not measure whether a model finished a task. When atex misses (7 of 22 here), the model still has to fall back to grep/read, so those chars are extra cost.

What changed in v0.3.2: IDF term weighting (common words like "build" no longer dominate), each entry counted once per term, digits and plurals indexed, results filtered by confidence, snippets with line ranges instead of file heads, and `atex init` now walks 5 directory levels.

### Claude Code turn hooks (v0.3.2)

`atex install` (or the Claude Code plugin's `hooks/hooks.json`) adds two hooks:

- **Stop** → `atex hook stop` saves the turn's user prompt, final assistant text and touched files as `conv::<project>::turn_<N>`, and refreshes `conv::<project>::latest_state`.
- **SessionStart** (only on `/clear` or compaction) → `atex hook start` injects `latest_state`: the last three turns, with the newest capped at 2,400 chars and the two before it at 900. In a test on real transcripts it was 4,391 bytes (~1.1K tokens). Normal startup injects nothing.

This lets you `/clear` whenever the context gets heavy and carry on with recent state, with older turns retrievable through `atex_recall`/`atex_search`. The saving comes from clearing more often. How much it saves in practice has not been measured on live API usage yet.

### Scale-validated retrieval (v0.2.0 spatial tex-grid)

The default retriever is keyword-scan (O(N), simple). v0.2 adds a **spatial tex-grid** backend (O(num_query_tokens), texture-shaped inverted index, CPU-only, no extra deps).

**Corpus-scale (20 queries per cell, auto-sized tex-grid):**

| Tokens | Entries  | KB-scan recall@1 | tex-grid recall@1 | KB-scan avg query | **tex-grid avg query** | **Speedup** |
|-------:|---------:|------------------|-------------------|------------------:|-----------------------:|------------:|
| 2      | 1        | 100%             | 100%              | 6.4 ms            | **0.015 ms**           | **425×**    |
| 500    | 10       | 100%             | 100%              | 6.7 ms            | **0.004 ms**           | **1675×**   |
| 50K    | 1,000    | 100%             | 95%               | 0.85 ms           | **0.004 ms**           | **212×**    |
| 1M     | 20,000   | 100%             | **100%**          | 24.3 ms           | **0.004 ms**           | **6075×**   |

Tex-grid maintains 95-100% recall@1 across four orders of magnitude of corpus size, with sub-microsecond query latency. KB-scan stays at 100% because it's exhaustive but at 1M tokens its average query is **24 ms** (linear in corpus size); tex-grid stays at **4 µs** because it's keyed by query length, not KB size.

**Long-session (no context degradation, 5 round-counts × 2 backends):**

| Rounds | Recall (probe round 1, mid, last) | KB-scan p99 | tex-grid p99 |
|-------:|-----------------------------------|------------:|-------------:|
| 2      | **3/3 ✓**                         | sub-ms      | sub-ms       |
| 5      | **3/3 ✓**                         | sub-ms      | sub-ms       |
| 50     | **3/3 ✓**                         | 2.95 ms     | 0.04 ms      |
| 500    | **3/3 ✓**                         | 3.75 ms     | 0.014 ms     |
| 2000   | **3/3 ✓**                         | 4.93 ms     | 0.023 ms     |

**Round 2000 retrieves the round-1 fact in 23 microseconds** with the tex-grid. Conversation length does not degrade recall — the data lives in the KB, not the model context window.

Replay: `atex demo --scenario corpus-scale --out scale.json` and `atex demo --scenario long-session --out session.json`.

### 20-query smoke (v0.1)

|                           | atex (KB-scan) | naive substring scan |
|---------------------------|----:|---------------------:|
| recall@1 (20-query bench) | **95%** |                  90% |
| recall@3                  | **100%** |                  95% |
| recall@5                  | **100%** |                  95% |
| avg query latency         | 0.5 ms |              0.05 ms |
| p99 query latency         | 8.5 ms |               1.0 ms |

Replay: `atex bench`. Full numbers in [`bench_results.md`](bench_results.md), source in `atex/bench/`.

## Validated end-to-end with a 0.5B open-source model

```
$ ollama pull qwen2.5:0.5b-instruct
$ atex demo --model qwen2.5:0.5b-instruct
[atex-validate] model=qwen2.5:0.5b-instruct steps=4 pass=4 fail=0 wall=5.54s
  ✓ pre-clear: probe key cleared: True
  ✓ remember-then-recall: wrote 103 bytes; round-trip exact-match=True
  ✓ rag-search-finds-fact: top_keys=['manual::atex-validation-probe', ...]
  ✓ rag-answer-quotes-fact: answer='The validation cookie value is azure-marmot-7421.'
```

The 0.5B model retrieved the validation cookie out of the seeded `atex` knowledge base via RAG and quoted it back exactly. Works with any model your `ollama` server has pulled.

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
| `atex_search(query, k)`       | The assistant should look something up before asking you to re-explain it |
| `atex_recall(key)`            | Exact path lookup, e.g. `project::src/auth.ts` |
| `atex_remember(key, text)`    | You explicitly tell it "remember that X" |
| `atex_list_keys(prefix, max)` | Discover what is known about an area |
| `atex_stats()`                | Inspect KB size / fill |

Server-side validation: `atex_remember` keys must match `^[a-zA-Z0-9_\-./:]{1,256}$`, must not contain `..`, text payload capped at 1 MiB.

## Storage format

Lossless byte-page key-value store. Pages are mem-mappable; the index is JSON. No proprietary formats, no embedding indices, no ML dependencies.

- `.atex/pages/page_<idx>.kb.page` — raw byte stream, default 1 MiB per page (configurable via `ATEX_PAGE_W` / `ATEX_PAGE_H`)
- `.atex/index.json` — entry index `{key: {page_idx, offset, length, meta}}`
- `.atex/manual/` — user-taught facts (kept in git for team sharing)
- `.atex/config.json` — project config (kept in git)

## Reproducibility

```bash
git clone https://github.com/Amnibro/amnitex
cd atex
pip install -e ".[dev]"
pytest                                                    # 31 tests pass in ~6 s
python -m atex.cli bench --out bench.json --md bench.md   # bench numbers above
ollama pull qwen2.5:0.5b-instruct
atex demo --model qwen2.5:0.5b-instruct                   # live RAG validation
```

## Paper

[`paper/atex.tex`](paper/atex.tex) — arXiv preprint draft, cs.IR + cs.CL. The paper expands every number above and includes the full case study of using `atex` to track context while building `atex` (see [`DOGFOOD.md`](DOGFOOD.md)).

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
