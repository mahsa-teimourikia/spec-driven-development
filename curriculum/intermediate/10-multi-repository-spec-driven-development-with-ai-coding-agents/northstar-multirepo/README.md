# Northstar AI-2500 multi-repository lab

This credential-free fixture turns Course 20 into an executable system. It creates five temporary Git repositories, commits their baseline and candidate states independently, runs local tests, derives actual diffs, computes a mixed-version compatibility matrix, executes 11 system scenarios, and evaluates a package bound to exact commits.

## Run

From the repository root:

```bash
python3 curriculum/intermediate/10-multi-repository-spec-driven-development-with-ai-coding-agents/northstar-multirepo/lab.py
python3 -m unittest tests/test_course_20.py -v
```

Expected reference outcome:

- course validation: `PASS`;
- candidate: `READY_FOR_INTEGRATION_REVIEW`;
- conformance: `16/16`;
- evaluation: `40/40`;
- integration scenarios: `11/11`;
- repository revisions: five full Git commit IDs; and
- merge/deployment authority: `false`.

## Artifact map

| Path | Purpose |
| --- | --- |
| `parent-change/` | canonical AI-2500 requirements, child specs, graph, and work units |
| `contracts/` | classification revisions 1 and 2 plus OpenAPI description |
| `repositories/` | five baseline/candidate repository templates with source and tests |
| `multirepo_app/git_harness.py` | real Git commits, local tests, compatibility, and trusted observations |
| `multirepo_app/control_plane.py` | parent/child, graph, scope, manifest, evidence, and authority gates |
| `integration/` | matrix and exact-revision manifest template |
| `openspec/changes/AI-2500/` | proposal, delta spec, and tasks |
| `candidate/` | unsafe local-CI-only comparison |
| `reference/` | bounded integration-review handoff |
| `workshop/starter/` | six learner decisions |
| `conformance-suite.json` | 16 named decisions |
| `evaluation-cases.json` | 40 labelled mutation decisions |
| `evidence/manifest.json` | reproducible evidence summary |

## Trust boundary

The candidate can propose repository content, child specs, dependencies, rollout, and evidence references. The trusted harness loads the parent and canonical contract independently, creates the Git repositories, runs their tests, derives commit IDs and diffs, computes compatibility, executes system scenarios, resolves evidence references, and decides readiness.

Repository-local CI is useful evidence for local properties. It never becomes proof of end-to-end behavior or release authority merely because all repositories are green.

## Fixture boundary

The repository templates and scenario populations are synthetic. Production adoption needs authenticated identities, signed provenance, isolated candidate execution, durable orchestration, real contract tooling, deployment controls, runtime telemetry, consumer inventory, and accountable approvals.
