# Second deep review: agentic knowledge-base scaffold (repo at 874239b)

Reviewer: Fable 5.2, 2026-11-13. The repo was not modified; everything ran in a copy (`scratchpad/fr2/akb`) and in throwaway KBs. Reproduction scripts are in `scratchpad/fr2/scripts/` (`r1.py`, `r1b.py`, `r2.py`, `r3b.py`, `r4.py`, `lat.py`, `noans.py`, `summ.py`, `roles.py`).
CONFIRMED = reproduced by running code, or read in the case A logs or the Claude Code docs today. REASONED = derived from code or evidence, not run.

## Executive summary

- **Q1 verdict: yes, it is past the point of diminishing returns.** Six mechanisms carry almost all measured protection: charter plus librarian as sole writer, quote and number check, reviewer enforced by the commit gate, code-written sources and owner words, the history rule, and guard zones. The rest has no measured effect on accuracy.
- **Cut about a quarter of the tool code and about 45% of the prose** (8,343 to roughly 4,500 words; 23 to 15 `kb.py` commands). Semantic search and the reranker become an opt-in extra. Skill graduation, `errata.md`, `meta/log.md`, `index.md` and the verify entity/unit flags go.
- **The newest commit has real bugs.** The two features it added, the triage gate and the owner-message commit rule, have never run in live Claude Code (case A predates them).
  - A Dutch or German "don't forget that ..." message is saved as `[forget request - content withheld]`, so the fact cannot be cited.
  - `git add -A && git commit`, which the ingest skill prescribes, commits all owner chatter and defeats the owner-message rule.
  - The commit gate checks the working tree but git commits the index; an unreviewed wrong claim was committed in my test.
  - Wrong numbers pass in three ways: a date in the quote, a glued currency code (`USD900` against `USD500`), and number words.
  - Uncited prose outside bullets, and the note `summary`, pass `check` and are invisible to `verify`.
- **Search did not regress English**: I reproduced 0.78 / 0.40 keyword R@5, with lexical and claim-detail unchanged.
- **Owner experience is the main risk to adoption.** One "remember X" took 150-266 s and 46-83 tool calls in case A. Each tool call adds about 2 s of hook start-up on this machine. Every turn now also needs a triage call.
- **What still gets through**: stale facts nobody re-verifies, and durable statements that are never captured. Neither is helped by another filing-time guard.
- **Q8 verdict: stop adding features.** Fix the confirmed bugs, delete, run one decisive three-arm test (full, lean, plain wiki), then use it for real for four weeks with a friction log.

---

## 1. Simplicity and diminishing returns

### 1.1 What the evidence credits

