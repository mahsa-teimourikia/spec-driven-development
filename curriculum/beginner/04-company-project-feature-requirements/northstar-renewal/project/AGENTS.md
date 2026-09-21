# Repository agent instructions

Before implementation, resolve the current project policy manifest, inspect
project ADRs, and stop on uncertainty, conflict, requested policy weakening, or
required authorization changes.

Modify only the paths granted by `agent-boundary.json`. Do not edit enterprise
policy, exceptions, authentication, or infrastructure to unblock yourself.
Produce a scope-expansion request when an approved task needs a protected path.
Path or tool access does not grant decision authority: even if a path becomes
writable, do not modify fixed controls, reassign owners, or approve exceptions.

Before completion, run unit tests, authorization checks, renewal evaluations,
and traceability checks. These instructions guide execution; they do not replace
the requirements or enforcement mechanisms they reference.
