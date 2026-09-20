# Design — Policy document Q&A

## Governing constraints

The design inherits the approved gateway, Canadian residency, Bedrock Knowledge Bases retrieval, corporate SSO, versioned prompts, stable response contract, evaluation evidence, and Tier 3 human-oversight controls. `CONFLICT-001` rejects direct provider access.

## Request flow

```text
authenticated underwriter
        ↓
existing authorization boundary
        ↓
authorized policy retrieval
        ↓
relevance check ── no support ──> insufficient_evidence
        ↓ sufficient support
approved AI gateway (Canadian route, versioned prompt)
        ↓
answer + selected supporting passage identifiers
        ↓
structured redacted telemetry
        ↓
human review before consequential use
```

The trusted application selects the route, region, prompt version, and response schema. Retrieved text and model output remain untrusted data; neither can change policy, identity, or permissions.

## Alternatives

- Direct public API: rejected because it conflicts with PRIV-003, AI-004, and ADR-013.
- New local vector database: rejected because it duplicates the approved retrieval platform and creates new residency/operations obligations.
- Retrieval-only response: safe baseline, but it does not satisfy the requested synthesized answer. It remains the fallback when generation evidence is insufficient.

## Evidence and limitations

Independent unit tests and labelled deterministic evaluations cover the local contract. Pre-production integration must still establish tenant isolation, real gateway routing, deployed residency, telemetry delivery, and representative domain answer quality. Therefore the local merge gate can pass while production release remains blocked.
