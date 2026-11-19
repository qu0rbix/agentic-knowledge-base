---
name: ask
description: Use when the owner asks a question about the work context (people, systems, processes, vendors, decisions, preferences, data facts).
---
1. `uv run tools/kb.py search "<key terms>"` in the note language (charter) - translate the question first if needed; on a miss try synonyms, an acronym, or the question's own language. Open only the 1-3 best notes.
2. **A hit is a pointer, not an answer**: answer only from an opened claim about the same entity and scope (a limit for API A does not answer API B). Give the note id and the claim's `[src: ...]`, and its date if it is dated.
   When a claim points to a source for the detail (the frozen schema, a full query output, a table), open that source at its locator and answer from it, citing the note and the source - that is a KB answer, not raw material.
3. A `STALE` line -> say "as of <date>, may be outdated". An `OPEN` line -> mention the open question or dispute.
4. "What was it before / when did it change": `search "<terms>" --in history` and read `history/<note-id>.md`.
5. Not in the notes -> say "not in KB". When useful, search the raw material - `--in sources,reports` (or `--all`: everything except code) - and say "the KB does not say, but source X mentions ...", clearly labelled. Never invent.
6. The owner wants the answer kept: `reports/answers/<today>-<slug>.md` with the answer and the note and source ids behind each statement.
7. Write nothing else while answering. A gap or error you found: offer a candidate or the `fix` skill.
