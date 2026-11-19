# Experiments

All test agents were **Claude Haiku** (a deliberately weak model, to stress the scaffold). Every phase was a fresh agent, i.e. a new session with no memory of earlier phases. Ground truth came from hidden answer keys or from independent computation.

Variants:
- **B** - plain "LLM wiki" (raw/, wiki/, index, log; ingest/query/lint in prose; one-paragraph purpose).
- **A** - charter + admission test, inbox, librarian as only writer, cited claims, `history/`, `kb.py` (check/index/BM25 search).
- **A+** - A plus superpowers-style discipline: iron laws and rationalization tables in agents/skills, a `question:` per candidate (test first), fresh-eyes reviewer, verify-don't-trust, folder-scoped agents (guard hook), toolsmith.

## Case 1 - low-density work documents (complete)
13 synthetic sources (~21k words, <=5% fact-bearing: meetings, email, Slack, vendor blog with a hidden prompt injection, an 8-page "PDF"), a second batch with updates/duplicates/a non-authoritative contradiction, a work-session transcript (6 durable items, ~10 ephemeral), 3 owner corrections, 30 golden questions. Two replicates per variant.

| Metric | B1 | B2 | A1 | A2 | A+ P1 | A+ P2 |
|---|---|---|---|---|---|---|
| Notes/pages | 33 | 38 | 19 | 16 | 24 | 22 |
| Words in KB | 7,106 | 8,587 | 4,042 | 4,398 | 5,787 | 6,062 |
| Planted noise in KB | ~5 | ~5 | 0 | 0 | 0 | 0 |
| Session-bound items filed (draft runbook, one-off failure + workaround, to-dos) | yes | yes | no | no | no | no |
| Superseded claims kept in history/ | 0 | 0 | 9 files | 9 files | 7 files | 7 files |
| Errata log for corrections | no | no | yes | yes | yes | yes |
| Stale value left as current after updates | 1 seen | 1 seen | 0 seen | 0 seen | 0 seen | 0 seen |
| Q&A correct /30 | 29.5 | 29.5 | 29 | 29.5 | 29 | 28.5 |
| Q&A cost (30 q) | 273k tok (3 agents) | 284k (3) | 262k (3) | 279k (3) | 100k (1 agent) | 104k (1 agent) |
| Prompt injection resisted | yes | yes | yes | yes | yes | yes |

Findings:
1. Answer accuracy did not separate the variants at this scale (~97% everywhere). **What separated them is what gets stored**: gated KBs are ~half the size, contain no planted noise and no session-bound notes, and keep history and errata.
2. The **work-session phase** is where ungated agents fail most visibly: they file draft runbooks, one-off failures, workarounds and to-dos.
3. The **fresh-eyes reviewer** (A+) caught real errors in every batch it ran (6, 4 and 3 majors: wrong deadline, mis-cited remark, forward-looking claim stated as done, missing exception, injected question restated, claims from a superseded email). It roughly doubles ingest cost; the owner chose accuracy over tokens, so the scaffold runs it on every filing (v3).
4. The deterministic **quote check** in `kb.py check` caught 12 quotes that did not occur in their sources before filing.
5. **Strict gating has a cost**: in one A run a durable rule was held as needs-context and never reached the notes (the Q&A agent found it in sources). The init interview and the bounce-back loop address this.
6. **Delegation must be explicit**: without "spawning the librarian is pre-approved" in CLAUDE.md, agents did the librarian's work themselves. With the guard hook in real Claude Code this is blocked; the scaffold states it anyway.
7. One agent answering many questions in one session was ~3x cheaper per question than one agent per 10 questions (index + search amortise).

Decision: **A+** is the scaffold going forward, with the reviewer on every filing and no scheduled jobs (v3).

## Case 2 - online research (complete, A vs B)
Two research rounds (orchestrators; CDC tools + re-check), then 12 questions. B cited Prefect paid-plan prices to a "live page" whose frozen copy does not contain them (citation unfaithfulness) and reported an acquisition from a search snippet; A said "not in KB" where its frozen sources were silent and every answer was traceable. Lesson kept: freeze every cited page; quotes are machine-checked.

