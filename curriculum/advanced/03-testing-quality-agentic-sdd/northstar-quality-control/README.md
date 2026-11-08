# Northstar AI-2605 independent quality-engineering lab

This credential-free package verifies actual behavior from exact temporary Git revisions of `ai-service`, `review-service`, and `underwriting-api`. It combines protected oracles, property and metamorphic populations, JSON contracts, SQLite concurrency, mutation testing, failure injection, deterministic AI evaluation, signed evidence, and a quality-only decision.

## What the reference proves

- every participating component is identified by a reproducible full Git commit;
- ambiguity requires review across 101 confidence values and three metamorphic pairs;
- cross-tenant access and direct AI mutation are denied inside trusted services;
- concurrent identical requests produce one effect while conflicting reuse is rejected;
- seven architecture-significant mutants are killed individually;
- six fault experiments preserve named safe states;
- model v2's higher fixture accuracy cannot offset protected routing and evidence failures;
- a visible-case overfit scores 8/8 on development but only 2/8 on the holdout;
- candidate, forged, malformed, stale, incomplete, and flaky evidence does not become conformance; and
- `CONFORMANT` stops at `READY_FOR_INTEGRATION_REVIEW` with all delivery-authority flags false.

## Package map

| Path | Purpose |
|---|---|
| `requirements/` | AI-2605, five protected invariants, and owner-controlled verification obligations |
| `repositories/` | Executable service sources copied into isolated Git repositories at runtime |
| `contracts/` | Classification, review-state, and quality-report JSON Schemas |
| `datasets/` | Versioned development, pedagogically protected holdout, and adversarial fixtures |
| `quality_app/repository_harness.py` | Reproducible commits and imports from the exact committed files |
| `quality_app/behavior_harness.py` | Service, concurrency, property, metamorphic, and failure observations |
| `quality_app/evaluation_engine.py` | Accuracy, per-class precision/recall, confusion matrix, slices, and protected violations |
| `quality_app/mutation_runner.py` | Seven policy-selected behavior mutations |
| `quality_app/evidence_registry.py` | Exact-subject receipt construction and signing |
| `quality_app/control_plane.py` | Independent evidence validation and typed decisions |
| `quality_app/test_selector.py` | Risk-adaptive selection plus mandatory protected checks |
| `scenarios/` | Human-readable failure contracts |
| `conformance-suite.json` | Fifteen golden scenarios |
| `evaluation-cases.json` | Forty-two labelled positive and adversarial decisions |
| `openspec/changes/AI-2605/` | Proposal, design, executable requirements, and tasks |
| `workshop/` | Staff-level strategy exercise and reference |
| `testing_quality.ipynb` | Guided notebook using the same tested implementation |

## Run

From the repository root:

```bash
python3 curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/lab.py
python3 -m unittest tests.test_course_27 -v
```

The default uses the Python standard library, SQLite, and installed Git. The lab emits a compact JSON summary with the exact revisions, explicit metric denominators, quality decision, and limitations.

Optional pytest/Hypothesis expansion:

```bash
python3 -m pip install -r curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/optional-tools.txt
python3 -m pytest curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/tests -q
```

## Golden decisions

| Population | Expected outcome |
|---|---|
| Clean exact-revision portfolio | `CONFORMANT` |
| Ambiguity, tenant, state-authority, concurrency, approval, or provenance defect | `BLOCKED` |
| Unsupported citation or protected model slice regression | `BLOCKED` |
| Candidate weakens oracle or deletes mandatory test | `INSUFFICIENT_EVIDENCE` |
| Unknown dependency impact | `INSUFFICIENT_EVIDENCE` |
| Commit changes after execution | `STALE_EVIDENCE` |
| Mixed results for a protected test | `REVIEW_REQUIRED` |

See [the full fifteen-scenario registry](conformance-suite.json) and [forty-two-case evaluation](evaluation-cases.json).

## Experiments

1. Change `requires_review` so high confidence overrides ambiguity; observe the example, property, metamorphic, mutation, and protected-slice failures.
2. Remove the tenant comparison from `can_read`; verify the cross-tenant negative test blocks.
3. Remove the SQLite primary-key semantics; run two identical requests and inspect durable effect count.
4. Change an approval after it is signed; verify proposal-digest binding rejects it.
5. Delete a negative case from the evidence payload; verify missing coverage is not a pass.
6. Re-sign evidence for old commits after changing one service; verify the subject mismatch is stale.
7. Compare v1, v2, and overfit outputs; explain why overall accuracy and development performance are insufficient.
8. Add easy mutants; verify they do not change the seven-item governed denominator.

## Staff workshop

Northstar's proposed classifier improves aggregate fixture accuracy but increases high-confidence ambiguity-routing and evidence-support violations, while a coding agent deletes one failing acceptance case. Complete the [starter strategy](workshop/starter/quality-strategy.json). Cover the requirement matrix, oracle ownership, adaptive selection, AI slices, mutations, provenance, CI decision, remediation, and what remains unproven. Compare with the [reference](workshop/reference/quality-strategy.json).

## Evidence limitations

The repository can inspect every checked-in “protected” case, so this is a pedagogical separation rather than a secrecy control. The 15/15 and 42/42 results describe fixed fixtures. SQLite behavior does not prove another database's isolation semantics. HMAC training keys do not provide production workload identity. No result establishes production model quality, defect absence, legal compliance, operability, or release authorization.

## Production upgrades

Use isolated trusted workers, verified source provenance, workload identity, managed signatures, immutable evidence storage, access-controlled datasets, audited label changes, actual database and queue integrations, resource budgets, trusted time, quarantine ownership/expiry, data lifecycle controls, artifact attestations, and Course 28 runtime telemetry. Course 24 remains the independent release authority.
