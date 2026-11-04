# Change proposal: executable architecture governance

## Problem

Northstar architecture intent is split across standards, diagrams, ADRs, and review knowledge. Coding agents can unintentionally bypass the AI gateway, access private data stores, reverse layer dependencies, introduce unsupported technology, or rely on obsolete decisions.

## Outcome

Introduce a teaching control plane that independently derives architecture facts from an exact Git revision, evaluates current enterprise policy and ADR state, validates exact-scope exceptions, and emits typed revision-bound evidence for a protected release workflow.

## Authority boundary

This change does not grant policy authorship, architecture approval, exception approval, release authorization, deployment authority, or a compliance claim to the coding agent or local lab.

## Affected capabilities

- architecture fact extraction;
- dependency and layer fitness functions;
- ADR lifecycle and conflict evaluation;
- exception verification;
- conformance reporting; and
- targeted architecture-change impact.
