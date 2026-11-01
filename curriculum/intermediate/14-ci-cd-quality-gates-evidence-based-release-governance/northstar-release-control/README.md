# Northstar trusted AI release-control lab

This credential-free fixture implements Course 24 as an executable delivery trust chain. It builds real local artifact bytes, authenticates a teaching provenance statement, parses a lockfile into an SBOM, executes functional/security/AI evaluation checks, binds evidence to the full effective release manifest, issues dual manifest-bound approvals, performs an observable deployment transition, verifies runtime invariants, reconciles unknown outcomes, and evaluates complete recovery.

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

The coding agent may propose source, configuration, or evidence candidates. The trusted application authenticates producers, resolves stored evidence, applies policy, consumes approvals, mutates environment state, verifies effects, and records terminal state.

The local HMAC fixture demonstrates authenticated provenance flow only. Its synthetic keys and external configuration identifiers are repository fixtures, not protected production trust roots or authenticated model/retrieval registries. It is intentionally not labelled as a Sigstore integration or SLSA certification. Remote deployment needs durable delivery, idempotency, retries, and target-state reconciliation beyond this local transaction. Recovery targets must be verified in the lab, but production recovery still requires applicable emergency or release authorization.
