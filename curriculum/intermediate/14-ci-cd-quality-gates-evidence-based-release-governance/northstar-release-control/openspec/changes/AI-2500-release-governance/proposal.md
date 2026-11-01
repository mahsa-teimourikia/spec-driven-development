# AI-2500 — Trusted release governance

## Problem

Green pull-request checks do not prove that the tested artifact and effective AI configuration are the ones deployed to production.

## Proposed change

Introduce a trusted release-control boundary that authenticates build and evidence producers, binds evidence and approvals to the full release manifest, promotes immutable artifact identity, verifies runtime protected invariants, reconciles unknown deployment outcomes, and governs recovery.

## Non-authorities

This proposal does not approve thresholds, certify a builder, grant deployment authority, or authorize a production release. Those decisions remain with named owners and protected systems.
