# GENERATED EFFECTIVE CONTEXT — DO NOT EDIT

Generated for `AI-2048` from stable requirement IDs, revisions, the project
manifest, `ARCH-031`, and resolver `0.5.0-training`.

## Governing requirements

- `AI-030@ai030v3-training`: human review is required before consequential use;
  Review Service v2 is the project binding. The agent has no authority to remove
  review, may propose the review mechanism, and may decide local implementation
  structure inside the approved design.
- `UW-041@uw041v21-training`: an authorized underwriter must approve renewal
  recommendations affecting premium or coverage.
- `AI-007@ai007v4-training`: production inference uses the enterprise AI
  gateway, subject only to the selected `EXC-014` compatibility-proxy scope and
  conditions through 2026-12-31.
- `AI-041@ai041v22-training`: evaluation evidence is required.
- `SEC-100@sec100v51-training`: customer-facing authentication uses an approved
  identity provider.

## Execution and enforcement

- Writable: `src/renewal/**`, `tests/renewal/**`, `evals/renewal/**`,
  `specs/renewal/**`.
- Protected: `auth/**`, `infrastructure/**`, and enterprise policy.
- Stop on conflict, uncertain applicability, authorization changes, requested
  weakening, or a required exception.
- Guidance in `AGENTS.md` is not enforcement. CI checks, runtime review/identity
  gates, network egress, and evidence records provide independent controls.

## Authorized exception

- `EXC-014` permits `legacy_enterprise_gateway_proxy` only for
  `REQ-REN-001`. Egress remains restricted to the AI Platform-managed proxy,
  audit events must be preserved, and migration must complete before expiry.
- The coding agent may implement within this bounded context. It may not edit,
  renew, widen, or approve the exception.

Source locators and owners are structurally complete fictional training data;
they are not authenticated authority or release approval.
