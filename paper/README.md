# atex paper

LaTeX source for the arXiv preprint *atex: A Lossless Byte-Page Memory Layer for MCP-Capable AI Coding Assistants*.

## Build

```bash
cd paper
pdflatex atex.tex
pdflatex atex.tex   # second pass for refs
```

Or use any LaTeX environment of your choice (Overleaf, TeX Live, MiKTeX). The document uses standard `article` class plus `geometry`, `booktabs`, `hyperref`, `enumitem`, `listings`, `xcolor`, and `microtype` — all in the LaTeX default trees.

## Files

- `atex.tex` — source
- `atex.pdf` — built PDF (gitignored, regenerable)

## arXiv submission notes

- Categories: `cs.IR` (primary), `cs.CL` (cross-list)
- Length: ~6 pages
- Endorsement: required for first-time cs.* submitters; check status before final submission
- Abstract has been written for arXiv's plain-text abstract field (it copies cleanly with no LaTeX-only macros)

## What's in the paper

- §1 Introduction — the problem, the three existing answer classes, our contributions
- §2 Design — byte-page KB, MCP 5-tool surface, bootstrap auto-config
- §3 Implementation — Windows-safe atomic writes, batched saves, file-handle hygiene
- §4 (= §5 in the source) Evaluation — bench harness with bug-fix story, live RAG validation with qwen2.5:0.5b-instruct, dogfooding case study
- §5 Reproducibility — one-command replay
- §6 Limitations — four most consequential, surfaced during the dogfood loop
- §7 Related Work — mem0, basic-memory, knowledge-graph-memory, vector DBs, RAG
- §8 Conclusion
