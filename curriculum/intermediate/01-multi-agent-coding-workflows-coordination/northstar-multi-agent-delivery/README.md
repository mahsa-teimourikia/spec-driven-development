# Northstar multi-agent delivery workshop

This fictional workshop starts with Course 10's approved AI-2219 work-unit DAG and asks learners to design the execution control plane. It never launches agents or grants access.

## Scenario

Northstar wants extraction and validation to proceed concurrently after `ProposedUpdate@2` is verified. Conflict, review, and integration remain dependency ordered. The workflow must keep repository revisions, shared context, assignments, identities, leases, locks, permissions, evidence, review capacity, and recovery state coherent.

The unsafe candidate demonstrates “start six agents” coordination: one shared branch, dependency violations, overlapping writes, role labels as identity, permanent wildcard permissions, no leases or locks, context divergence, unbounded delegation, implementer-controlled verification, and an integration agent allowed to rewrite everything.

The reference demonstrates:

- five dependency-aware execution waves;
- one branch/worktree and assignment identity per work unit;
- minimal logical write locks with leases and recovery;
- shared-source pinning with work-unit-specific local context;
- artifact-based handoff and durable coordination events;
- independent-context verification;
- revision-bound integration evidence and routed failures;
- pull scheduling with typed reviewer capacity and WIP limits;
- bounded delegation, retry classification, and recovery inspection; and
- a review package derived from durable artifacts rather than agent persuasion.

## Run

```bash
python3 curriculum/intermediate/01-multi-agent-coding-workflows-coordination/lab.py
```

Expected reference result: `COORDINATION_READY`, no findings, five waves, extraction and validation in wave two, and 31/31 exact labelled evaluation cases. The unsafe candidate must remain blocked. These are transparent fixture checks, not estimates of general orchestrator correctness or productivity.

## Workshop sequence

1. Inspect `candidate/workflow.json` and identify where speed is confused with useful concurrency.
2. Complete the starter coordination plan, handoff, and recovery record.
3. Compare them with the reference only after defending identity, authority, state, and evidence boundaries.
4. Inject a shared-contract revision and calculate active work, completed work, and stale evidence.
5. Model a saturated security-review queue and explain why pull scheduling should wait.
6. Compare the single-agent, unsafe-parallel, and governed-multi-agent fixture observations without claiming a benchmark.

## Evidence boundary

Every identity, approval, digest, commit, time, and metric is synthetic. A production implementation still requires authenticated workload identity, durable transactional state, real repository integration, atomic lease/lock transitions, policy enforcement, secrets isolation, telemetry, representative evaluations, and accountable human decisions.
