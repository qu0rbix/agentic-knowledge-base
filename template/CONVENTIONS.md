# Conventions (change via a proposal in meta/proposals/, approved by the owner)

Markup is fixed syntax in every note language (like YAML keys): `[src: ...]`, `(as of YYYY-MM-DD)`, `since YYYY-MM-DD`, `## Related`, `## Superseded YYYY-MM-DD`, `reason:`, `History:`, `RESOLVED`. Claims are written in the charter's note language; owner quotes stay verbatim in the owner's language.

## Note
`notes/<id>.md`, id = lowercase-kebab, unique across notes/ and archive/, stable forever (renames go in `redirects.tsv`: `old-id<TAB>new-id`).

```
---
id: change-approval
type: process
title: Production change approval
summary: How many approvals a production change needs and who can approve.
aliases: [CAB, change review, deploy approval]
status: current
updated: 2026-09-10
last_verified: 2026-09-10
---
## Claims
- Production changes need 2 approvals since 2026-10-01. [src: 2026-09-29-email-change-policy §Policy]
- Approvers must be from the Data Platform team. [src: user 2026-09-10 "approvers have to be Data Platform people"]

## Related
- [[on-call-rotation]]

History: history/change-approval.md
```

- Types: process system person team vendor decision preference topic method dataset (add more via init-kb).
- One subject per note, and **one note per entity**: a vendor, a person, a team, a system, a customer, a product each get their own note. Cross-cutting topics ("incident handling", "licence costs") are short hub notes that link the entity notes and hold only claims about the topic as a whole.
- Claims are bullets (`-`, `*` or `+`), one fact each, each cited. Link-only lists go under `## Related` (or `## See also`, `## Members`); bullets elsewhere need `[src:]`.
- **Citations are short**: `[src: <id> <locator>]` - the source id plus where in it (`§Policy`, `table 2`, `p. 4`); no quote. Every number and date in a claim must appear in a source it cites (`kb.py check` enforces this, any date notation). Owner statements are the exception: `[src: user <date> "their exact words"]`, because the owner's words are the source. (Why no quotes: a verbatim quote makes a later review confirm the quote instead of asking whether a newer source changed the fact - experiment case E.)
- **Dates**: put `(as of YYYY-MM-DD)` or `since YYYY-MM-DD` on anything that can change. Freshness is per claim: the stamp, else the cited source's date. `last_verified` is set only after re-checking the note's claims against a source.
- Notes over 400 words are split (`kb.py check` warns); folders and hubs come from proposals (`refactor` skill).

**Footnotes** keep dense notes readable: a claim may end with `[^id]` and a `## Sources` block at the bottom holds
`[^id]: [src: <id> <locator>]`. Same rules as inline citations (`kb.py check` expands them). Make the kind visible
in the source id: freeze with
`--slug schema-<table>` or `--slug query-<what>`; owner statements read `user <date>`.

**Examples** (queries, commands): a fenced block indented under its claim bullet, copied verbatim from a frozen source
that claim cites (freeze the query that ran together with its output). `check` fails an example that is not verbatim.

**Table / dataset notes** (`type: dataset`, one per table) hold only what the database cannot tell you - never a copied
column list. Sections: `## Schema` (one claim pointing at the frozen `describe` output, plus grain and keys),
`## Meaning`, `## Joins`, `## Gotchas` (lead with the column name), `## Examples` (at most 3, each saying which
question it answers), `## Related`, `## Sources`. Longer recipes become `method` notes. Freeze schema output and
aggregates, never customer rows or personal data (frozen sources are committed and immutable).

## History (`history/<note-id>.md`)
```
## Superseded 2026-11-13
- <old bullet exactly as it was, with its citation written out inline (expand a footnote)>
reason: changed | source-wrong | scope | filing-error | rewording - <one line>
```
Every claim that leaves a note (edited or removed) must appear in such an entry; `kb.py check` enforces it. Archiving a whole note: `kb.py archive <id> --reason "..."`.

## Forget (`meta/purges.tsv`)
Written by `kb.py forget` (`fix` skill): `date<TAB>id<TAB>reason code`. Lets that removal pass `kb.py check` without a history entry.
