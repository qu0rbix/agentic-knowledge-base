---
name: fix
description: Use when the owner says something in the KB or in your answer is wrong, outdated or has changed - or asks, in any wording or language, to forget or remove something.
---
## Correct
1. Cite the owner's words: `[src: user <today> "their exact words"]` (already saved by the capture hook).
2. Find every affected claim: `uv run tools/kb.py search "<terms>"` (2-3 phrasings, `--in history` for old values) and `uv run tools/kb.py links <note-id>`.
3. Cause: `changed` (true until a date - give the date), `source-wrong`, `scope` (too broad) or `filing-error`.
4. Replace each claim and move the old one to `history/<note-id>.md` with `reason: <cause> - <one line>` (Filing in `CLAUDE.md`). Add a question that would have exposed the error to `eval/golden.md`. `source-wrong`: list the other claims citing that source in `meta/open-questions.md` for re-checking. Commit.

## Forget (for something that must not be kept: filed by mistake, private, never true - not for normal corrections)
1. Find every place it lives: `uv run tools/kb.py forget-check <distinctive words>` (notes, sources, owner messages including the request itself, meta/, caches).
2. `uv run tools/kb.py forget <note-id> <source-id>... <message-id>... --reason owner-request|filed-by-mistake|private|never-true --words <distinctive words>` - it records the purge (as a hash, so the subject's name is not kept), deletes the named sources and messages, and lists what still contains the words.
3. Remove the claims from the notes without a history entry, and clean every file the residue list names (open questions, parking, audit files). Repeat `forget-check` until it prints "not found in the working tree". `kb.py check`, then commit with a neutral message (`kb: forget requested by owner`) - never name the subject.
4. Tell the owner: messages no claim cited never reached git; anything committed earlier is still in git history (`git filter-repo` is their step), in Claude Code's own session transcripts, and - with a hosted embedding provider - was sent to it.
