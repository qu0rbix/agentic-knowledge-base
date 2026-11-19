---
id: orion
type: system
title: Orion warehouse
summary: Orion, the Data Platform warehouse and transformation layer: owner, release changes and API breaking changes.
aliases: [Orion, Orion platform, Orion transformation layer, Orion warehouse owner]
status: current
updated: 2026-11-14
---
## Claims
- Priya Nair owns the Orion warehouse going forward, as settled at the ops sync of 14 Sep 2026. [src: 2026-09-14-ops-sync 1. Orion ownership "it was settled that Priya Nair owns the Orion warehouse going forward"] [src: 2026-09-14-ops-sync header "Data Platform Ops Sync - 14 Sep 2026"]
- Requests to the Orion team go through the #data-requests channel and get a first response within 2 business days (as of 27 Oct 2026). [src: 2026-10-27-ops-sync 4. Intake "Requests to the Orion team now go through the #data-requests channel and get a first response within 2 business days."] [src: 2026-10-27-ops-sync header "Data Platform Ops Sync - 27 Oct 2026"]
- Priya triages Orion team requests (as of 27 Oct 2026). [src: 2026-10-27-ops-sync 4. Intake "Priya is the person who triages."] [src: 2026-10-27-ops-sync header "Data Platform Ops Sync - 27 Oct 2026"]
- Orion 4.2 (released 12 October 2026) removed the v1 events API; calls to /v1/events receive HTTP 410. [src: 2026-10-12-orion-4-2-release-notes Breaking changes "The v1 events API is removed in 4.2. Clients still calling /v1/events will receive HTTP 410."] [src: 2026-10-12-orion-4-2-release-notes header "Released 12 October 2026."]
- The replacement for the removed Orion v1 events API is /v2/events, available since Orion 4.0. [src: 2026-10-12-orion-4-2-release-notes Breaking changes "Please move to /v2/events, which has been available since 4.0."]
- From Orion 4.2 (released 12 October 2026) the Orion SDK requires Python 3.12 or newer; Python 3.10 and 3.11 are no longer supported. [src: 2026-10-12-orion-4-2-release-notes Breaking changes "The SDK now requires Python 3.12 or newer. Python 3.10 and 3.11 are no longer supported."] [src: 2026-10-12-orion-4-2-release-notes header "Released 12 October 2026."]
- In Orion 4.2 the default query timeout was raised from 300 seconds to 600 seconds; jobs that set their own timeout are not affected. [src: 2026-10-12-orion-4-2-release-notes Breaking changes "The default query timeout was raised from 300 seconds to 600 seconds. Jobs that set their own timeout are not affected."]
- The 4.1 line gets security fixes only for 90 days after the Orion 4.2 release; 4.2 itself gets patch releases. [src: 2026-10-12-orion-4-2-release-notes Support policy "the 4.1 line gets security fixes only for 90 days after the 4.2 release."]

## Related
- [[orion-nightly-load]]
- [[orion-on-call]]
- [[orders-service]]

History: none
