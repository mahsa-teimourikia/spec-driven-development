# Parallel agent delivery delta specification

## ADDED requirements

### Requirement: Dependency-aware dispatch

The trusted scheduler SHALL dispatch a work unit only after every declared prerequisite has trusted `VERIFIED` or `INTEGRATED` state.

#### Scenario: Independent parallel wave

- **GIVEN** the canonical contract work unit is verified
- **WHEN** the scheduler evaluates Document, AI, and Review work
- **THEN** those work units may be ready concurrently
- **AND** API and UI work remain blocked until their dependencies verify

### Requirement: Fenced ownership

The protected submission service SHALL accept a consequential write only from the authenticated holder of the current unexpired lease generation.

#### Scenario: Stale worker returns

- **GIVEN** generation 41 expired and generation 42 was issued
- **WHEN** generation 41 submits a candidate
- **THEN** the service rejects it with `STALE_FENCING_TOKEN`

### Requirement: Exact-revision integration

The integration barrier SHALL bind the approved contract digest, exact component commits, trusted evidence receipts, and passing system scenarios.

#### Scenario: Tested revision differs from proposed revision

- **GIVEN** evidence covers `(A, B)`
- **WHEN** the manifest proposes `(A, C)`
- **THEN** integration is blocked pending fresh evidence

### Requirement: Trusted submission facts

The submission boundary SHALL accept only a candidate commit and SHALL use a trusted Git service to prove repository identity, commit existence, approved-base ancestry, and the actual changed paths.

#### Scenario: Worker understates its diff

- **GIVEN** a candidate commit changes an unauthorized infrastructure path
- **WHEN** the worker submits only the candidate commit
- **THEN** the trusted Git-derived diff exposes the unauthorized path
- **AND** submission is blocked

### Requirement: Lease-bound idempotent effects

The effect boundary SHALL bind every logical operation to the current authenticated lease subject, repository, work unit, generation, request digest, and allowlisted capability.

#### Scenario: Unknown remote outcome

- **GIVEN** the remote effect may have occurred before acknowledgement
- **WHEN** the coordinator restarts and receives a retry
- **THEN** the operation remains `UNKNOWN_OUTCOME`
- **AND** the adapter reconciles the stable remote identity before any retry

### Requirement: Executed evidence

The integration verifier SHALL generate receipts from independently observed repository tests and executable cross-service scenarios rather than accept receipt metadata from a worker.

#### Scenario: Documentation claims a protected behavior

- **GIVEN** the behavioral contract says ambiguous proposals require review
- **WHEN** the exact revision set is evaluated
- **THEN** the harness executes a high-confidence ambiguous proposal through Review Service
- **AND** integration fails if runtime behavior bypasses review

### Requirement: Revocation on replan

Contract invalidation and retry SHALL revoke the current lease and effect grants, advance the fencing generation, invalidate resumable checkpoints and stale evidence, and only then return work to planning or the ready queue.
