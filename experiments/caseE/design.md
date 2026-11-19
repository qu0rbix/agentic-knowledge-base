# Case E design: how much provenance does the wiki need?

Question from the owner: would a wiki that cites nothing (but is very careful about what it admits, and is audited
periodically against the sources) be better? Also test a light Wikipedia style where only the important bits are cited.

## Arms (same 22 scripted sessions and documents as case D, Haiku, 2 runs each)
All four "wiki" arms use the plain-wiki harness from case D (fast, cheap, and in case D as accurate as the gated
scaffold). Only the provenance paragraph of CLAUDE.md differs; every arm gets the same careful-admission paragraph.
1. CITE  - every claim cites its source file and quotes the passage (case D PLAIN).
2. LIGHT - Wikipedia style: inline `[file]` / `[owner, date]` only on claims that matter or could be challenged
           (dates, versions, numbers, decisions, policies, surprising/contested); no quotes; background uncited.
3. NOTE  - no inline citations; each note ends with `## Sources` listing the files / owner dates it relies on.
4. NONE  - no citations, no record of origin; very careful admission only.
5. KB    - the actual scaffold at main (per-claim quotes + deterministic checks, direct filing), as reference.

## Measures
A. Accuracy (blind Opus judge, case D key): 16 key facts, wrong current claims / total, 30 answers, owner statements, traps.
B. Readability (same judge): three fixed notes (Node.js 16 / Node schedule, PostgreSQL policy, our standards) rated 1-5
   for "a busy engineer gets the answer fast", plus "can you tell how solid a statement is" 1-5.
C. Audit: after s22, copy each KB and plant 4 errors in the arm's own style:
   P1 stale value: Node 16 EOL current value set back to 2024-04-30 (history left as is)
   P2 mangled number: PostgreSQL 13 EOL 2025-11-13 -> 2025-11-20
   P3 invented claim with a plausible citation (where the style cites): "Node.js 18 security support extended to
      2025-10-31 for OpenSSL 3 users."
   P4 overstated plan: "The build servers were upgraded to Debian 12 (bookworm)." (owner said: planned Q1 2025)
   Then one audit session per KB (same prompt for all arms: check every current claim against sources/ and
   work/owner-messages.md, report problems, do not edit). Measures: planted found (of 4), false alarms (judge-checked
   sample), audit cost/time/tool calls. Haiku auditor on all runs; Sonnet auditor on run 1 of each arm.
   KB arm also: does `kb.py check` catch any plant deterministically?
D. Cost and wall time of the 22 sessions.

## Known limits
- Owner messages are given to the auditor as a file in every arm (simulates the capture hook).
- 2 runs per arm; case D showed large run-to-run variance (LEAN 10 vs 15 key facts).
- Plants are added after the questions, so they affect only the audit measure.
