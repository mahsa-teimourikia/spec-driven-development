# Quality evidence specification

## ADDED requirements

### QL-REQ-001 — Exact quality subject

The trusted observer SHALL bind quality evidence to the exact repository revision, implementation digest, specification revision, and policy revision.

### QL-REQ-002 — Independent evidence authority

Candidate-produced tests SHALL be diagnostic only. Evidence used by the quality decision SHALL be authenticated from the registered independent harness.

### QL-REQ-003 — Requirement-to-evidence portfolio

Every registered requirement SHALL have passing evidence for each risk-selected test kind. Unknown requirement references SHALL block.

### QL-REQ-004 — Independent oracle

A passing test SHALL count only when its oracle is grounded in the approved specification, an independent reference, or a versioned contract.

### QL-REQ-005 — Governed mutation set

The mutation denominator SHALL be the policy-selected critical set. A missing mutation is insufficient evidence and a surviving critical mutant blocks.

### QL-REQ-006 — Failure and recovery

Required timeout, duplicate-delivery, and stale-approval experiments SHALL preserve the registered safe-state oracle.

### QL-REQ-007 — Flake treatment

Mixed outcomes for the same subject SHALL NOT satisfy a quality obligation and SHALL require owner review.

### QL-REQ-008 — Metric integrity

Each metric SHALL expose population, numerator, denominator, value, claim, and relevant exclusions.

### QL-REQ-009 — Release authority separation

A quality report SHALL remain evidence only and SHALL NOT authorize release.

