# Agent execution instructions

## Scope

- Work only in the comparison module and its tests.
- Treat `reference/spec.md` as approved feature intent for this exercise and preserve every stable requirement ID.
- Follow `reference/design.md` and `reference/ADR-007-comparison-caching.md`; do not add generated-response caching.

## Required checks

- Run acceptance, authorization, human-review, telemetry, load, and domain-evaluation checks from `reference/evidence-plan.md`.
- Report results against evidence and requirement IDs.

## Stop conditions

Stop and request the named owner when work would change authorization, data retention, human-review policy, SLO workload, or requirement meaning. These instructions do not authorize exceptions, product decisions, release approval, or deployment.
