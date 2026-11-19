# log

2026-11-14 | file | retention-policy | Customer personal data in Orion is retained 24 months after last order (policy v3.1)
2026-11-14 | file | retention-policy | Temporary PII access is granted for no more than 90 days, renewable once
2026-11-14 | file | incident-inc-2291 | INC-2291 root cause: unannounced orders column on 2026-10-02 blocked Fivewire sync
2026-11-14 | file | incident-inc-2291 | INC-2291 Orion nightly load completed 08:40 UTC on 2026-10-05, 2h10m after 06:30 deadline
2026-11-14 | file | incident-inc-2291 | Schema contract check added to orders ingestion on 2026-10-06
2026-11-14 | file | vendor-security | Security policy requires SOC 2 Type II report from every PII vendor
2026-11-14 | file | orion-warehouse | Priya Nair owns the Orion warehouse (14 Sep 2026 ops sync)
2026-11-14 | file | orion-warehouse | Orion nightly load must land by 06:30 UTC
2026-11-14 | file | monitorly | Monitorly costs $640 per month, contract ends 2026-12-31
2026-11-14 | file | fivewire | Fivewire offered Brightcart $1,020/month for 12-month term if signed by 30 Nov 2026 (list-price figure dropped)
2026-11-14 | file | schema-change-notice | Source teams post schema changes in #src-schema-alerts 3 business days before release
2026-11-14 | reject | - | StreamHub retention 7 days: contradicted; 14 days since 2026-10-22 (2026-10-27-ops-sync)
2026-11-14 | reject | - | Orion 4.2 default query timeout 900 s: source says 600 s
2026-11-14 | reject | - | Orion nightly load deadline: quote does not support claim (duplicate of 06:30 UTC, filed)
2026-11-14 | reject | - | Cobalt Cloud reserved commitment $410,000 attributed to Fivewire: wrong vendor
2026-11-14 | reject | - | Fivewire retains Brightcart payloads: claim inverts its quote (does not retain)
2026-11-14 | file | retention-policy | Raw clickstream events retained 13 months (policy v3.1, section 2.2)
2026-11-14 | reject | - | Fivewire 20% discount for annual billing: quote says 15%; tier-4 pricing page
2026-11-14 | merge | retention-policy | Customer personal data in Orion kept 24 months (two years) after last order: existing bullet
2026-11-14 | reject | - | Priya Nair owns StreamHub: quote is about the Orion warehouse; 27 Oct 2026 ops sync says Marcus owns StreamHub
2026-11-14 | file | orion-release-4-2 | Orion 4.2 SDK requires Python 3.12 or newer (since 2026-10-12); new note
2026-11-14 | file | budget-fy27 | Helen Okafor is budget owner; requests pushing FY27 spend over the cap go through her (15 Oct 2026); new note
2026-11-14 | file | on-call | Orion pages escalate to secondary on-call if primary has not acknowledged within 15 minutes (2 Oct 2026); new note
2026-11-14 | file | tallybase | 30-day Tallybase pilot starting 2 Nov 2026, decided 27 Oct 2026; Marcus Lindqvist owns pilot; new note
2026-11-14 | file | monitorly | Monitorly stays primary alerting system during the Tallybase pilot (decided 27 Oct 2026); split from the same candidate
2026-11-14 | file | fivewire | Fivewire DPA refresh not signed, nothing approved (as of 20 Oct 2026)
2026-11-14 | file | budget-fy27 | Hiring freeze on two open data engineer roles holds until April 2027 (15 Oct 2026)
2026-11-14 | merge | fivewire | Fivewire holds Brightcart at $1,020/month for 12-month term: existing bullet keeps 30 Nov 2026 condition
2026-11-14 | reject | - | Helen Okafor said FY27 budget can rise by $300,000: quote not in any source; owner's 16 Oct 2026 message says no increase agreed
2026-11-14 | reject | - | Production PII extracts stored on shared drives or personal cloud: inverts policy 3.3 (must not)
2026-11-14 | park | - | Fivewire Standard overage $0.35 per million rows: source says per 1,000; tier-4 only (meta/parking.md)
2026-11-14 | reject | - | Tallybase replacing Monitorly (2 Oct 2026 status): superseded by the 27 Oct 2026 decision
2026-11-14 | merge | on-call | Orion pages escalate to secondary on-call: less precise duplicate of the 15-minute claim; citation added
2026-11-14 | park | fivewire | Fivewire DPA not signed, nothing approved (as of 20 Oct 2026): WIP status, moved from file after review (expires 2027-01-13)
2026-11-14 | file | budget-fy27 | FY27 cloud spend cap for the data platform is $2.4 million (15 Oct 2026): added after review
2026-11-14 | file | monitorly | Review fix: Monitorly remains primary during Tallybase pilot, linked to [[tallybase]] (replaces the duplicated pilot bullet)
2026-11-14 | file | schema-change-notice | Checkout owns the orders-service and its schema; Checkout responsible for contract changes (as of 3 Nov 2026)
2026-11-14 | reject | - | Fivewire 99.99% pipeline reliability: marketing claim from tier-4 pricing page, does not answer the list-price question
2026-11-14 | reject | - | Orion ingestion schema check mandatory until 2027-03-31: end date not in cited postmortem; supported fact already in incident-inc-2291
2026-11-14 | file | privacy-deletion | Customer deletion requests propagated to Orion within 7 days (design notes 9 Nov 2026); new note; "Legal" wording dropped, source says Lucia and Priya Nair
2026-11-14 | file | retention-policy | Exceptions to the retention and access policy need written sign-off from the Head of Data (policy 3.1, effective 1 Sep 2026)
2026-11-14 | reject | - | Brightcart pays $1,150 per month for Fivewire Standard: $1,150 is list price on tier-4 page; Brightcart offer is $1,020 (fivewire note)
2026-11-14 | reject | - | Brightcart replacing Monitorly with Tallybase: 2 Oct 2026 "evaluate" status superseded by 27 Oct 2026 decision (Monitorly stays primary)
2026-11-14 | file | fivewire | Brightcart's current Fivewire renewal date is 31 January 2027 (as of 21 Sep 2026)
2026-11-14 | file | orion-warehouse | Requests to the Orion team go through #data-requests, first response within 2 business days; Priya Nair triages (27 Oct 2026); two bullets
2026-11-14 | reject | - | Brightcart decided a three-year Cobalt Cloud commitment: source says only "could look at", "No plan to do this now" (considering, not decided)
2026-11-14 | reject | - | Airflow 2.10 upgrade scheduled for 2026-10-20: stale scheduling fact; upgrade completed per 27 Oct 2026 ops sync
2026-11-14 | reject | - | Vendors must provide SOC 2 Type II (C45 candidate): cited quote is about a pen test summary; fact already in vendor-security with correct citation
2026-11-14 | merge | budget-fy27 | Data platform cloud spend capped at $2.4 million for FY27: already filed with same citation; no second bullet
2026-11-14 | file | streamhub | Marcus owns StreamHub, Aiko is backup (27 Oct 2026); new note
2026-11-14 | file | budget-fy27 | Cobalt Cloud quoted one-year reserved commitment of $410,000 for Orion compute, saves roughly a fifth vs on-demand (15 Oct 2026); quoted, not decided
2026-11-14 | park | fivewire | Fivewire annual billing discount 15% versus monthly: tier-4 pricing page only (meta/parking.md, expires 2027-01-13)
2026-11-14 | file | streamhub | StreamHub retention raised from 7 days to 14 days (decided at 14 Sep 2026 ops sync)
2026-11-14 | file | retention-policy | Production PII extracts must not be stored on shared drives or in personal cloud storage (policy 3.3, v3.1)
2026-11-14 | file | fivewire | Fivewire does not retain Brightcart payloads after delivery to Orion (questionnaire, 20 Oct 2026)
2026-11-14 | reject | - | Fivewire syncs up to 10x faster: marketing line on tier-4 pricing page; does not answer the list-price question
2026-11-14 | file | customer-360 | customer_360 refreshes every 4 hours (as of 3 Nov 2026); new note
2026-11-14 | file | orion-release-4-2 | Orion 4.2 removes the v1 events API; /v1/events returns HTTP 410, clients move to /v2/events
2026-11-14 | park | fivewire | Fivewire annual plans auto-renew unless cancelled 60 days before renewal: tier-4 pricing page only (expires 2027-01-13)
2026-11-14 | file | streamhub | StreamHub retention is 14 days (as of 27 Oct 2026); change applied 22 Oct 2026
2026-11-14 | merge | orion-warehouse | Priya Nair owns the Orion warehouse: identical bullet and citation already filed; no edit
2026-11-14 | park | fivewire | Fivewire Standard list price $1,150 per month incl. 5 million rows: tier-4 pricing page only (expires 2027-01-13)
2026-11-14 | park | fivewire | Fivewire Standard overage $0.35 per 1,000 rows: already in meta/parking.md; duplicate, no new entry
2026-11-14 | needs-context | orion-release-4-2 | Python 3.12 requirement enforced from 2027-01-01: no source gives that date; base fact already filed
2026-11-14 | file | orion-release-4-2 | Orion 4.2 raises default query timeout from 300 to 600 seconds; jobs with own timeout unaffected
2026-11-14 | file | fivewire | Dana Whitcombe is Brightcart account manager for Fivewire and commercial contact; outages go to support portal
2026-11-14 | reject | - | Lucia Moretti: Fivewire DPA signed by end of October: forward-looking promise, not durable; DPA status is parked
2026-11-14 | reject | - | Orion nightly load must complete by 06:30 CET: source says 06:30 UTC; filed bullet already correct
