# Proposal — governed parallel delivery for AI-2500

## Why

Five repository contributions can shorten the critical path only after the shared contract is approved and independent work is isolated. Unbounded parallel agents create stale-context, duplicate-effect, authority, and late-integration risk.

## What changes

- Add application-owned work-unit state and dependency-aware dispatch.
- Bind authenticated workload identities to repository and path scope.
- Enforce time-bounded leases with monotonic fencing generations at submission.
- Reconcile retries through durable logical operation identities.
- Validate checkpoints before resume and invalidate affected work after contract change.
- Assemble exact-revision integration evidence without granting merge or deployment authority.

## Authority boundary

This proposal does not approve the contract, architecture, merge, deployment, activation, or contract retirement. Those decisions remain with authenticated accountable controls and owners.
