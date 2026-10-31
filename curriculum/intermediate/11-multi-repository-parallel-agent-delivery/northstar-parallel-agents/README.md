# Northstar AI-2500 parallel-agent delivery lab

This credential-free fixture turns Course 21 into an executable distributed-delivery model. It creates five real temporary Git repositories, derives immutable commits and rename-aware diffs, executes cross-service behaviors, then drives work through a trusted state machine with authenticated worker scope, leases, fencing, recoverable idempotency, checkpoints, selective invalidation, generated evidence, and an exact-revision integration barrier.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/11-multi-repository-parallel-agent-delivery/northstar-parallel-agents/lab.py
python3 -m unittest tests/test_course_21.py -v
```

Expected reference outcome:

- course validation: `PASS`;
- candidate: `READY_FOR_INTEGRATION_REVIEW`;
- repositories: five exact baseline/candidate Git revision pairs;
- conformance: `12/12`;
- evaluation: `30/30`;
- system scenarios: `6/6`; and
- merge, deployment, and release authority: `false`.

## Guided path

1. Read the [Course 21 chapter](../README.md).
2. Execute the [notebook](parallel_agent_delivery.ipynb).
3. Inspect the canonical [parent change](parent-change/AI-2500.json), [dependency graph](parent-change/dependency-graph.json), and [work units](parent-change/work-units.json).
4. Compare contract [revision 2](contracts/classification-v2.schema.json) and proposed [revision 3](contracts/classification-v3.schema.json).
5. Trace the trusted controls in [`control_plane.py`](parallel_app/control_plane.py).
6. Complete the six decisions in the [starter package](workshop/starter/integration-package.json).
7. Compare your result with the [reference integration package](reference/integration-package.json).

## Artifact map

| Path | Purpose |
| --- | --- |
| `parallel_app/control_plane.py` | state, identity, leases, fencing, scope, evidence, invalidation, and barrier |
| `parallel_app/git_harness.py` | real temporary repositories, commits, diffs, and local tests |
| `parallel_app/evidence_service.py` | receipts generated from observed Git and executed test results |
| `parallel_app/system_harness.py` | executable classifier, review, tenant, approval, replay, and authority scenarios |
| `parallel_app/simulation.py` | reference delivery, failure injection, scheduling comparison, and evaluation |
| `repositories/` | maintained baseline/candidate inputs for five repository subjects |
| `parent-change/` | requirements, graph, work units, and integration policy |
| `contracts/` | structural revisions and behavioral obligations |
| `scenarios/` | human-readable scenario intent; executable outcomes come from state transitions |
| `conformance-suite.json` | twelve named invariants |
| `evaluation-cases.json` | thirty labelled decisions and declared population |
| `openspec/` | change proposal, delta requirements, and implementation tasks |
| `evidence/manifest.json` | reproducible summary bound to exact commits |
| `workshop/starter/` | six learner decisions |

## Trust boundary

The worker proposes code, checkpoints, or a contract change. The trusted control plane authenticates identity, evaluates dependency readiness, issues a bounded lease, enforces the current generation and effect capability, asks trusted Git to derive the real diff, generates evidence from executed checks, revokes stale authority, and decides integration-review eligibility. No model response, role name, branch, worker-supplied path list, receipt-shaped object, checkpoint, or green local suite can approve its own authority.

## Scenario descriptors are not proof

Files under `scenarios/` document the intended failure injection. The lab does not read an `expected` flag and return it. Tests invoke real methods, perform Git operations, compare generations and digests, and assert observed decisions.

## Fixture boundary

The lock and snapshot are deterministic in-process teaching mechanisms. The snapshot preserves `PENDING`, `COMPLETED`, and `UNKNOWN_OUTCOME` operation state and demonstrates reconciliation, not distributed exactly-once execution. Production adoption needs transactional storage, an outbox or provider reconciliation, authenticated workload identity, protected repository mutation endpoints, signed evidence, isolated execution, queue-redelivery handling, clock and failover testing, real CI integrations, and accountable release controls.
