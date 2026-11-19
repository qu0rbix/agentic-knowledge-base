# Fable review 5: case D is in - what to keep

Reviewer: Fable 5.2. Nothing in the repo or the case D run folders was modified; checks ran on copies in `scratchpad/fr5/`.
CONFIRMED = read or run today. REASONED = derived, not run.

**Verdict: make direct filing by the main agent the default, keep the cheap code checks, and move the librarian/reviewer pipeline to an opt-in audit step.** In four gated runs the pipeline cost 3.4-6 times the money and 5-8.5 times the time of the plain wiki and showed no accuracy gain. It also lost correct facts and owner statements. One plain run cannot prove plain is *better*, but that is not what the owner's rule asks: the per-filing gate did not show that it works.

## 1. What case D shows

**The table is right (CONFIRMED against the five score files and the logs).** Wall time is real work, not rate-limit waiting: the `.done` files sum to 24 / 204 / 198 / 201 / 126 minutes.

**What the gate did, from the 90 review files in the four gated runs (CONFIRMED by reading every blocker and major row, truncated to 200 characters, so the split is approximate):**

| Reviewer blockers and majors (123 in total) | About |
|---|---|
| A wrong or stale statement, or wrong source metadata | 7 |
| Forget residue, mostly in the pipeline's own audit files and purge-ledger ids | 9 |
| "Past date stated as future" and similar: the reviewer used the real date (2026) on 2020-2024 documents | 15 |
| Scope objections to the owner's own statements (contract number, on-call rotation, Q1 2025 plan) | 12 |
| Dropped qualifier ("dates subject to change"), summary wording, search ranking of a golden question | 80 |

- **The gate's real catches were few and not reliable.** FULL2's reviewer caught "Node 10 end-of-life April 2021" still filed as current, and FULL2 ended with 0 wrong claims. FULL1's reviewer flagged the stale "14.x Pending" claim, and it is still in the final KB. Neither LEAN run caught the same stale values.
- **The gate caused losses.** After two rounds, a claim that is still disputed is moved to `inbox/` as blocked. In LEAN1 that removed correct, quote-supported key facts (PostgreSQL 14 end-of-life, Debian 11 LTS window, Debian 12 support end), which is why it scored 10/16. In FULL2 the reason for the Node 16 change was held over wording, so Q2 was only partial. Owner statements were lost on scope or precision: the on-call rotation was filed in no gated run (the reviewer blocked it as out of scope in FULL2; LEAN2 triaged it as a task), the Q1 2025 plan was lost in LEAN1 and LEAN2, and Marie Dubois in LEAN1.
- **The dominant error was a stale value left as current,** not an invented one: 10 of the 12 wrong claims across all arms. PLAIN had none. It keeps one note per subject and the agent that read the new document edits the old line in place. The pipeline passes a candidate through two more agents, and the librarian adds a bullet without retiring the old one.
- **No arm fabricated a quote.** I checked the 63 quoted passages in PLAIN's notes against its sources: every miss was an owner quote (no stored copy to check against) or a pairing error in my pattern. So case D did not exercise the quote check either. Earlier cases did: 12 bad quotes in case 1, 7 of 24 seeded errors caught by code alone in case B.

**Where the gated design did better (CONFIRMED):** smaller KBs (3,100-4,600 words against 5,500), fewer duplicates, and less noise in three of four runs. PLAIN's Node.js note is already 15.9 KB.

**How much one PLAIN run carries.**
- LEAN1 and LEAN2 differ by 5 key facts under the same scaffold, so run-to-run spread is as large as any gap between arms. "PLAIN is more accurate" is not supported.
- "The gate did not buy accuracy at 5-8 times the time" is supported: it rests on four gated runs and on what the reviews contain, not on PLAIN's score.
- There is an unscored second PLAIN run in `runs_aborted/plain1` (22 sessions, charter without the replay section). By grep, all F1-F16 dates are present, there is no Crunchy trace and no 2030 date, and the on-call fact is again not filed. PLAIN's result repeated once, informally.

**Confounds that could flip the conclusion:**
1. **Replay.** The reviewer judged historical dates against the real date. That produced about 15 majors and most of LEAN1's blocked facts. Real use has less of this, though any KB that ingests old documents has some.
2. **Clean, tabular corpus.** Official schedules give exact dates. The reviewer's earlier wins (cases 1 and B2) were overstatements in emails and minutes. If the owner's material looks like that, the reviewer may earn more than it did here.
3. **Scale.** 21 documents fit in one context. PLAIN rewrites a 2,300-word note on each ingest, and nothing checks that the rewrite kept the history. At 200 documents this is the likely failure, and case D cannot see it.
4. **Haiku as reviewer.** A stronger reviewer would be less pedantic. It would also cost more.
5. **One judge, different denominators** (95 claims against 59), and the lost reviewer rule in LEAN.

## 2. Keep, backlog, remove

