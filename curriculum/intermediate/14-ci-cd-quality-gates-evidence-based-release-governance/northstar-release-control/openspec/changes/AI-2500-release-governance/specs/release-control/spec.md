# Release-control specification

## Requirements

- **REL-001:** The control plane SHALL recompute and compare the exact artifact digest before release eligibility.
- **REL-002:** The control plane SHALL authenticate provenance and evidence producers against protected trust policy.
- **REL-003:** The control plane SHALL bind evidence to the release manifest and its declared dependencies.
- **REL-004:** The control plane SHALL derive required evidence from protected risk policy and fail closed on unknown risk.
- **REL-005:** Production approval SHALL bind the exact manifest digest, environment, principal, role, issuance, expiry, and state.
- **REL-006:** Approval consumption and operation acceptance SHALL be atomic and single-use.
- **REL-007:** A release SHALL become `ACTIVE` only after required runtime protected invariants pass.
- **REL-008:** A protected-invariant failure SHALL halt and contain the feature while preserving manual review.
- **REL-009:** An unknown external outcome SHALL be reconciled against target state before retry.
- **REL-010:** Recovery SHALL compare the complete effective release identity and remain incomplete while consequential reconciliation is open.
- **REL-011:** Deployment authorization SHALL reverify the stored manifest, immutable registry artifact, provenance, current evidence, current policy, and current scoped authority before consuming receipts.
- **REL-012:** Functional, AI, and security evaluation SHALL execute the exact packaged artifact identified by the evidence subject digest.
- **REL-013:** Runtime activation SHALL resolve authenticated, operation-bound observations from a protected registry and enforce minimum coverage.
- **REL-014:** Recovery SHALL require incident-scoped authorization before effects and independently observe restored state and authenticated reconciliation evidence before activation.
- **REL-015:** Evaluation thresholds SHALL be resolved from the approved contract revision rather than duplicated in evaluator code.

## Evidence boundary

Local deterministic fixtures establish executable control behavior, not production builder certification, general AI quality, or deployment authority.
