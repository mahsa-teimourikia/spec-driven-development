# AI-2605 quality evidence specification

## ADDED requirements

### QL-REQ-001 — Exact multi-repository subject

The trusted observer SHALL bind evidence to all participating full Git commits, contract digest, protected-oracle digest, evaluation-dataset digest, specification revision, policy revision, suite revision, producer, and execution interval.

### QL-REQ-002 — Independent correctness ownership

Candidate tests SHALL remain diagnostic. A coding agent SHALL NOT change protected requirements, oracle revisions, holdout labels, or mandatory obligations to make its candidate pass.

### QL-REQ-003 — Actual behavior

Quality evidence SHALL execute service behavior for QI-001 through QI-005 and SHALL NOT treat configuration flags, test names, or self-reported receipts as proof.

### QL-REQ-004 — Concurrency and failure safety

The harness SHALL exercise concurrent duplicate delivery, conflicting idempotency reuse, interrupted transactions, stale and revoked approval, service outage, contract change, and unsupported evidence. Each experiment SHALL assert the expected safe state.

### QL-REQ-005 — AI evaluation integrity

AI evaluation SHALL report explicit populations, overall and per-class metrics, protected slices, unsupported-evidence rate, and limitations. A protected violation SHALL NOT be offset by aggregate improvement.

### QL-REQ-006 — Test effectiveness

The policy-selected mutation population SHALL include ambiguity, tenant, authority, idempotency, approval, provenance, and outage faults. Each critical mutant SHALL be reported individually.

### QL-REQ-007 — Uncertainty and freshness

Unknown impact, missing mandatory tests, untrusted oracles, forged receipts, and absent evidence SHALL be insufficient. Changed subjects or policy/suite revisions SHALL produce stale evidence. Mixed results SHALL require review.

### QL-REQ-008 — Authority separation

The reference package SHALL stop at `READY_FOR_INTEGRATION_REVIEW` and SHALL NOT authorize merge, deployment, activation, or release.
