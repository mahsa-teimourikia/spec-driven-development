# ADR-007 — Defer generated comparison caching

**Status:** Accepted for first release
**Owner:** Underwriter Assistant architecture owner

## Context

Repeated comparisons may increase model cost and latency. Generated responses also depend on policy versions, retrieval state, prompt/model route, caller authorization, tenant, and review status. A response cache therefore creates freshness, invalidation, privacy, retention, and authorization obligations not resolved by AI-1842.

## Options considered

1. Do not cache generated responses.
2. Cache complete generated responses in Redis.
3. Cache only authorized retrieval results after a separate data-lifecycle design.

## Decision

Do not cache generated comparison responses in the first release. Instrument repeated comparison patterns and cost. Reconsider response or retrieval caching only with approved tenant-safe keying, retention, invalidation, encryption, freshness, and authorization-recheck rules.

## Consequences

- First-release model cost can be higher.
- The release avoids inventing an unapproved generated-content store.
- Redis is neither selected nor prohibited; any later cache technology must follow the approved cache boundary.
- The decision is revisited with measured repetition, latency, and cost evidence.
