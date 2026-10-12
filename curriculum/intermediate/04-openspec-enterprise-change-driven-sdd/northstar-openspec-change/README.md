# Northstar OpenSpec enterprise-change workshop

This credential-free workshop compares a governed reference portfolio with an intentionally unsafe candidate. It uses OpenSpec-compatible concepts while keeping enterprise controls external and explicit.

## What you will inspect

```text
baseline/
  approved current document-processing truth

changes/
  AI-2310 governed classification proposal
  AI-2331 conflicting automated-triage proposal

enterprise/
  revision-bound effective context and authority map

reference/
  conflict-aware portfolio, AWUs, evidence, and integration state

candidate/
  labelled unsafe mutations

openspec-snapshot/
  pinned v1.14.1 semantics and official-source digests
```

## Run the lab

From the repository root:

```bash
python3 curriculum/intermediate/04-openspec-enterprise-change-driven-sdd/northstar-openspec-change/lab.py
```

Expected summary:

```text
reference: READY_FOR_OWNER_REVIEW
unsafe candidate: BLOCKED
golden scenarios: 10/10
control mutations: 53/53
```

`READY_FOR_OWNER_REVIEW` is deliberately weaker than approved, integrated, archived, or released.

## Exercise sequence

1. Read `baseline/document-processing.md` and locate `REQ-DOC-014@3`.
2. Compare the complete `MODIFIED` blocks in `AI-2310` and `AI-2331`.
3. Inspect the two recorded conflicts in `reference/change-portfolio.json`.
4. Run `apply_change` and confirm it produces a candidate target without mutating the baseline.
5. Remove the conflict records and observe `CONCURRENT_CHANGE_CONFLICT_UNRECORDED`.
6. Remove `manual_fallback_regression` and observe that delta success is insufficient.
7. Request archive without authorization and confirm the baseline remains unchanged.
8. Complete the three TODOs in `workshop/starter/change-portfolio.json`.

## Safety boundary

The fixture contains only synthetic identities, approvals, evidence, and revisions. It performs no network calls, invokes no model, writes no production state, and issues no approval or release receipt.

The implementation boundary is:

```text
agent → proposes and implements
trusted application → validates, authorizes, integrates, archives, and releases
```

## Interpreting the scores

The 10/10 and 53/53 results measure exact outcomes on labelled training cases. They do not establish general semantic-conflict recall, production reliability, security certification, or OpenSpec vendor conformance.

## Optional real OpenSpec comparison

If you separately install the pinned CLI, compare the training artifacts with the official workflow:

```text
openspec list --specs
openspec show document-processing --type spec
openspec validate AI-2310 --strict
openspec status --change AI-2310
```

Do not run archive against a real repository merely for the exercise. Archive mutates current specs and change history.

