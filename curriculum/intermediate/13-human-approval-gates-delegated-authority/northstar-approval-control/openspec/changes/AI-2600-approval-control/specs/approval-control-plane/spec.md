# Approval control-plane delta

## ADDED Requirements

### Requirement: exact-subject authorization

The control plane SHALL bind every approval receipt to the digest of the action, resource, environment, artifact, specification, policy revision, risk tier, and incident context.

#### Scenario: artifact changes after approval

- **WHEN** an executor presents a subject whose artifact differs from the stored request
- **THEN** execution SHALL return `APPROVAL_SUBJECT_MISMATCH` and SHALL NOT register an operation

### Requirement: trusted current authority

The control plane SHALL authenticate the approver, resolve direct or delegated authority from protected state, retain the issuance-time authority-registry revision and grant-chain snapshot, and revalidate current authority at execution. Delegated role SHALL equal parent role, and every use SHALL recheck child containment within the current parent. Caller-supplied role labels SHALL NOT establish authority.

#### Scenario: parent grant is revoked

- **WHEN** a delegated receipt exists and its parent authority is revoked before execution
- **THEN** execution SHALL return `DELEGATED_AUTHORITY_REVOKED`

### Requirement: separation of duties

The requester and implementation author SHALL NOT approve their own protected request. Consequential production deployment SHALL require distinct principals for release and AI-governance roles.

### Requirement: atomic single-use consumption

Receipt validation, conditional consumption, simulated protected-resource mutation, effect verification, operation success, and audit evidence SHALL occur in one transaction. Durable operation states SHALL distinguish `AUTHORIZED`, `DISPATCHED`, `SUCCEEDED`, `FAILED`, and `UNKNOWN_OUTCOME`; only a verified effect may reach `SUCCEEDED`.

#### Scenario: two workers race

- **WHEN** two workers concurrently execute one approved request
- **THEN** exactly one SHALL register an operation and the other SHALL receive `APPROVAL_ALREADY_CONSUMED`

### Requirement: bounded emergency containment

Emergency authorization SHALL require an active qualifying incident, affected resource, permitted containment action, dedicated policy revision, scoped responder authority, expiry, and audit evidence. It SHALL NOT imply general deployment authority.

### Requirement: reconstructable audit

The service SHALL record request, approval, denial, revocation, delegation, operation transition, effect, and reason-code events in an ordered integrity-verifiable chain. Verification SHALL compare the local chain with a separately retained latest-sequence checkpoint so modification and tail truncation are detectable.

### Requirement: lifecycle and lifetime consistency

A rejected request SHALL atomically revoke outstanding approval receipts. Receipt expiry SHALL be later than issuance and no later than either the policy maximum or the underlying direct/delegated authority expiry.