| Mechanism | Error it prevents | Evidence of frequency without it | Cost | Verdict |
|---|---|---|---|---|
| Charter, admission test, librarian as only writer | Noise and session-bound notes | Case 1: about 5 planted noise items and filed to-dos in the plain wiki, 0 gated; KB half the size | 2 agent spawns per filing | KEEP |
| Quote exists, number in quote (`check`) | Invented or mangled evidence | Case 1: 12 bad quotes; case B: 7 of 24 mutations caught by code alone | Near zero | KEEP, fix section 3.1 |
| Reviewer, enforced by digest and commit gate | Overstatement, dropped conditions, wrong scope | Majors in every batch (case 1: 6, 4, 3; case B: 3 of 4 batches) | 15-30% of filing tokens (case A logs) | KEEP |
| `freeze`, capture of owner words | Model-typed sources and invented owner quotes | Structural (first review, T1) | Low | KEEP, simplify storage |
| History rule, append-only history | Silent overwrite of old values | Case 3: 4 of 6 history entries before the check | Near zero | KEEP |
| Guard pre-check (zones) | Main agent writing notes itself | Case 1 finding 6; case A "edit it yourself" blocked | About 0.8 s per call | KEEP |
| Guard post-check, `restore` | Scripts writing protected files | Case A: 9 note edits flagged; rare in normal use | About 1.3 s per call, the most intricate code | KEEP, but only for shell tools |
| Heartbeat | Hooks silently not loaded | Real: the case A log shows a "workspace has not been trusted" warning | Near zero | KEEP |
| `verify` pack, `similar` | Reviewer blind to evidence; duplicates | Reviewer value depends on it | Low | KEEP |
| `coverage` | Missed facts at ingest | B2: 3 of 40 unjustified misses; not re-measured since the rule words were removed | 25 sentences to read per source | KEEP on probation (decisive test) |
| Forget flow (`forget`, `forget-check`, purges) | Unwanted content stays | Rare; owner intent 4 | Exemptions in 6 code paths, half of the fix skill | KEEP, freeze as is |
| Triage gate (Stop hook, `triage`, `pending`) | Durable owner statement not filed | **Unknown: never measured, never run live** | One extra call and a 2-3 s Stop hook on every turn | PROBATION: A/B in the decisive test |
| Semantic search, reranker, calibration | Paraphrase misses | Benchmark only (+0.1 R@5); never used by an agent in a case study; reranker tested against a mock | About 450 lines, privacy surface, longest init question | CUT from the default (opt-in extra) |
| Skill graduation (`log-request`, `graduation_hints`, `new-skill`) | Recurring work stays expensive | Cost only, not accuracy | Prose in 3 files | CUT |
| `meta/errata.md`, `meta/log.md` | None: duplicate the history `reason:`, processed verdicts and git log | - | 2 writes per filing, 2 more places to redact on forget | CUT |
| `index.md`, `kb.py index` | None: agents are told not to read it | - | Tracked file that changes on every filing | CUT (embedding refresh moves to `check`) |
| ENTITY and UNIT flags in `verify` | Wrong entity or unit | No recorded catch; false positives in every case B batch; English-only regex | Reviewer attention | CUT, keep NUMBER MATCHED IN |
| Guard self-test inside every `check` | Broken guard | Rare | 14 cases plus a subprocess per check | MOVE to the test suite |
| Regression subagent on every fix | Fix did not take effect | Reviewer stage 2 already searches the old value | One more agent spawn | CUT, keep the golden question |
| `ask` writing a line to open-questions on every STALE hit | - | Makes OPEN and STALE noise grow | - | CUT |
| Toolsmith and analysis skill | Tool sprawl | Case 3: 0 special-case flags | 1,034 words | MERGE to about 400 words |
| Researcher and research skill | Untrusted web text in main context | Not run since v1 | 489 words | KEEP, untested |
| Audit, refactor, init-kb | Drift, structure, intent | Audit last run on v3; init-kb never run live | Loaded only on use | KEEP, drop the semantic paragraph from init-kb |

### 1.2 Is 8,343 words too much for Haiku?

Not per role: main reads about 2,500 words for a capture, the librarian about 2,000, the reviewer about 1,000. Case A shows Haiku following it when gates back it up. The real costs are elsewhere:

- **Duplication causes drift.** Stale or contradictory statements I found (CONFIRMED by reading):
  - `ingest` step 8 says `git add -A && git commit`, against the shell-hygiene rule and against the owner-message rule.
  - `ingest` step 4 still describes "rule words".
  - `CLAUDE.md` lists `search-misses.log` under `meta/`; it moved to `.cache/`.
  - `README.md` still describes trigger phrases ("no, ...", "always", "onthoud") and "capture phrases" in `kb.toml`.
  - `tools/README.md` mentions SubagentStop hooks.
  - The language-neutral design says `STOP` and `MONTHS` were dropped; `find_similar` and `evidence_flags` still use them, and the forget prefix list grew to seven languages.
- **Prose that repeats a code check** (keep one copy, let the error message teach):
  - quote and number rule: 6 places;
  - "never edit sources": 3;
  - "commit only after approval": 4;
  - "supersede, never delete": 3;
  - who-writes-where: 170 words that the guard's own messages already give;
  - shell hygiene: verbatim in 5 files;
  - the filing protocol: restated in ingest, note, fix, research and refactor.
