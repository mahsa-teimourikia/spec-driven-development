# Northstar quality-control lab

This lab turns Course 27's evidence model into a credential-free executable control plane.

## What it proves

- a candidate test report is diagnostic, not independent attestation;
- signed evidence must match the exact implementation and specification subject;
- every risk-selected test kind must trace to a registered requirement;
- unregistered or candidate-controlled oracles cannot satisfy obligations;
- the policy owns the critical mutation and failure-experiment populations;
- surviving critical mutants and unsafe failure behavior block;
- missing, stale, forged, or wrong-subject evidence is insufficient;
- flaky tests require review and do not count as passing evidence; and
- a quality report never authorizes release.

## Package map

| Path | Purpose |
|---|---|
| `quality-policy.json` | Active requirements, required test kinds, mutation set, failure population, and trust anchors |
| `quality_app/models.py` | Typed subject, finding, and report contracts |
| `quality_app/control_plane.py` | Independent evidence validation and decision logic |
| `quality_app/simulation.py` | Twelve golden scenarios and twenty-four labelled evaluations |
| `contracts/quality-report.schema.json` | Machine-readable report shape |
| `conformance-suite.json` | Golden scenario registry |
| `evaluation-cases.json` | Explicit evaluation population |
| `openspec/` | Proposal, design, executable requirements, and tasks |
| `traceability.json` | Requirement-to-code-and-test map |
| `workshop/` | Staff quality-strategy exercise |
| `testing_quality.ipynb` | Guided notebook using the same tested implementation |

## Run

From the repository root:

```bash
python3 curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control/lab.py
python3 -m unittest tests.test_course_27 -v
```

The lab emits JSON so CI, the notebook, and learners inspect the same contract.

## Scenario decisions

| Scenario | Expected |
|---|---|
| Complete independent portfolio | `QUALITY_EVIDENCE_ACCEPTED` |
| Candidate-only evidence | `INSUFFICIENT_EVIDENCE` |
| Forged evidence | `INSUFFICIENT_EVIDENCE` |
| Wrong subject | `INSUFFICIENT_EVIDENCE` |
| Stale suite | `INSUFFICIENT_EVIDENCE` |
| Failed independent test | `BLOCKED` |
| Missing negative evidence | `INSUFFICIENT_EVIDENCE` |
| Surviving critical mutant | `BLOCKED` |
| Flaky required test | `REVIEW_REQUIRED` |
| Unsafe failure experiment | `BLOCKED` |
| Missing failure experiment | `INSUFFICIENT_EVIDENCE` |
| Unknown requirement reference | `BLOCKED` |

## Failure experiments

Try one change at a time:

1. alter the subject implementation digest without re-signing;
2. replace the evidence producer with `candidate-agent`;
3. remove the negative authorization case;
4. mark `REMOVE_AUTHORIZATION` as `SURVIVED`;
5. report both PASS and FAIL for the same case;
6. remove `STALE_APPROVAL` from fault experiments; and
7. add easy unregistered mutants and observe that the denominator remains four.

The tests name each invariant and provide the repair path.

## Staff workshop

Northstar proposes automatic persistence after a high-confidence classification. Complete the [starter strategy](workshop/starter/quality-strategy.json). Your design must cover requirement risk, independent oracles, negative/boundary evidence, critical mutations, failure experiments, flake policy, exact evidence binding, and the release boundary. Compare with the [reference strategy](workshop/reference/quality-strategy.json).

## Evidence limitations

The reported 100% values describe only the fixed labelled fixture populations. They do not establish production defect-detection accuracy, model quality, legal compliance, or release authorization.

## Production upgrades

Replace training HMAC keys with protected workload identity and managed verification. Run isolated harness workers against immutable artifacts. Protect test and policy catalogs. Govern test data and evaluation populations. Add trusted time, revocation, retention, replay protection, cost budgets, flake ownership, artifact provenance, and integration with Course 24 release governance and Course 28 observability.

