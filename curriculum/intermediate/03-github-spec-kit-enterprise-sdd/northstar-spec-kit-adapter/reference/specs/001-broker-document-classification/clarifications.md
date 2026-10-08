# Clarifications — AI-2310

**Context:** `CTX-AI-2310@3-training`
**Specification:** `SPEC-AI-2310@3-training`

| ID | Question | Status | Owner | Effect |
|---|---|---|---|---|
| Q-DOC-001 | What calibrated, population-bound rule may satisfy a document requirement without human review? | OPEN | Underwriting Risk | `automatic_requirement_satisfaction` remains `BLOCKED` |

The workflow may implement classification proposals, deterministic supported-type validation, ambiguity states, and human-review routing while this question remains open. It may not infer a threshold, reuse another product's threshold, or redefine “ambiguous” as a raw model score.

## Clarification state transitions

- An answer from the authenticated accountable owner is written back into `spec.md` with its decision provenance, and the affected capability is revalidated.
- If no authorized answer exists, the question remains `OPEN` and only the affected capability stays blocked.

`/speckit.clarify` can encode answered clarifications into the specification. The enterprise layer determines whether the respondent has authority to supply the answer; the command does not create that authority.

## Recorded non-decisions

- No model provider has been selected.
- No vector database or cache has been approved.
- No authorization or submission-mutation boundary has changed.
- No exception to `AI-030@7-training` has been requested.
