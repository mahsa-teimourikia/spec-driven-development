# Design

The course creates reproducible commits for `ai-service`, `review-service`, and `underwriting-api`, imports code from those exact revisions, and executes protected behavior. SQLite supplies a real unique-key and transaction boundary for concurrent idempotency. Versioned JSONL data compares v1, v2, and an intentionally overfit classifier across development and holdout populations.

The trusted harness owns oracle and dataset digests, runs 17 verification obligations, seven critical mutations, and six failure experiments, and signs the resulting receipt. The quality gate validates the producer, exact subject, time, policy, suite, traceability, oracle source, flake state, mutation population, and safe-state experiments.

Decisions are `CONFORMANT`, `BLOCKED`, `INSUFFICIENT_EVIDENCE`, `REVIEW_REQUIRED`, `STALE_EVIDENCE`, or `CONFORMANT_WITH_EXCEPTION`. The reference result stops at `READY_FOR_INTEGRATION_REVIEW`; all delivery authorization fields remain false.
