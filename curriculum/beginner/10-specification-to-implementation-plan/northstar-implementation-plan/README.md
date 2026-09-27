# Northstar implementation-planning scenario

This fictional, offline scenario asks you to turn approved specification `AI-2219` into a reviewable plan and bounded agent work units. Northstar Underwriter must extract proposed broker-response updates while preserving source provenance, verified values, human review, and the model-facing mutation boundary.

The scenario deliberately separates five things that teams often collapse:

1. the approved specification says **what must remain true**;
2. repository discovery says **what exists at one revision**;
3. the plan says **how the change could be delivered**;
4. a work unit says **what one agent may change and when it must stop**;
5. completion and verification evidence say **what actually happened**.

None of these artifacts grants production access, approves an architecture change, or proves release readiness.

## Artifact map

| Path | Purpose |
|---|---|
| `approved-specification.json` | Approved requirements, invariants, acceptance references, and capability gates |
| `repository-snapshot.json` | Fictional repository evidence bound to `repo-abc123` |
| `architecture-context.json` | Approved and proposal-only architecture decisions |
| `candidate/plan.json` | Unsafe ticket-to-agent plan used for diagnosis |
| `reference/discovery.json` | Requirement-guided discovery with explicit confidence |
| `reference/plan.json` | Reviewable plan, dispositions, tasks, provenance, and evidence links |
| `reference/work-units.json` | Dependency graph, path authority, readiness evidence, and stop conditions |
| `reference/contract-change-request.json` | Mid-flight proposal with transitive downstream impact |
| `reference/completion-report.json` | Executor report that remains distinct from independent verification |
| `reference/rollout-boundary.json` | Separate shadow/release/enablement boundary; no activation authorization |
| `reference/escalation-artifacts.json` | Clarification, architecture, and dependency examples that remain unapproved proposals |
| `workshop/starter/` | Editable learner artifacts with `TODO` prompts |
| `evaluation-cases.json` | Transparent labelled cases for deterministic rule evaluation |

## Recommended path

1. Read the ticket and approved specification.
2. Compare the unsafe candidate with repository and architecture evidence.
3. Complete the starter discovery before creating tasks.
4. Give every in-scope requirement an explicit disposition.
5. Decompose cohesive work units around stable contracts and exclusive write ownership.
6. Add task justification, evidence outputs, decision authority, typed stop routing, and temporary permission requests.
7. Compare explicit edges with the contract registry; schedule waves and identify the critical path.
8. Test a mid-flight contract change and keep implementation, merge, rollout, and enablement readiness separate.
9. Compare your package with the reference only after recording your own decisions.

The reference is one defensible answer for this fixture, not a universal repository design.
