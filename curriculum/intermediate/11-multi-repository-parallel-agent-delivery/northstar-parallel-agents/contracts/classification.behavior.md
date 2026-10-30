# Classification proposal behavioral contract

1. `ambiguity_status` is derived from trusted classification state. Ambiguous proposals require review regardless of model confidence; confidence is observable but cannot waive review.
2. `AMBIGUOUS` and `UNSUPPORTED` proposals **MUST** set `review_required` to `true`.
3. Proposal, document, evidence, review, and authenticated workload tenant **MUST** match.
4. The AI Service produces proposals only. It **MUST NOT** mutate authoritative underwriting requirement state.
5. Duplicate logical operations **MUST** reconcile to one effect.
6. A shared revision change requires contract-owner approval, affected-work invalidation, and fresh exact-revision evidence.
