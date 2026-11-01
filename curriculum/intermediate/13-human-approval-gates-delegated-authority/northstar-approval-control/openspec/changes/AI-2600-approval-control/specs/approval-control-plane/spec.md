# Approval control-plane delta

## ADDED Requirements

### Requirement: exact-subject authorization

The control plane SHALL bind every approval receipt to the digest of the action, resource, environment, artifact, specification, policy revision, risk tier, and incident context.

#### Scenario: artifact changes after approval

- **WHEN** an executor presents a subject whose artifact differs from the stored request
- **THEN** execution SHALL return `APPROVAL_SUBJECT_MISMATCH` and SHALL NOT register an operation

### Requirement: trusted current authority

The control plane SHALL authenticate the approver, resolve direct or delegated authority from protected state, and revalidate that authority at execution. Caller-supplied role labels SHALL NOT establish authority.

#### Scenario: parent grant is revoked

- **WHEN** a delegated receipt exists and its parent authority is revoked before execution
- **THEN** execution SHALL return `DELEGATED_AUTHORITY_REVOKED`

### Requirement: separation of duties

The requester and implementation author SHALL NOT approve their own protected request. Consequential production deployment SHALL require distinct principals for release and AI-governance roles.

### Requirement: atomic single-use consumption

Receipt validation, conditional consumption, and operation registration SHALL occur in one transaction.

#### Scenario: two workers race

- **WHEN** two workers concurrently execute one approved request
- **THEN** exactly one SHALL register an operation and the other SHALL receive `APPROVAL_ALREADY_CONSUMED`

### Requirement: bounded emergency containment

Emergency authorization SHALL require an active qualifying incident, affected resource, permitted containment action, dedicated policy revision, scoped responder authority, expiry, and audit evidence. It SHALL NOT imply general deployment authority.

### Requirement: reconstructable audit

The service SHALL record request, approval, denial, revocation, delegation, execution, and reason-code events in an ordered integrity-verifiable chain.
