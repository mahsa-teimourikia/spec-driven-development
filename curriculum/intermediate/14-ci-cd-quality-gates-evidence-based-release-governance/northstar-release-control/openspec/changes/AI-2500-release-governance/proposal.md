# AI-2500 — Trusted release governance

## Problem

Green pull-request checks do not prove that the tested artifact and effective AI configuration are the ones deployed to production.

## Proposed change

Introduce a trusted release-control boundary that derives source identity from Git, executes the exact packaged artifact, authenticates build and evidence producers, revalidates immutable artifact and evidence state at deployment, rechecks scoped authority, resolves protected runtime observations, reconciles unknown deployment outcomes, and requires authorized, independently observed recovery.

## Non-authorities

This proposal does not approve thresholds, certify a builder, grant deployment authority, or authorize a production release. Those decisions remain with named owners and protected systems.
