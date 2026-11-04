# Northstar AI governance control-plane lab

This package turns the Course 25 concepts into a credential-free, executable governance boundary for `AI-UC-2500`.

## What is authoritative in the fixture

- `registry/` supplies canonical use-case, model, agent, tool, deployment, principal, session, and signed assessment-approval relationships.
- `assessments/` supplies the illustrative impact assessment whose owner, methodology, revision, tier, and validity must be independently verified.
- `policies/` selects risk tiers, evidence obligations, reassessment triggers, producers, and key IDs.
- `trusted-harness/` injects deterministic verification keys outside the candidate records.
- `governance_app/` resolves current state, persists versioned evidence and lifecycle transitions, verifies authority, and atomically consumes approval.

The scenario files and learner workshop are documentation and inputs for exploration. The evaluator does not trust their expected labels to make governance decisions.

## Run

From the repository root:

```bash
python3 curriculum/advanced/01-enterprise-ai-governance-agentic-software-development/northstar-ai-governance/lab.py
python3 -m unittest tests.test_course_25 -v
```

Expected summary:

- 13 of 13 executed golden scenarios pass;
- 15 of 15 independently executed adversarial decisions pass;
- the reference subject becomes eligible for accountable approval;
- a governance authority issues an exact-subject receipt;
- a protected executor atomically consumes it for one bounded operation;
- a model revision produces targeted `REASSESSMENT_REQUIRED` obligations;
- a deployment-bound protected-invariant violation durably suspends the capability across restart;
- accountable reinstatement stops at reassessment rather than silently restoring approval; and
- the overall report stops at `ELIGIBLE_FOR_ACCOUNTABLE_REVIEW`.

## Trust boundaries

```text
candidate artifacts                       trusted governance boundary
-------------------                       ---------------------------
registration proposal   ────────────────▶ canonical registry resolution
risk-tier claim         ────────────────▶ independent risk derivation
result JSON             ────────────────▶ producer and signature verification
claim support           ────────────────▶ append-only evidence history + current evidence-set digest
approval request        ────────────────▶ authenticated scoped authority + evidence-set binding
operation request       ────────────────▶ durable-state recheck + atomic consume
runtime observation     ────────────────▶ invariant/deployment/window/count validation
```

The repository-visible HMAC keys teach authenticity mechanics. They are not secrets, production identities, or formal assurance. The caller-supplied timestamps make the fixture deterministic; production enforcement must obtain time from a trusted control-plane clock.

## Durable suspension and evidence semantics

SQLite is the authoritative teaching store for lifecycle, append-only evidence records, approval receipts, operations, and audit events. Every authorization reads that store. Evidence records use stable IDs and explicit claim IDs, preserve history instead of overwriting a kind, and can be revoked without deletion. Approval binds both the resolved subject digest and the exact evidence-set digest.

Runtime suspension accepts only an authenticated observation for a policy-registered invariant and active deployment. Its window must be ordered and current, counts must be coherent, and event IDs must support the violation count. Reinstatement requires an authenticated governance principal and signed remediation evidence; it transitions to `REASSESSMENT_REQUIRED`, requiring fresh evidence and approval.

## Workshop

Complete the seven decisions in `workshop/starter/governance-design.json` for Northstar's proposed authority expansion. Compare your result with `reference/governance-design.json` only after defending:

1. change classification;
2. registry updates;
3. risk and policy floors;
4. human authority;
5. evidence obligations;
6. reassessment and activation; and
7. runtime containment.

## Evidence limitations

The deterministic fixtures prove implementation invariants for this teaching package. They do not measure a live model, establish legal classification, certify ISO/IEC 42001 conformity, demonstrate EU AI Act compliance, or authorize any external use case.
