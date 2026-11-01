# Northstar trusted AI release-control lab

This credential-free fixture implements Course 24 as an executable delivery trust chain. It derives source identity from a clean Git commit, packages an executable local artifact, runs functional/security/AI evaluations against those exact bytes, authenticates teaching provenance and evidence, applies risk-adaptive approval, revalidates trust at deployment, performs an observable transition, resolves signed runtime observations, reconciles unknown outcomes, and verifies authorized recovery from protected state.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/14-ci-cd-quality-gates-evidence-based-release-governance/northstar-release-control/lab.py
python3 -m unittest tests.test_course_24 -v
```

The report must show:

- `ELIGIBLE_FOR_ACCOUNTABLE_REVIEW` as the course-level decision;
- 12/12 golden scenarios;
- 12/12 adversarial evaluations;
- the exact built and deployed digest;
- operation states `AUTHORIZED → DISPATCHED → VERIFYING → ACTIVE`;
- manual review preserved; and
- explicit non-authorities.

## Learner path

1. Read the [Course 24 chapter](../README.md).
2. Run `lab.py` and inspect the JSON evidence.
3. Execute [release_governance.ipynb](release_governance.ipynb) from this directory.
4. Review `release_app/` and the focused tests.
5. Mutate one dependency in a release manifest and predict the invalidated evidence.
6. Complete [workshop/starter/release-design.json](workshop/starter/release-design.json).

## Trust boundaries

The coding agent may propose source, configuration, or evidence candidates. The trusted application authenticates producers, resolves stored evidence, applies policy, rechecks current authority, consumes approvals, mutates environment state, verifies effects from protected observation registries, and records terminal state.

The local HMAC fixture demonstrates signature-verification flow only. Trust policy contains key IDs; public deterministic keys are injected from `trusted-harness/` and never passed to the packaged candidate. They are not protected production trust roots. The fixture is intentionally not labelled as a Sigstore integration or SLSA certification. Production requires workload identity, isolated secret management, rotation, revocation, externally verified attestations, durable delivery, idempotency, bounded retries, and authenticated target-state observation.
