# Changelog

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
