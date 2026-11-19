---
name: init-kb
description: Use when charter.md says NOT YET INITIALISED, or the owner says "set up this KB", "initialise", or wants to re-scope the KB's purpose.
---
Goal: turn the owner's intent into the files every later agent relies on. Interview first, write second, keep every answer in the owner's words (the capture hook saves them in `sources/user/`).

## 1. Interview (one topic at a time; offer examples; max ~12 questions)
1. **Purpose** - who uses this KB, for which decisions or recurring work? ("If it works perfectly in 3 months, what can you do that you can't now?")
2. **Must-answer questions** - 10-30 real questions. They become `eval/golden.md`, the KB's tests.
3. **In scope / out of scope** - domains, systems, people, vendors; explicit non-goals.
4. **Sources** - where knowledge comes from and how trustworthy each is (tiers 1-4).
5. **Volatility** - what changes often (prices, owners, versions) and needs dates or short review intervals.
6. **Work** - recurring tasks, reports, data systems and access (seeds for later; build no tools now).
7. **Preferences and languages** - output formats, tone, things to never do; the languages the owner works in, and the ONE language claims are written in (owner quotes stay verbatim). No trigger words or word lists to configure.
8. **Approval** - what the agent may change without asking (e.g. small splits, aliases) and what always needs the owner.
9. **Semantic search (optional)** - keyword search always works; semantic search adds paraphrase and cross-language matching but sends note text and queries to an embedding endpoint: hosted (key), local (LM Studio/Ollama: nothing leaves the machine), or none. Configure only outside the KB (OS environment or `~/.config/akb/env`: `KB_EMBED_URL`, `KB_EMBED_MODEL`, `KB_EMBED_KEY`, optional `KB_RERANK_URL/MODEL/KEY`; see `tools/kbsem.py`). Prefer a strong multilingual model. Raw material (sources, reports) is embedded too if the owner adds it to `[search] embed` in `kb.toml`. Then `uv run tools/kb.py embed`; once `eval/golden.md` has `notes:` ids and 20+ questions the KB should NOT answer, calibrate with `uv run tools/kb.py search-eval eval/golden.md --calibrate`.

## 2. Write (show the owner each file before saving)
- `charter.md`: purpose, scope, admission test (keep the 7 points, add domain non-goals), tiers with the owner's real sources, conflict rule, note language, approval rules, embedding choice and (hosted) its retention policy, must-answer list. Remove the NOT YET INITIALISED line.
- `eval/golden.md`: one line per must-answer question (`Q01 | question | expected answer | category | notes:`), plus 20+ questions the KB should NOT answer (category `out-of-scope`).
- `CLAUDE.md`: replace only the `## Project` block.
- `kb.toml`: domain note types and review intervals if clearly needed.
- `meta/open-questions.md`: anything the owner was unsure about.

## 3. Seed (with the owner's go-ahead)
Ingest 3-10 core documents (`ingest` skill); file the preferences from step 1.7 as candidates. Keep `notes/` flat; folders come later (`refactor`).

## 4. Hand over
`uv run tools/kb.py check`, commit `kb: init` (`kb.py commit`), and tell the owner what was written, the first things to ingest, and that a weekly `audit` (a reviewer agent checking the filings against their sources) keeps it honest.