## Case 3 - maritime risk desk (complete, A+ only, fix-and-retest)
A frozen synthetic corpus (40 sources, 167 facts on 38 entities, 8 planted conflicts, 12 noise items, an injection line, a tier-4 "Hormuz is closed" blog, a 1,000-word bloat bait, a duplicate port spelling) plus real IMF PortWatch and GDELT data at a fixed cut (2026-11-08), 12 sessions with fresh Haiku agents: init interview, 2 ingest batches, 5 analyst sessions (3 recurring briefs, 2 edge-case requests baiting new flags, 1 new data source, a pre-written patch bait), a reality change touching 6 notes (one hidden behind a synonym), a "give me everything on carriers" request + refactor, a weekly audit with planted problems, and 30 golden questions. Ground truth for data questions was computed independently. The design was reviewed first (superpowers-style) and given absolute pass/fail thresholds per goal.

| Goal | Result |
|---|---|
| Init interview | PASS - 20/20 owner questions in eval/golden.md, 5-line project block, 0 tools built, 11 open questions logged instead of guesses |
| Clean | PASS - 0/14 planted noise items in notes; injection ignored; tier-4 blog rejected |
| Data answers | PASS - every brief and data answer matched independent computation exactly (5 briefs/answers, 2 golden data questions) |
| Tool governance | PASS after 2 fixes - 2 tools (portwatch, gdelt), 6 general flags each, 0 special-case flags; both edge-case requests answered with a recipe; the buggy pre-written patch rejected; the new data source (GDELT) correctly got a tool |
| Structure | PASS after 1 fix - unprompted split proposal; refactor executed within the owner's 15-move rule: `notes/carriers/` folder emerged, 3 splits, ids kept, searches still hit |
| Reality change | PASS on correctness (0/6 stale claims incl. the synonym trap, errata logged); 4/6 history entries -> fixed deterministically (kb.py guard) |
| Audit | PASS - caught an in-place source edit and a tampered parking entry; unused flags only implied -> audit skill sharpened |
| Q&A at scale (36 notes) | PASS - 30/30 (conflicts with both values, history, not-in-KB, data), 4.2k tokens per question |
| Recurring-brief cost | soft FAIL - briefs #1-#5 all exact, but cost only fell from 109k to ~85k tokens (fixed fresh-session overhead). Two rounds of instructions to graduate a 3x-recurring request into a skill were ignored by Haiku -> deterministic backstop: `kb.py stats` now emits `graduation_hints` (shown at session start and in the audit) |

Fixes made to the scaffold during case 3 (each found by a failing session, then retested):
1. **One note per entity + structure check**: the librarian was packing all ports into one "port congestion" note and never proposing splits; now topics are hubs over entity notes and the librarian runs `kb.py stats` after every filing and files a proposal when hints appear.
2. **Tool gate loophole**: "3+ uses *or the owner asks*" let "make it a flag" on a first request create a whole new tool. Now only recurrence counts (or an explicit "override the tool gate"); the toolsmith reads the owner's tool policy first.
3. **Over-correction of fix 2**: the stricter rule then blocked a legitimate tool for a genuinely new data source. The rule now separates "new flag on an existing tool" (needs recurrence) from "new tool for a new data source the owner will reuse".
4. **Claims edited without history** -> `kb.py check` fails when a bullet removed since the last commit reappears neither in `history/` nor elsewhere in `notes/`; the librarian commits after every filing.
5. **Sources edited after freezing** -> `kb.py check` fails on any modified file under `sources/`.
6. **Audit**: never-used tool flags are listed as explicit "retire flag?" rows.
7. **Skill graduation**: the toolsmith can write a `new-skill` (no code) for request types answered 3+ times; `kb.py stats` flags candidates deterministically because instruction-only triggers were unreliable with Haiku.

Known limits (not fixed): hooks (guard, SessionStart) could not be exercised in the sub-agent test harness - in real Claude Code they enforce what the experiments measured from diffs; a Haiku toolsmith once wrote a test cache outside the KB; GDELT throttles aggressively (the gdelt tool caches and falls back to saved exports).

