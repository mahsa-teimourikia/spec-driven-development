# AI-2410 design record

- **Status:** APPROVED_FOR_BOUNDED_IMPLEMENTATION
- **Revision:** `ADR-RISK-008@2`
- **Pattern:** proposal → deterministic validation → human review

## Components

1. Trusted context builder selects authorized, submission-scoped evidence.
2. A model-facing generator creates non-authoritative risk claims.
3. Trusted validation checks exact context, citation existence, evidence support, freshness, scope, and forbidden actions.
4. Human review consumes an authenticated, expiring receipt bound to the exact validated proposal.
5. Integration review receives evidence; merge and release authority remain outside this slice.

## Protected decisions

- underwriting approval or rejection;
- authoritative submission-state mutation;
- broker communication;
- external data transfer;
- model-gateway replacement; and
- production release.

## Alternatives

| Option | Decision | Reason |
| --- | --- | --- |
| Direct coding from the ticket | Rejected | Collapses unresolved authority and evidence questions into code |
| Autonomous agent with send capability | Rejected | Enlarges the consequential authorization and evaluation surface |
| Proposal and review | Selected | Reuses current services and keeps protected effects behind trusted controls |
| Deterministic rules only | Retained fallback | Strongest predictability, but insufficient for all unstructured evidence |

This record approves a bounded design. It does not approve merge, deployment, or production outcomes.
