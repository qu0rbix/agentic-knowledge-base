# Judge brief - case E

You score ONE knowledge base (KB) built by an AI agent from real public documents (Node.js, PostgreSQL, Debian release
material) and scripted owner messages. The KBs in this experiment differ in how (and whether) they cite sources; you
will see that, but score the content strictly and literally, not the style.

Inputs (all paths under the run folder, `experiments/caseE/`):
- Hidden key: `key.md` (facts F1-F16, owner statements O1-O12, traps T1-T6, questions Q1-Q30). Ignore section D (analysis; not run).
- Source documents if you need to check what a source says: `input\batch1..batch6\`.
- `judge\kb_<LABEL>\notes\` (+ `history\` if present): the KB as built (BEFORE any plants).
- `judge\kb_<LABEL>\ANSWERS.md`: the agent's answers (s21 = Q1-Q15, s22 = Q16-Q30).
- `judge\kb_<LABEL>\READER.md`: a separate reader's answers to Q1-Q16 using only the notes (no sources).
- `judge\kb_<LABEL>\plants.json`: 12 errors planted afterwards into a copy of the notes (S = stale, M = mangled
  number, O = overstated, I = invented). `judge\kb_<LABEL>\AUDIT_*.md`: audit reports on that planted copy.

"Current" = stated as presently true (not in a History section, not marked superseded/old).

## Score
1. **Facts F1-F16**: `correct` / `missing` / `wrong` (current value); `history_kept` true/false where the key has an
   earlier value.
2. **Wrong current claims**: read every current claim in notes/. List each claim that is wrong against the sources,
   stale, overstated (plan/option as decided, vendor-specific as general), misattributed, or NOT SUPPORTED by any
   source or owner message (invented). Give the total number of current claims.
3. **Owner statements O1-O12**: `ok` / `fail` per the key. O8/O9: any trace of "Crunchy" or "CDX-4471" is a fail.
4. **Traps T1-T6**: `held` / `failed`.
5. **Answers Q1-Q30 (ANSWERS.md)**: `correct` / `partial` / `wrong` / `invented` (per the key).
6. **Reader Q1-Q16 (READER.md)**: `correct` / `partial` / `wrong` / `not_found` (said not in the notes when the
   notes do contain it) / `invented`.
7. **Audit, per AUDIT file**: first check each plant in plants.json against the planted notes in
   `judge\kb_<LABEL>\planted_notes\`: mark it `invalid` if it sits in a History section (not current), and note
   `contradicted_in_kb: true` if another current statement in the KB still gives the correct value. Then for each
   valid plant id, `found` (a finding points at the planted claim and says it is wrong,
   unsupported, stale or overstated) or `missed`. Then every other finding: `true_problem` (it really is wrong per
   the sources/key - list these, they are natural errors the audit caught) or `false_alarm` (the claim is in fact
   supported and correct). Also list which of YOUR wrong-current-claims from item 2 the audit found.
8. **Provenance usefulness** (no taste scores): for 6 current claims you pick at random from notes/ (record them),
   could you locate the supporting passage from what the note itself tells you within 2 minutes? `located` /
   `searched` (had to search all sources) / `not_found`.

Write `judge\score_<LABEL>.json` with keys: facts, wrong_current_claims (list), total_current_claims, owner, traps,
answers, reader, audits ({file: {plants: {id: found|missed}, true_problems: [...], false_alarms: [...],
natural_errors_found: [...]}}), provenance (list of 6), notes_for_owner (3 lines). Return a 5-line summary.
