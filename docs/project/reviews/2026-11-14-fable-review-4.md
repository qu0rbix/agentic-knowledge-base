# Fable review 4: user friendliness and fool-proofing

Reviewer: Fable 5.2. The repository was not modified. Everything ran in throwaway KBs copied from `template/` and in a patched scratch copy. Scripts and outputs are in `<local path>` (`r1.py` mistakes and today's behaviour, `r2.py` the prototype, `r3.py` history, `kb_prototype.patch`).
CONFIRMED = reproduced today. REASONED = derived from the code, not run. Nothing here was run in a live Claude Code session; hooks were replayed.

**Verdict.** For talking, asking, correcting and forgetting the owner has to remember almost nothing: the hooks and gates carry it. It is not yet fool-proof in four places, all outside the agent's own lane: a commit from the owner's terminal, two sessions at once, material pasted into chat, and a filing that stops halfway. Each passes silently today. The SQL-table case needs three small code changes (one of them closes an accuracy hole that exists now) and one layout decision.

## 1. What the owner must know today

| Area | Must the owner know it? | If they don't |
|---|---|---|
| Start `claude` in the KB root, with uv and git installed | Yes | Hooks and settings may not load (REASONED). `check` reports a stale heartbeat only inside Claude Code |
| "set up this KB" | No: the charter marker triggers `init-kb` | The interview asks for 10-30 golden questions plus 20+ questions the KB should not answer, and explains embedding endpoints. A heavy first hour, and never run live (README) |
| Ingest | Give a file path. Pasting is different (section 2) | Pasted text is filed as the owner's own statement |
| Telling facts, correcting, asking | No | Nothing. But each fact costs a librarian and a reviewer run in that turn |
| Forgetting | Only that it is best effort; the `fix` skill tells them | Text stays in earlier commits and transcripts |
| Committing | One rule: never commit yourself | Unreviewed notes enter history, undetected (section 2) |
| Pushing | Yes, the owner's step; no instruction covers it | No backup |
| Upgrading the scaffold | No path exists. `.akb/version.json` is written by `create_kb.py` only, and nothing reads it | Hand-merge of `tools/`, `.claude/` and `CLAUDE.md`, which also holds the owner's `## Project` block |
| Permission prompts | Edits to charter, `CLAUDE.md`, `CONVENTIONS.md`, `kb.toml`, `.claude/`, `tools/`: approve only what you asked for. Any shell command outside `kb.py`, `fetch.py` and read-only git prompts: the SQL client, `uv run python work/...`, `git checkout`, web tools | Prompt fatigue. Case A counted 18 prompts in one ingest before the shell-hygiene rule |
| Guard and gate messages | No: all are written for the agent and name the next command | Two are for the owner and easy to miss: `guard.py clear` "in their own terminal", and `git filter-repo` after a forget |
| Pending work (blocked claims, proposals, open questions) | Yes, and nothing tells them | `stats` runs at session start, but no rule tells the agent to report it |
| Audit | Must remember to ask; nothing is scheduled | Stale claims are still flagged at answer time |

**One finding specific to this machine (CONFIRMED).** The owner's global RTK hook rewrites every Bash command: `rtk rewrite "uv run tools/kb.py verify"` returns `rtk uv run tools/kb.py verify`, and the same for `git status`, `git diff`, `git checkout`.
- The allow rules in `template/.claude/settings.json` match `uv run tools/kb.py:*`. If Claude Code matches rules against the rewritten command, every `kb.py` call prompts (REASONED; check in the first session).
- RTK sits between the evidence and the agent. `kb.py verify` came through intact in my run, but `rtk git diff` is condensed, and `rtk psql` advertises "strip borders, compress tables". A `describe` run through it and redirected to a file would freeze RTK's version (REASONED).
- Exclude the KB folder from RTK, or at least `uv run tools/kb.py` and the SQL client.

## 2. Mistakes a normal user will make

| Mistake | What happens | Caught? | Recovery clear? |
|---|---|---|---|
| Edits a claim in a note by hand | `check` fails twice: number not in quote, and "claim changed ... without a history/ entry". `commit` refuses | Yes (CONFIRMED) | No. The message is written for the librarian. No rule says: restore the file, then file the edit as a correction |
| Adds an indented paragraph under a bullet, after a blank line | Passes `check`, `verify` shows 0 changed claims, search returns it as a note hit | **No (CONFIRMED)** | Accuracy hole, see section 3 |
| `git add -A && git commit` in their own terminal | The unreviewed claim is committed. Afterwards `check` is clean, `precheck` says "review: skip", `stats` says nothing | **No (CONFIRMED)** | Nothing to see. Uncited owner messages stay out (git-ignored) |
| Pastes `describe` output into chat | Saved as an owner message, tier 1. A candidate citing `[src: user ...]` from the paste passes `check --inbox`. `verify` prints no paste warning: the message is under 1,500 characters and matches no hint | **No (CONFIRMED)** | The clean route does not exist: `kb.py freeze sources/user/<id>.md` works but copies the message frontmatter into the source body |
| "Just update the page" | Guard blocks main; the block message names the filing protocol | Yes (case A) | Yes |
| Deletes a note | One "claim removed without history" failure per claim | Yes (CONFIRMED) | Partly. `git checkout -- notes/x.md` passes the guard, but no message suggests it |
| Deletes a source | "source deleted (only the forget flow may delete sources)" | Yes (CONFIRMED) | Yes |
| Renames a note file | `id 'table-x' != filename` | Yes (CONFIRMED) | Partly. Renaming the id too passes `check` and needs a review; links from other notes then break and `redirects.tsv` is not mentioned (REASONED) |
| Two sessions at once | Session A's harmless command is blamed for the note session B's librarian wrote: `BLOCKED ... changed protected files`. `kb.py restore`, which the message offers, **deleted B's note** | **No (CONFIRMED)** | The message says "if you did not make it, ask the owner", so it depends on the agent reading closely |
| Usage runs out after the librarian, before review | The note change stays uncommitted. `stats` shows `inbox_pending: 0` and nothing else. Search serves the unreviewed claim as a normal note hit | **No (CONFIRMED)** | It is reviewed with the next filing, whenever that is |
| Ignores the Stop reminder | Blocks once, then silent in this and later sessions. One `check` warning and `owner_messages_pending: 1` remain | Partly (CONFIRMED) | A fact the owner stated is not filed. No wrong claim results |

## 3. The SQL table case

**The worry is justified (CONFIRMED).** In the case B notes, 59% and 63% of the body characters are citations. For owner tradecraft it is worse, because the quote nearly repeats the claim.

### How today's `kb.py` handles each part of the proposal

| Proposal | Today | Verdict |
|---|---|---|
| Footnotes `[^n]` plus a `## Sources` block | 8 failures on a 2-claim note: definitions are "text outside a claim bullet", claims are "without [src:]". The `3` of `[^3]` is read as a number by `similar` | Sound, with two changes below |
| Provenance grouped by kind in the Sources block | No check can enforce the grouping | Drop it |
| Schema by reference | Works with no change. One pointer claim cites the frozen `describe`. A re-freeze on a later date gives a new source id, and `git diff --no-index` between the two is already allowed. Same-day re-freeze needs another `--slug` | Adopt as is |
| Fenced example under a cited bullet | Not indented: every line fails. Indented directly under the bullet: the SQL is joined into the claim text, so its dates and numbers must be in the quote, and `similar`, `verify` and the embedding all carry the SQL | Needs code |
| Query results as evidence | `"9 | 1204"` fails: quotes need 12 characters. `"2 | 3907 9 | 1204"` passes, because whitespace and pipes are normalised | Works; the message tells the agent |

### Recommendation

1. **Examples: require the block to be verbatim in a source its claim cites.** This is stricter than the proposal and it is what protects accuracy: the librarian cannot "improve" a query that ran. The evidence is one frozen file holding the query and its output. The claim text excludes the block, so the number rule, `similar` and embeddings see only the sentence. `verify` prints the block under the claim.
2. **Close the blank-line hole in the same change.** A blank line must end a bullet. The current test `prev[:1] in " \t"` is true for an empty string, which is the bug.
3. **Footnotes: implement them as expansion inside `claims()`.** Each marker is replaced by its definition at parse time, so `check_evidence`, `verify`, `similar`, staleness and `sem_units` see inline citations and need no change. `norm()` drops markers, so renumbering is not a claim change. A missing or unused footnote fails `check`.
4. **Do not group the Sources block by kind.** Make the kind readable in the source id: freeze with `--slug schema-table-x` and `--slug query-<what>`; owner statements already read `user <date>`. A claim the owner stated and a query confirmed carries both markers, which shows "confirmed in data" at a glance.
5. **History entries stay inline.** A history bullet with a bare `[^3]` passes `check` and loses its evidence (CONFIRMED). Today's code has the same gap: a history bullet with no citation at all passes. One line for the librarian, or a check.
6. **Row-level data.** A frozen query output is immutable and committed. Freeze `describe` output and aggregates, not customer rows; put that in the charter at setup (REASONED).

**Prototype (CONFIRMED).** `kb_prototype.patch` adds a net 46 lines to `kb.py` for items 1-3 and the `verify` display. On a `table-x` note with five footnoted claims, four sections and one example:
- `check` is clean, and converting an inline note to footnotes shows 0 changed claims in `verify`;
- an edited example, a dangling marker, an unused footnote, a changed number under a footnote and the uncited paragraph each fail with a specific message;
- the existing suite passes on the patched copy (83 tests). The patch has no tests of its own yet.

**If the owner wants no parser change yet:** put the citation on an indented line under the claim. This passes today (CONFIRMED) and makes the raw file scannable, though a rendered page still shows citations inline.

**Reviewer and librarian flow.** Unchanged for the reviewer: `verify` prints expanded claims. The librarian gains a two-place edit (marker and definition); `check` catches the mechanical slips. All test evidence so far (cases A-D) is on inline notes, so the first footnoted filings deserve a read.

**One accuracy bug found on the way (CONFIRMED, today's code).** `find_similar` skips every pool entry whose text equals the claim, including history entries. A superseded value that returns word for word gets no `SUPERSEDED` line; reworded, it does. The conflict with the current claim is still shown. Fix: apply the skip to current claims only.

### Structure of a table note

One note per table, `type: dataset`, sections as headings (these pass today):

```
## Schema     one pointer claim to the frozen describe, plus grain and keys
## Meaning    what a row is, what the columns mean where the name misleads
## Joins      which key, and why not the other one
## Gotchas    status codes, reused ids, soft deletes; lead with the column name
## Examples   at most 3, each bullet says which question it answers
## Related
## Sources
```

- The note holds only what the `describe` output cannot give. Admission test point 3 already rejects a copied column list.
- Over 400 words, recipes move to `method` notes (`table-x-active-accounts`), linked under Related. The table note stays the place for meaning and gotchas.
- `dataset = 90` review days will mark owner tradecraft stale every quarter. Raise it, or the owner learns to ignore `STALE`.

## 4. Changes with the most friendliness per unit of complexity

| # | Change | Kind | Fixes |
|---|---|---|---|
| 1 | Five owner rules at the top of the README: start in the KB root; one session per KB; give files, or say what a paste is; never edit `notes/` or commit yourself; approve owner-file edits only when you asked for them | Text | Most of section 2 |
| 2 | One line in `CLAUDE.md`: the first reply of a session reports what `stats` shows as pending, blocked or proposed | Text | Hidden pending work |
| 3 | `stats` reports an uncommitted note change that needs review, and commits touching `notes/` whose subject lacks `kb:` | ~8 lines | Half-finished filing, owner's own commit |
| 4 | `freeze` strips the frontmatter when given a `sources/user/` file; the paste hint also fires on a message with several lines | ~4 lines | Pasted material, without retyping |
| 5 | Example blocks, the blank-line fix and the `similar` fix (section 3) | ~30 lines, tested | SQL case, two accuracy holes |
| 6 | One line in `CLAUDE.md` for a hand edit: restore the file, file the owner's change through `fix` | Text | Hand edits |
| 7 | In a working session, write the candidate at once and file at a pause or before the session ends. A cited message already counts as handled for the Stop hook | Text; measure in week 1 | A librarian and reviewer run after every remark |
| 8 | Move the `## Project` block from `CLAUDE.md` to `charter.md`. An upgrade is then "copy `tools/`, `.claude/`, `CLAUDE.md`, `CONVENTIONS.md`" | Simplification | Upgrading |
| 9 | Take the semantic-search question out of the setup interview; add "which command runs your SQL" and put it on the allow list with `uv run python work/` | Simplification | First hour, prompts |
| 10 | Footnotes (section 3) | ~15 lines | Readability of rendered pages |

I would not build a lock for parallel sessions (rule 1 covers it) or a git pre-commit hook against the owner's own commit (it needs an install step on every creation route; item 3 detects the commit for less).

**Looks friendly, weakens accuracy. Do not do these:**
- Let the main agent make "small" edits to notes, or skip the reviewer for owner statements. Owner remarks get reworded and scoped on the way in, and the reviewer found majors in every batch of case 1.
- Accept hand edits by writing the history entry automatically.
- One shared footnote for many claims, or a citation with no quote ("see the describe output").
- Copy the schema into the note for convenience.
- Relax the 12-character quote or the number rule for tables.
- Keep citations in a sidecar file: claim and evidence must change in one edit.
- Auto-commit at Stop.
- Condense tool output between `verify` and the reviewer.

## 5. Readiness

**Ready for supervised daily use by the owner, one KB, one session, once case D is scored and items 1-6 are in.** Not ready to hand to someone who has not read the five rules. Three things remain unverified and will be exercised on day one: `init-kb` live, a model stronger than Haiku in every role, and the RTK interaction.

**First two weeks:**
1. **Day 1.** Run `init-kb` and keep it short: 10 golden questions, no semantic search. In the first session, count permission prompts and check whether `kb.py` calls prompt under RTK.
2. **Days 1-3.** Three tables. For each: freeze `describe` from a file, then one working session of real remarks. Read every resulting note and its review file in `meta/audits/`.
3. **Keep a friction log**: minutes and cost per filing, prompts per session, `triage` calls per session, anything filed wrongly or not at all. If most triage calls are `task`, let `triage` take several ids.
4. **End of week 1.** Run `git log --format=%s -- notes` and look for subjects without `kb:`. Run `audit`. Decide on footnotes with real pages in hand, and on filing at a pause (item 7) with real timings.
5. **Week 2.** Re-freeze one `describe` and follow a schema change through to the note. Make one correction and one forget on purpose. Push to a private remote. Only then add a second domain.

Stop and fix before continuing if a wrong claim reaches a committed note, or if a session ends with an uncommitted note change that nobody was told about.
