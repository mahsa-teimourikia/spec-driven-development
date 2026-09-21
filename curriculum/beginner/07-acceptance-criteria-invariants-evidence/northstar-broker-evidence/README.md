# AI-2219 workshop — Acceptance and evidence portfolio

Course 06 defined the broker-response behavior. Your Course 07 assignment is to design credible,
version-bound evidence for a high-risk slice without rewriting that behavior or inventing release
authority.

## Source behavior

Read these Course 06 artifacts first:

- [behavior contract](../../06-writing-executable-requirements/northstar-broker-response/reference/behavior-contract.json);
- [decision table](../../06-writing-executable-requirements/northstar-broker-response/reference/decision-table.json);
- [state machine](../../06-writing-executable-requirements/northstar-broker-response/reference/state-machine.json); and
- [proposal schema](../../06-writing-executable-requirements/northstar-broker-response/reference/contracts/proposed-update.schema.json).

Then read the [verification ticket](ticket/AI-2219-verification.md).

## Your assignment

1. State the verification scope and exclusions.
2. Complete the [starter acceptance contract](workshop/starter/acceptance-contract.json) with positive,
   negative, boundary, failure, staleness, security, and compatibility criteria.
3. Derive safety, functional, provenance, idempotency, and frame-condition properties with explicit populations.
4. Complete the [evaluation contract](workshop/starter/evaluation-contract.json), including population,
   label provenance, split policy, metrics, and limitations.
5. Complete the [human rubric](workshop/starter/human-rubric.json), including qualifications, independent rating, anchors, adjudication, and agreement denominators; keep its status `not_run`.
6. Complete the [evidence manifest](workshop/starter/evidence/manifest.json) and mark each record `planned` or `executed` without representing not-run work as pass.
7. Complete the [gate policy](workshop/starter/gate-policy.json). Leave the statistical threshold unresolved unless the supplied sources authorize it.
8. Connect requirement → criterion/invariant → evidence in [traceability](workshop/starter/traceability.csv).
9. Run the Course 07 lab and tests. Inject at least one semantic mutant and one stale-evidence failure.
10. Compare with [the reference](reference/) only after you can defend each oracle, population, producer, and gate.

## Expected boundary

- Deterministic acceptance and safety gates may pass for the finite training populations.
- The statistical extraction-quality gate remains blocked because `OQ-EVAL-001` has no approved threshold.
- Human evidence is `not_run`.
- Runtime evidence is visibly labelled simulated and does not authorize a production release.
- Inputs outside the evaluated language, modality, and field population route to manual review.
- Producer names, digests, and revisions are fixture metadata, not signed attestations.

## Run

```bash
python3 curriculum/beginner/07-acceptance-criteria-invariants-evidence/lab.py
python3 -m unittest tests.test_course_07 -v
```
