# atex (amni-tex)

**A lossless byte-page memory layer for MCP-capable AI coding assistants.**
Local. No embeddings. No cloud. MIT-licensed. Zero runtime dependencies beyond stdlib.

> Install name on PyPI is `amnitex`; the command-line tool itself is `atex`.

```bash
pipx install amnitex
cd /path/to/your/project
atex init
atex demo            # auto-detects MCP clients (Claude Desktop, Claude Code, Cursor, Cline, Continue, Zed) and wires the config with [y/N] consent
```

That's it. Restart your AI client; `atex_search`, `atex_recall`, `atex_remember`, `atex_list_keys`, `atex_stats` are now available as tools.

---

## What it does

Every AI coding assistant forgets your project the moment a new session starts. `atex` persists project knowledge to a local lossless byte-page key-value store and exposes it over the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) so any compliant client can call it mid-conversation.

## Numbers

|                           | atex | naive substring scan |
|---------------------------|----:|---------------------:|
| recall@1 (20-query bench) | **95%** |                  90% |
| recall@3                  | **100%** |                  95% |
| recall@5                  | **100%** |                  95% |
| avg query latency         | 0.5 ms |              0.05 ms |
| p99 query latency         | 8.5 ms |               1.0 ms |
| cold-start latency        | 2 ms |                    — |

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
git clone https://github.com/Amnibro/atex
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

Issues and PRs welcome at [github.com/Amnibro/atex](https://github.com/Amnibro/atex). See [DOGFOOD.md](DOGFOOD.md) for the case study of using atex while building atex (19/19 search hits, 18/18 recall hits across the build).