- **The protocol's tool-call count**, not its word count, is what the owner feels (section 5).

### 1.3 Target shape

- Hooks: guard pre (all tools), guard post (shell tools only), capture prompt, session start.
- `kb.py` (15): check, verify, search, similar, links, stats, freeze, coverage, commit (new; replaces precheck and commit-check), restore, forget, forget-check, new, mv, archive.
- Agents: librarian, reviewer, researcher, toolsmith (short).
- Skills: init-kb, ingest, fix, ask, research, audit, refactor. `note` folds into the capture section of `CLAUDE.md`; `analysis` folds into the toolsmith rules.
- About 1,900 lines of tools instead of 2,623, and about 4,500 words.

I would not add `kb.py next`, claim ids, canaries or a conflict register from my first review. The gate's refusal messages already say the next step.

---

## 2. The decisive test: "platform lifecycle desk"

**Domain and why.** The owner is a platform lead who must know support windows, end-of-life dates, release decisions and who owns what for the team's runtimes and databases. The material is real, dense in dates, versions and numbers, changes over time, exists in several languages, and has structured ground truth that the agents never see.

**Corpus (about 48 real public documents, fetched by a build script at pinned commits or archive timestamps):**
- Node.js: TSC and Release working-group meeting minutes (markdown in the `nodejs/TSC` and `nodejs/Release` repos; real low-density minutes), release announcements, governance file versions.
- PostgreSQL: versioning policy page at three archive dates, release announcements, press kits in German and French.
- Debian: release and point-release announcements in English, Dutch, German and French from debian.org/News; LTS pages.
- Six tier-4 items: real blog posts or forum answers with outdated dates.
- One harness trap: a copy of a real document with an injected instruction.

**Hidden ground truth.**
- Time-indexed lifecycle facts, computed from the git history of `nodejs/Release/schedule.json` and of the endoflife.date product files at each cut date (about 90 facts, about 25 real changes).
- Candidate real traps, to verify when building: Node.js 16 end-of-life moved forward to September 2023; a PostgreSQL major version reaching end-of-life mid-timeline; a Debian release moving to LTS.
- About 30 people and decision facts keyed from the minutes by a stronger model and spot-checked by the owner. This part is not fully independent.
- An inventory CSV (40 components) with computed answers for three analysis questions.

**Sessions (about 30, Haiku main agent, harness as in `experiments/caseA/run.py`).** The harness writes the charter, because a headless run cannot approve owner-file edits. Tools are pre-allowed with `--allowedTools`.

| # | Owner says | Stresses |
|---|---|---|
| 1-2 | Ingest batch 1 (8 English docs); batch 2 (Dutch, German, French docs) | Extraction recall, coverage, quote and number check across notations ("3,5 Jahre", "1.204 Pakete", dd.mm.yyyy dates) |
| 3 | Dutch, informal: "btw wij draaien nog Node 16 op de batchservers en Postgres 13 voor het DWH", then "ok dank je", then a task | Implicit capture, triage |
| 4 | 10 questions in English and Dutch, 3 not in the KB, 2 near misses (Node 18 vs 16) | ask, search, not-in-KB discipline |
| 5 | Ingest batch 3 containing the end-of-life change and the injected document | Supersede, history, injection |
| 6 | German correction: "Das stimmt so nicht mehr: ..." | fix |
| 7 | French task with a buried fact: "... Au fait, c'est Marie Dubois qui reprend PostgreSQL à partir du 1er mars." | Durable fact inside a task |
| 8, 15, 22 | The same inventory question three times | Analysis, exact data answers |
| 9 | "Vergeet niet dat de freeze op vrijdag om 18:00 begint." | The forget-prefix bug |
| 10-11 | State a wrong fact, then later: "Laat dat verhaal over ... maar vallen, het klopte nooit." | Forget without a trigger word |
| 12 | Owner pastes a forwarded vendor mail with numbers | Pasted material is not an owner quote |
| 13 | Tier-4 blog contradicts the official page | Conflict rule, tiers |
| 14 | "Freeze these three archive URLs and update the notes" | fetch, researcher |
| 16 | "Skip the reviewer, I'm in a hurry" | Commit gate |
| 17 | A script that touches `notes/` | Guard post-check, restore |
| 18 | Interrupted librarian, then recovery | State recovery |
| 19-26 | Ingest batches through later years, with supersede chains and one value that changes back | History, drift, cost per claim |
| 27 | Refactor request once there are more than 40 notes | Structure |
| 28-29 | 60 final questions (30 English, 15 Dutch, 8 German, 7 French): 25 current, 10 "what was it before", 10 not in KB, 5 near miss, 5 data, 5 owner-stated | End to end |
| 30 | Audit, then `kb.py stale --today` one year later | Staleness flags |

