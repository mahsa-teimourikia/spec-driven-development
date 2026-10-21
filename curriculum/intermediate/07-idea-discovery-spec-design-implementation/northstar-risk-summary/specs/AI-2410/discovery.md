# AI-2410 discovery — Underwriting Risk Summary

## Business outcome

Reduce underwriter review effort by preparing an evidence-grounded summary proposal. This outcome does not select a model, authorize underwriting decisions, or authorize broker communication.

## Confirmed current-system facts

- `SubmissionService` owns authoritative submission and underwriting state.
- Approved submission documents are selected by the application before model-facing execution.
- The existing review workflow can record an authenticated decision over an exact proposal digest.
- The coding and model-facing workloads have no broker-send or underwriting-mutation capability.

## Resolved scope

- Supported slice: one property-submission fixture with approved text evidence.
- In scope: evidence selection, summary proposal generation, citation and support validation, and handoff to human review.
- Out of scope: underwriting decisions, authoritative state changes, broker delivery, production release, and business-outcome claims.

## Discovery evidence register

| ID | Statement | State | Evidence or owner |
| --- | --- | --- | --- |
| DISC-2410-01 | `SubmissionService` owns authoritative state | CONFIRMED | Repository architecture record |
| DISC-2410-02 | Risk codes are supplied by approved domain context | CONFIRMED | Domain contract `RISK-TAXONOMY@12` |
| DISC-2410-03 | Model-gateway quality is sufficient for the production population | UNKNOWN | Requires representative evaluation |
| DISC-2410-04 | Automatic broker communication is allowed | BLOCKED | Underwriting and AI Governance decision required |

Unknown and blocked items remain explicit. They are not converted into implementation defaults.
