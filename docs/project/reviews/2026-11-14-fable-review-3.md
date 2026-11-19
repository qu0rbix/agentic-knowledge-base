# Fable review 3: did the cuts break anything? (tags `pre-cut` .. `lean`)

Reviewer: Fable 5.2. The repo was not modified; everything ran in a clone at `lean` (`scratchpad/fr3/akb`) and in throwaway KBs. Reproduction script: `scratchpad/fr3/scripts/r5.py`.
CONFIRMED = run or read today. REASONED = derived, not run.

**Verdict: the cuts are safe.** The suite passes (80 tests, 414 s, CONFIRMED). No agent lost a rule that a code check does not back up, and none of the six core mechanisms is weaker. I found two real bugs in the new search code, one small hole in the commit rule, and a stale root README. The test plan needs five corrections to be runnable headless.

## 1. Lost rules

**No agent is missing a rule it needs.** I compared every deleted line with what each agent still reads.

- **Librarian** (own file, charter, CONVENTIONS): complete. The dropped lines are all enforced by `check` (history entry, quote and number rule, sources only from `sources/`) or shown in the CONVENTIONS example (`History:` line, citation format).
- **Reviewer** (own file, charter): complete. `precheck`, `verify`, `forget-check` and `search --keyword` all exist.
- **Researcher and toolsmith** (CLAUDE.md): shell hygiene and zones now come from CLAUDE.md only, which they read. The toolsmith may write its `method` candidate to `inbox/` (guard zone "open").
- **Main**: the folded `note` and `analysis` steps are in CLAUDE.md. One soft loss: "write for a stranger: full names, since when, scope" is gone. The librarian's cold read catches it, at the cost of a `needs-context` round trip. Count those bounces in the test (section 3) before restoring any text.

**References to removed things (CONFIRMED by grep and by running the commands):**

| Where | Problem | Severity |
|---|---|---|
| Root `README.md` lines 40-56 | Still lists the `note` and `analysis` skills, trigger phrases ("no, ...", "onthoud"), "an errata line", "request log for skill graduation" | Fix: this is what a new owner reads first |
| `audit` skill step 6 | "tools or flags nobody used": `meta/tool-usage.log` is gone, so there is no evidence to use | Minor: drop the step |
| `fix` skill step 2 | `--history` still works (legacy flag), but `ask` teaches `--in history` | Cosmetic: use one |
| `guard.py` docstring, `MUTATING_KB` | Mention `commit-check` and `index`, which no longer exist | Cosmetic |
| `kb.py` | `guard_selftest` text and dead `--sources` flag | Cosmetic |

`kb.py stale` and `kb.py index` now exit 2 and no instruction calls them. `stats --stale --today` works.

## 2. Regressions

**Holds (CONFIRMED):**
- `kb.py commit` commits the reviewed working tree, not the index: a bad version I staged did not reach HEAD.
- It refuses without a review, after any edit following approval, and with a message that does not start with `kb: `.
- An uncited owner message is never tracked; a cited one is added.
- Dropping the Write/Edit post-hook loses nothing. A librarian Write followed by a main shell call gives no violation; a script that touches `notes/` is still caught; main is still blocked from writing `notes/`.

**Problems, most important first:**

1. **Chunking has no size cap (CONFIRMED bug).** A file without blank lines becomes one chunk: a 3,000-line minutes file was sent to the embedding endpoint as a single input of 153,799 characters. A real endpoint rejects or truncates that. A CSV in `data/` behaves the same. Fix: hard-split any paragraph over 700 characters (on line breaks, then by length).
2. **Embedding `sources` sends every owner message to the provider (CONFIRMED).** With `sources` in `[search] embed`, the uncited "private aside" message was sent. Those messages are git-ignored precisely because they are chatter. Fix: exclude `sources/user/` files that no claim cites from embedding, and say so in the init-kb question.
3. **`--all` surfaces unreviewed and rejected text with no label (CONFIRMED).** A claim the reviewer blocked (`inbox/<date>-blocked-...`) and a `work/` guess both came back for "Orion quota". `--in sources` returns uncited owner chatter. Only the path tells the agent what it is. This is the one place where the cuts touch a core mechanism (the reviewer gate), at answer time. Fix: print a fixed tag on every non-note row (`RAW - not reviewed`, and `BLOCKED` for blocked candidates), and exclude uncited `sources/user/` from search by default.
4. **Raw `git commit` inside quotes passes the guard (CONFIRMED).** `bash -c "git add -A && git commit -m x"`, `sh -c '...'`, `git ci` and a `python -c` subprocess all pass the pre-check, and the post-check does not see commits. Before the fix, a quoted commit was gated. This only matters for deliberate evasion, and uncited owner messages stay out either way (git-ignored). I would not add code for it; measure "unreviewed commits" in the test instead.
5. **A message cited only by a rejected candidate is committed (CONFIRMED).** `cited_user_files` reads `inbox/processed/` too. The quote is already in the processed file, so nothing new leaks, but "until a claim cites them" is not exact. Document it or restrict to `notes/`.
6. **Unquoted `kb.py search git commit policy` is refused (CONFIRMED).** Minor; the error message is clear.
7. **Uncited owner messages are never pruned (REASONED).** They pile up on disk and are now searchable. The 14-day prune from review 2 is not implemented.

