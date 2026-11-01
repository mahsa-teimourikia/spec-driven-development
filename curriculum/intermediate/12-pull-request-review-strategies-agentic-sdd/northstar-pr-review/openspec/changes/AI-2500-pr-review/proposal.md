# Proposal: governed PR review for AI-2500

## Why

Agent-generated changes can align code, tests, and prose while silently changing unauthorized intent. Northstar needs exact-revision review evidence and explicit decision ownership.

## What changes

- Derive review subjects and changed paths from trusted Git state.
- Resolve required review scopes from protected paths.
- Bind approvals and CI evidence to the exact head, specification, and contract.
- Test merge-group compatibility independently of local PR checks.
- Preserve merge, deployment, and release as separate authorities.

## Impact

This teaching change creates no production deployment and uses no GitHub credentials.
