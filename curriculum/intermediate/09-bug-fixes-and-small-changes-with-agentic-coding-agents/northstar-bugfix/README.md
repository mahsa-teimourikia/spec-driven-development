# Northstar Mutual BUG-2415 lab

This lab turns Course 19 into a runnable structured bug-fix package. It demonstrates why a one-character production patch still needs a protected requirement, confirmed cause, bounded write set, actual-diff validation, and revision-bound red-green evidence.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/09-bug-fixes-and-small-changes-with-agentic-coding-agents/northstar-bugfix/lab.py
python3 -m unittest tests/test_course_19.py
```

The runner prints JSON and makes no network calls.

## Learning path

1. Read `specs/BUG-2415/bug-contract.json` and the protected acceptance contract.
2. Compare the four causal hypotheses.
3. Inspect the writable paths, protected paths, allowed purposes, and stop conditions.
4. Run the lab and examine all ten experiments.
5. Compare `candidate/direct-agent-fix.json` with `reference/bugfix-package.json`.
6. Complete the five decisions in `workshop/starter/bugfix-package.json`.
7. Use the notebook to mutate the oracle, scope, cause, requirement revision, and evidence binding.

## Package map

| Path | Purpose |
| --- | --- |
| `bugfix_app/risk_engine.py` | Reproducible boundary defect and minimal correction |
| `bugfix_app/api.py` | Production path and alternative upstream fault |
| `bugfix_app/workflow.py` | Trusted triage, scope, oracle, evidence, and decision checks |
| `bugfix_app/trusted_harness.py` | Protected contract/work-unit loading, real Git observation, independent execution, and evidence registry |
| `specs/BUG-2415/` | Bug, acceptance, hypothesis, work-unit, and evidence contracts |
| `fixtures/change-requests.json` | Proportional workflow-selection examples |
| `conformance-suite.json` | Twelve stable decisions |
| `evaluation-cases.json` | Thirty single and combined mutations |
| `evidence/manifest.json` | Reproducible artifact digests and explicit authority boundary |
| `candidate/` | Unsafe self-reported baseline |
| `reference/` | Governed integration-review handoff |
| `workshop/starter/` | Five learner decisions |
| `assets/` | Validated diagram specification and deterministic renderer |

## Expected boundary

The teaching suite reports `course_validation.status = PASS`. Separately, the exact reference candidate—identified by baseline commit, candidate commit, specification revision, and oracle digest—reports `candidate_assessment.status = READY_FOR_INTEGRATION_REVIEW`. Neither result authorizes merge or deployment.

The harness loads the approved oracle and work unit outside the candidate, creates real Git commits, derives the actual diff, executes the regression and boundary population itself, and resolves evidence through a trusted registry. It remains a deterministic teaching stand-in for CI; production implementations need isolated execution, authenticated workload identity, signed provenance, retained artifacts, protected registries, and platform-specific path hardening.