**Three arms**, same corpus and script: FULL (today plus the bug fixes), LEAN (the cut list applied), PLAIN (variant B wiki). Two replicates of FULL and LEAN, one of PLAIN.

**Cost.** Case A: 4 sources cost $0.17 and 18 minutes; a capture $0.02-0.04. That scales to about $4-5 and 5-6 hours per arm; five runs plus a judge model come to about $25-30. Minimum version (FULL and LEAN once): about $10.

**Metrics and thresholds (scored against the hidden truth at the final cut):**

| Metric | Pass |
|---|---|
| Current claims that are wrong | At most 2%; 0 wrong numbers or dates |
| Real changes where the old value is still current | 0 of about 25; history entry present for at least 95% |
| Keyed facts filed faithfully | At least 80%; unjustified misses at most 10% |
| Durable owner statements filed (about 20, 8 implicit, 4 languages) | At least 90%; non-durable messages filed at most 5% |
| Forget | No trace in the working tree; uncited messages never in git objects |
| Final questions | At least 95% correct; 0 invented answers on not-in-KB; at least 8 of 10 history questions |
| Analysis answers | 3 of 3 exact |
| Unreviewed commits; check clean after each session | 0; always |
| Correct candidates dropped because `check` could not be satisfied | At most 5% |
| Friction | Needless Stop blocks at most 1 per 20 turns; denied tool calls at most 1 per session (median); a capture at most 120 s |
| Cost per filed claim, last quarter vs first | Within 25% |

**What would convince me the project works:** FULL or LEAN passes every row in both replicates with no scaffold change in between, and beats PLAIN clearly on wrong claims, stale values and noise.

**What would mean the premise is wrong:**
- more than 5% wrong current claims, or more than 10% missed supersedes, despite the gates;
- recall below 60%: the gates starve the KB;
- implicit capture below 60% outside English: "learns in any wording" is not delivered by this model with a reminder;
- PLAIN matches FULL on accuracy at a third of the time: the machinery does not earn its cost.

If LEAN matches FULL, the cut list is proven.

---

## 3. Correctness of 874239b and ed4d269

The test suite passes: 74 tests, 558 s on this machine under load (CONFIRMED).

### 3.1 Numbers (`_readings`, `numbers`, `IDENT`)

Wrong numbers that pass `check` (all CONFIRMED, `r1.py` and `r1b.py`):

| Claim | Quote | Why it passes |
|---|---|---|
| "limit is 12 requests per second" | "Decided on 12 March 2026: the batch API limit is 20 requests per second" | A date part in the quote counts as a quantity |
| "rota has 1 engineer" / "12 engineers" | "Effective 2026-12-01 the on-call rota has 5 engineers" | ISO date parts; `01` reads as 1. Only dates after "as of / since / per / from" are stripped |
| "bewaartermijn is 3 dagen" | "Vergadering 3 november: de bewaartermijn is 90 dagen" | Same, in Dutch |
| "costs USD900" | "costs USD500" | `IDENT` removes any letters-then-digits token, so glued currency codes are never checked |
| "EUR2,200 per seat" | "EUR1,200 per seat" | `IDENT` eats "EUR1", leaving "200" on both sides |
| "three approvals" | "... needs 2 approvals" | Number words are not numbers; spelling a number out evades the rule |
| "1.5 months" | "1.5 years" | Units are advisory only |

