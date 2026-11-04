# Design: trusted architecture conformance boundary

## Decision

Separate observation from decision. A trusted scanner binds the actual Git base and head, parses source and dependency artifacts, calculates resource digests, and signs an observation. A control plane resolves current policy, standards, ADR status, exception authority, and system impact from external registries.

## Alternatives

1. **Candidate self-report:** rejected because the subject could assert the condition being evaluated.
2. **Human review only:** retained for novel decisions, but insufficient for repeatable high-volume checks.
3. **One Boolean gate:** rejected because known prohibition, missing evidence, review, and reassessment require different remediation.

## Trust boundaries

- Candidate owns source and may propose ADRs or exceptions.
- Scanner owns derived repository observations.
- Enterprise authority owns active policy, standards, and ADR lifecycle.
- Architecture authority owns exception approval.
- Release control consumes the report but remains a separate authorization boundary.

## Failure behavior

Identity, signature, policy revision, Git binding, and exception ambiguity fail closed. Missing runtime egress evidence returns `INSUFFICIENT_EVIDENCE`. A novel technology returns `REVIEW_REQUIRED`. A superseded ADR returns `REASSESSMENT_REQUIRED`.
