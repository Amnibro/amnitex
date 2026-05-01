# atex v0.1.0 — release checklist

Run-through for the launch. Each step is independent; you can pause at any point.

## Pre-flight (already done — verify only)

```powershell
cd C:\Users\antho\Documents\ai\atex
C:\Users\antho\Documents\ai\Amni-Ai\.venv\Scripts\python.exe -m unittest discover -s tests   # expect: 31 tests OK
C:\Users\antho\Documents\ai\Amni-Ai\.venv\Scripts\python.exe -m atex.cli bench               # expect: recall@1=95%
```

If any of those fail, stop and investigate.

## Step 1 — record the demo GIF (~2 min)

The launch GIF is the "atex demo --model qwen2.5:0.5b-instruct" run that already passed 4/4 on your machine. Re-record it for GitHub:

```powershell
# pick a recorder (any of these work):
#   - https://github.com/charmbracelet/vhs (deterministic, scriptable)
#   - https://obsproject.com (manual, free)
#   - https://www.cockos.com/licecap (Windows-friendly, lightweight)

# the deterministic record script:
.\scripts\record_demo.ps1
# capture the terminal window during the run; trim to ~30 seconds
# save as docs/demo.gif (the README's GIF link points there)
```

If you'd rather skip the GIF for v0.1.0 and add it in v0.1.1 — totally fine. The README already shows the same content as a code block.

## Step 2 — push to GitHub (~3 min)

```powershell
cd C:\Users\antho\Documents\ai\atex
git init
git add -A
git status   # sanity check — should NOT include .atex/ or .atex_metrics.jsonl (gitignored)
git -c user.name=Amnibro -c user.email=99765883+Amnibro@users.noreply.github.com commit -m "atex v0.1.0 - initial public release"
gh repo create Amnibro/amnitex --public --source=. --remote=origin --push --description "Lossless byte-page memory layer for MCP-capable AI coding assistants"
```

GitHub Actions CI should fire automatically on push. Watch the Actions tab — expect green across Win/Mac/Linux × py3.10/3.11/3.12.

If anything red: don't pull-down the repo, just push a fix commit. CI red on a brand-new public repo isn't a launch-blocker — fix it in public.

## Step 3 — publish to PyPI (~3 min)

You'll need `twine` and a PyPI account.

```powershell
C:\Users\antho\Documents\ai\Amni-Ai\.venv\Scripts\python.exe -m pip install --upgrade build twine
cd C:\Users\antho\Documents\ai\atex
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
C:\Users\antho\Documents\ai\Amni-Ai\.venv\Scripts\python.exe -m build
# creates dist/amnitex-0.1.0-py3-none-any.whl and dist/amnitex-0.1.0.tar.gz
C:\Users\antho\Documents\ai\Amni-Ai\.venv\Scripts\python.exe -m twine upload dist/amnitex-0.1.0*
# enter your PyPI API token when prompted
```

Verify: `pip install amnitex` from a fresh shell should pull v0.1.0; the `atex` command becomes available on PATH.

## Step 4 — submit to arXiv (~10 min, blocked on endorsement)

**Endorsement check first.** If you've never published to `cs.*` on arXiv before, you need an endorser. Ask anyone in your network with a prior `cs.IR`, `cs.CL`, or `cs.AI` arXiv submission to endorse you. The endorsement page is at https://arxiv.org/auth/endorse and you supply them with a 6-character code from your account.

Build the PDF:

```powershell
cd C:\Users\antho\Documents\ai\atex\paper
# install MiKTeX or use any LaTeX environment, then:
pdflatex atex.tex
pdflatex atex.tex   # second pass for refs
```

Verify `atex.pdf` builds clean (no LaTeX errors). Then:

1. Go to https://arxiv.org/submit
2. Categories: `cs.IR` (primary), `cs.CL` (cross-list)
3. Title: *atex: A Lossless Byte-Page Memory Layer for MCP-Capable AI Coding Assistants*
4. Authors: Amni-Scient
5. Abstract: paste from `paper/atex.tex` (the `\begin{abstract}...\end{abstract}` block)
6. Upload `atex.tex` + the built `atex.pdf`
7. Submit. arXiv preprint typically goes live in 24-72 hours.

Once the arXiv ID is assigned (e.g. `2605.XXXXX`), update the `@misc` BibTeX entry in `README.md` with `eprint = {2605.XXXXX}, archivePrefix = {arXiv}, primaryClass = {cs.IR}`.

## Step 5 — submit to MCP servers directory (~5 min)

The official MCP servers directory is at https://github.com/modelcontextprotocol/servers.

