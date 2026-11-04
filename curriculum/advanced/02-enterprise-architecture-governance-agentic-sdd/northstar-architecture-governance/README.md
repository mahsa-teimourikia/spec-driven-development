# Northstar architecture governance lab

This credential-free package turns Course 26 into an executable architecture control plane over temporary, real Git repositories.

## Run

From the repository root:

```bash
python3 curriculum/advanced/02-enterprise-architecture-governance-agentic-sdd/northstar-architecture-governance/lab.py
python3 -m unittest tests.test_course_26 -v
```

Expected results:

- 13 of 13 golden scenarios produce their exact decision;
- 16 of 16 adversarial cases pass;
- valid exact-scope exceptions work while expired, revoked, wrong-environment, wrong-subject, forged, and under-evidenced records fail closed;
- a report becomes stale when Git `HEAD` advances; and
- the retrieval-platform ADR produces targeted repository, contract, evaluation, and control impact.

## Artifact map

| Path | Role |
|---|---|
| `architecture/` | Principles, technology standards, reference architecture, dependency rules |
| `adrs/` | Accepted and superseded decisions with preserved history |
| `registry/` | Active authority, ADR lifecycle, and cross-system impact graph |
| `policies/` | Rego illustration of decision logic |
| `repositories/ai-service/` | Clean source fixture copied into temporary Git repositories |
| `governance_app/` | Fact extraction, fitness functions, exceptions, ADR checks, impact, and control plane |
| `scenarios/` | Human-readable golden expectations, never trusted as evaluation input |
| `trusted-harness/` | Training trust-boundary explanation and public key metadata |
| `workshop/` | Staff design starter and reference response |
| `openspec/` | Proposal, design, SHALL requirements, scenarios, and completed task trace |
| `contracts/` | Report JSON Schema and governed data-boundary OpenAPI excerpt |
| `traceability.json` | Requirement-to-control-and-test mapping |

## Trust boundary

```text
candidate-controlled                         trusted control plane
--------------------                         ---------------------
source and dependency files ───────────────▶ Git and AST fact extraction
ADR proposal                ───────────────▶ authority and conflict resolution
exception request           ───────────────▶ signature, scope, digest, time, controls
expected scenario label     ──────X          executed mutation determines result
policy copy                 ──────X          external active policy registry
```

The candidate cannot choose the base/head range, policy revision, scanner identity, exception authority, or decision. The report remains evidence only; no code path in this package deploys software.

## Guided investigation

1. Run the clean scenario and locate the derived imports, dependency edges, and changed files.
2. Compare direct provider import, provider endpoint, and ambiguous generic HTTP behavior.
3. Inspect why an unapproved technology routes to review instead of immediate prohibition.
4. Compare a valid exception with wrong-environment and expired variants.
5. Follow `ADR-027` to `ADR-028` and inspect targeted change impact.
6. Advance the repository after a report and confirm stale evidence is rejected.

## Evidence limitations

The fixture demonstrates control semantics with Python source, declared service edges, local Git, and deterministic teaching keys. It does not observe a live network, prove every dynamically loaded dependency, secure a production key, certify an architecture, authorize a release, or establish legal compliance.

## Workshop

Complete `workshop/starter/architecture-review.json` for the Claims Assistant. Defend which choices are governed centrally, which remain local, how every important fact is derived, how uncertainty is represented, and who owns each exception. Compare with the reference only after presenting failure experiments.
