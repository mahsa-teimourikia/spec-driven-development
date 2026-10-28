# Broker document review delta

## ADDED Requirements

### Requirement: classification proposals preserve provenance

The system SHALL bind every proposal to document evidence and model identity.

#### Scenario: missing evidence

- **WHEN** a classification proposal has no authorized evidence reference
- **THEN** Review Service rejects the proposal before creating review work

### Requirement: ambiguous classifications require review

The system SHALL route ambiguity to an authorized human reviewer and SHALL NOT let the AI service satisfy an underwriting requirement.

#### Scenario: review service unavailable

- **WHEN** the review dependency is unavailable
- **THEN** the proposal remains non-authoritative and no underwriting transition occurs
