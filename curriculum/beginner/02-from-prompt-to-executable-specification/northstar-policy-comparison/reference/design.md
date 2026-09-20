# Policy comparison design v1

## Boundaries

1. The existing authorization service validates the caller, tenant, and both document IDs before retrieval.
2. A comparison orchestrator requests evidence independently for each document through the existing retrieval boundary.
3. A comparison composer emits structured claims with per-side citation references or an explicit insufficient-evidence marker.
4. The presentation layer labels exploratory results and requires an AI-021 reviewer receipt before consequential-record promotion.
5. Telemetry emits IDs, route, outcome, and timing only; prompts and document content stay outside traces.

## Requirement allocation

| Design element | Requirements |
|---|---|
| Authorization adapter | REQ-CMP-001, SEC-CMP-001 |
| Two-document retrieval and composer | REQ-CMP-002, REQ-CMP-003 |
| Review-receipt gate | REQ-CMP-004 |
| Timing and safe trace adapter | PERF-CMP-001, OBS-CMP-001 |

The design does not grant permission to change authorization, privacy, retention, or review policy. Such changes return to their owners.
