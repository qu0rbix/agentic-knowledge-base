# Design: language-neutral KB (draft for review)

## Goal
The owner works with the KB in any language and any wording, and never has to think about trigger words. Accuracy of
the KB stays the top priority (above token cost). Nothing runs on a schedule. Deterministic guards stay where they
protect accuracy, but **code never has to understand the owner's words**: understanding goes to a model, and code
checks the outcome with language-free tests.

## Inventory of language-dependent code today (v5.1 + case A)
| Where | What | Who writes the text | Failure if language/wording unknown |
|---|---|---|---|
| capture.py `owner_text` | `^/?(forget\|vergeet)` withholds a forget request's content | owner | **privacy**: content of a forget request saved verbatim |
| capture.py + kb.toml `[capture] phrases` | EN/NL regexes set a "file this" flag; Stop hook blocks once | owner | missed reminder -> durable correction not filed |
| capture.py `PASTED` | strips `<pasted_content>` blocks | owner UI | the CLI expands pasted text in place (docs): pasted material may be saved as the owner's own words (tier 1) |
| kb.py `STAMP`/`FRESH` | `as of / since / per / from <ISO date>` | librarian | wrong freshness / number exemption |
| kb.py `IDENT` | `section/policy/clause/rule/step/version/art N` are not quantities | sources | false FAIL (safe) |
| kb.py `numbers()` | strips `,` -> "3,5"="35", "1.204"!="1,204" | sources + librarian | false FAIL across notations (safe) |
| kb.py `wsnorm` | only ' ' " " normalised | sources | correct quote fails on „ « » ‚ (safe) |
| kb.py `STOP` | EN+NL stopwords for keyword search | owner/agent queries | ranking noise |
| kb.py FTS5 `porter` | English stemmer | all | Dutch/German inflections and compounds missed |
| kb.py `MONTHS`, entity skip list | verify ENTITY flags | librarian | advisory noise (German nouns are capitalised) |
| kb.py `RULE_WORDS` | coverage recall aid | sources | recall aid blind in other languages |
| `RESOLVED`, `## Superseded`, `History:`, `## Related` | structure markers | agents | none if they stay fixed syntax |

## Proposal

### 1. Owner messages: the model judges, code verifies
- **Prompt-time reminder (every owner message, language-free).** `capture.py prompt` keeps saving the message verbatim and
  returns `hookSpecificOutput.additionalContext`: `Owner message saved as [src: user <date> ...] (id <id>). Decide, in
  whatever language it is in: does it state a durable fact, correction, preference or rule, or ask to forget/remove
  something? If so, act this turn (note / fix skill; forget -> fix skill Forget steps, including this message id).`
  The main model reads every language; no phrase list.
- **Stop backstop - options to review:**
  - (a) **Agent hook** (`type: "agent"`, experimental) on Stop: reads the owner messages captured this turn and the
    inbox/notes changes, returns `{ok:false, reason}` if something durable was left unfiled. Invisible, language-free,
    but a subagent call on every turn (latency, cost) and experimental.
  - (b) **Triage record + command hook**: the main agent ends each turn that had an owner message with one tool call
    `uv run tools/kb.py triage <msg-id> none|filed|forget "<one-line why>"` (or files a candidate, which counts).
    `capture.py stop` (command hook, deterministic) blocks once if a message of this turn has neither a triage line nor
    an inbox/notes change. Language-free (agent writes fixed syntax), cheap, auditable (`meta/triage.log` untracked),
    but one extra visible tool call per turn.
  - (c) Prompt hook on Stop: rejected - its input has `last_assistant_message` but not the owner's message.
  - (d) Prompt hook on UserPromptSubmit: rejected - `ok:false` ends the turn (blocks the owner's message).
  Draft choice: **(b)**, because the check stays deterministic and auditable; (a) as a fallback if (b) proves noisy.
- **Forget without a prefix.** Recognising a forget request is the model's job (prompt-time reminder + fix skill). The
  forget flow already deletes captured messages (`kb.py forget`); it now always includes the request's own message id
  (given in the additionalContext). `forget-check` verifies in code that the words are gone. The old `forget|vergeet`
  prefix stays as a harmless extra. New `kb.py check` warning: an uncommitted `sources/user/` file older than N days
  that no claim cites and no triage line covers (left behind by a crashed session).
- **Pasted material.** The hook cannot tell typed from pasted text once the CLI expands it. Rule instead of detection:
  an owner quote (`[src: user ...]`) must be the owner's own statement; material the owner pasted (an email, a vendor
  page) is frozen with `kb.py freeze` as its own source with its real tier. Reviewer checks: a `user` quote that reads
  like a pasted document is a major. Code aid: `verify` marks `user` quotes from messages longer than ~1,500 characters.

### 2. Agent-written syntax stays fixed (no translation)
`(as of YYYY-MM-DD)`, `since YYYY-MM-DD`, `[src: ...]`, `## Superseded`, `History:`, `## Related`, `RESOLVED` are
markup like YAML keys, written by agents in any note language. CONVENTIONS.md says so. No word lists.

### 3. Remove word lists from checks
- `numbers()`: a number in a claim matches a number in a quote if they are equal under either reading (`,` or `.` as
  decimal separator; thousands separators `,` `.` `'` thin space removed). No language needed.
- `IDENT` word list: keep the structural parts (letters+digits, `§`, `#`, versions) and drop the English words; an
  unknown identifier is a safe FAIL that the librarian fixes by quoting the passage that holds it.
- `wsnorm`: normalise every Unicode quotation mark (categories Pi/Pf and „ ‚ « » ‹ ›) and all Unicode spaces.
- `coverage`: list every source sentence that no quote covers (numbers first), drop `RULE_WORDS`; the librarian judges.
- `verify` entity flags: only words absent from the whole source; drop `MONTHS`; skip when the claim's language
  capitalises nouns? -> simpler: keep advisory, whole-source test only.
- Keyword search: drop `STOP`; FTS5 `tokenize = 'trigram'` (language-free, handles compounds and inflection) as the
  default, with `porter` selectable in kb.toml `[search] tokenizer` for English-only KBs; queries shorter than 3
  characters fall back to LIKE. Ranking stays BM25.

### 4. Init
init-kb asks: which languages the owner works in, and which one claims are written in (`note_language` in the charter;
quotes are always verbatim). The librarian adds aliases in the owner's other working languages so keyword search finds
the note whatever language the question is in; the `ask` flow translates the question to the note language before the
keyword search. Semantic search: recommend a multilingual model when more than one language is used. No word lists to
configure.

## Verification plan
- Unit tests: number readings, quote marks, trigram search (Dutch/German inflections, compounds), coverage without
  rule words, triage gate, stale-capture warning.
- Live case study (headless Claude Code, Haiku main agent): ~24 owner messages across EN/NL/DE/FR, formal, informal and
  indirect ("btw Jonas took over Fivewire", "das stimmt so nicht mehr", "laat dat Zanzibar-verhaal maar vallen, het
  klopte nooit"), a hidden key of durable / not durable / forget. Metrics: durable messages filed (target >= 90%),
  non-durable filed (<= 10%), forget requests that leave no trace (100%), turns blocked needlessly by the backstop.
