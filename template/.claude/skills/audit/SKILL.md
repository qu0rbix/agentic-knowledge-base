---
name: audit
description: Use when the owner asks for a health check ("audit the KB", "is the KB still right?"), weekly or monthly, or right after a big change in reality (reorg, project end, vendor switch). Never scheduled.
---
Read-only until the owner approves. Output: `meta/audits/<today>-audit.md` with at most 7 decisions for the owner, sorted by risk, plus the reviewer's findings.

1. **Review recent filings and what new sources touch** - this is where the reviewer lives in the default mode. Take the notes changed since the last audit (`git log --since=<last audit date> --name-only --format= -- notes`) plus the notes about the subjects of sources frozen since then (`git log --since=<last audit date> --name-only --format= -- sources`, then `uv run tools/kb.py search "<subject>"` per new source): stale claims sit in old notes a new document changed. Spawn the reviewer (Agent tool, `subagent_type: reviewer`): "Today is <today>. Review these notes: run `uv run tools/kb.py verify --all <ids>` in batches of about 10." Count its evidence findings (blockers and majors) per 50 claims - that number tells the owner whether review should be "always".
2. **Mechanical**: `uv run tools/kb.py check`, `uv run tools/kb.py stats --since 30d --stale`. Every failure is a row.
3. **Golden questions**: one fresh reviewer per 5-10 lines of `eval/golden.md`: "Answer these from the KB only using the ask skill, write nothing; say not in KB when absent." A wrong or newly missing answer is a row.
4. **Staleness**: stale claims and tier-1/2 web sources past their review interval; re-fetch web sources (`uv run tools/fetch.py <origin> --slug <slug>-recheck`) and compare. Changed -> row "re-verify claims citing <id>".
5. **Clean-up candidates**: notes never linked and untouched for 180 days, expired parking entries, `uncited_sources`, repeated search misses, `owner_messages_not_filed_7d` that look durable -> rows. Never delete.
6. Write the audit file: `severity | item | evidence | proposed action | default if no answer` (safe defaults: keep, flag). Stop. Approved rows are applied afterwards with the normal filing steps.
