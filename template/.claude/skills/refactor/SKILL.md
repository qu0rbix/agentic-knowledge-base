---
name: refactor
description: Use when the KB's structure gets in the way - a search keeps missing, a note is too long, many notes share a theme, notes/ has grown past ~40 files, or the owner asks to reorganise.
---
Structure grows from evidence, never from a plan made up front.

## When (check `uv run tools/kb.py stats`)
- A note > 400 words (`check` warns) -> **split** by sub-subject (one note per entity stays the rule).
- 3+ notes on one theme with no hub, or a folder > 40 notes -> **group** into `notes/<area>/` and/or a hub note.
- Two notes on the same subject -> **merge** (keep the older id, redirect the other in `redirects.tsv`).
- Repeated search misses for a note that exists -> fix its **aliases or title** (no approval needed).

## Steps
1. Propose to the owner: the problem with evidence (stats, missed searches, word counts) and the moves (`old -> new | why`, links affected via `kb.py links <id>`). An explicit owner request for this exact change is the approval. Small splits and alias fixes need none if the charter says so.
2. Execute: `uv run tools/kb.py mv <id> <folder>` for moves (ids never change, links keep working); splits and merges move claims with their citations intact (nothing lost, no history needed for a pure move); renames go in `redirects.tsv`.
3. `kb.py check`, re-run the missed searches (they must hit now), commit `kb: refactor <what>`.
