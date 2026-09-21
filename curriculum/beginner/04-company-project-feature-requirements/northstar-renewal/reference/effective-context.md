# Bounded agent context

Gate: `READY` for the dated fixture.

The generated context preserves requirement IDs, source locators, meaning owners, fixed controls, delegated fields, specialization IDs, enforcement owners, evidence IDs, and selected exception metadata. It is content-addressed with a resolver version and context digest.

The repository boundary allows feature, implementation, and test changes but treats policy and exception sources as read-only or prohibited. Path access and semantic authority are separate checks. A coding agent may decide only fields explicitly delegated with `agent_authority = decide`; it may propose other delegated choices and must not modify fixed controls, reassign decision owners, or approve exceptions even if a tool can write the corresponding file.

Execution stops for missing applicability facts, fixed-control weakening, unauthorized delegated ownership, stale parent review, invalid exception authority or lifecycle, missing automated enforcement/evidence, and writes beyond the approved boundary.
