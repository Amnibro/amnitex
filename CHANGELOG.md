# Changelog

## [0.4.2] — 2026-11-09

### Changed

- `atex_where` now tells assistants to call it before reading whole files.
- The README now focuses on what ships today, and result files from removed code are gone.

## [0.4.1] — 2026-11-09

### Fixed

- The MCP server and `atex bench` reported an old version number. Tests now check both.
- The README no longer points at commands and files that were removed in v0.4.0.

## [0.4.0] — 2026-11-09

### Added

- `atex replay` reads the usage Claude Code logged in your own sessions and models what each setting would have saved, with prompt-cache prices included. It makes no model calls.
- `atex install` now sets Claude Code to compact at about 250K tokens, so context stays bounded. A value you already set is kept, and `atex install --no-compact-window` turns it off.
- A new Bash hook keeps long output on disk. The assistant sees the start, the end, and any error lines, plus the path to the full output.
- `atex uninstall` and `atex doctor` are now native commands, and `atex install` wires Cursor directly.

### Changed

- `atex install` now merges into an existing `~/.claude/settings.json`, replacing old atex hooks and keeping everything else. It used to stop and ask you to edit the file by hand when a `hooks` block existed.
- `atex doctor` reports when hooks and search use different knowledge bases. Saved turns can only be searched when they share one.
- Lookup benchmark questions now cover the native code, so lookup numbers are not comparable with v0.3.6.
- The README now shows input and cost saved separately, with prompt-cache prices included.

### Removed

- The Python engine, CLI, clients and tests. Everything runs on the native binary, and tests are now a Gold program in `tests/`.
- `atex demo` and `atex bench-cursor`, which only existed in Python.

## [0.3.6] — 2026-11-09

### Added

- `atex_where` finds which files hold something, returning file keys, line numbers, and one best line each, with a per-folder count when more files match.
- `atex_recall(key, query="...")` returns only the matching lines in one entry.
- Folders registered with `atex init <folder>` stay current: edited, new, and deleted files are picked up on each lookup without re-indexing. The check backs off on large trees, and your home folder is never registered.
- `atex bench` now reports the new route and a modeled grep route.
- More file types are indexed, including `.tsx`, `.jsx`, `.mjs`, `.cpp`, `.html`, `.css`, and `.sql`.

### Changed

- Searching for an identifier now matches the whole identifier instead of its parts. If it exists nowhere, `atex_where` says so before listing partial matches.
- Re-running `atex init` only stores files that changed.
- Deleted files no longer appear in `atex_recall` or `atex_list_keys`.

## [0.3.5] — 2026-11-09

### Fixed

- Lost writes: sessions sharing one knowledge base could silently overwrite each other. Writes now take a lock that works across processes and across the native and Python engines.
- Missed updates: changes made within the same second went unnoticed by other servers. Servers now compare the index contents.
- Stale search: after an entry was replaced, a running server could still match its old words.
- `atex_remember` no longer reports success when the write failed.
- `atex --selftest` and load failures now exit non-zero, so installers can catch them.
- The Python server now searches facts remembered in the same session, accepts every key the native server accepts, and no longer stores `manual::manual::`.
- `curl | sh` install works again; the installer no longer needs a repository checkout.

### Changed

- Native start time on a 1,276-entry knowledge base drops from about 13 ms to 2 ms.
- `atex --selftest` now checks replaced entries and 8 concurrent writers.
- Python package and server versions now match the native release.

## [0.2.1] — 2026-05-01

- Docs correction: README and `corpus_scale_results.json` now reflect the auto-sized tex-grid measurements. The 1M-token recall@1 is **100%** (was reported as 80% from the pre-auto-sizing baseline); speedup vs keyword-scan at 1M is **6075×** (was 3320×). No code changes — `auto_grid_dim()` was already in 0.2.0.

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