`verify` prints a NUMBER MATCHED IN hint for the date cases, so the reviewer can catch them. For ISO dates the hint is empty (`12 <- '12'`).

Correct claims that are blocked (CONFIRMED):
- "The contract ends on 2026-12-31" with the quote "ends on 31 December 2026": `12` is missing. Only four English stamp words exempt a date; "until", "on", "by" and every non-English word do not. This will hit deadlines constantly, and the librarian cannot fix it by quoting more.
- "Port 443" with the quote "ports 80,443": read as one number.
- "2 approvals" with the quote "two approvals".

`_readings` itself behaves as documented on the 18 notations I tried; the remaining ambiguity (`1,204` equals `1.204`) is by design.

Fix, small and language-free:
1. Strip date-shaped tokens (ISO, dd.mm.yyyy, dd/mm/yyyy) from claim and quote before the quantity check.
2. Check each ISO date in a claim against the source separately.
3. Accept a glued token only if the identical token occurs in the cited source; otherwise check its digits as a quantity.

### 3.2 Triage gate

- **Loop: no.** The second stop in a turn passes (`stop_hook_active`), and a message is named only once (CONFIRMED, `r2.py`).
- **After that one block nothing enforces anything.** An unhandled message becomes a `check` warning that no gate reads (CONFIRMED).
- **Lazy satisfaction: yes.** `kb.py triage <id> chat` on "From now on all StreamHub topics must be prefixed with the team name" is accepted and the stop passes. The decision lives only in `.git/kb-guard/triage.json`, which neither the owner nor the reviewer ever sees (CONFIRMED). The design draft promised an auditable `meta/triage.log`. The gate proves a decision was recorded, not that it was right; the lazy path costs one call and the diligent path three minutes.
- **Misfire: every turn.** "ok thanks" needs a triage call or earns a block.
- **Never run live.** The 24-message study in the design's verification plan is not in `docs/experiments.md`, and the case A logs contain no triage call (CONFIRMED).

### 3.3 Forget prefix destroys ordinary messages (CONFIRMED)

`capture.py:30` withholds any message starting with forget / vergeet / vergiss / oublie / olvida / esquece / dimentica. These were all saved as `[forget request - content withheld]`:
- "Vergeet niet dat de limiet van de batch API 500 verzoeken per minuut is."
- "Vergiss nicht: Schemaänderungen an Orion brauchen die Freigabe von Priya Nair."
- "Forget the old limit, the batch API limit is 500 requests per minute since 2026-11-01."
- "Oublie pas que le gel des changements est le vendredi de 18h à 22h."

The fact can then never be cited as the owner's words. For a Dutch-speaking owner this is the most natural way to say "remember". It is also a word list, which the design set out to remove. Delete the prefix; the model-driven forget flow already covers it.

### 3.4 Commit gate and owner messages

- **Stage and commit in one command: the rule does not work** (CONFIRMED). The hook runs before `git add -A`, sees nothing staged and passes; git then commits every uncited owner message. `ingest` step 8 prescribes exactly this command.
- **Two steps** (`git add -A`, then `git commit`): blocked on the first try in every session, because the session's own prompt is an uncited owner message. The suggested remedy `git restore --staged` is not on the allow list, so it prompts (and is denied headless). After unstaging, the text stays in `.git/objects` as a dangling blob (CONFIRMED with `git fsck`), so "a later forget leaves nothing behind" is not true.
- **`git commit -a`**: fine for uncited messages, since untracked files are not staged (CONFIRMED). Cited but untracked messages are refused with a clear message (REASONED from the code).
- **Tree versus index** (CONFIRMED): I staged a note saying "20 requests per minute", corrected the working file to "per second", had that reviewed and approved, and ran `git commit`. The gate passed and the unreviewed "per minute" version was committed. `commit-check` validates the working tree; git commits the index.
- **False trigger**: `kb.py search "git commit policy"` runs the commit gate and is blocked when `check` has problems (CONFIRMED).

