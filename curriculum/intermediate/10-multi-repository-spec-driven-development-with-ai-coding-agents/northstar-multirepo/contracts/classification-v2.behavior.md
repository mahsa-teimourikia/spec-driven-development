# Classification proposal v2 behavioral contract

The JSON Schema defines structure. These normative obligations define behavior
that cannot be proven by structural validation alone.

- The trusted application, not model confidence, determines
  `ambiguity_status`.
- `AMBIGUOUS` and `UNSUPPORTED` proposals **MUST** set `review_required` to
  `true`, regardless of model confidence.
- `SUPPORTED` proposals **MUST** set `review_required` to `false` unless a
  stricter policy applies.
- The Review Service **MUST** reject a v2 proposal whose document, tenant,
  evidence, or model provenance is absent or inconsistent.
- Required review **MUST** fail closed when the review service is unavailable,
  the reviewer is unauthorized, or the approval is absent, stale, or invalid.
- A review approval **MUST** carry a stable receipt ID, authenticated reviewer
  identity and role, tenant, exact proposal digest, and expiry; it is single-use
  outside an exact idempotent replay.
- A submission ID **MUST** be idempotent. Reuse for a changed proposal **MUST**
  be rejected; an exact duplicate **MUST NOT** create another effect.
- Neither the AI Service nor Review Service may mutate authoritative
  underwriting state. Only the Underwriting API owns that transition.

These obligations are verified by repository-local negative tests and by the
exact-revision integration scenarios in `multirepo_app/git_harness.py`.
