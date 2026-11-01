# Proposal: trusted human approval control for AI-2600

## Why

Northstar currently records review comments but cannot prove that current, scoped authorities approved the exact deployment artifact. Reusable and unbound approvals create replay, drift, and self-approval risk.

## What changes

- Model normal and emergency decisions as versioned policy.
- Resolve identity, issuance-time authority provenance, current grants, durable delegation, resources, and incidents from protected state.
- Issue exact-subject, expiring, revocable, single-use receipts.
- Enforce separation of duties and dual control.
- Consume approval, mutate the simulated protected resource, verify the effect, and register a successful operation atomically.
- Record checkpointed hash-linked audit evidence and test negative, restart, truncation, and concurrent paths.

## Impact

This repository change creates a local teaching fixture only. It uses synthetic identities, performs no production deployment, and grants no release authority.
