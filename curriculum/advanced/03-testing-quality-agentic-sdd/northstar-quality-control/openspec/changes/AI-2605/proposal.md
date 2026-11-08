# Proposal: independent quality engineering for AI-2605

## Problem

AI-2605 changes classification and review routing across three repositories. Repository-local tests can all pass while the integrated system bypasses human review, leaks tenant data, duplicates a consequential effect, accepts stale approval, drops provenance, or improves average model accuracy while regressing a protected slice.

## Change

Add owner-controlled verification obligations, real Git-backed service revisions, transactional concurrency tests, property and metamorphic populations, requirement-weighted mutations, failure experiments, protected evaluation data, authenticated evidence, and a risk-adaptive quality gate.

## Non-goals

- certify defect-free or production-ready software;
- let a coding agent change protected oracles or holdout labels;
- infer tenant isolation, authority, or idempotency from configuration flags; or
- authorize merge, deployment, activation, or release.
