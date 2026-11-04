# ADR-025: Route model access through the enterprise AI gateway

- Status: Accepted
- Scope: Enterprise
- Owners: Architecture Board and AI Platform
- Decision date: 2026-06-12

## Context

Northstar needs consistent model allowlists, residency routing, audit correlation, quota enforcement, and emergency revocation across agentic services.

## Decision

Applications SHALL call the enterprise AI gateway rather than provider SDKs or provider endpoints directly. The rule is enforced by static dependency checks and trusted runtime egress evidence.

## Consequences

Teams retain freedom inside their domain boundary but accept gateway availability and contract constraints. A time-bounded, exact-subject exception requires compensating network and review controls.
