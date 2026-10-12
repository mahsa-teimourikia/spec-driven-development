# Spec Delta

## MODIFIED Requirements

### Requirement: Manual classification

Supported broker documents SHALL be automatically triaged to a downstream queue using a classification result.

#### Scenario: Supported document triage

- **WHEN** a supported broker document is extracted
- **THEN** an automated classification result selects its downstream queue

> Training note: this delta is individually based on `REQ-DOC-014@3` but conflicts with `AI-2310` and the review authority preserved by the applicable context. It is not ready to apply.

