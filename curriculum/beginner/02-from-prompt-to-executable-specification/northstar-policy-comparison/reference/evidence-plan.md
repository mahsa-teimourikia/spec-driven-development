# Evidence plan

| Evidence ID | Kind | Claim supported | Requirement |
|---|---|---|---|
| TEST-001 | Acceptance | Exactly two authorized policy IDs are accepted; unauthorized IDs reveal no content | REQ-CMP-001, SEC-CMP-001 |
| EVAL-001 | Domain evaluation | Claims have applicable-side support; missing support causes abstention | REQ-CMP-002, REQ-CMP-003 |
| TEST-002 | Policy gate | Consequential record promotion requires a linked authorized reviewer receipt | REQ-CMP-004 |
| LOAD-001 | Load test | p95 complete response meets SLO-CMP-001 under W1 | PERF-CMP-001 |
| TEST-003 | Telemetry inspection | Required IDs exist and prohibited content is absent | OBS-CMP-001 |

Passing evidence demonstrates the listed claims under the tested conditions. It does not prove the requirements are complete, grant a policy exception, or authorize production release.
