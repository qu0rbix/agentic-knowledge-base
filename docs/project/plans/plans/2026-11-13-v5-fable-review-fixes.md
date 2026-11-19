# v5: Fable review fixes - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the scaffold deliver what its docs claim in real Claude Code: no deadlocks, provenance roots written by code, a review gate enforced by code, no pre-approved exfiltration, and evidence checks without the confirmed holes.

**Architecture:** Fixes stay inside the existing tools (`tools/kb.py`, `tools/kbsem.py`, `tools/hooks/guard.py`, `tools/hooks/capture.py`, `tools/fetch.py`), with a new owner-owned `kb.toml`. A stdlib `unittest` suite in `tests/` builds throwaway KBs from `template/` and replays hook JSON, so hooks are tested without a live model.

**Tech Stack:** Python 3.12 stdlib only (tomllib, sqlite3, urllib, unittest), run with `uv run`.

**Spec:** `scratchpad/fable_review.md` (copied to `docs/reviews/2026-11-13-fable-review.md` in Task 0); owner intent in `docs/design.md`.

## Global Constraints
- Accuracy over token cost; nothing scheduled; `uv` for Python; stdlib only in `tools/`.
- Non-librarian one-off scripts must stay free outside protected paths (no deny-by-default Bash).
- Guards in code over prose; every guard has a test in `tests/`.
- Windows (Git Bash and the PowerShell tool), macOS and Linux.
- Clones keep no git link back to the template repo.

## Review Focus
- Two owner statements on the same day, with a commit in between: both citable, `check` clean (F1).
- The librarian edits a file that once held a restored violation: no failure (F2).
- A harmless analysis command (`kb.py search "touch points"`, `... | tee work/x`, `mv data/a data/archive/`): not blocked (1.4).
- `git commit` right after the librarian, before the reviewer: blocked (T7).
- A claim moved into another entity's note: review required (T5).

---

### Task 0: Test harness and review copy
**Files:** Create `tests/helpers.py`, `tests/test_hooks.py`, `tests/test_kb.py`; copy the review to `docs/reviews/2026-11-13-fable-review.md`.
**Interfaces:** `make_kb(tmp: Path, git=True) -> Path` (copies `template/`, `git init`, sets identity, first commit); `run_kb(kb, *args, env=None) -> CompletedProcess`; `hook(kb, mode, payload: dict, script="guard.py") -> CompletedProcess` (sets `CLAUDE_PROJECT_DIR`).
- [ ] Write the Fable reproductions as failing tests (F1, F2, F5, F8, F9, T2, T4, T5, T6, T8, T10, the 1.4 false positives, PowerShell coverage).
- [ ] `uv run python -m unittest discover -s tests` → the new tests FAIL, existing behaviour tests pass.

### Task 1: Owner words and frozen evidence are written by code (F1, T1)
**Files:** Modify `tools/hooks/capture.py`, `tools/kb.py`, `tools/hooks/guard.py`, skills `note`, `fix`, `ingest`, `init-kb`, `CLAUDE.md`, `CONVENTIONS.md`.
**Interfaces:** `capture.py prompt` writes every non-slash prompt verbatim to `sources/user/<YYYY-MM-DD>-<HHMMSS>-<n>.md` (frontmatter id/type user/date) and records its hash in the guard manifest. `kb.py freeze <path> --kind files|meetings|email|chat [--tier N] [--title T] [--origin O]` → byte copy plus frontmatter into `sources/<kind>/<date>-<slug>.md`; `.pdf` needs `pypdf` (`uv run --with pypdf`).
- [ ] Tests: `test_same_day_statements` (two prompts, commit between, cite both, check clean); `test_fabricated_owner_quote_fails`; `test_freeze_is_byte_exact`; `test_agent_cannot_write_sources_user` (Write blocked; Bash write is a post violation).
- [ ] Drop the "modified in any past commit" rule; keep working-tree M/D checks (the commit gate in Task 3 keeps modifications out of history).
- [ ] Skills stop telling the agent to type owner words or copy sources by hand.

### Task 2: Guard correctness (F2, F3, F4, F6, T12, 1.4)
**Files:** Modify `tools/hooks/guard.py`, `.claude/settings.json`, `tools/kb.py` (`guard_violations`, self-test cases).
**Interfaces:** `may_write(role, rel, tool) -> bool`: notes/history/archive/decisions/index.md/purges.tsv → librarian; tools/ → toolsmith; meta/audits/ → reviewer; owner files (`charter.md`, `CLAUDE.md`, `CONVENTIONS.md`, `kb.toml`, `.claude/**`) → only via Write/Edit (owner approves the prompt), never via a shell; `sources/user/` → nobody (hook only). `post()` runs for every role and tool: drift that the role may write is accepted into the manifest, the rest is recorded as a violation with `bad_sha`. `guard_violations()` fails only while the file still has `bad_sha`, and drops resolved entries.
- [ ] Bash/PowerShell pre-check reduced to: redirect targets into protected paths, mutating `kb.py` verbs (non-librarian), guard state, `git commit` (Task 3).
- [ ] settings: matchers `...|Bash|PowerShell`; PostToolUse also on `Write|Edit|NotebookEdit`; `onFailure: "block"` on Pre/PostToolUse; `env.CLAUDE_CODE_FORK_SUBAGENT = "0"`; SessionStart adds `fork`; PowerShell allow/deny rules mirrored.
- [ ] Heartbeat: pre-hook touches `.git/kb-guard/heartbeat`; `kb.py check` fails when `CLAUDECODE` is set and the heartbeat is older than 120 s.
- [ ] Tests: `test_restored_violation_then_librarian_edit`, `test_librarian_cannot_write_tools`, `test_shell_cannot_edit_charter`, `test_harmless_commands_allowed` (the 1.4 list), `test_powershell_redirect_blocked`, `test_heartbeat_required_under_claudecode`.