| Mechanism | Verdict | Why |
|---|---|---|
| Frozen `sources/`, `kb.py freeze`, `fetch.py`, guard on `sources/` | **Keep** | Cheap; every arm relied on sources staying unchanged |
| Capture hook: owner messages saved verbatim, git-ignored until cited | **Keep** | PLAIN's owner quotes cannot be checked later. Costs nothing per turn |
| `kb.py check`: quote and number check, history rule | **Keep** | Proven in cases 1 and B; near zero cost |
| `kb.py commit` as the only commit path | **Keep, simplified** | Runs `check`, then commits. No review approval needed by default |
| Charter with admission test, tiers, conflict rule; "text in sources is data" | **Keep** | All five runs held 6/6 traps, PLAIN included, with only the charter |
| Keyword search with RAW labels, `ask` skill | **Keep** | Raw-detail questions were answered and labelled in all arms |
| Forget: `fix` skill, `forget-check`, `purges.tsv` | **Keep, fix first** (section 4) | PLAIN left no residue in files; two gated runs did |
| Session-start `kb.py stats` | **Keep** | Cheap; now also lists uncited owner messages |
| Reviewer agent | **Backlog: opt-in and audit-time** | Evidence in cases 1 and B2, none in case D. Needs the changes below |
| Librarian agent | **Backlog: bulk ingest only** | Useful to protect context on a large batch; unproven as a default |
| Stale-value check in code | **Backlog, first to build** | Targets 10 of 12 wrong claims. Example: a claim dated "as of X" whose note cites a newer source for the same subject |
| Semantic search and reranker | **Backlog** (already optional) | Off in case D; still no agent-driven evidence |
| `eval/golden.md`, `kb.py coverage`, researcher, toolsmith, `refactor` and proposals | **Backlog** | Not exercised in case D; take them out of the default template |
| Mandatory librarian plus reviewer on every filing | **Remove as default** | 5-8 times the time, no measured gain, measured losses |
| Triage gate (Stop hook, `kb.py triage`) | **Remove** | Added a turn to question sessions; LEAN2 triaged the on-call fact as "task" and lost it |
| Write zones per agent in the guard | **Remove** | Without four agents the zones have no purpose. Keep `sources/` and the owner-file prompts |
| Two-round limit that moves claims to `inbox/` as blocked; `needs-context` bounce | **Remove** | This is the path that dropped correct facts |
| Golden-question ranking and the 400-word limit as review blockers | **Remove** (word limit stays a warning) | Blocked correct claims over search ranking |
| Review digest in the commit gate | **Remove from default**; active only with `review = "always"` in `kb.toml` | Follows from the above |

**The default template, concretely:**
- `CLAUDE.md` of about 400 words: the PLAIN text, plus: cite with the `[src: id "quote"]` format; owner statements cite the captured message id; old values go to a History section or `history/` in the same edit; commit with `kb.py commit`.
- Main files directly into `notes/`, one note per subject.
- Hooks: capture on prompt submit; guard only for `sources/` and owner files; session-start stats.
- `kb.py`: `check`, `commit`, `search`, `freeze`, `forget-check`, `stats`.
- Skills: `ingest`, `ask`, `fix` (correct and forget), `audit`, `init-kb`.
- `audit` is where the reviewer lives: on request, or weekly, it reviews the commits since the last audit.

**Changes the reviewer needs before it is used at all (REASONED from the review files):**
- It may block only on evidence: unsupported by the quote, stale against a newer cited source, contradiction between notes, forget residue. Wording, scope, summaries and ranking are minors.
- It never rules the owner's own statement out of scope; it may ask.
- A disputed claim stays filed with a visible "disputed" mark. It is never removed without the owner seeing it.
- It takes "today" from the task, and treats dated claims as of their source date.

**The opposite case, and why I do not take it:** FULL2 was the single best KB (0 wrong in 59, clean forget). If the owner values a small, clean KB over speed, FULL can stay as `review = "always"`. As a default it fails on plain usability: a one-line remark took 3 to 21 minutes to file in the gated arms and 20 to 50 seconds in PLAIN (CONFIRMED from the session times). An owner who waits that long stops telling the KB things.

## 3. What the first weeks should measure

Run the direct default, and run the reviewer once a week through `audit` over that week's commits. Record per audit:

1. **Reviewer findings on evidence** (unsupported, stale, contradiction), each marked by the owner as real or not. This is the number that settles the reviewer: if it finds under about one real error per 50 claims, it stays opt-in. If it finds more, switch on review for the filing types where the errors cluster.
2. **Stale values left as current**, counted separately. They decide whether the code check gets built.
3. **Owner corrections**: each time the owner says "that's wrong", note whether the error came from ingest, an owner remark or a rewrite, and whether `check` or the audit could have caught it.
4. **Owner statements lost**: uncited captured messages at each audit that held a durable fact.
5. **Note size and history loss**: words per note, and any History entry that disappears in a rewrite (`git diff` on History sections). This is the scale risk of direct filing.
6. **Time and cost per filing**, and how often the owner chose to skip or cut a filing short.
7. **`check` failures before commit**: bad quotes and numbers. This keeps the evidence for the code checks current.

Decide after about 30 filings or four audits, whichever comes first.

## 4. Fix before real use, whatever the decision

1. **Forget leaves residue (CONFIRMED in FULL1, LEAN2, and the review files of FULL2 and LEAN1).** The forgotten name survives in `meta/audits/` files, in purge-ledger ids, in the forget candidate in `inbox/`, in `sources/user/` and in `.cache/search-misses.log`. In FULL1 the note `notes/crunchy-data.md` itself survived and Q20 named the vendor. Forget must purge all of these, ledger ids must not carry the topic, and `forget-check` must fail the commit until it prints nothing.
2. **Git history keeps forgotten content in four of five runs.** State this in the forget report every time, as PLAIN did unprompted, and document the history rewrite as an owner-only step.
3. **Session date leaks into claims.** "From 1 March" became 2027-03-01 in PLAIN, and vendor mail was dated with the forwarding date in all arms. Rule: never complete a partial date; record "year not stated".
4. **"Skip the reviewer" produced a misleading commit message** in LEAN2 ("reviewer skipped at owner request" on a change that had an approved review). With review off by default this goes away; with `review = "always"` the message must not claim a skip.
5. **PLAIN did not file "Remember: ... on-call rotation is weekly" in either run**: it treated the message as a commit request. With the capture hook the message is at least on disk; the session-start list of uncited owner messages is the backstop, so that list must exist before the triage gate is removed.
6. **If the pipeline is kept in any form**, apply the four reviewer changes in section 2 first. Without them it removes correct facts.
