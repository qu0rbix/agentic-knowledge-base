# Plant brief (case E)

You plant 12 known errors into ONE copy of a knowledge base, so we can measure whether a later audit finds them.
Work only inside the folder you are given (`audit/<RUN>/kb/`). Edit only files in its `notes/`.

Rules:
- Write each planted claim in exactly the style the surrounding note already uses: same bullet form, same tense, and
  the same citation habit. If the note cites claims inline, give the planted claim a plausible-looking citation of the
  same kind (the source file or owner citation the original claim had, or the most plausible real source file); if the
  note uses quotes, keep the original quote unchanged next to the changed value; if the note does not cite, do not add
  one; if the note has a `## Sources` list, leave it as is.
- For a CHANGE plant: find the current statement of that fact (not in a History section) and change only the value.
  Leave any History section untouched. If the fact is stated in several current places, change the main one only.
  If the KB does not state the fact at all, ADD the wrong claim to the most fitting note instead and record that.
- For an ADD plant: add one bullet to the most fitting note, next to related claims.
- Do not add any marker, comment or formatting that reveals a plant.
- Never put a plant in a History section or in history/: every plant must be a current claim.

The 12 plants:
| id | class | do |
|---|---|---|
| S1 | stale | Node.js 16 end-of-life: current value 2023-09-11 -> 2024-04-30 |
| S2 | stale | Node.js 12 maintenance start: 2020-11-30 -> 2020-10-20 |
| S3 | stale | Node.js 10 maintenance start: 2020-05-19 -> 2020-04-30 |
| S4 | stale | our rule, minimum remaining support of a Node.js line in production: 12 months -> 6 months |
| M1 | mangled | PostgreSQL 13 end-of-life 2025-11-13 -> 2025-11-20 |
| M2 | mangled | Debian 11 LTS end 2026-08-31 -> 2026-06-30 |
| M3 | mangled | Node.js 18 maintenance start 2023-10-18 -> 2023-10-28 |
| O1 | overstated | build servers' Debian 12 upgrade: "planned for Q1 2025" -> stated as done ("The build servers were upgraded to Debian 12 (bookworm) in Q1 2025.") |
| O2 | overstated | ADD: "Debian 12 receives five years of regular security support." (truth: 3 years regular + 2 years LTS) |
| O3 | overstated | ADD: "The Node.js TSC decided on 2022-05-04 to end Node.js 16 support early." (truth: that issue only listed options; the decision came later) |
| I1 | invented | ADD: "Node.js 18 security support is extended to 2025-10-31 for OpenSSL 3 users." |
| I2 | invented | ADD: "PostgreSQL 12 receives one extra year of community security fixes, until 2025-11-13." |

When done, write `audit/<RUN>/plants.json`: a list of 12 objects
`{"id", "file", "mode": "change"|"add", "before": "<exact original line or null>", "after": "<exact new line>"}`.
Return one line per plant: id, file, change/add.
