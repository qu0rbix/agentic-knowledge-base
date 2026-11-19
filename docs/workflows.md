# Workflows

How daily work with the KB goes. In every workflow you talk normally, in any language you set up. The commands shown
are what the agent runs, so you can recognise them in its output; you never need to type them yourself.

- [A normal day](#a-normal-day)
- [Ingest a source](#ingest-a-source)
- [Research to grow the KB](#research-to-grow-the-kb)
- [Co-work: learning while you work](#co-work-learning-while-you-work)
- [Ask a question](#ask-a-question)
- [Correct something, or forget it](#correct-something-or-forget-it)
- [Data and SQL](#data-and-sql)
- [Recurring work and tools](#recurring-work-and-tools)
- [Audit the KB](#audit-the-kb)
- [Refactor the KB](#refactor-the-kb)
- [The weekly rhythm](#the-weekly-rhythm)

## A normal day

1. **Open a session in the KB folder** (`claude`). The first reply mentions anything that needs you - an unfinished
   filing from last time, a commit made outside the KB's tools, or a message of yours from the last days that looks
   worth keeping but was never filed. Say "file that" or "leave it".
2. **Work.** Ask questions, hand over documents, run analyses, think out loud. The agent answers from the KB and keeps
   an eye out for durable facts.
3. **At a natural pause** it files what came up: evidence frozen, claims written with citations, `check` run, committed.
   You get a short report - what was filed, merged, superseded, parked or skipped, and why.
4. **Close the session.** Nothing runs after you leave.

Filing a remark takes under a minute; an ingest of a few documents a few minutes. Questions are answered in seconds.

## Ingest a source

**When:** you have a document worth keeping - meeting notes, a policy, a release announcement, a vendor contract,
query output, a web page.

**You say:** "ingest work/2024-03-12-ops-review.md", "ingest the files in work/batch1/", or "ingest
https://example.com/pricing".

**What happens:**
1. The file is **frozen** into `sources/` by code, byte for byte, with a hash (`kb.py freeze`, or `fetch.py` for a
   page). A date at the start of the file name becomes the source date. Nobody edits it afterwards.
2. The agent picks the claims that pass the admission test - most of a document is not knowledge; 0-8 claims per
   source is normal - and runs a **recall check** (`kb.py coverage`) that lists the sentences it has not used yet, most
   fact-like first, so nothing important is skipped by accident.
3. For each claim it **searches first**: the same fact gets the new citation added; a changed fact replaces the old
   claim, which moves to `history/` with the date and reason; a conflict that is not clearly newer or more trustworthy
   goes to `meta/open-questions.md` and neither value is filed as current.
4. `kb.py check` verifies every citation, number and date; then `kb.py commit`.

**You get:** a report with the sources frozen and what was filed or skipped. A source that tells "AI assistants" to do
something is reported to you, never obeyed.

**Tip:** name files with the date first (`2024-03-12-...`).

## Research to grow the KB

**When:** you want the KB to know about a topic it does not cover yet - a vendor's limits, a library's support policy.

**You say:** "research Postgres logical replication limits" or "find out X's pricing tiers".

**What happens:** the goal becomes 3-6 sub-questions within the charter; what the KB already knows is skipped; the
agent searches the web, prefers primary sources and **freezes every page it cites** (a summary is never evidence);
claims are filed as in ingest; sources that disagree go to open questions instead of a silent pick; prices and limits
need an official source or two independent ones.

**You get:** new claims, a list of what could not be found (in `meta/open-questions.md`) and, if you ask, a narrative
in `reports/research/`.

## Co-work: learning while you work

**When:** always. This is how the KB learns from normal work - a debugging session, a design discussion, an analysis.

**You say:** nothing special. "btw Jonas took over the Fivewire contract", "no, that limit is per second, not per
minute", "vergeet niet dat we upgrades eerst een week op staging draaien".

**What happens:**
1. Every message you send is saved verbatim in `sources/user/` by a hook. That is what lets the KB quote you later
   (`[src: user 2024-03-12 "your exact words"]`) and makes an invented quote impossible.
2. The agent judges each message - there are no trigger words. Durable facts, corrections, preferences and rules are
   filed at the next pause; task status, today's error and small talk are not.
3. What the agent observes itself (a query result, a command's output) is frozen as a source first, then cited.
4. A message that looked like chat but held a durable fact is not lost: the next session's first reply lists your
   recent messages that no claim cites, so you can say "file that one".

**Tip:** when you paste material (an email, a log, query output), say what it is - it is evidence from its author,
not your own statement.

## Ask a question

**You say:** any question about your work context.

**What happens:**
1. The agent searches the notes (translating your question into the note language if needed) and opens the best 1-3.
2. It answers only from a claim about the same thing - a limit for API A does not answer a question about API B - and
   names the note and the source. If a claim points to a fuller source (a schema, a full query output), it opens that
   source and answers from it.
3. Dated or stale claims come with their date ("as of 2023-06, may be outdated"); open disputes are mentioned.
4. Not in the notes: "not in KB". If useful it then searches the raw material (`--in sources,reports` or `--all`) and
   says "the KB does not say, but source X mentions ...", clearly labelled.
5. "What was it before?" questions use the history.

**Tip:** "save that answer" keeps it in `reports/answers/`. A wrong answer? Say so - that starts a correction.

## Correct something, or forget it

**Correct** - "that's wrong: the freeze is 19:00-23:00, not 18:00-22:00", "das stimmt nicht mehr: ...": the agent
finds every affected claim, replaces them, moves the old values to history with the cause (changed, source wrong, too
broad, misread), and adds a question that would have caught the error to `eval/golden.md`.

**Forget** - "forget the Crunchy contract story, it was never true", in any wording: for things that must not be kept
(filed by mistake, private, never true). Claims are removed without history, the sources and messages holding the
content are deleted (including your request, which repeats it), every remaining trace is listed and cleaned until a
search finds nothing, and the purge is recorded as a hash so the subject's name is not kept.

What forget cannot do: content committed earlier stays in git history (rewriting history is your step), and Claude
Code keeps its own session transcripts. Messages no claim ever cited were never committed, so forgetting them leaves
nothing behind.

## Data and SQL

Tables and queries need a little structure to stay readable.

**Schema by reference.** Hand over the schema as a file ("ingest this describe output" for a saved
`describe orders`) or let the agent run and freeze it. The note does **not** copy the column list - the database
already knows it. One claim points to the frozen schema; the note holds what the database cannot tell you.

**A table note** (`type: dataset`, one per table):

```markdown
## Schema     one claim pointing at the frozen describe output, plus grain and keys
## Meaning    what a row is; columns whose name misleads
## Joins      which key, and why not the other one
## Gotchas    status codes, reused ids, soft deletes - lead with the column name
## Examples   at most three, each saying which question it answers
## Related
## Sources    the footnotes
```

**Footnotes keep it readable.** A claim ends with `[^status]` and the citation lives at the bottom
(`[^status]: [src: query-status-counts §1]`). The same checks apply as for inline citations. The
kind of evidence shows in the source name: `schema-orders`, `query-active-accounts`, `user 2024-03-12`; a claim you
stated and a query confirmed carries both.

**Example queries** go in a code block under their claim and must be copied verbatim from a frozen source - the query
that ran, together with its output. Nobody "improves" a query that never ran.

**Never freeze customer rows or personal data** - frozen sources are committed and immutable. Freeze schema output and
aggregates. Answers from data come with the query behind them and the data cut date.

## Recurring work and tools

A one-off is answered with a query or a short script in `work/`. When the same procedure keeps coming back, the agent
saves it as a recipe (a `method` note with the query) or, if it really recurs, a small general tool in `tools/`
(listed in `tools/README.md`). Edge cases become recipes, not flags.

## Audit the KB

**When:** weekly or monthly, before relying on the KB for something important, or after a big change (a
reorganisation, a vendor switch).

**You say:** "audit the KB".

**What happens:**
1. **The reviewer reads every claim filed since the last audit** next to its source and reports evidence problems: a
   cited source that does not support the claim, an overstatement, a stale value (it reads the newest source on the
subject first), a contradiction between notes.
2. Mechanical checks and stale claims; the golden questions answered by a fresh agent; web sources re-fetched to see
   if they changed; clean-up candidates (orphan notes, expired parked items, durable-looking messages never filed).

**You get:** `meta/audits/<date>-audit.md` with at most seven decisions, each with a safe default, plus the reviewer's
findings per 50 claims. Tick what you want; it is applied with the normal filing steps. If the reviewer keeps finding
real problems, switch to `[review] mode = "always"`.

## Refactor the KB

**When:** a note gets too long (the check warns above 400 words), a folder passes ~40 notes, several notes share a
theme without a hub, or searches keep missing the right note.

**You say:** "reorganise the vendor notes into a folder", "split the orion note".

**What happens:** the agent proposes the moves with the evidence (asking for it counts as approval); notes are moved
with `kb.py mv` (ids never change, so links keep working), split or merged with their citations intact; missed
searches are re-run to confirm they now hit. Structure grows from evidence, never from a plan made up front.

## The weekly rhythm

- **"What changed this week?"** (`kb.py stats --since 7d`): new commits, history entries, open questions, refactor
  hints, search misses. Answer open questions; drop or file parked items.
- **"Audit the KB"** - the reviewer's pass over the week's filings. In the first weeks, note how many real problems it
  finds; that tells you whether review should run on every filing.

See also: [Troubleshooting](troubleshooting.md) for the messages you may see, [Configuration](configuration.md) for
settings, review mode and semantic search.
