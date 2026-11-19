# Tools registry

| Tool | Run | Purpose | Flags | Added | Last reviewed |
|---|---|---|---|---|---|
| kb | `uv run tools/kb.py --help` | KB bookkeeping: check, verify, precheck, commit, search (`--in <scopes>` / `--all`: notes by default, raw material on request; STALE/OPEN flags), similar, links, stats (`--since`, `--stale`), freeze, coverage, restore, forget, forget-check, new, mv, archive, embed, search-eval | - | template | - |
| fetch | `uv run tools/fetch.py <url> --slug <slug> --tier <1-4>` | Freeze a public http(s) page into `sources/web/<id>.md` with frontmatter + hash; prints the id to cite | `--tier --today --dir` (sources/web or work/) | template | - |
| kbsem | (imported by kb.py) | Optional semantic search and reranker, bring your own key or a local server: embeds note cards, claims and history (plus chunks of the scopes listed in `kb.toml` `[search] embed`); config only outside the KB | env `KB_EMBED_*`, `KB_RERANK_*` | template | - |
| hooks/guard | (PreToolUse; PostToolUse for shell tools; SessionStart) | Protects sources, owner messages, owner and scaffold files; a post-command check catches scripts that write them; agents commit only via `kb.py commit` | - | template | - |
| hooks/capture | (UserPromptSubmit) | Every owner message saved verbatim, with a reminder to judge it in any language | - | template | - |

The scaffold files (kb, kbsem, fetch, hooks) are the owner's. The KB's own tools are added here only for procedures that recur: small, general, with `--help` and a read-only default. One-offs live in `work/`.
