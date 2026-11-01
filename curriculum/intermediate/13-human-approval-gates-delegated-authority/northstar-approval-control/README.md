# Northstar human approval control-plane lab

This credential-free fixture implements Course 23 as a trusted application boundary. It authenticates synthetic sessions, resolves resource-scoped authority from protected registries, issues revision-bound approval receipts, durably persists attenuated delegation and grant changes, atomically consumes single-use receipts, performs and verifies simulated protected-resource transitions, constrains emergency actions to active incidents, and verifies hash-linked audit records against a separately retained checkpoint.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/13-human-approval-gates-delegated-authority/northstar-approval-control/lab.py
python3 -m unittest tests.test_course_23 -v
```

The lab is deterministic, makes no network calls, needs no credentials, and creates temporary SQLite databases for scenarios.

## Learner path

1. Read the [Course 23 chapter](../README.md).
2. Execute [`lab.py`](lab.py) and inspect the reason codes.
3. Work through [`human_approval_gates.ipynb`](human_approval_gates.ipynb).
4. Review the normal and emergency policies in [`policies/`](policies/).
5. Inspect the synthetic authority and incident facts in [`registry/`](registry/).
6. Complete the six `TODO` decisions in [`workshop/starter/approval-design.json`](workshop/starter/approval-design.json).
7. Compare your design with [`reference/approval-design.json`](reference/approval-design.json).

## Trust boundary

```text
caller or coding agent
  supplies request details and opaque receipt references
                  │
                  ▼
trusted approval application
  resolves identity, policy, grants, delegation, incident, receipt state
                  │
                  ▼
protected executor
  validates exact subject + current authority
  atomically consumes receipts + records one operation
```

The evaluator never reads scenario `expected` fields. They document intent for learners; actual decisions are derived from protected state.

## Decision codes

Positive execution returns `SUCCEEDED` only after the simulator verifies the protected-resource effect. Durable operation events record `AUTHORIZED`, `DISPATCHED`, and `SUCCEEDED`; the model also reserves `FAILED` and `UNKNOWN_OUTCOME` for external adapters. Fail-closed codes include `UNAUTHENTICATED_PRINCIPAL`, `POLICY_REVISION_MISMATCH`, `APPROVAL_POLICY_UNRESOLVED`, `AUTHORITY_SCOPE_DENIED`, `SEPARATION_OF_DUTIES_VIOLATION`, `DELEGATION_SCOPE_EXPANSION`, `DELEGATED_AUTHORITY_REVOKED`, `RECEIPT_LIFETIME_EXCEEDED`, `REQUEST_NOT_AUTHORIZED`, `APPROVAL_SUBJECT_MISMATCH`, `APPROVAL_EXPIRED`, `APPROVAL_REVOKED`, `APPROVAL_ALREADY_CONSUMED`, `UNTRUSTED_RECEIPT`, `REQUIRED_APPROVAL_MISSING`, `EMERGENCY_AUTHORIZATION_DENIED`, and `EMERGENCY_SCOPE_VIOLATION`.

## Conformance populations

- 12 golden scenarios cover the required normal, negative, delegation, concurrency, and emergency paths.
- 12 separately labelled adversarial evaluations cover identity, policy, incident, role, authority, dual-control, and forgery failures.
- One audit mutation demonstrates detection before and after tampering.

## Security properties

- The caller cannot assert identity or authority through request JSON.
- A receipt is stored state referenced by ID, not a caller-minted bearer object.
- Production deployment requires two roles exercised by distinct principals.
- Requesters and implementation authors cannot approve their own protected request.
- Delegation cannot exceed the parent action, resource, environment, risk, or time scope.
- The delegated role must equal the parent role, and current containment is rechecked after parent narrowing.
- Delegations and grant revocations survive service restart; parent revocation invalidates delegated authority at execution.
- Receipt lifetime cannot exceed its policy maximum or underlying direct/delegated authority.
- Each receipt retains the authority-registry revision and an immutable issuance-time authority snapshot.
- Emergency action requires an active affected incident and a dedicated policy revision.
- Receipt consumption, simulated resource mutation, effect verification, operation success, and audit evidence share one transaction.

## Limitations

Synthetic sessions do not implement workforce identity. The separately retained checkpoint demonstrates tail-truncation detection but is only a local sidecar, not independently administered immutable storage. SQLite demonstrates transactional semantics and a local resource simulator; deployment at scale may require a network database and carefully chosen isolation. A local transaction cannot atomically commit an external side effect, so production needs idempotency, durable workflow state, explicit `UNKNOWN_OUTCOME` reconciliation, and protected checkpoint storage. The lab report grants no production authority.