```powershell
gh repo fork modelcontextprotocol/servers
git clone https://github.com/Amnibro/servers.git mcp-servers-fork
cd mcp-servers-fork
# add an entry to README.md under "Community Servers" with:
#   ### atex
#   A lossless byte-page memory layer. Local, no embeddings, no cloud. MIT.
#   - Repo: https://github.com/Amnibro/amnitex
#   - PyPI: https://pypi.org/project/atex
git -c user.name=Amnibro -c user.email=99765883+Amnibro@users.noreply.github.com checkout -b add-atex
git -c user.name=Amnibro -c user.email=99765883+Amnibro@users.noreply.github.com commit -am "add atex - lossless byte-page memory layer"
git push -u origin add-atex
gh pr create --title "Add atex memory server" --body "Adds atex (https://github.com/Amnibro/amnitex) to the Community Servers list. Lossless byte-page key-value store, MCP-native, no embeddings, MIT-licensed."
```

## Step 6 — Show HN post (~10 min)

Title (under 80 chars): `Show HN: atex – local, lossless memory layer for AI coding assistants`

Body draft (paste into https://news.ycombinator.com/submit):

```
Hi HN — I built atex, a memory layer for AI coding assistants over MCP.

The pain it solves: every assistant forgets your project at session boundaries. Existing
answers (vector DBs, mem0, basic-memory) work but require an embedding model, a service,
or non-trivial config. For exact-recall over coding-project context, you don't need any
of that. atex is a 200-line byte-page key-value store with mmap reads, a JSON address
index, and a 5-tool MCP surface (search, recall, remember, list_keys, stats).

Numbers (from the bench harness in the repo):
- 95% recall@1, 100% recall@3, 100% recall@5 on a 20-query benchmark
- 0.5 ms avg query latency, 8.5 ms p99
- 2 ms cold-start
- Stdlib-only runtime deps, MIT, ~30 KB of Python

Validated end-to-end with qwen2.5:0.5b-instruct via ollama: the 0.5B model retrieves a
validation cookie out of the seeded KB via RAG and quotes it back exactly. 4/4 steps pass
in 5.5 s on commodity hardware. (Spoiler: the 5.5 s is the model, not atex.)

Quirky meta-thing: I dogfooded atex while building atex. 19/19 search hits, 18/18 recall
hits across 7 build iterations. The bench harness caught a real correctness bug in the
retriever (key-first short-circuit suppressing text scores) — fix lifted recall@1 by 25
percentage points. Whole DOGFOOD.md is in the repo.

Repo: https://github.com/Amnibro/amnitex
PyPI: pipx install atex
Paper: https://arxiv.org/abs/<id-once-live>

Happy to answer questions.
```

(Adjust to your voice. The numbers above are real and replayable via `atex bench` and `atex demo --model qwen2.5:0.5b-instruct`.)

## Step 7 — r/LocalLLaMA post (~5 min)

Same content, framed for the local-model crowd:

Title: `atex: a lossless local memory layer for any MCP-capable AI client (works with local Llama/Qwen via ollama)`

Body: emphasize the "works with any local model, no embedding step, MIT" angle. Paste the qwen2.5:0.5b validation output as the proof-of-life.

## Step 8 — X/Twitter (~2 min)

Demo GIF + one-liner + repo link:

> Built `atex` — a lossless local memory layer for AI coding assistants over MCP. 95% recall@1, validated with a 0.5B local model on commodity hardware. MIT, stdlib-only, no embeddings. github.com/Amnibro/amnitex
>
> [GIF: terminal showing `atex demo --model qwen2.5:0.5b-instruct` returning 4/4 PASS]

Tag @AnthropicAI for visibility into the MCP ecosystem.

---

## What to do if something goes sideways

- **PyPI name taken**: rename to `atex-mcp` in `pyproject.toml`, regenerate, retry. Keep the GitHub repo name `atex`.
- **CI red on GitHub**: check the matrix. Most likely cause: a Win-vs-POSIX path quirk. Push a fix commit.
- **arXiv endorsement blocked**: don't let it gate everything else. Ship the GitHub release and Show HN now; submit arXiv when endorsement clears (likely within a week).
- **Show HN flops**: HN is moody. Re-post in 7 days at a different time-of-day (US morning vs evening) if it sinks. Don't post-edit.
- **Demo GIF doesn't capture cleanly**: use the deterministic `scripts/record_demo.ps1` to make the run reproducible, then any screen recorder works.

---

## After launch

- Watch issues at github.com/Amnibro/amnitex/issues
- The dogfood `.atex_metrics.jsonl` log keeps accumulating — at v0.2 cadence (a few weeks), publish a follow-up post with cumulative numbers
- v0.2 priority list (in order): tombstone/delete operation, BM25 / TF-IDF length-normalized scoring, file-watch daemon (`atex watch`), embedding sidecar (optional)
