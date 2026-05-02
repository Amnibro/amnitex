# Changelog

## [0.2.0] — 2026-05-01

### Added — texture-map retrieval backend

- `atex.tex_grid.TexGrid` — texture-shaped inverted index. CPU-only, numpy-optional, no extra runtime deps.
- `atex.tex_retriever.TexRetriever` — drop-in replacement for `KBRetriever` with **O(num_query_tokens)** retrieval (independent of corpus size).
- `auto_grid_dim()` — heuristic auto-sizing so the grid scales with KB size and keeps recall@1 above 95%.
- `atex demo --scenario long-session` — degradation test at rounds 2 / 5 / 50 / 500 / 2000.
- `atex demo --scenario corpus-scale` — KB-size test at 2 / 500 / 50K / 1M tokens.
- 6 new tex-grid tests covering insert, query, overflow, retriever round-trip, lazy build, dynamic add.

### Validated

- Long-session: **100% recall (3/3) at every round count**; round-1 fact recallable at round 2000 in 23 µs with tex-grid.
- Corpus-scale: tex-grid is **425× to 3320× faster** than KB-scan at 1–20K-entry scale; recall@1 95-100% with auto-sized grid.
- 37/37 tests pass on Win/Mac/Linux × py3.10/3.11/3.12.

## [0.1.1] — 2026-05-01

- Fix `pyproject.toml` URLs to point at `Amnibro/amnitex` (the actual GitHub repo); `Amnibro/atex` was a stale placeholder.
- Add `Changelog` URL to project metadata.

## [0.1.0] — 2026-05-01 (initial public release)

### Added

- `atex.kb.KnowledgeBase` — lossless byte-page key-value store with mmap reads, JSON address index, configurable page geometry (default 4096×64×4 = 1 MiB)
- `atex.retriever.KBRetriever` — keyword-overlap retrieval with additive key + text scoring
- `atex.serve` — MCP JSON-RPC 2.0 server exposing 5 tools (`atex_search`, `atex_recall`, `atex_remember`, `atex_list_keys`, `atex_stats`)
- `atex.init` — project-root walker that ingests source files into a `.atex/` directory with auto-generated `.gitignore` rules
- `atex.bootstrap` — auto-detects 6 MCP-capable clients (Claude Desktop, Claude Code, Cursor, Cline, Continue, Zed) and wires them with `[y/N]` consent + automatic backup
- `atex.seed` — 4 self-recall starter entries (`atex_overview`, `atex_faq`, `install_guide`, `clients`) auto-ingested by `atex demo`
- `atex.clients.AtexRagClient` — model-agnostic RAG client wrapping a chat callable
- `atex.clients.ollama` — stdlib-only adapter for local ollama servers with graceful HTTP/connection error wrapping
- `atex.clients.validate` — 4-step validation loop (pre-clear, remember-then-recall, rag-search-finds-fact, rag-answer-quotes-fact)
- `atex.bench` — 20-doc fixed corpus with ground-truth queries, plus `naive-substring-scan` baseline backend
- CLI: `atex {init,serve,stats,demo,bench}` subcommands
- `atex demo --model <ollama-model-name>` runs the live RAG validation loop
- 31-test pytest suite covering KB round-trip, retriever scoring, MCP 7-call round-trip, Sentinel input validation, bootstrap detect/wire/backup/dry-run, seed-ingest, paradigm audit, RAG client, validation loop, ollama probe
- GitHub Actions CI: matrix Win/Mac/Linux × py3.10/3.11/3.12, runs pytest + grep-gate + bench smoke

### Validated

- 7-call MCP JSON-RPC round-trip (initialize → tools/list → atex_stats → atex_search → atex_remember → atex_recall → atex_list_keys → shutdown)
- Sentinel input validation rejects path-traversal keys, regex-violating keys, oversize text payloads
- 4/4 live RAG validation steps pass with `qwen2.5:0.5b-instruct` (5.54 s wall time on commodity hardware)
- Bench numbers: 95% recall@1, 100% recall@3, 100% recall@5 on 20-query benchmark (beats naive substring-scan baseline at 90%/95%/95%)

### Security

- All write-surface inputs validated server-side before reaching `KnowledgeBase.add()`
- Bootstrap config writers require explicit consent and back up the prior config to `<config>.atex-backup-<unix-timestamp>` before any modification
