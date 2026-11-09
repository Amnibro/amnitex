---
name: amnitex
description: Lossless local byte-page memory in native Gold/Helium. Always call atex_search, atex_recall, and atex_list_keys FIRST before running grep, find, or reading full files.
---

# AmniTex (Native Gold/Helium Memory)

## Mandatory Retrieval Order

1. **At the start of a turn or when resuming context:** Read the restored atex card if one was injected. Otherwise call `atex_recall` on `conv::<project>::latest_state`. Full turns, including tool output, are `conv::<project>::turn_<n>`. Recall a turn before reading a whole file.
2. **Before running `grep`, `find`, or reading full files:** Call `atex_search(query="...")` or `atex_list_keys(prefix="...")` to locate exact documentation sections, architecture maps, build rules, and prior turn facts through the native Helium nonce texture LUT.
3. **When the user teaches a persistent project fact:** Call `atex_remember(key="manual::<topic>", text="...")` so it is stored losslessly in `.atex` across sessions and AI tools.

## Reading Results Without Loss

- Each snippet header is `--- key La-b`; `also: L.. (+n)` lists other matching lines in that entry. Fetch any of them with `atex_recall(key, lines="a-b")` instead of reading the file.
- The footer `[+N more: k1 · k2 …; page=X]` enumerates every remaining matching entry. Call `atex_search(query, page=X)` to see them.
- For a literal string (identifier, error text, path), call `atex_search(query="...", exact=true)`; it returns every matching `key:Ln: line` across all stored text, paged.
- A truncated `atex_recall` ends with `rest: lines="a-b"`; pass that range to continue.

## Installing the Native Helium Binary

If the `atex` native Helium binary is not yet on `PATH`, install it in one line:

```bash
curl -fsSL https://amni-scient.com/atex-install.sh | sh
```
