# Document Processing Baseline

Revision: `document-processing@4-training`

This synthetic baseline represents approved current truth before either active change is integrated.

## Requirements

### REQ-DOC-010@2 — Approved extraction

PDF documents SHALL be extracted through the approved extraction service.

#### Scenario: Supported PDF

- **WHEN** a supported PDF enters document processing
- **THEN** the approved extraction service produces the extraction record

### REQ-DOC-014@3 — Manual classification

Broker documents SHALL be manually classified before underwriting processing.

#### Scenario: Classification required

- **WHEN** extraction completes for a broker document
- **THEN** the document enters the manual classification queue

#### Scenario: Authority retained

- **WHEN** a classification candidate exists
- **THEN** an authorized underwriter confirms the authoritative classification

### REQ-DOC-015@2 — Confirmed persistence

Classification SHALL be persisted only after authorized underwriter confirmation.

#### Scenario: Unconfirmed value

- **WHEN** a classification has not been confirmed
- **THEN** the authoritative classification remains unchanged

### REQ-DOC-016@1 — Manual fallback

Unsupported documents SHALL remain available for manual processing.

#### Scenario: Unsupported input

- **WHEN** automated processing does not support a document
- **THEN** the document remains available in the manual queue

## Invariants

- `INV-DOC-004`: no generated value becomes authoritative without an authorized review decision.
- `INV-DOC-007`: unsupported or ambiguous documents remain recoverable through manual processing.

