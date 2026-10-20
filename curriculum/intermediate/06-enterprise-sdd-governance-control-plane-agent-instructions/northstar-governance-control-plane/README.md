# Northstar governance control-plane workshop

This workshop turns change `AI-2310` into a revision-bound dispatch decision for Codex-, Claude-, and Copilot-style coding agents. It is a deterministic, credential-free teaching model—not a production identity provider, policy distributor, or sandbox.

## What is here

| Artifact | Purpose |
| --- | --- |
| `policy/trusted-governance-plane.json` | protected policy, rule, identity, exception, grant, source-control, and compatibility facts |
| `reference/governance-package.json` | safe learner reference package |
| `reference/AGENTS.md`, `CLAUDE.md`, `.github/copilot-instructions.md` | generated target adapters |
| `reference/instruction-manifest.json` | compiler, context, compatibility, and output bindings |
| `candidate/` | deliberately unsafe package and authoritative changed-path observation |
| `policy/dispatch.rego` | illustrative fail-closed OPA decision policy |
| `conformance-suite.json` | 16 golden governance scenarios |
| `evaluation-cases.json` | 23 mutation families expanded into 92 labelled cases |
| `workshop/starter/` | three learner decisions |
| `lab.py` | deterministic compiler, validator, gates, handoff, and evaluation |
| `enterprise_governance_control_plane.ipynb` | guided experiments |

## Run the reference and failure injection

From the repository root:

```bash
python3 curriculum/intermediate/06-enterprise-sdd-governance-control-plane-agent-instructions/northstar-governance-control-plane/lab.py
```

Inspect the JSON report. Confirm that:

- the reference is only `ELIGIBLE_FOR_AGENT_DISPATCH`;
- all seven gates report explicitly;
- the unsafe candidate is blocked for multiple independent reasons;
- the applicable policy change pauses and requires revalidation;
- all 16 golden scenarios and 92 labelled mutations pass; and
- the Course 15 handoff is eligible for delivery review, not merge or deployment.

## Learner task

Open `workshop/starter/governance-package.json` and replace exactly three `TODO` values:

1. the trusted base revision;
2. the governing human-review obligation; and
3. the generated adapter-manifest digest.

Derive each value from an authoritative artifact. Do not copy the candidate’s claim, create an exception, or edit generated adapters. Compare with `reference/governance-package.json`, then explain which system owns each value.

## Experiments

1. Delete a trusted subject fact and observe `APPLICABILITY_UNKNOWN`.
2. Weaken a project semantic while keeping its JSON valid and observe `NORMATIVE_AUTHORITY_CONFLICT`.
3. Edit generated adapter text and recompute only its digest; regeneration still exposes the mismatch.
4. Change the authenticated principal to a role name and observe identity failure.
5. Add an authoritative changed path outside the grant and observe scope failure.
6. Request an external-network capability absent from the grant and observe dispatch authorization failure.
7. Give the child `src/**`, a traversal path, or a capability its parent lacks and observe delegation failure.
8. Add a second project requirement that hides a conflicting semantic in a last-write-wins map; the relationship-preserving validator still reports both the internal and enterprise conflict.
9. Withdraw a governing policy or change only its protected decisions and observe lifecycle or revalidation routing.
10. Remove trusted evidence for an exception condition and observe fail-closed exception validation.

## Limits

The model uses static JSON fixtures, SHA-256 digests, simplified predicates, a restricted exact-file/subtree path grammar, and an in-process decision function. Its path containment validates declared scope but does not enforce filesystem access. It does not implement signatures, secure time, revocation propagation, real workload attestation, hardened policy distribution, concurrent authorization consumption, or an actual filesystem/network sandbox. The Rego file demonstrates a decision boundary only; a trusted enforcement point must consume the decision.

Return to the [Course 16 chapter](../README.md).
