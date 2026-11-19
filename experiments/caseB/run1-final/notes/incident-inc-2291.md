---
id: incident-inc-2291
type: topic
title: INC-2291 Orion nightly load missed SLA
summary: Root cause, timeline impact and fixes of INC-2291 (Orion nightly load late on 2026-10-05).
aliases: [INC-2291, Orion SLA miss 2026-10-05, INC-2291 postmortem]
status: current
updated: 2026-11-13
---
## Claims
- INC-2291 root cause: the Checkout team added a new column to the orders table on 2026-10-02 without announcing it, and Fivewire's connector set to block on change stopped the orders sync instead of adding the column. [src: 2026-10-07-incident-postmortem-inc2291 §Summary "Postmortem: INC-2291 - Orion nightly load missed SLA"] [src: 2026-10-07-incident-postmortem-inc2291 §Root cause "The Checkout team added a new column to the orders table on 2026-10-02"] [src: 2026-10-07-incident-postmortem-inc2291 §Root cause "The change was not announced"] [src: 2026-10-07-incident-postmortem-inc2291 §Root cause "Fivewire's schema handling for this connector is set to block on change"]
- INC-2291: the Orion nightly load completed at 08:40 UTC on 2026-10-05, 2 hours 10 minutes after the 06:30 UTC deadline (deadline: [[orion-warehouse]]). [src: 2026-10-07-incident-postmortem-inc2291 §Summary "completed at 08:40 UTC on 2026-10-05, which is 2 hours 10 minutes after the 06:30 UTC deadline"] [src: 2026-10-07-incident-postmortem-inc2291 §Summary "Postmortem: INC-2291 - Orion nightly load missed SLA"]

History: history/incident-inc-2291.md
- A schema contract check was added to the orders ingestion on 2026-10-06; it pages the primary on schema mismatch. [src: 2026-10-07-incident-postmortem-inc2291 §Action items "A schema contract check was added to the orders ingestion on 2026-10-06"]
