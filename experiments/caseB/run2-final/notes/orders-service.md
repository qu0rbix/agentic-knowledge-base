---
id: orders-service
type: system
title: Orders service and orders ingestion
summary: Checkout's orders-service and its schema, and the schema contract check on orders ingestion into Orion.
aliases: [orders-service, orders ingestion, orders schema, orders contract check]
status: current
updated: 2026-11-14
---
## Claims
- Checkout owns the orders-service and its schema; Tomasz Brandt says his team is on the hook for contract changes (as of 2026-11-03). [src: 2026-11-03-slack-analytics-eng Chat "Checkout owns the orders-service and its schema, my team is on the hook for contract changes"] [src: 2026-11-03-slack-analytics-eng header "analytics-eng - export 2026-11-03"]
- Since 2026-10-06 the orders ingestion compares the source schema to the contract before each sync and pages the primary on a mismatch (INC-2291 postmortem action item, marked done). [src: 2026-10-07-incident-postmortem-inc2291 Action items 1 "A schema contract check was added to the orders ingestion on 2026-10-06; it compares the source schema to the contract before each sync and pages the primary on mismatch."]

## Related
- [[inc-2291]]
- [[fivewire]]
- [[customer-360]]

History: none
