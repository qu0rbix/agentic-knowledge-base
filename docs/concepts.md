# Concepts

A short tour of the moving parts. You do not need any of this to use the KB - the agent follows these rules for you -
but it explains what you see in the files and in the agent's messages.

## The files

| Folder / file | What it holds |
|---|---|
| `charter.md` | Your intent: purpose, scope, the admission test, how much each kind of source is trusted, the conflict rule, the note language. Every filing decision is judged against it. |
| `notes/` | The knowledge. One note per subject (a system, vendor, person, table, process), current claims only. |
| `history/` | Every claim that was replaced, with the date and the reason. Nothing is silently overwritten. |
| `archive/` | Retired notes. |
| `sources/` | Evidence, frozen by code: documents, web pages, query output, and every message you send (`sources/user/`). Never edited. |
| `meta/` | Open questions, parked items, review and audit reports (`meta/audits/`), the forget log. |
| `eval/golden.md` | Questions the KB must keep answering correctly. |
| `work/`, `data/`, `reports/` | Scratch space, data and outputs. `work/` is never cited. |
| `tools/` | The deterministic helpers (`kb.py`, `fetch.py`, hooks) and any tools the KB grows. |
| `kb.toml` | Your settings: note types, review intervals, search options. |

## A claim

A note is a list of claims. Each claim is one fact, written so a stranger understands it, dated if it can change, and
cited by source id and locator:

```markdown
- Node.js 16 reaches end-of-life on 2023-09-11 (as of 2022-06-08). [src: 2022-06-08-nodejs-blog-node16-eol §1]
```

`kb.py check` verifies that the source exists and that every number and date in the claim appears in it (in any
notation: `3,5` and `3.5`, `31 December 2026` and `2026-12-31`). It cannot verify that the claim means what the
source means, or that a newer source has not changed it - that is the reviewer's job.

There are no quotes in notes, except your own words (`[src: user 2024-03-12 "your exact words"]`). Quotes made
notes almost twice as long, and in testing (experiment case E) they made reviews worse: a reviewer confirmed that
the quote was in the cited source instead of asking whether a newer source had changed the fact. The reviewer
therefore reads the newest source on a subject first and the cited one second.

Dense notes (a database table, a system with many settings) can use footnotes so the page stays readable; see
[Data and SQL](workflows.md#data-and-sql).

## Who does what

| | Role |
|---|---|
| **You + the agent** | The conversation. The agent does your work, runs scripts and queries, and files durable facts directly into the notes - citing the source, after searching for what is already there, keeping the old value when something changes. |
| **Reviewer** | A second agent that reads claims cold, next to their sources, and reports evidence problems: a cited source that does not support the claim, a newer source that changed it, a claim stronger than its source (a plan stated as done, "considering" as decided, a dropped condition), a stale value, two notes that contradict each other. It runs when you ask for an **audit** - weekly is a good rhythm - or on every filing if you set `[review] mode = "always"` in `kb.toml`. |

Why not review every filing by default? In the decisive test on real documents (case D), reviewing every filing took
5-8 times as long and cost 3-6 times as much, with no accuracy gain over direct filing; see
[experiments](project/experiments.md). The cheap code checks below run on every commit either way.

## The admission test

A fact gets in only if it passes all seven points in `charter.md`: in scope, durable, not derivable in a minute,
consequential, evidenced, new, and understandable on its own. Most of a meeting transcript fails it, and that is the
point: a typical source yields 0-8 claims.

## Trust and conflicts

Sources have tiers (1 = you and official documents, 4 = forums and marketing). A newer, at least as trustworthy
source supersedes an older claim, which moves to history. When it is not clearly newer or better, the conflict goes to
`meta/open-questions.md` and neither value is filed as current.

## What is enforced by code

These are not instructions the agent may forget; they are checked:

- Sources are never edited, your saved messages cannot be written by an agent, and owner files (charter, settings) change only with your approval (a guard hook blocks it, and a check after every shell command catches scripts).
- Every claim cites an existing source; its numbers and dates must be in that source.
- Every replaced claim is in history.
- Your words are saved by a hook, so the agent cannot invent a quote from you.
- Nothing is committed unless `check` is clean (`kb.py commit` is the only way agents commit; with review mode "always", also only after the reviewer approved exactly this change).
- Messages you send that no claim cites stay out of git.

## Searching

`kb.py search` searches the notes by default. With `--in sources,reports` (or `--all`, everything except code) it
reaches the raw material too. Every result says what it is: a note, a source a note cites (`SOURCE cited by notes/x`),
unreviewed raw material (`RAW`), a disputed candidate (`BLOCKED`), or history. Optional semantic search adds matches by
meaning and across languages ([configuration](configuration.md)).

## Nothing runs on a schedule

There are no cron jobs or background syncs. Every filing is checked when it happens, answers flag stale figures when
they are given, and the reviewer runs when you ask for an audit.
