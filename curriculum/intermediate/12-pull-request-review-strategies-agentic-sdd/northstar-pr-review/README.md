# Northstar AI-2500 PR review control-plane lab

This credential-free fixture turns Course 22 into an executable review system. It creates real temporary Git repositories, derives exact commits and changed paths, resolves protected review obligations, validates revision-bound approvals and evidence, tests a real combined-branch conflict, and stops at merge-review eligibility.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/12-pull-request-review-strategies-agentic-sdd/northstar-pr-review/lab.py
python3 -m unittest tests.test_course_22 -v
```

The JSON report exposes the exact subject, decision, findings, metric populations, strategy inputs, and non-authorities.

## Learner path

1. Read the [Course 22 chapter](../README.md).
2. Execute [`lab.py`](lab.py) and inspect the exact Git SHAs.
3. Work through [`pr_review_strategies.ipynb`](pr_review_strategies.ipynb).
4. Read the approved [requirements](specifications/approved-requirements.json), [acceptance contract](specifications/acceptance-contract.json), and [shared contract](contracts/classification-v2.schema.json).
5. Compare the [mega](strategies/mega-pr.json), [staged](strategies/staged-prs.json), and [parallel](strategies/parallel-prs.json) inputs.
6. Resolve the six `TODO:` decisions in the [starter package](workshop/starter/review-package.json).
7. Compare your decisions with the [reference package](reference/review-package.json).

## Trusted boundary

```text
agent / contributor
  proposes code, tests, descriptions, evidence references
                  │
                  ▼
trusted application
  resolves Git state, ownership, identity, approvals,
  evidence subjects, merge groups, and terminal decision
```

Contributor metadata remains untrusted. The engine ignores scenario `expected_finding` labels during execution.

## Package map

| Path | Purpose |
| --- | --- |
| `review_app/git_harness.py` | Creates real Git subjects and executes a combined-branch merge |
| `review_app/review_engine.py` | Enforces scope, ownership, freshness, evidence, and separation of duties |
| `review_app/simulation.py` | Builds scenarios and labelled evaluation populations |
| `specifications/` | Approved intent and protected acceptance oracle |
| `review-policy/` | Ownership, risk tiers, and protected decisions |
| `scenarios/` | Human-readable experiment intent; not evaluator truth |
| `openspec/` | Change proposal, delta specification, and completed tasks |
| `evidence/manifest.json` | Stored summary bound to deterministic fixture SHAs |
| `workshop/starter/` | Six learner decisions |
| `reference/` | Non-authoritative review handoff |

## Decision codes

The engine returns `ELIGIBLE_FOR_MERGE_REVIEW` only when all modeled obligations pass. Failures use stable finding codes such as `UNAUTHORIZED_SPEC_CHANGE`, `CONTRACT_APPROVAL_MISSING`, `STALE_REVIEW_APPROVAL`, `TEST_ORACLE_CHANGED`, `AWU_SCOPE_VIOLATION`, `EVIDENCE_SUBJECT_MISMATCH`, `REQUIRED_REVIEW_MISSING`, and `SELF_APPROVAL_DENIED`.

The Git merge experiment is reported separately as `merge_group_conflict` because its result comes from an actual combined merge attempt.

## Security notes

- The fixture has no network calls, secrets, tokens, or production repositories.
- Exact 40-character Git commits are derived by the trusted harness.
- The author cannot satisfy its own approval obligation.
- Evidence must come from an allowlisted producer and bind the exact subject.
- `ELIGIBLE_FOR_MERGE_REVIEW` grants no merge, deployment, or release authority.
- Production CI must isolate untrusted code and use least-privilege tokens and ephemeral runners.

## Limitations

Temporary Git repositories demonstrate revision and merge semantics, not hosted-platform configuration or durable storage. Synthetic reviewers and metrics do not measure human understanding or organizational performance. Production systems require authenticated identity, durable registries, trusted execution, revocation, audit, rulesets, and release controls.
