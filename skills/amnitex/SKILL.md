---
name: amnitex
description: Lossless byte-page memory layer and Fresh-Turn LUT in native Gold/Helium. Always call atex_search, atex_recall, and atex_list_keys FIRST before running grep, find, or reading full files.
---

# AmniTex (Native Gold/Helium Memory & Fresh-Turn LUT)

## Mandatory Retrieval Order

1. **At the start of a turn or when resuming context:** Call `atex_recall(key="conv::latest_state")` to inspect the stateless conversation LUT index (`conv::<id>::turn_<N>`) and active edited files before scanning the repository.
2. **Before running `grep`, `find`, or reading full files:** Call `atex_search(query="...")` or `atex_list_keys(prefix="...")` to locate exact documentation sections, architecture maps, build rules, and prior turn facts in **1.66 µs** via the native Helium spatial `TexGrid`.
3. **When the user teaches a persistent project fact:** Call `atex_remember(key="manual::<topic>", text="...")` so it is stored losslessly in `.atex` across sessions and AI tools.

## Installing the Native Helium Binary

If the `atex` native Helium binary is not yet on `PATH`, install it in one line:

```bash
curl -fsSL https://amni-scient.com/atex-install.sh | sh
```
