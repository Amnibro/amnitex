# What Cursor can and cannot shrink

Fetched 2026-11-09 from [Cursor hooks](https://cursor.com/docs/hooks) and the [cloud-agent hook table](https://cursor.com/docs/hooks) on that page. This is the contract `atex hook cursor` implements.

| Mechanism | What the docs allow | What atex does |
|---|---|---|
| `preToolUse` | `permission` allow/deny, `agent_message` back to the model, `updated_input` for local tools | Denies a `Read`/`Shell cat` of a file over 1,500 characters, or any repeat of a path already sent in that conversation. The model receives a short excerpt instead of the file. |
| `beforeReadFile` | `permission` allow/deny. `user_message` is shown to the user. Invalid JSON blocks the read. | Same size and duplicate rule. This stops the file body from being attached. It does not, by itself, give the model the excerpt. |
| `postToolUse` | `updated_mcp_tool_output` replaces MCP output only. `additional_context` adds text. | Trims MCP output over 800 characters to the kept lines. Non-MCP output is left unchanged. |
| `sessionStart` | `additional_context` is added once | Injects the restored card when one exists. |
| `stop` | May return `followup_message`, which would start another turn | Saves the transcript. Returns `{}` so it does not add a turn. |
| `beforeSubmitPrompt` | Official output is `continue` and `user_message` only. A forum note from Cursor staff says `updated_input` is stripped and does not change the prompt. | Returns `{"continue": true}` and does not claim to rewrite history. |
| `preCompact` | Observational. It cannot change the summary. Output is a `user_message` for the user. | Saves the transcript when a path is present and returns `{}`. |
| Rules (`.cursor/rules/*.mdc`, `alwaysApply`) | Sent with the prompt | One short rule telling the agent not to reread whole files. That rule is a per-turn cost, counted in the benchmark. |
| MCP `atex serve` | The model may call search/recall | Native Helium server. It does not delete history by itself. |

Cloud agents, from the same page: project `.cursor/hooks.json` runs; user `~/.cursor/hooks.json` does not. `sessionStart` is deferred. `postToolUse` on cloud agents gets a redacted tool result and cannot replace it with `updated_mcp_tool_output`. `preToolUse` `updated_input` is ignored for HTTP MCP tools.

User and assistant turns are still resent by Cursor on every ordinary turn. Nothing in the documented hook outputs deletes earlier messages.
