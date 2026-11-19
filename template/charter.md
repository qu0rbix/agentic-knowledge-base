# KB charter

<!-- NOT YET INITIALISED. Run the `init-kb` skill ("set up this KB") - it interviews the owner and fills this in.
     Owned by the owner: agents may propose changes (meta/proposals/), never edit it directly. -->

## Purpose
_Who this KB serves, and what decisions or work it supports._

## In scope
- _domains, systems, topics_

## Out of scope (non-goals)
- Task status and to-dos (belongs in a tracker).
- One-off errors, debugging steps, temporary workarounds (unless they reveal a durable rule).
- Small talk, personal life, opinions without a decision.
- General knowledge any practitioner already knows.
- Row-level data, customer records, personal data (freeze schema output and aggregates only).

## Admission test (ALL must hold)
1. In scope (above).
2. Durable: still true and useful in a month (or explicitly dated "as of").
3. Not derivable in a minute from a source we hold, the code/data, or general knowledge.
4. Consequential: would change an answer or an action.
5. Evidenced: stated by the owner, cited from a frozen source, or observed in data/outcomes. Not a guess.
6. Novel: no existing claim says it (otherwise reinforce or supersede that claim).
7. Stand-alone: understandable without the session it came from.

## Source trust tiers
| Tier | Sources | Weight |
|---|---|---|
| 1 | The owner; official decisions/docs the owner's org owns | wins conflicts unless older |
| 2 | Colleagues, internal docs, vendor docs about their own product | normal |
| 3 | Reputable third parties | corroborate important claims |
| 4 | Marketing, blogs, unknown | never sole source for important claims |

## Conflicting evidence
Never average or merge conflicting claims. Record each with source, date and what it measures; say which the KB relies on and why, or log it in `meta/open-questions.md`.

## Must answer (golden questions - also in eval/golden.md)
- _10-30 questions the KB must be able to answer_