Older than the cuts, but it will hit the test: after a script appended a line to an uncommitted new note, `kb.py restore` deleted the whole note, including the librarian's unreviewed filing (CONFIRMED).

Not a regression: the embedding refresh after `commit` prints a warning and never fails the commit (REASONED from the code); the 400-word warning fires in `check`.

## 3. The decisive test, adjusted

**Five corrections to the plan:**

1. **Make it runnable headless.**
   - The harness writes `charter.md`, the `## Project` block and `kb.toml` before session 1 (no init-kb).
   - Add `Bash(uv run python work/:*)` and the PowerShell twin to `--allowedTools` in every arm; otherwise each analysis script is a denied prompt.
   - Drop session 14 (web research needs WebSearch and network), session 18 (interrupt) and session 27 (refactor).
   - Session 30 uses `stats --stale --today <date>`.
   - Count denied tool calls per session as a friction metric rather than treating them as failures.
2. **Add scope-search questions (10 of the final set).**
   - Six "detail" questions whose answer exists only in raw material, such as an attendee or a minor number in the minutes that fails the admission test. Pass: "not in the KB, but source X says ...", with the source id.
   - Four traps where raw material disagrees with a correct note: a tier-4 blog, a superseded announcement, a candidate the reviewer blocked, an owner message later corrected. Pass: the answer comes from the note.
   - New thresholds: raw-material answers labelled as such 100%; 0 answers that present inbox, work or history text as current.
   - This is where LEAN (`--in`, `--all`) differs from FULL (`--sources` only) and PLAIN (grep).
3. **Keep the arms equal except for the cut.**
   - Same harness-written charter, same messages, same allow list, Haiku in every role.
   - Semantic search off in all filing sessions: a headless run has no embedding server, and a hosted one adds a confound.
   - Test semantic search separately and cheaply: replay only the final question sessions against the finished LEAN KB, keyword versus hybrid. That is the first agent-driven evidence for the feature the owner kept, and it costs two extra sessions.
4. **Measure where a lost rule would show.** Per filing in FULL and LEAN: `needs-context` bounces, review rounds, tool calls, seconds, tokens. A lost rule shows up as more bounces or more majors, not as a wrong claim. Add "unreviewed commits" by comparing `git log` with the review files (item 4 above).
5. **Decide the rule before the run, in counts.** With one replicate and about 35 facts, percentages mean little.
   - LEAN passes if it has at most one more wrong current claim and at most one more missed supersede than FULL, the same or better capture count, and lower cost per filed claim.
   - PLAIN gets the same Haiku, corpus and owner messages, a wiki instruction of about 300 words, no hooks, and the same blind scoring.
   - If one arm must go for budget, drop the second replicates, not PLAIN.

**Minimum corpus (18 documents, enough for the change, language and noise traps):**

| # | Documents | Purpose |
|---|---|---|
| 3 | Node.js Release or TSC meeting minutes, one of them discussing the Node 16 end-of-life change | Low-density sources, recall, detail questions |
| 3 | Node.js announcements: the Node 16 end-of-life date change, two major releases | The real supersede |
| 2 | `nodejs/Release` schedule at two commits | "What was it before" |
| 2 | PostgreSQL versioning policy at two archive dates | A version leaving support mid-timeline |
| 1 | PostgreSQL release announcement with an end-of-life notice | Dates and numbers |
| 1 | PostgreSQL press kit in German or French | Notation and cross-language |
| 2 | One Debian release announcement in English and in Dutch or German | Same fact in two languages (merge, not duplicate) |
| 1 | Debian LTS hand-over announcement | Second supersede type |
| 2 | Tier-4 blog posts with outdated dates | Conflict rule, scope-search trap |
| 1 | Copy of a real document with an injected instruction | Injection |

Verify the three candidate traps against the real pages when building; I have not re-checked them.

With that corpus:
- about 35 time-indexed facts and 8-10 real changes from the schedule and endoflife.date histories;
- 10 scripted owner statements (4 implicit; Dutch, German, French), 1 forget, 1 pasted mail;
- a 15-row inventory CSV with one analysis question asked twice;
- 30 final questions: 12 current, 4 history, 4 not in KB, 6 detail, 4 traps;
- about 14 sessions per arm.

From the case A figures that is roughly 2-3 hours and $2-3 per arm (REASONED, not measured).

## Do before the test

| # | Action | Effort |
|---|---|---|
| 1 | Cap chunk size (2.1) | S |
| 2 | Keep uncited owner messages out of embedding and default search; tag non-note search rows (2.2, 2.3) | S |
| 3 | Fix the root README; drop audit step 6 | S |
| 4 | Nothing else. Items 2.4-2.7 are measured by the test, not fixed first | - |
