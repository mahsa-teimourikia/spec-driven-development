# Design — AI-2310

## Context

The approved extraction and review services already exist. The change adds a classification adapter and deterministic validation between them.

## Goals

- reuse existing extraction and review contracts;
- keep generated classifications non-authoritative;
- isolate untrusted document content; and
- produce revision-bound evidence.

## Non-goals

- new messaging infrastructure;
- new authorization semantics;
- extraction replacement; and
- automatic persistence.

## Decisions

1. Extend the document-processing domain model rather than add a parallel classification service.
2. Place deterministic validation after model inference and before proposal persistence.
3. Reuse `CONTRACT-DOC-REVIEW@2-training` for authoritative review.

## Risks and mitigations

- Incorrect proposals → keep proposals non-authoritative and evaluate supported slices.
- Instruction-like content → isolate content as data and run injection-resistance tests.
- Contract drift → bind integration evidence to the contract revision.

## Migration plan

Deploy proposal generation disabled, verify shadow evidence, then enable only supported document classes after an external release decision. Manual processing remains the rollback path.

## Open questions

Automatic persistence is deliberately excluded and remains blocked by `Q-AI2310-004`.

