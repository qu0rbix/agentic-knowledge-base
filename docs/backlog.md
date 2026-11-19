# Backlog

Ideas that are promising but not proven, and known gaps. Each entry says what the evidence so far is and what would
settle it. Contributions and real-use reports are welcome, especially for the first three.

## Next to build

### Stale-value check in code
**Why:** in the decisive test (case D) 10 of 12 wrong claims across all arms were old values left as current - not
invented facts. **Idea:** `kb.py check` warns when a claim dated "as of X" sits in a note that also cites a newer
source about the same subject, or when two notes state different values for the same entity and attribute.
**Settled by:** the stale-claim count in the first audits of real use.

### Review where it pays
**Why:** a reviewer on every filing cost 5-8x the time with no accuracy gain in case D, yet it caught real errors in
earlier cases (overstatements, dropped conditions, a colleague's remark filed as policy). It now runs in `audit` and,
optionally, on every filing (`[review] mode = "always"`). **Open:** measure the reviewer's evidence findings per 50
claims in the first four audits; if they are frequent, make review automatic for risky filings only (numbers, owner
policy, supersedes) instead of all or nothing. A stronger model than the main agent probably matters most here.

### Upgrades for existing KBs
**Why:** a KB created from the template does not receive fixes. `.akb/version.json` records the template version.
**Idea:** ship the tools, hooks and skills as a Claude Code plugin with a thin template, so upgrades come through
Claude Code; or a `kb.py upgrade` that copies the scaffold files and keeps the owner's charter, settings and project
block. Fable's recommendation: the plugin route.

## Promising, needs evidence

- **Librarian agent for bulk ingest.** A separate filing agent protects the main context on a large batch (dozens of
  documents). As a per-filing default it was slow and dropped correct facts through its review rounds (case D).
- **Researcher and toolsmith agents.** Research and tool-building now run in the main agent. Separate agents kept
  untrusted web text out of the main context and resisted tool sprawl in early cases, but were not exercised recently.
- **Semantic search driven by an agent.** Benchmarked (paraphrase and cross-language recall improve), never used by
  an agent in a case study. Calibrate on real golden questions.
- **Footnote citations** for dense notes (tables). Implemented and tested in code; no agent has written one yet.
- **Coverage recall aid** (`kb.py coverage`). Surfaced one missed fact in case B2; not re-measured since it stopped
  using English rule words.
- **Model allocation.** All testing used Claude Haiku in every role. A stronger reviewer, and possibly a stronger main
  agent, is expected to matter; unmeasured.

## Known gaps

- **Forget is best effort in git.** Removed from the working tree and never committed if no claim cited it; otherwise
  still in earlier commits until the owner rewrites history. Claude Code's own session transcripts keep everything.
- **One session per KB.** Two sessions at once can blame each other's changes; there is no lock.
- **Not yet verified:** the setup interview (`init-kb`) in a live session, Linux and macOS, models stronger than Haiku,
  a KB of thousands of notes (scale, note size, history loss on rewrite), a second person filing in a parallel clone.
- **Command-rewriting hooks** (for example a global hook that prefixes every Bash command) can break the KB's
  allow list; there is no detection yet.

## Removed after testing (kept here for the record)

- **Mandatory librarian + reviewer pipeline on every filing** - 5-8x time, 3-6x cost, no accuracy gain, measured
  losses through blocked claims (case D, Fable review 5). Still available as `review = "always"`.
- **Triage gate** (a Stop hook that forced a decision on every owner message) - added a turn to plain question
  sessions and lost a durable fact to a lazy "task"; replaced by listing uncited messages at session start.
- **Per-agent write zones** - no purpose without the separate agents; sources and owner files stay protected.
- **Skill graduation, index.md, meta/log.md, errata, entity/unit flags** - no measured value (Fable review 2).