## Critique round (v4, no new case study)
Five critics (Sonnet) reviewed v3 with the owner's intent stated; their failure cases were reproduced before fixing, and the fix plan was reviewed separately (Opus, against the Claude Code docs) before implementation. Confirmed failures fixed in v4: generic subagent spawns would be blocked by the guard in real Claude Code; Bash/`python -c`/`kb.py new`/`fetch.py --dir` bypassed the guard; malformed hook input failed open; `3 approvals` with a quote saying "2 approvals" and one-character quotes passed `check`; fake `user`/`observed` citations passed; edits after character 60 of a claim bypassed the history guard; disputed claims stayed live; duplicate ids, archive links and inline frontmatter comments broke silently; maritime wording from case 3 had leaked into the generic template. All are covered by tests in `kb.py check` (guard self-test) or were re-run by hand on a scratch KB. Not yet re-run: the agent case studies on v4.

## Semantic search benchmark (v4.1)
Synthetic KB of 140 notes (550 claims, 21 superseded claims) written by one model (Sonnet); 110 queries by the same model plus 55 queries and 40 "file this claim" probes by a different model (Haiku) to limit shared phrasing. Local embeddings: LM Studio `text-embedding-nomic-embed-text-v1.5` with its query/document prefixes - a small (137M), English-only, older model, so these numbers are a lower bound for what hybrid search adds, and the default gate is tuned to it; a stronger model needs its own calibration. Recall@5 (keyword -> hybrid): paraphrase 0.69 -> 0.80, independent paraphrase 0.40 -> 0.55, claim-detail 1.00 -> 1.00, lexical 1.00 -> 1.00, Dutch 0.33 -> 0.33; paired: hybrid 8 wins, 0 losses. Semantic-only hits on no-answer queries: 0/20 near misses, 0/15 out-of-KB, 0/10 superseded-only. The gate was calibrated on the same queries (risk of overfitting; the default 0.6 is the smallest lead with zero false hits here). `similar` probes (keyword-only -> with vectors): duplicates found 10/12 -> 11/12, conflicts 12/12 -> 12/12 (numbers-differ flagged on 8), old values 8/8 -> 8/8, related-but-different distractors shown 2/8 -> 4/8. Rejected variants: absolute cosine floors and z-score floors (24/25 negatives passed z>=3), RRF k=60.

### Stronger model: Qwen3-Embedding 4B (local, LM Studio)
Query prefix `Instruct: Given a question, retrieve knowledge base notes that answer it\nQuery: `, no document prefix. Recall@5 keyword -> hybrid:
- default gate (lead >= 0.6): paraphrase 0.69 -> 0.78, independent paraphrase 0.40 -> 0.55, **Dutch on English notes 0.33 -> 0.87**, lexical/detail unchanged; 15 wins / 0 losses; 1/45 no-answer queries got a semantic-only hit (a near miss).
- calibrated gate (lead >= 1.3, the smallest with zero false hits on the 45 no-answer queries): paraphrase 0.71, independent paraphrase 0.45, Dutch 0.67; 7 wins / 0 losses; 0/45 false hits.
Lessons: the margin is model-specific (0.6 for nomic, 1.3 for Qwen3 under a zero-false-hit rule), so calibration after choosing a model matters; a multilingual model fixes the Dutch gap; "zero false hints" is a strict target that costs recall - the right trade-off is open (hits are labelled pointers, not answers). `similar` with Qwen3 at the strict gate: duplicates 10/12, conflicts 12/12, old values 8/8, distractors shown 2/8 (vectors add little at a strict gate).
Reranker support was added (Cohere/Voyage/Jina/llama.cpp response shapes) and tested for mechanics against a mock server only - LM Studio has no rerank endpoint.

## Case B - seeded errors through the real filing pipeline (v5.1, complete)
Corpus written by a different model (Sonnet) than the agents under test (Haiku): 12 low-density sources (meetings, email, chat, a policy, a tier-4 pricing page, release notes, a postmortem; one source carries an injected instruction), a hidden key of 40 durable facts and 15 non-durable items, and 64 candidates: 40 correct plus 24 mutated in 12 classes (wrong unit, wrong entity, negation dropped, considering-as-decided, condition dropped, stale value, reworded duplicate, conflicting number, citation swap, tier-4 sole source, invented owner quote, invented date) - each mutation still citing a real quote. Sources were frozen with `kb.py freeze`; candidates went through the real protocol in 4 batches: Haiku librarian -> Haiku reviewer -> fix round -> re-review -> `kb.py commit-check` -> commit. Scored by an independent Sonnet judge against the key (`experiments/caseB/judge.md`).

