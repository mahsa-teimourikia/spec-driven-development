# Northstar SDD delivery-control workshop

This workshop turns `AI-2310` from a specification package into a governed enterprise delivery decision. It is deliberately credential-free and uses only the Python standard library.

## What is here

| Path | Purpose | Trust position |
| --- | --- | --- |
| `policy/trusted-control-plane.json` | Git diff, component/evidence registries, validator execution, producers/builders, runtime contract, receipts | trusted fixture |
| `reference/delivery-package.json` | finding-free proposal eligible for integration review | safe teaching reference |
| `candidate/delivery-package.json` | unsafe mutations layered on the reference | untrusted PR fixture |
| `workshop/starter/delivery-package.json` | three incomplete learner decisions | learner workspace |
| `conformance-suite.json` | eleven named golden failure scenarios | expected test oracle |
| `evaluation-cases.json` | 17 families × 4 labelled mutations | bounded robustness check |
| `lab.py` | deterministic gate and receipt engine | teaching implementation |
| `enterprise_pdlc_delivery.ipynb` | guided analysis | canonical notebook |

## Workflow

1. Read the parent [course chapter](../README.md).
2. Run `python3 lab.py` from this directory, or use the repository-root command below.
3. Inspect the unsafe candidate and explain why its technical-quality gate still passes.
4. Complete the three `TODO` decisions in `workshop/starter/delivery-package.json`.
5. Predict the gate results before running your package through `evaluate_delivery`.
6. Use the notebook to inspect evidence identity, merge composition, receipts, artifact identity, and runtime coverage.
7. Compare your package with the reference only after recording your reasoning.

From the repository root:

```bash
python3 curriculum/intermediate/05-enterprise-pdlc-ci-cd-integration/northstar-sdd-delivery/lab.py
python3 -m unittest tests.test_course_15 -v
```

## Workshop tasks

### Task 1 — Complete the gate contract

Replace the starter's three `TODO` values so that:

- the package identifies the current approved specification;
- the claim for `REQ-AI-2310-01` is covered by exact-subject evidence; and
- the requested transition stops at integration review rather than claiming merge authority.

### Task 2 — Explain the unsafe green PR

Create a table with one row per unsafe finding. Notice that the protected auth path exists only in `candidate/trusted-observations.json`; the package cannot hide the Git-provider observation by omitting that path. For each finding, name:

- the changed subject;
- the authoritative source used by the validator;
- the invalidated descendant evidence or decision; and
- the owner who must resolve it.

### Task 3 — Exercise authorization

Copy the reference in memory, set `integration.requested` to `true`, and use receipt `INT-AI2310-001`. Verify it, consume it once, then show that reuse fails. Do not change the on-disk trusted registry.

### Task 4 — Prevent artifact substitution

First consume the integration receipt so the training control plane records the exact integrated subject. Then request deployment with `DEP-AI2310-001` and change either the provenance subject or deployment artifact digest. Explain why source-level evidence remains true but no longer authorizes this deployment subject, and why deployment is blocked before integration completion is recorded. In production, that completion record must be durable and shared across workers.

### Task 5 — Interpret runtime evidence

Set `runtime.observed` to `true`. Compare:

- zero violations with healthy instrumentation and 500 applicable events;
- zero violations with an unhealthy instrument; and
- zero violations covering only `english_pdf` while `scanned_image` is in rollout scope; and
- one violation with healthy, complete instrumentation.

## Stop conditions

Stop and route a decision when you encounter an unknown risk profile, unresolved owner decision, policy/context revision drift, protected requirement change, semantic merge conflict, or receipt that is missing, expired, replayed, or bound to another subject.

## Evidence limitations

This fixture demonstrates decision structure, exact identity, invalidation, and fail-closed behavior. Its Git-provider observations, evidence registry, workload attestation, and component registry are deterministic trusted fixtures—not authenticated external services. Its `threading.Lock` protects only one Python process. It does not execute GitHub Actions, sign SLSA provenance, contact Jira, evaluate a real model, deploy software, or prove production suitability. Production requires authenticated providers, protected storage, isolation, transactional compare-and-swap receipt state shared across workers, durable replay records, and operational controls.
