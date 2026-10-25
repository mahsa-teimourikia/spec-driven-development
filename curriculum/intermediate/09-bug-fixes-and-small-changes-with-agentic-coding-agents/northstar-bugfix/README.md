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

The reference state is `READY_FOR_INTEGRATION_REVIEW`. It does not authorize merge or deployment. The evidence producer is a deterministic teaching stand-in for trusted CI; production implementations need isolated execution, signed provenance, retained artifacts, repository-derived diffs, and platform-specific path hardening.
