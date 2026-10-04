# Northstar Spec Kit enterprise adapter lab

This credential-free lab turns a Spec Kit-shaped feature package into a governed enterprise review package. It does not invoke a hosted model or require GitHub credentials.

## Artifact map

```text
source/                     revision-bound intent and constraints
spec-kit-snapshot/          dated official CLI observation and template digests
reference/.specify/         typed constitution
reference/specs/            Spec Kit-shaped spec, plan, and tasks
reference/control-package.json
candidate/control-package.json
conformance-suite.json      eight golden workflow scenarios
evaluation-cases.json       36 control mutations
lab.py                      deterministic adapter and validators
workshop/starter/           learner workspace
```

## Run

From the repository root:

```bash
python3 curriculum/intermediate/03-github-spec-kit-enterprise-sdd/northstar-spec-kit-adapter/lab.py
python3 -m unittest tests.test_course_13 -v
```

The reference package should be `READY_FOR_OWNER_REVIEW`; this is deliberately not `APPROVED` or `PRODUCTION_READY`. The unsafe candidate should be blocked. All eight golden scenarios and 36 mutations should pass.

## Workshop path

1. Read every file in `source/` and identify source, revision, authority, and scope.
2. Compare the reference constitution, spec, plan, and tasks with the unsafe candidate.
3. Copy the starter JSON files into a scratch location.
4. Correct source binding and authority classification.
5. Preserve the unresolved confidence decision.
6. add full requirement dispositions and remove orphan work.
7. Add AWU boundaries and independent evidence.
8. Run the validators and explain every remaining finding.

## Important boundaries

- Generated output is a proposal, not approval.
- A project constitution does not supersede enterprise policy.
- A task is not an autonomous execution boundary until it is enriched.
- A completion report is not independent conformance evidence.
- Convergence may add repair work; it may not rewrite intent to fit code.
- Synthetic evidence proves no production claim.
