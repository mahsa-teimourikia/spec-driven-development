# Implementation plan — AI-2310

**Plan:** `PLAN-AI-2310@2-training`
**Specification:** `SPEC-AI-2310@3-training`
**Repository revision:** `repo-docs@a17-training`
**Architecture:** `ADR-058@3-training`

## Current truth

- The existing OCR pipeline extracts PDFs.
- `DocumentType` already exists.
- `SubmissionService` owns authoritative requirement state.
- The document agent has no authoritative mutation tool.

## Proposed change

1. Extend the document model with a non-authoritative classification proposal.
2. Reuse existing OCR output.
3. Add a classifier adapter and deterministic supported-type validation.
4. Preserve `UNSUPPORTED` and `AMBIGUOUS` outcomes.
5. Integrate proposals with the existing review workflow through a versioned contract.
6. Produce provenance-bearing evidence through independent CI and evaluation.

## Requirement disposition

- `REQ-DOC-001`: implement through T001 and T002.
- `REQ-DOC-002`: implement through T002 and T003.
- `REQ-DOC-003`: implement through T003 and T004.
- `REQ-DOC-004`: implement through T001, T002, and T005.
- `SEC-DOC-001`: implement through T003 and T005.
- `PERF-DOC-001`: preserve external target reference; verify through T005.

## Architecture impact

No approved architecture change. A cross-repository review contract is proposed as `CONTRACT-DOC-REVIEW@1-training`; any change to extraction, authorization, or submission mutation requires a separate ADR or protected-decision change request.

## Release boundary

Spec Kit artifacts may propose and organize implementation. They do not approve policy exceptions, architecture changes, execution permissions, merge, release, or automatic satisfaction.
