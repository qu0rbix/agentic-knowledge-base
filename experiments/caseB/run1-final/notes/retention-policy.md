---
id: retention-policy
type: process
title: Brightcart data retention and access policy
summary: Retention periods and PII access limits for the Brightcart data platform (policy v3.1).
aliases: [data retention policy, PII access policy, retention and access policy]
status: current
updated: 2026-11-14
---
## Claims
- Customer personal data in the Orion warehouse is retained for 24 months after the customer's last order, then purged by the monthly purge job (policy version 3.1, effective 1 September 2026). [src: 2026-09-25-data-retention-policy §2.1 "retained for 24 months after the customer's last order"] [src: 2026-09-25-data-retention-policy §header "Version 3.1, effective 1 September 2026, supersedes version 3.0"]
- Raw clickstream events are retained for 13 months (policy version 3.1, effective 1 September 2026). Aggregated clickstream tables may be kept longer if they contain no personal data. [src: 2026-09-25-data-retention-policy §2.2 "Raw clickstream events are retained for 13 months"] [src: 2026-09-25-data-retention-policy §2.2 "Aggregated clickstream tables may be kept longer if they contain no personal data"] [src: 2026-09-25-data-retention-policy §header "Version 3.1, effective 1 September 2026, supersedes version 3.0"]
- Temporary PII access is granted for no more than 90 days and can be renewed once. [src: 2026-09-25-data-retention-policy §3.2 "Temporary PII access is granted for no more than 90 days and expires automatically; it can be renewed once."]
- Exceptions to any rule in the retention and access policy require written sign-off from the Head of Data (policy version 3.1, effective 1 September 2026). [src: 2026-09-25-data-retention-policy §4.1 "require written sign-off from the Head of Data"] [src: 2026-09-25-data-retention-policy §header "Version 3.1, effective 1 September 2026, supersedes version 3.0"]
- Production PII extracts must not be stored on shared drives or in personal cloud storage (policy section 3.3, version 3.1, effective 1 September 2026). [src: 2026-09-25-data-retention-policy §3.3 "3.3 Production PII extracts must not be stored on shared drives or in personal cloud storage"] [src: 2026-09-25-data-retention-policy §header "Version 3.1, effective 1 September 2026, supersedes version 3.0"]

History: history/retention-policy.md
