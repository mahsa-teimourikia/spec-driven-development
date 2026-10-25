# AI-2410 discovery record

## Approved intent

Add an evidence-grounded risk-summary **proposal** for authorized underwriting submissions. Preserve deterministic risk classification, the v1 response contract, and human underwriting authority.

## Verified repository and runtime facts

- `LegacyRiskEngine` calculates the authoritative category for the v1 API and nightly batch.
- `SubmissionAPIv1` returns `submission_id`, `risk_category`, and `review_required`.
- High-risk submissions require human review.
- The legacy portal has a published consumer contract, but current production traffic has not yet been confirmed.
- Existing plain-text summaries remain readable during the migration.

The executable discovery manifest binds these claims to repository revision `9c6a4d8f1e2b7a5036d991ac84f0b234d6a19e72` and preserves provenance and confidence.

## Discrepancies and unknowns

| ID | Finding | State | Route |
| --- | --- | --- | --- |
| Q-DISC-001 | Is the legacy portal still an active external consumer? | OPEN | Service owner plus runtime telemetry |
| Q-DISC-002 | Is deprecated logging field `legacy_reason` consumed externally? | OPEN | Data governance and reporting owners |
| DISC-DEF-003 | A malformed submission can return a 500 instead of a controlled 4xx | DEFECT CANDIDATE | Separate defect decision; do not preserve silently |

## Non-goals

- Replacing deterministic risk classification.
- Automatically approving, declining, or repricing a submission.
- Sending broker communication.
- Retiring the v1 API, legacy summary field, or nightly batch.
- Claiming production model quality from the deterministic teaching fixture.
