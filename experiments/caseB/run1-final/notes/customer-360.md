---
id: customer-360
type: dataset
title: customer_360 table
summary: The customer_360 table in the warehouse: current refresh interval and the change from hourly.
aliases: [customer_360, customer 360 table, customer_360 refresh]
status: current
updated: 2026-11-14
---
## Claims
- The customer_360 table refreshes every 4 hours (as of 2026-11-03). [src: 2026-11-03-slack-analytics-eng §analytics-eng "customer_360 refreshes every 4 hours"] [src: 2026-11-03-slack-analytics-eng §header "# analytics-eng - export 2026-11-03"]
- The customer_360 refresh was hourly until the Orion 4.2 migration; it was moved to every 4 hours to keep the cluster calm, and hourly is off the table for now (as of 2026-11-03). [src: 2026-11-03-slack-analytics-eng §analytics-eng "it was hourly until the Orion 4.2 migration, we moved to every 4 hours to keep the cluster calm"] [src: 2026-11-03-slack-analytics-eng §header "# analytics-eng - export 2026-11-03"]
