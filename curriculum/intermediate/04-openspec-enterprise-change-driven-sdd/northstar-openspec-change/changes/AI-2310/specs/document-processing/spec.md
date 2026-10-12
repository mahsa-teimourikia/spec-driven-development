# Spec Delta

## MODIFIED Requirements

### Requirement: Manual classification

Supported broker documents MAY receive an AI-generated classification proposal before underwriting processing. Ambiguous or unsupported results SHALL remain available for manual classification. The authoritative classification SHALL require an authorized underwriter decision.

#### Scenario: Supported document proposal

- **WHEN** a supported broker document is extracted
- **THEN** the system may create a non-authoritative classification proposal

#### Scenario: Ambiguous proposal

- **WHEN** classification is ambiguous
- **THEN** the document remains available in the manual classification queue

#### Scenario: Authority retained

- **WHEN** a classification proposal exists
- **THEN** it does not become authoritative without an authorized underwriter decision

## ADDED Requirements

### Requirement: Classification proposal provenance

Every classification proposal SHALL retain source-document, supporting-evidence, model, and governing-context provenance.

#### Scenario: Proposal stored

- **WHEN** a classification proposal is stored
- **THEN** every provenance reference resolves to its exact source and revision

### Requirement: Untrusted document content

Document content SHALL be treated as untrusted domain data and SHALL NOT modify agent control instructions.

#### Scenario: Instruction-like document text

- **WHEN** document content contains instruction-like text
- **THEN** the text remains classification input and cannot alter policy, tools, identity, or permissions

