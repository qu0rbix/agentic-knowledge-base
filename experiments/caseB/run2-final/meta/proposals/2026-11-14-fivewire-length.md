# Proposal: fivewire note length (2026-11-14)

Status: open (owner decision). Nothing moved.

## Problem
`kb.py stats` flags "split fivewire (>400 words)". By `wc -w`, `notes/fivewire.md` is 504 words and `notes/orion.md` is 405 words, both over the 400 threshold. Both counts are inflated by the long exact quotes in the citations.

## Evidence
- `uv run tools/kb.py stats` on 2026-11-14: refactor_hints includes "split fivewire (>400 words)".
- Word counts (`wc -w`): fivewire 504, orion 405, data-retention-policy 386.
- Fivewire holds seven claims: renewal date, renewal offer ($1,020 until 30 Nov 2026), commercial contact, outage route, DPA status, audit report period, payload retention.
- Candidates: 46 in total. 40 are filed or merged (38 new bullets, 2 merges); 5 are parked and 1 is rejected.
- Search misses that stats counts come from the pre-filing searches run against the empty KB on 2026-11-14. After filing and after the review fixes, the 40 filed or merged items were re-checked with `search --keyword` (41 questions, one extra variant); each returned its expected note.

## Options
1. No change (recommended). The rule says one note per entity, and not to split an entity just because it has many claims. Fivewire and orion are each one entity, and their claims belong to that entity. The word counts are inflated by citations; orion is only 5 words over the threshold.
2. Split the security sub-subject out of `fivewire` into `notes/fivewire-security-review.md` (type `topic`): DPA status, audit report period, payload retention. Four claims would move; the renewal and contact claims stay in `fivewire`. This goes against the one-entity rule, so only do it if the owner wants it. No split is proposed for `orion`.

## Moves table (only if option 2 is approved)
| old path | new path | why |
|---|---|---|
| notes/fivewire.md (DPA, audit report, payload retention bullets) | notes/fivewire-security-review.md | security sub-subject, to keep fivewire under 400 words (orion at 405 is left as is) |

Impact: `[[fivewire]]` links from orders-service, inc-2291 and data-platform-budget stay valid. The moved claims keep their citations and history. A new note needs links to fivewire and orders-service.

## What stays the same
Entity ids, all citations, the seven claims and their dates. No claim is removed.