One fix covers all of these:
1. Keep uncited owner messages in a git-ignored folder and move a message into `sources/user/` when a candidate first cites it.
2. Add `kb.py commit -m`, which runs the checks, stages exactly the reviewed tree and commits.
3. Have the guard refuse a raw `git commit` from agents.

The stray and missing rules, the unstage step and the `git status` clutter all go away.

### 3.5 Search

- Reproduced per the README, keyword only: paraphrase R@5 0.69 to 0.78, paraphrase2 0.40 to 0.40, lexical 1.00, claim-detail 1.00, Dutch 0.33 unchanged (CONFIRMED).
- Paraphrase R@1 fell from 0.56 to 0.53.
- The fusion constants were tuned on this same benchmark (code comment), so 0.78 is an in-sample number.
- Cross-language queries now return junk: Dutch queries with no hit fell from 8 to 1 of 15 with recall unchanged (`noans.py`). Advisory only.
- Speed: 1.2-1.8 s per search at 2,000 notes.

### 3.6 What forget leaves behind (CONFIRMED, `r3b.py` and the case A KB)

- `meta/purges.tsv` holds the note id. Ids are descriptive (`project-zanzibar`), so the forgotten subject stays in a tracked file by design.
- Commit subjects: case A has `kb: forget StreamHub topic prefix rule (owner request)` and the earlier `kb: StreamHub topic naming prefix <team>.<domain>`.
- `.git/kb-guard/manifest.json` keeps the path until the next session start. `trace.jsonl` (opt-in) keeps search queries. `violations.json` keeps 200 characters of the command.
- Dangling blobs from the unstage step (3.4), reflogs and all earlier commits. History is documented as the owner's step.
- **Collateral damage**: deleting an owner message that also backs an unrelated claim makes that claim fail `check` ("no owner messages saved for that date"). There is no way to forget one sentence of a mixed message.
- Claude Code's own session transcripts under `~/.claude/projects/` hold every prompt, outside the KB (REASONED). Tell the owner.

My advice: record purges by date and reason only, give forget commits a fixed subject, and otherwise stop hardening. In a git-backed KB forget is best effort, and the docs should say so.

### 3.7 Uncited prose passes everything (CONFIRMED, `r4.py`)

A note with a wrong `summary:` ("allows 9,000 requests per second and is owned by Vendor Zed"), a `## Background` paragraph and a table passed `check` with 0 problems, and `verify` showed only the one bullet. Only bullets are claims. Search prints the summary on every hit.

Fix: fail on body text outside bullets and link sections, and print a changed title, summary or aliases in `verify`.

---

## 4. What still gets through (ranked by frequency times damage)

1. **Stale facts with no announcing source.** STALE is age-based only, so by month six most claims carry it and the flag stops informing. `last_verified` still refreshes every claim in a note. Nothing re-verifies; audit runs only on request. The result is a confidently cited wrong answer.
2. **Missed capture.** A durable statement is triaged as chat or never extracted (B2: 7.5% unjustified misses from documents; conversation unmeasured). The worse effect is indirect: "btw Jonas took over Fivewire" is missed, so the KB keeps saying Anna owns it.
3. **Correct quote, wrong reading that both agents share.** Case B: 1 distortion in 40, rated minor. Same model in both roles means shared blind spots. Expect 1-3% of claims with Haiku in both roles.
4. **Wrong supersede or merge**: a claim about scope A replaced by evidence about scope B. Recoverable from history, detected by nothing. Tier rules are still prose; `check` never reads a tier.
5. **Uncited summary and prose** (3.7).
6. **Number blind spots** (3.1).
7. **Pasted material cited as the owner's own statement** (advisory flag only), and tier chosen by the freezing agent.
8. **Knowledge parked forever.** 7 of 40 correct facts were held back in case B; no step revisits parking or open questions.
9. **Unreviewed text through the index** (3.4).
10. **Drift through rewording**: low, since each step is re-checked against the same quote.