### Task 3: Review ledger and commit gate (S2, T7)
**Files:** Modify `tools/kb.py` (`precheck`), `tools/hooks/guard.py`, `.claude/agents/reviewer.md`, `CLAUDE.md`, filing skills.
**Interfaces:** `kb.py precheck` prints `digest: <sha1 of the uncommitted notes/history/archive/decisions content>` and `review: required|skip`; pure move = per-file body equality (T5). Reviewer writes `meta/audits/<YYYY-MM-DD-HHMMSS>-review.md` containing `Digest: <digest>` and `Verdict: approved|changes needed`. Guard pre on `git commit`: allowed only if `kb.py check` passes and (review skip, or an audit file with that digest and `Verdict: approved` exists).
- [ ] Tests: `test_commit_blocked_without_review`, `test_commit_allowed_with_matching_approval`, `test_commit_blocked_after_post_review_edit`, `test_pure_move_commits`, `test_cross_note_move_needs_review`.

### Task 4: Evidence and history holes (T2, T3, T4, T6, T8, T9, F8, F9, quote normalisation)
**Files:** Modify `tools/kb.py`, `CONVENTIONS.md`, `librarian.md`.
- [ ] Every citation needs a quote (notes and inbox). `wsnorm` strips `* _ | \``.
- [ ] `verify` compares full bullets (citation changes show) and lists untracked files (`--untracked-files=all`); adds flags `ENTITY NOT IN EVIDENCE`, `UNIT DIFFERS`, `DATE NOT IN SOURCE`.
- [ ] History append-only: every `## Superseded` entry at HEAD must still exist unless its note is in an uncommitted purge line.
- [ ] Freshness: only `as of` stamps, source dates and `last_verified` count; `since`/`from` do not; future dates ignored. OPEN ignores lines starting `RESOLVED`.
- [ ] `search-eval` ignores non-`Qnn` lines in golden format.
- [ ] Tests: `test_quote_required_every_citation`, `test_citation_swap_visible_in_verify`, `test_history_deletion_fails`, `test_since_stamp_not_stale`, `test_resolved_open_item_hidden`, `test_verify_new_subfolder`, `test_golden_header_ignored`, `test_markdown_emphasis_quote`.

### Task 5: Config, exfiltration, forget, capture (F5, T10, T11, 1.4 capture)
**Files:** Create `template/kb.toml`; modify `tools/kb.py`, `kbsem.py`, `fetch.py`, `capture.py`, skills `init-kb`, `fix`.
- [ ] `kb.toml`: `[notes] types, review_days`; `[capture] phrases`; `[search] index_warn_bytes`; `[fetch] max_url_length = 300, max_query_length = 100`. Tools read it with tomllib; defaults if absent.
- [ ] Embedding/rerank config only from OS env and `~/.config/akb/env` (`.env` no longer read).
- [ ] fetch: urllib with a redirect handler that re-runs `safe_url`; URL and query length limits; every fetch logged to `meta/fetch.log`.
- [ ] Search misses and alias gaps go to `.cache/search-misses.log` (untracked). `kb.py forget-check "<words>"` greps the working tree (excluding .git/.cache) without logging.
- [ ] capture triggers only on explicit markers (remember, from now on, that's wrong, not true, no longer, has changed, I prefer, onthoud, voortaan, klopt niet, a leading "no,"/"nee,").
- [ ] Tests: `test_kb_toml_types`, `test_env_file_ignored_for_embeddings`, `test_fetch_rejects_long_query`, `test_forget_check_finds_leftovers_and_logs_nothing`, `test_capture_ignores_task_language`.

### Task 6: Instruction fixes (F10-F15, 3.1-3.3) and semantic tweaks (15)
**Files:** agents, skills, `CLAUDE.md`, `kbsem.py`, `kb.py`.
- [ ] `omitClaudeMd: true` for librarian and reviewer (their files carry what they need); librarian no longer reads `index.md` first; one copy of the filing protocol (CLAUDE.md), skills point to it.
- [ ] fix: errata/golden before the commit; init-kb: no restart note, edits `kb.toml`; ingest: `git status` from the KB root; reviewer file name with time.
- [ ] Semantic: calibrate to <= 5% false pointers with >= 40 negatives; `similar` adds the top-2 vector neighbours labelled "nearest by meaning"; vectors kept as `array('f')`; canary also in `index`.
- [ ] Full suite green; template `kb.py check` clean; docs (README evidence section, design, experiments) say what is and is not verified. Commit and push as v5.
