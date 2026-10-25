# Northstar AI-2410 — end-to-end Agentic PDLC lab

This credential-free workshop turns approved business intent into a verified, non-authoritative underwriting risk-summary proposal. It is a real bounded feature slice: typed application contracts, authorization rechecked at validation, structured exact-claim support, controlled abstention, registry-backed human review, durable replay demonstration, reproducible evidence, and failure injection.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/07-idea-discovery-spec-design-implementation/northstar-risk-summary/lab.py
python3 -m unittest tests.test_course_17 -v
```

Expected summary:

- reference state: `READY_FOR_INTEGRATION_REVIEW`;
- required experiments: 7/7;
- golden scenarios: 12/12;
- labelled mutations: 39/39;
- semantic traceability mutations: 4/4;
- three real dependency-ordered commits and durable restart replay: passed; and
- merge, deployment, and business-outcome claims: false.

## Artifact map

| Path | Purpose |
| --- | --- |
| `specs/AI-2410/discovery.md` | outcome, current-system facts, scope, unknowns, and blockers |
| `specs/AI-2410/requirements.yaml` | revisioned normative behavior |
| `specs/AI-2410/acceptance.yaml` | independently owned evidence design |
| `specs/AI-2410/design.md` | bounded architecture and rejected alternatives |
| `specs/AI-2410/work-units.yaml` | dependency graph and agent decision rights |
| `specs/AI-2410/pr-sequence.yaml` | three reviewable PRs, exercised as real local commits |
| `specs/AI-2410/traceability.json` | semantically checked requirements → acceptance → design → AWUs → code → tests → evidence |
| `specs/AI-2410/execution-context.json` | pinned revisions and permission boundary |
| `app/` | reusable vertical-slice implementation |
| `fixtures/submissions.json` | authorized, cross-submission, restricted, and injection-shaped documents |
| `evidence/manifest.json` | reproducible run, implementation, dataset, criterion, and result digests with explicit limitations |
| `candidate/direct-coding-output.json` | deliberately unsafe direct-coding comparison |
| `reference/lifecycle-package.json` | complete training handoff |
| `workshop/starter/` | four learner-owned decisions |
| `conformance-suite.json` | twelve end-to-end cases |
| `evaluation-cases.json` | thirty-nine labelled control mutations |
| `assets/` | validated diagram specification, renderer, and SVG |
| `.github/workflows/validation.yml` | illustrative independent PR check; root CI is authoritative |

## Required experiments

1. **Valid summary:** confirm a current, supported citation reaches integration review.
2. **Missing source:** observe `CITATION_NOT_FOUND`.
3. **Unsupported claim:** prove topic relevance is not exact claim support; observe `EVIDENCE_INSUFFICIENT_FOR_CLAIM`.
4. **Prompt injection:** let instruction-shaped evidence induce an attempted broker action, reject it, and confirm zero effect invocations.
5. **Stale context:** observe `STALE_CONTEXT`.
6. **Unauthorized mutation:** observe `UNAUTHORIZED_SIDE_EFFECT` without modifying underwriting state.
7. **Specification change:** confirm the old proposal requires revalidation and cannot rewrite the specification.

The lab also exercises evidence authorization after context construction, wrong-submission access, outside-context evidence, empty evidence, missing risk facts, evidence-revision drift, forged or expired receipt handles, process restart, and replay.

## Workshop task

Open `workshop/starter/lifecycle-package.json` and resolve exactly four `TODO` values from authoritative artifacts. Do not infer them from the candidate output. Do not mark merge or release as authorized.

Then answer:

- Which readiness state does each value support?
- Which owner can change it?
- What invalidates it?
- Which downstream evidence can survive a revision?

Compare with `reference/lifecycle-package.json` only after recording your reasoning.

## Working PR sequence

Use `specs/AI-2410/pr-sequence.yaml` as the delivery exercise:

1. establish approved behavior, design, contracts, and the work graph;
2. rebase on the merged contract PR and implement the bounded proposal path; and
3. rebase again, add exact-subject review and independent evidence, and stop at integration review.

Each PR has a narrow review purpose, dependency, exclusion set, required checks, and merge condition. `app/pr_exercise.py` creates three actual commits in an isolated temporary Git repository, verifies the parent chain, then changes the prerequisite revision and observes `STALE_CONTRACT_REVISION`. A later PR cannot use its own green status to erase an unmet predecessor or authorize production release.

## Evidence and traceability

`lab.build_evidence_manifest()` executes the named scenarios and emits the exact manifest stored in `evidence/manifest.json`. Every record carries a run ID, implementation digest, dataset identity and digest, criterion IDs, result payload, and result-artifact digest. This makes the local result reproducible, not authenticated; production needs signed attestations and an immutable evidence registry.

`lab.run_traceability_evaluation()` checks relationship meaning, not only field presence. Its clean reference and four mutations cover an unknown test, unrelated acceptance criterion, stale requirement revision, and evidence bound to another requirement.

The caller supplies only an opaque approval receipt ID. `TrustedReceiptRegistry` supplies authenticated approval facts; caller-authored booleans cannot create authority. The default in-memory store demonstrates the limitation, while `SqliteReceiptStore` uses an atomic uniqueness constraint and proves replay remains blocked after the store object restarts. Production still requires a managed durable service, revocation, secure time, and authenticated identity.

## Framework comparison

Represent the same change once as a Spec Kit-style spec/plan/tasks flow and once as an OpenSpec-style proposal/delta/design/tasks flow. Keep the application contracts, evidence checks, and authority boundaries unchanged. The exercise demonstrates that framework artifacts are adapters around the enterprise operating model, not replacements for it.

## Limits

This lab uses static structured facts, SHA-256 digests, deterministic outputs, an in-process trusted registry, and local SQLite for a narrow restart exercise. Exact structured matching establishes only fixture claim support; it is not general semantic entailment. The lab does not implement tenant infrastructure, cryptographic signatures, secure time, real workload identity, model evaluation, concurrent workflow recovery, or production deployment. Passing the fixture supports a teaching claim only.

Return to the [Course 17 chapter](../README.md).
