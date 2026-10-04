# Clarifications — AI-2310

**Context:** `CTX-AI-2310@2-training`
**Specification:** `SPEC-AI-2310@3-training`

| ID | Question | Status | Owner | Effect |
|---|---|---|---|---|
| Q-DOC-001 | What calibrated, population-bound rule may satisfy a document requirement without human review? | OPEN | Underwriting Risk | `automatic_requirement_satisfaction` remains `BLOCKED` |

The workflow may implement classification proposals, deterministic supported-type validation, ambiguity states, and human-review routing while this question remains open. It may not infer a threshold, reuse another product's threshold, or redefine “ambiguous” as a raw model score.

## Recorded non-decisions

- No model provider has been selected.
- No vector database or cache has been approved.
- No authorization or submission-mutation boundary has changed.
- No exception to `AI-030@7-training` has been requested.
