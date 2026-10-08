# Dated Spec Kit v1.1.0 observation

This manifest records an actual credential-free initialization of the official `v1.1.0` source release on 2026-10-04 using the Codex skills integration. It records the reported CLI version, resolved release commit, exposed core commands, selected scaffold paths, and SHA-256 digests of the bundled templates.

The repository does not vendor the generated Spec Kit command files. The course's `spec.md`, `plan.md`, and `tasks.md` are authored training artifacts that use the documented lifecycle and file semantics. Re-run the official installation and inspect the diff before enterprise adoption or upgrade.

The snapshot proves only what the observed CLI exposed at that pinned release. It is not a benchmark, security audit, vendor certification, or proof that a generated artifact is correct.

`core_commands` is the workflow surface required by Course 13, not a complete inventory of every shipped command. `speckit.taskstoissues` is recorded separately because issue export is not required for SDD conformance. `command_contracts` binds every required command artifact to a digest and expected semantics so an upgrade must pass semantic golden scenarios, not merely retain the same command names.
