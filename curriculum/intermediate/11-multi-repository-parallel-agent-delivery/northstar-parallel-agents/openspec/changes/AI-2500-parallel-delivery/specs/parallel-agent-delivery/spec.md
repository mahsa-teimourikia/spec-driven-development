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
