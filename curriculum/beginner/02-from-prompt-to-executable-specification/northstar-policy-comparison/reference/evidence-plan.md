# Evidence plan

| Evidence ID | Kind | Claim supported | Requirement | Plan/version | Threshold owner |
|---|---|---|---|---|---|
| TEST-001 | Acceptance/security | Exactly two authorized policy IDs are accepted; unauthorized IDs reveal no content | REQ-CMP-001, SEC-CMP-001 | TEST-001 v1 | Product Security |
| EVAL-001 | Domain evaluation | Citation completeness, citation correctness, claim faithfulness, and abstention correctness meet their thresholds | REQ-CMP-002, REQ-CMP-003 | D1 v1 + EVAL-001 v1 | Underwriting domain owner + AI Governance |
| TEST-002 | Policy gate | Consequential record promotion requires a valid linked authorized-review receipt | REQ-CMP-004 | TEST-002 v1 | AI-021 owner |
| LOAD-001 | Load test | p95 complete response meets SLO-CMP-001 under W1 | PERF-CMP-001 | LOAD-001 v1 | Product + service owner |
| TEST-003 | Telemetry inspection | Required IDs exist and prohibited content is absent | OBS-CMP-001 | TEST-003 v1 | Observability Platform |

## Planned EVAL-001 measures

| Measure | Meaning | First-release threshold |
|---|---|---|
| Citation completeness | Proportion of factual claims with all required source support identified | 100% |
| Citation correctness | Proportion of cited passages that support the proposition for which they are cited | ≥ 95% |
| Claim faithfulness | Proportion of factual claims entailed by authorized retrieved evidence | ≥ 95% |
| Abstention correctness | Proportion of insufficient-evidence cases that abstain without inventing a policy fact | ≥ 95% |

These are fictional approved training thresholds. Execution must still record the dataset version, evaluator/rubric version, environment, implementation SHA, numerator, denominator, result, and approval identity.

## Evidence lifecycle at specification time

| Evidence | Planned | Implemented | Executed | Passed | Approved | Observed in production |
|---|---:|---:|---:|---:|---:|---:|
| TEST-001 | ✓ | — | — | — | — | — |
| EVAL-001 | ✓ | — | — | — | — | — |
| TEST-002 | ✓ | — | — | — | — | — |
| LOAD-001 | ✓ | — | — | — | — | — |
| TEST-003 | ✓ | — | — | — | — | — |

The links are 100% planned, but verification coverage is 0% because nothing has been implemented or executed. Later evidence can support only the listed claims under recorded conditions; it cannot prove the requirements are complete, grant an exception, or authorize production release.