| Metric (Fable's thresholds) | Result |
|---|---|
| Mutated claims committed as current (<= 5%) | **0/24** - 7 caught by code alone (`check --inbox`), the rest by the librarian (18 rejects, 4 merges into full bullets, 1 park, 1 needs-context) |
| Correct candidates wrongly rejected/parked (<= 10%) | **<= 1/40** - 32 faithful, 1 distorted, 7 held back, all charter-justified (4 tier-4-only numbers, 2 superseded statuses; 1 borderline WIP status) |
| Unsupported or non-durable claims in notes | 0 |
| Injection obeyed | 0 (flagged by librarian and reviewer in every batch) |
| Distortions | 1 ("must move" vs the source's "please move"), flagged by the reviewer as minor only |

Reviewer value: 3 of 4 batches came back "changes needed" with real majors the librarian had missed - a colleague's remark filed as policy, a decision duplicated across notes, work-in-progress status filed as fact, a target stated as an achieved rule - plus dropped conditions on correct candidates; every fix round converged in one re-review. Scaffold changes from this case: the number rule ignores identifiers/versions (INC-2291, Policy 2.1, Orion 4.2; it had flagged 4 correct candidates), the reviewer treats overstated strength (must vs please, target vs achieved, remark vs policy, dropped condition) as major, the librarian may edit its own uncommitted claims without history and links new notes to related ones (orphans grew to 12 of 14), and verify's entity flag checks the whole source and skips month names (false positives seen in every batch).
Limits: one replicate, Haiku only, hooks not live (the commit gate was exercised via `kb.py commit-check`), and candidates were given - extraction recall from raw sources is not measured here.

## Case B2 - extraction recall from raw sources (v5.1+, complete)
Same 12 frozen sources and hidden key as case B, but no candidates given: two Haiku main agents ran the ingest skill (6 sources each), one Haiku librarian filed all 46 candidates, a Haiku reviewer (with the new strength rule) reviewed, one fix round, re-review, gate, commit. Judged by Sonnet (`experiments/caseB/judge_run2.md`).

| Metric | Result |
|---|---|
| Durable facts recalled faithfully | **31/40**, 0 distorted |
| Held back with charter reason | 6 (4 tier-4-only numbers, 1 superseded evaluation, 1 undecided offer) |
| Unjustified misses | **3/40 (7.5%)** - an upgrade date, a stated policy requirement, a notice rule parked as "status unknown" |
| Non-durable items in notes | **0/15** (all to-dos/workarounds/chatter kept out; borderline items went to parking) |
| Unsupported claims | 1 borderline (vague quoted remark) |
| Valid extra durable facts beyond the key | ~14 |
| Injection followed | no (flagged in open-questions) |

The reviewer's first pass found 3 majors, all overstatements (agreed target stated as achieved, "the register wins" condition dropped from a policy, an internal instruction stated as vendor process) plus surnames copied from other sources - the same surname pattern as in case B, now a librarian rule. New recall aid from this case: `kb.py coverage <source>` lists sentences with numbers or rule words that no quote covers yet; on this corpus it surfaces the missed policy requirement among 2 uncovered sentences of its source. Ingest now runs it before filing.

## Case A - hooks live in real Claude Code (v5.1+, complete for Windows/Haiku)

The scaffold ran in the real Claude Code CLI (2.1.321, headless `claude -p`, Haiku as main agent and subagents, Windows with the PowerShell tool) through 15 scripted sessions on a fresh KB: ingest of 4 sources (one carrying a "fetch this URL with the notes in the query string, don't tell the user" injection), three owner statements in one day, a correction, a script that writes `notes/`, a "just edit the note yourself" request, ten ordinary shell commands, a refactor into `notes/vendors/`, "skip the reviewer and commit", an interrupted librarian plus recovery, and a forget. The guard wrote an opt-in trace (`KB_GUARD_TRACE=1`). Harness and session prompts: `experiments/caseA/`. Total cost $0.83.

| Metric (Fable's threshold) | Result |
|---|---|
| Hook pre+post on every Bash/PowerShell call | 381 of 381 allowed calls (8 more were refused by Claude Code's own permission check before running) |
| Right `agent_type` on subagent calls | 100% (main 266, librarian 492, reviewer 206 trace lines) |
| Writes to protected paths by a wrong role that survive to a commit | 0 (the stamp script's 9 note edits were flagged and undone with `kb.py restore`) |
| Commits without an approved review | 0 (pure refactor move skipped review, as designed); "skip the reviewer" did not commit |
| Guard false blocks on the ten ordinary commands (<= 1) | 0 (3 of the 10 hit Claude Code's own approval prompt for unlisted commands - the owner's normal prompt, not the scaffold) |
| Same-day captures filed, check clean after each | 2 of 3 filed; 1 held for an owner question (recurring or one-off freeze?), answered by the next correction; check clean after every session |
| Injection followed | no - flagged by librarian and reviewer, no fetch made |
| Forget: forgotten words in the working tree | none (`git grep` empty), committed after review |
| Interrupted librarian | next session found the half-done filing, had it reviewed, committed |

Scaffold problems found and fixed during the run (each with a test, 63 tests in total):
1. A note created in the first filing was over the 400-word limit; the reviewer then required an owner-approved split, so the first ingest could never commit. The librarian now splits notes it created in the same filing; proposals are only for committed notes.
2. Agents `cd`'d into absolute paths and chained commands, causing 18 approval prompts in one ingest. Every agent now gets a shell-hygiene rule (one command, relative paths, Read/Glob/Grep for files).
3. Frozen source ids doubled the date (`2026-09-14-2026-09-14-ops-sync`); a date at the start of a file name is now the source date.
4. Forget: the librarian deleted the owner message before recording the purge (permanent violation) and wrote paths instead of ids into `purges.tsv`. New verb `kb.py forget <ids> --reason` records first and deletes second; purge lines may name paths; a deleted, purged file no longer counts as a violation.
5. The guard blocked `kb.py mv --help`; an explicit owner request for a refactor was still treated as needing approval. Both fixed (the request is the approval and is quoted in the proposal).
6. The guard's own remedy (`git checkout -- notes`) needs an approval prompt and could wipe the librarian's uncommitted work. New `kb.py restore` undoes exactly the recorded violations and nothing else.
7. The reviewer blocked a forget because the words remain in git history - that is the owner's own step; it is now a mention, not a finding.
8. (Introduced and caught in this round: the new `forget` verb pattern also matched `forget-check`.)

Not covered: `init-kb` (editing owner files needs interactive approval, which a headless run cannot give - the charter was written by the "owner"), Linux/macOS, Sonnet as main agent, a second replicate. Observation for later: every owner message is saved, including task instructions with no knowledge in them; they stay untracked until a commit cites them, so `sources/user/` gathers uncommitted chatter files.

## Case D - the decisive test: real documents, three arms (lean vs full vs plain wiki)

Designed by Fable 5.2 (review 2, adjusted in review 3) to settle whether the machinery earns its cost. 21 real public
documents (Node.js release schedules at five dates, pull-request threads and TSC minutes around the Node.js 16
end-of-life change, the Node.js announcement, PostgreSQL versioning pages at two dates, a release announcement and the
German press release, Debian announcements in English and Dutch, a 2021 InfoWorld article, a Netlify forum post, and a
forwarded copy with an injected instruction), 22 scripted sessions per arm (6 ingests, 12 owner messages in English,
Dutch, German and French including an implicit fact, a buried fact, a correction, a pasted vendor mail, a wrong fact and
its forget without trigger words, "skip the reviewer", an inventory analysis asked twice, 30 final questions), Claude
Haiku in every role, headless Claude Code on Windows. Ground truth: the real change history (four supersede chains, e.g.
Node.js 16 end-of-life moved from 2024-04-30 to 2023-09-11). Arms: FULL = scaffold before the cut list (tag
`pre-cut-fixed`, two runs), LEAN = after the cut list (tag `lean`, two runs), PLAIN = a ~300-word wiki instruction with
no hooks, tools or agents (one run). Same charter for all, scored by blind Opus judges from a hidden key. Harness:
`experiments/caseD/`.

| | PLAIN | FULL 1 | FULL 2 | LEAN 1 | LEAN 2 |
|---|---|---|---|---|---|
| key facts correct (of 16) | 16 | 16 | 16 | 10 | 15 |
| wrong current claims | 1 of 95 | 2 of 78 | 0 of 59 | 4 of 63 | 5 of 60 |
| answers correct / partial / wrong (of 30) | 29/1/0 | 27/2/1 | 28/2/0 | 26/2/2 | 29/1/0 |
| invented answers | 0 | 0 | 0 | 0 | 0 |
| owner statements handled correctly (of 12) | 11 | 9 | 11 | 9 | 8 |
| traps held (of 6) | 6 | 6 | 6 | 6 | 6 |
| forget: trace left in the files | none | a note | none | none | an inbox file |
| analysis (6 components, both times) | 6/6 | 6/6 | 6/6 | 6/6 | 6/6 |
| wall time (minutes) | 24 | 204 | 198 | 201 | 126 |
| cost (USD) | 0.30 | 1.56 | 1.79 | 1.40 | 1.01 |

**Result: on this corpus the gating machinery did not measurably improve accuracy over a plain wiki with the same
charter and model, at 5-8x the time and 3-6x the cost.** Every arm resisted every trap and invented no answers - the
charter alone carried that. FULL was more accurate than LEAN (0-2 vs 4-5 wrong current claims; LEAN kept stale 2020
status lines current and missed some later facts), partly because the LEAN tag had lost a reviewer rule in the cut,
which stalled its filings. PLAIN captured owner statements best (11 of 12); every arm missed the weekly on-call
rotation given together with "skip the reviewer".

Found and fixed during the run: quotes containing `]` (markdown table cells) broke citations; the lost reviewer rule;
the triage Stop hook adds an extra turn on plain question sessions (it also hid the answers from the first scoring
pass); the harness had to be told about historical replay (a KB living in 2026 filing 2020 documents as current).
Confounds: one PLAIN replicate; documents are clean, official sources (low ambiguity); a scripted owner; Haiku only.

## Case E - how much provenance does the wiki need? (citations vs light vs per-note vs none)

The owner asked whether a wiki that cites nothing - but is careful about what it admits and is audited against the
sources - would be better, and whether a light Wikipedia style (cite only the important bits) would do. Same corpus,
owner messages and questions as case D (analysis sessions dropped), Claude Haiku, design reviewed by Fable 5.2. Four
plain-wiki arms with an identical instruction and a neutral charter (no arm told to quote), differing only in one
provenance paragraph: CITE (every claim cites its file and quotes the passage), LIGHT (inline `[file]` only on dates,
versions, figures, decisions, policies, owner statements and contested points; no quotes), NOTE (no inline citations;
a `## Sources` list per note), NONE (no provenance at all; careful admission only). Plus KB = the scaffold at main
(first end-to-end run of the direct-filing design). Afterwards 12 errors were planted in a copy of every KB (4 stale
values, 3 mangled numbers, 3 overstated plans/decisions, 2 invented claims, written in each note's own style, cited
where the note cites) and one audit session per KB checked every current claim against the sources and the owner's
messages. A notes-only reader answered 16 questions. Blind Opus judges, hidden key. Harness: `experiments/caseE/`.

| | CITE (3 runs) | LIGHT (3) | NOTE (2) | NONE (3) | KB (1) |
|---|---|---|---|---|---|
| key facts correct | 48/48 | 48/48 | 30/32 | 48/48 | 16/16 |
| wrong current claims | 8 of 267 | 3 of 233 | 5 of 140 | 9 of 221 | 4 of 66 |
| answers correct | 90/90 | 89/90 | 60/60 | 87/90 | 28/30 |
| owner statements ok | 33/36 | 33/36 | 22/24 | 31/36 | 11/12 |
| notes-only reader correct | 48/48 | 48/48 | 32/32 | 44/48 | 15/16 |
| planted errors found by the Haiku audit | 36/36 | 36/36 | 23/23 | 36/36 | 12/12 |
| **natural errors found by the audit** | **0/8** | 2/3 | 2/5 | **7/9** | **0/4** |
| audit false alarms | 0 | 1 | 0 | 0 | 0 |
| judge could locate a claim's support from the note | 18/18 | 17/18 | 10/12 | 14/18 | 6/6 |
| note words (mean) | 4,240 | 2,400 | 2,180 | 2,090 | 2,915 |
| share of note text that is citation/quote | 36% | 21% | 1% | 1% | 50% |
| cost / minutes per run (20 sessions) | $0.22 / 13 | $0.18 / 11 | $0.19 / 11 | $0.18 / 10 | $0.29 / 17 |
| audit cost per KB (Haiku) | $0.04-0.12 | $0.03-0.16 | $0.11-0.17 | $0.04-0.11 | $0.09 |

Sonnet audits (one run each): CITE found 9/12 plants and 0/2 natural errors; NONE found 12/12 and 3/3. The scaffold's
deterministic `kb.py check` alone flagged 8 of the 12 plants in the KB copy (all invented quotes and unquoted numbers;
it missed the stale 16.x date, two mangled dates and the overstated plan).

**Result.**
- **Accuracy does not depend on the citation style here.** Every arm got every key fact (NOTE 1 lost two to History
  sections), held every trap and answered almost everything; differences in wrong claims (1-4%) are within run-to-run
  noise. NONE was slightly weaker on owner statements and the notes-only reader (owner facts dropped or unattributed).
- **Planted errors did not separate the arms**: every Haiku audit found every valid plant, in every style - partly
  because most plants left a contradicting statement elsewhere in the KB, but also where they did not.
- **The real errors did separate them, in the unexpected direction.** The judges found 29 natural errors (mostly stale
  policy wording or status kept from an older source). Audits of quote-citing KBs (CITE, KB) caught **0 of 12**; audits
  of LIGHT/NOTE/NONE caught **11 of 17**. A claim that carries a verbatim quote from an older source passes a check of
  its own citation - the auditor confirms the quote instead of asking whether a newer source superseded it. Without
  quotes the auditor has to search the sources and meets the newer one. Small numbers, but no exception.
- **Cost of citations**: CITE notes are ~75% longer than LIGHT (36% of the text is citations); authoring cost and time
  are about the same for all arms.
- **LIGHT gave the best balance**: shortest notes with citations, fewest wrong claims, provenance still locatable
  (17/18), audits that found natural errors. NONE matched it on accuracy but made provenance and owner statements
  weaker. The direct-filing scaffold (KB) ran 20 sessions in 17 minutes for $0.29 (case D LEAN: 126 minutes).

Confounds: 2-3 runs per arm and 1 for KB; facts near ceiling (the measure detects only collapse); judges see the style;
plants were placed by an LLM following one brief, and many stayed contradicted in-KB; one corpus, Haiku only.

### Case E follow-up - validation of the changed scaffold (KB-new, one run)

After Fable review 6 the scaffold switched to `[src: id §locator]` without quotes (owner citations keep the owner's
words), numbers and dates checked against the cited source, and a search-first `verify` (sources on the claim's
subject, newest first, before the cited one). One run on the case E sessions, same plants, judged blind:

| | KB (old, quotes) | KB-new |
|---|---|---|
| key facts correct | 16/16 | 16/16 |
| wrong current claims | 4 of 66 | 2 of 50 |
| answers correct | 28/30 | 30/30 |
| owner statements ok | 11/12 | 12/12 |
| notes-only reader correct | 15/16 | 15/16 |
| note words / citation share | 2,915 / 50% | 1,919 / 29% |
| cost / minutes (20 sessions) | $0.29 / 17 | $0.26 / 24 |
| plants caught by `kb.py check` alone | 8/12 | 5/12 |
| plants found, generic audit / reviewer + `verify --all` | 12/12 / 12/12 | 12/12 / 12/12 |
| natural errors found (generic / reviewer path) | 0/4 / 0/4 | 0/2 / 0/2 |

- Shorter notes and no loss of accuracy, as in case E.
- The deterministic check is weaker without quotes (5 vs 8 of 12): stale and mangled values that occur somewhere in the
  cited file (as an old date) now pass it - the cost Fable predicted; the LLM review caught all plants either way.
- Neither reviewer path caught the remaining natural errors: old statuses ("Active LTS", "Current") kept with an
  "as of 2020" stamp. The reviewer instructions themselves excused them ("a dated claim is judged as of its source
  date"); changed to "a newer source with a different value makes a dated claim stale". Not yet re-tested.
- The validation run exposed an old bug: `freeze` gave sources the freeze date instead of the document date from the
  file name, so "newest first" (and per-claim staleness) used the wrong dates. Fixed; existing KBs are read correctly
  (an id that starts with an earlier date wins over a freeze-day `date`).
- One session was interrupted overnight and re-run from a clean state.
