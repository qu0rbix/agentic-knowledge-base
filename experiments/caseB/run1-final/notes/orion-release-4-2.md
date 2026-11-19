---
id: orion-release-4-2
type: system
title: Orion Platform 4.2 release
summary: Orion Platform 4.2, released 12 Oct 2026: SDK requires Python 3.12 or newer, v1 events API removed, default query timeout 600 seconds.
aliases: [Orion 4.2, Orion 4.2 release notes, Orion 4.2 SDK, v1 events API removal]
status: current
updated: 2026-11-14
---
## Claims
- The Orion 4.2 SDK requires Python 3.12 or newer (since 2026-10-12). [src: 2026-10-12-orion-4-2-release-notes §Breaking changes "The SDK now requires Python 3.12 or newer"] [src: 2026-10-12-orion-4-2-release-notes §header "Released 12 October 2026"]
- Orion 4.2 removes the v1 events API (released 12 Oct 2026). [src: 2026-10-12-orion-4-2-release-notes §Breaking changes "The v1 events API is removed in 4.2"] [src: 2026-10-12-orion-4-2-release-notes §header "Released 12 October 2026"]
- Clients still calling /v1/events receive HTTP 410 and must move to /v2/events (as of 2026-10-12). [src: 2026-10-12-orion-4-2-release-notes §Breaking changes "Clients still calling /v1/events will receive HTTP 410. Please move to /v2/events, which has been available since 4.0"] [src: 2026-10-12-orion-4-2-release-notes §header "Released 12 October 2026"]
- Orion 4.2 raised the default query timeout from 300 seconds to 600 seconds (as of 2026-10-12). [src: 2026-10-12-orion-4-2-release-notes §Breaking changes "The default query timeout was raised from 300 seconds to 600 seconds"] [src: 2026-10-12-orion-4-2-release-notes §header "Released 12 October 2026"]
- Jobs that set their own query timeout are not affected by the new default (as of 2026-10-12). [src: 2026-10-12-orion-4-2-release-notes §Breaking changes "Jobs that set their own timeout are not affected."] [src: 2026-10-12-orion-4-2-release-notes §header "Released 12 October 2026"]