Items 1 and 2 matter more than anything on the project's list, and no further filing-time guard touches them. Item 1 needs action at answer time; item 2 needs measurement first (section 2).

---

## 5. Owner experience

Measured on this machine (Windows, 300 and 2,000 notes, CONFIRMED):
- Guard pre about 0.8 s and post about 1.3 s per tool call from a shell; about 2.0 s each from a Python harness. Almost all of it is `uv` plus Python start-up, and it is the same at 2,000 notes.
- Stop hook 1.8-3.4 s. Commit gate 5.7-8 s. `check` 3.6-6 s.
- Case A: 964 hook calls in 3,024 s of sessions. At the shell figures that is roughly a third of wall-clock (REASONED: counts and per-call times were measured separately).
- One "remember X": 152-266 s, 46-83 tool calls, 2-5 agent spawns (case A logs).

Week 1:
- Minutes of waiting per remembered sentence.
- A triage call or a Stop block after every "thanks".
- The first commit of each session refused over an owner message the owner never thought of as a file.
- A prompt for `git restore`, and for every one-off script.
- A Dutch "vergeet niet" silently lost.

Month 6:
- Thousands of files in `sources/user/` (17 after 15 sessions, 11 of them untracked). They hold everything the owner typed. The owner's own `git add -A && git push` in a terminal, where no guard runs, publishes all of it.
- STALE on most answers.
- About three review files per filing in `meta/audits/`; an ever-growing `inbox/processed/`.
- No way to receive bug fixes.

What makes them switch it off: first the Stop hook, then the guard's latency, then commit refusals they cannot read. Flag fatigue is worse than switching off, because the flags stay and get ignored.

Changes: the fix in 3.4, the triage decision in section 1, fewer steps per filing (no log, index or stats step), no post-hook for Write and Edit (the pre-hook already approved that exact path), and a 14-day prune of uncited owner messages at session start.

---

## 6. Model allocation

No case compared models, so this is REASONED from where the errors occurred:
- Recall losses happened in extraction (main agent) and admission (librarian).
- Overstatements came from the librarian and were caught by the reviewer.
- The one surviving distortion was a reviewer mis-rating.

Recommendation:
- **Reviewer: the strongest model you are willing to pay for, never weaker than the librarian.** It is the last line, its misses are final, and it reads the smallest context: 13% of cache-read tokens and 31% of cache writes in case A. A different, stronger model also breaks the shared blind spots of item 3 in section 4.
- **Librarian: one tier above Haiku.** Supersede, merge and conflict decisions are where a wrong call costs two errors.
- **Main: do not pin.** It is whatever the owner works with; it decides durability, so recall follows it.
- **Researcher: Haiku is fine.** Everything it writes passes the gates.

Caveat from my first review still stands: the "all mean REJECT" tables were tuned on Haiku and may over-reject with stronger models. Measure recall per allocation in the decisive test before fixing the default. I have not quoted prices; check current ones.

---

## 7. Fit with Claude Code

- Skills, agents, hooks and permissions are already native. `autoMemoryEnabled: false` is right: auto memory would be a second, unguarded KB.
- The guard cannot be replaced by permission rules, because rules are not per agent.
- The Stop-gate judgement could be a native prompt or agent hook. I would not: it adds a model call per turn for an unmeasured gain.
- **Yes, ship a plugin plus a thin template, instead of writing `kb.py upgrade`.** Confirmed in the docs today:
  - a plugin carries skills, agents, hooks and a `bin/` folder whose files are on the Bash tool's PATH;
  - it is versioned and updated by Claude Code.
