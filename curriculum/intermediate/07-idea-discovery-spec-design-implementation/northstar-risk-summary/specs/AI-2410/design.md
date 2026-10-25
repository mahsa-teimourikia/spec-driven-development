# AI-2410 design record

- **Status:** APPROVED_FOR_BOUNDED_IMPLEMENTATION
- **Revision:** `ADR-RISK-008@2`
- **Pattern:** proposal → deterministic validation → human review

## Components

1. Trusted context builder selects authorized, submission-scoped evidence and pins its revisions.
2. A model-facing generator creates non-authoritative risk claims or a controlled insufficient-evidence outcome.
3. Trusted validation independently rechecks context membership, authorization, submission scope, freshness, citation existence, topic relevance, exact structured-fact support, and forbidden actions.
4. An effect boundary remains uncalled when untrusted evidence induces a forbidden action request.
5. Human review resolves an opaque caller receipt ID through a trusted registry, then consumes the exact authenticated record once.
6. Integration review receives reproducible executed evidence; merge and release authority remain outside this slice.

## Receipt durability

The reference path uses a process-local store to make the limitation visible. A second exercise uses SQLite with a primary-key uniqueness constraint so consumption is atomic and replay remains blocked after a store-object restart. A production design requires managed durable storage, atomic compare-and-set semantics, revocation and expiration checks, secure time, authenticated principals, audit retention, and concurrency testing.

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
