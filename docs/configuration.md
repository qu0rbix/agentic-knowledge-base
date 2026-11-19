# Configuration

Most of the KB is configured by the setup interview (`init-kb`). This page covers what you might change later.

## `charter.md` - what the KB is for

Purpose, scope, the admission test, source tiers, the conflict rule, the note language and what needs your approval.
Change it by asking the agent ("narrow the scope: no more vendor pricing"); you approve the edit. Every filing
decision follows from it.

## `kb.toml` - settings the tools read

```toml
[notes]
types = ["process", "system", "person", "team", "vendor", "decision", "preference", "topic", "method", "dataset"]

[notes.review_days]   # after how many days a claim counts as stale, per note type
default = 180
vendor = 90
dataset = 365

[review]
mode = "audit"                 # "always": every filing needs an approved review before kb.py commit

[search]
embed = ["notes", "history"]   # what semantic search covers; add "sources", "reports" ... to search raw material by meaning

[fetch]
max_url_length = 300
max_query_length = 100
hosts = []                     # optional allowlist for fetch.py; empty = any public host
```

## Review mode

By default the agent files directly and the reviewer checks the recent filings when you ask for an audit. Set
`mode = "always"` under `[review]` in `kb.toml` to have every filing reviewed before it can be committed - more
thorough, much slower (in testing, a one-line remark took minutes instead of seconds to file). Start with audits;
switch if the weekly audits keep finding real problems.

## Models

The agent uses the model of your Claude Code session; the reviewer uses the same unless you set one. All testing so far
used Claude Haiku in every role (a deliberately weak model). Giving the reviewer a stronger model than the main agent is
the cheapest way to make audits catch more: add `model: sonnet` or `model: opus` to the frontmatter of
`.claude/agents/reviewer.md` (an owner file - you approve the edit).

## Semantic search and reranker (optional)

Keyword search always works and stays the source of truth. Semantic search adds matches by meaning and across
languages. Configure it **outside the KB** - in your OS environment or `~/.config/akb/env` - never in the KB's own
files, which agents can edit:

```
KB_EMBED_URL=https://api.voyageai.com/v1        # or https://api.openai.com/v1, http://localhost:1234/v1 (LM Studio), http://localhost:11434/v1 (Ollama)
KB_EMBED_MODEL=voyage-3.5
KB_EMBED_KEY=...                                 # not needed for local servers
KB_EMBED_QUERY_PREFIX=search_query:              # only for models that need prefixes (nomic, e5, bge ...)
KB_EMBED_DOC_PREFIX=search_document:
KB_RERANK_URL=https://api.voyageai.com/v1/rerank # optional second stage (Voyage, Cohere, Jina, llama-server --reranking)
KB_RERANK_MODEL=rerank-2.5
KB_RERANK_KEY=...
```

Then ask the agent to run `uv run tools/kb.py embed`. Embeddings refresh after every commit.

- **Pick a strong, multilingual model** if you work in more than one language. In our benchmark a weak local model
  (nomic-embed-text v1.5) improved paraphrase recall from 69% to 80%; Qwen3-Embedding-4B lifted Dutch questions on
  English notes from 33% to 87%.
- **Calibrate** once `eval/golden.md` has answers with note ids and at least 20 questions the KB should not answer:
  `uv run tools/kb.py search-eval eval/golden.md --calibrate`. This sets how clearly a meaning-only match must lead
  before it is shown, so "not in KB" stays possible.
- **Privacy**: with a hosted provider, note text and queries (and raw material, if you add it to `embed`) are sent to
  it. A local server keeps everything on your machine. Messages you sent that no claim cites are never embedded.

## Permissions and hooks

`.claude/settings.json` pre-approves the KB's own tools and wires the hooks (guard, capture, session start). Do not
remove the hooks: they are what makes the rules enforceable. Personal additions (an extra allowed command, a local
SQL client) go in `.claude/settings.local.json`, which is not committed.

## Upgrading the scaffold

There is no automatic upgrade yet ([backlog](backlog.md)). Your KB records its template version in
`.akb/version.json`. To take fixes manually, copy `tools/`, `.claude/` (except `settings.local.json`) and
`CONVENTIONS.md` from a newer template, keep your own `charter.md`, `kb.toml` and the `## Project` block of
`CLAUDE.md`, then run `uv run tools/kb.py check`.
