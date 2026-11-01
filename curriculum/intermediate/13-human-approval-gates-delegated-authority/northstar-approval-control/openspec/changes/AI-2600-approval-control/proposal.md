# Proposal: trusted human approval control for AI-2600

## Why

Northstar currently records review comments but cannot prove that current, scoped authorities approved the exact deployment artifact. Reusable and unbound approvals create replay, drift, and self-approval risk.

## What changes

- Model normal and emergency decisions as versioned policy.
- Resolve identity, grants, delegation, resources, and incidents from protected state.
- Issue exact-subject, expiring, revocable, single-use receipts.
- Enforce separation of duties and dual control.
- Consume approval and register an operation atomically.
- Record hash-linked audit evidence and test negative and concurrent paths.

## Impact

This repository change creates a local teaching fixture only. It uses synthetic identities, performs no production deployment, and grants no release authority.
