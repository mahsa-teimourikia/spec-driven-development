# Feature specification — AI-2310 Broker Document Classification

**Specification:** `SPEC-AI-2310@3-training`
**Source intent:** `TICKET-AI-2310@1-training`
**Effective context:** `CTX-AI-2310@2-training`
**Constitution:** `CONSTITUTION-DOCS@4-training`

## Supported population

English machine-readable PDFs for inspection reports, valuation reports, loss histories, and floor plans. Images, handwriting, French documents, and unrecognized document types follow the manual-review path until representative evidence supports a wider population.

## Requirements

### REQ-DOC-001 — Produce a classification proposal

WHEN a supported broker document is received for an active submission, THE SYSTEM SHALL produce a non-authoritative `DocumentClassification` proposal containing document identity, supported document type, an outstanding-requirement candidate, and supporting evidence.

Owner: Underwriting Operations · Source: `DOMAIN-DOC-11@2-training` · Revision: 1

### REQ-DOC-002 — Preserve unsupported documents

IF no supported document type can be established, THEN THE SYSTEM SHALL classify the document as `UNSUPPORTED`, retain it for manual triage, and SHALL NOT mutate authoritative underwriting state.

Owner: Underwriting Operations · Source: `DOMAIN-DOC-11@2-training` · Revision: 1

### REQ-DOC-003 — Preserve ambiguity

IF more than one materially plausible underwriting-requirement mapping exists, THEN THE SYSTEM SHALL classify the association as `AMBIGUOUS`, expose all plausible candidates, and SHALL NOT automatically satisfy an underwriting requirement.

Owner: Underwriting Risk · Source: `AI-030@7-training` and `DOMAIN-DOC-11@2-training` · Revision: 1

### REQ-DOC-004 — Retain provenance

Every classification proposal SHALL retain document identity, source evidence, classifier version, effective-context digest, and applicable requirement context.

Owner: Quality Engineering · Source: `PROJECT-QUALITY-004@2-training` · Revision: 1

### SEC-DOC-001 — Treat document content as untrusted data

Document content SHALL NOT modify agent instructions, authorization, tool permissions, workflow policy, or the set of allowed side effects.

Owner: Product Security · Source: `SEC-DOC-009@4-training` · Revision: 1

### PERF-DOC-001 — Preserve the approved performance target reference

The feature SHALL be evaluated against `PERF-TARGET-003`; generated plans and tasks SHALL NOT replace its target value.

Owner: Service Reliability · Source: `PERF-TARGET-003@1-training` · Revision: 1

## Open question

### Q-DOC-001 — Automatic satisfaction authority

Does an accepted classification proposal ever authorize automatic satisfaction of an underwriting requirement?

Status: `OPEN` · Owner: Underwriting Risk and AI Governance · Blocks: `automatic_requirement_satisfaction`

Classification, proposal generation, evaluation, and review integration may continue. Automatic satisfaction remains disabled.

## Acceptance criteria

- `AC-DOC-001` verifies `REQ-DOC-001` and `REQ-DOC-004`: a supported fixture produces a proposal with complete revision-bound provenance.
- `AC-DOC-002` verifies `REQ-DOC-002`: unsupported input is retained for manual triage without authoritative mutation.
- `AC-DOC-003` verifies `REQ-DOC-003`: ambiguous input exposes all plausible mappings and records zero automatic satisfactions.
- `AC-DOC-004` verifies `SEC-DOC-001`: an embedded instruction cannot change authority, tools, policy, or side effects.
- `AC-DOC-005` verifies `PERF-DOC-001`: the plan retains the target reference and routes any proposed change to its owner.

## Capability gates

- `classification_proposal`: READY
- `manual_review_routing`: READY
- `automatic_requirement_satisfaction`: BLOCKED by `Q-DOC-001`

This training specification is ready for bounded implementation review; it is not an authenticated business approval or production-release authorization.