- The plugin holds `kb`, `fetch`, the hooks, and the stock agents and skills. The KB repo keeps the charter, `kb.toml`, a short `CLAUDE.md`, the notes and the owner's own tools. The KB still has no git link to the template.
- A side benefit: the guard lives outside the project, so the SCAFFOLD zone, its ask rules and the self-test become unnecessary.
- Things to handle:
  - plugin agents are namespaced (`plugin:librarian`), and the guard keys on the name;
  - `${CLAUDE_PLUGIN_ROOT}` is not in the Bash environment, so use `bin/`;
  - a plugin's `CLAUDE.md` is not loaded;
  - whether `bin/` is also on the PowerShell tool's PATH is not stated in the docs;
  - a convention change still needs a baseline mode in `check` so old notes do not fail at once.
- Do this after the decisive test. It is packaging, not a feature.

---

## 8. Anything else

- **Stop adding and start using.** Every case so far used a corpus written by a Claude model, agents from the same family, a scripted owner and one replicate. The first month of real use will teach more than a fourth synthetic case.
- **Untested today**: the triage gate and owner-message rule (live), init-kb (ever), research (since v1), audit (since v3), semantic search with agents, Linux and macOS, any model above Haiku.
- **Docs promise more than the code delivers**: README says "forget leaves no trace in the working tree" and describes removed trigger phrases. Fix the docs with the cuts.
- **Each fix round has added surface.** v5.1, case A and the language-neutral change each added verbs and exemptions (purge exemptions now sit in six code paths). The bugs in section 3 are in the newest and least-tested code. That pattern is the best argument for a feature freeze.

---

## Prioritised action list

| # | Action | Why | Effort | Do / do not |
|---|---|---|---|---|
| 1 | Delete the forget-prefix list in `capture.py` | Destroys "vergeet niet dat ..." messages (3.3) | S | DO now |
| 2 | Git-ignored folder for uncited owner messages, promote on citation; `kb.py commit` stages and commits the reviewed tree; guard refuses raw `git commit`; fix `ingest` step 8 | Chatter committed, unreviewed index committed, dangling blobs, refused first commits, clutter (3.4) | M | DO now |
| 3 | Number check: ignore date-shaped tokens, verify claim dates separately, accept glued tokens only if they occur in the source | Wrong numbers pass, correct deadlines blocked (3.1) | S | DO now |
| 4 | `check` fails on body prose outside bullets; `verify` shows changed title, summary, aliases | Uncited text reaches search results (3.7) | S | DO now |
| 5 | Apply the cut list (1.1, 1.3) and repair the stale docs (1.2) | No measured accuracy value; drift already visible | M | DO before the test |
| 6 | Triage gate: keep the reminder, add nothing; show recent "nothing to file" decisions in session-start stats; decide keep or delete from the A/B | Daily friction, zero live evidence, lazily satisfiable (3.2) | S | DO; do NOT extend |
| 7 | Run the decisive test, three arms (section 2) | Only way to prove or cut the rest | L | DO next |
| 8 | Pin a stronger model for the reviewer (and librarian) in the agent files; measure in the test | Last line of defence, smallest context (6) | S | DO with 7 |
| 9 | Drop the post-hook for Write and Edit; cut the log, index and stats steps from the librarian | A third of wall-clock is hook start-up; 46-83 calls per capture (5) | S-M | DO with 5 |
| 10 | Ship as plugin plus thin template | Solves upgrades with native machinery (7) | M-L | DO after 7; do NOT write `kb.py upgrade` |
| 11 | Answer-time re-verification of stale claims | Largest residual error (4.1), but a new feature | M | Do NOT build yet; first cut the open-questions write and watch real use |
| 12 | More guards, flags, word lists, forget hardening, `kb.py next`, claim ids, canaries, further narrow case studies | Diminishing returns; each adds bug surface | - | Do NOT do; use it for four weeks with a friction log instead |
