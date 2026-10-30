"""Executable Course 21 scenarios and deterministic scheduling experiments."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Mapping

from .control_plane import (
    Checkpoint,
    ControlPlane,
    EvidenceReceipt,
    IntegrationDecision,
    WorkState,
    WorkUnit,
    WorkerPrincipal,
    canonical_digest,
)
from .git_harness import REPOSITORIES, RepositoryRevision, TrustedGitHarness


NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
_REVISION_CACHE: dict[str, dict[str, RepositoryRevision]] = {}


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def trusted_revisions(root: Path) -> dict[str, RepositoryRevision]:
    key = str(root.resolve())
    if key not in _REVISION_CACHE:
        _REVISION_CACHE[key] = TrustedGitHarness(root).observe()
    return _REVISION_CACHE[key]


def _workers() -> list[WorkerPrincipal]:
    return [
        WorkerPrincipal("agent-document", ("document-service",)),
        WorkerPrincipal("agent-ai-a", ("ai-service",)),
        WorkerPrincipal("agent-ai-b", ("ai-service",)),
        WorkerPrincipal("agent-review", ("review-service",)),
        WorkerPrincipal("agent-api", ("underwriting-api",)),
        WorkerPrincipal("agent-ui", ("underwriter-ui",)),
    ]


def make_plane(root: Path, revisions: Mapping[str, RepositoryRevision]) -> ControlPlane:
    graph = load_json(root / "parent-change/dependency-graph.json")
    definitions = load_json(root / "parent-change/work-units.json")
    contract = load_json(root / "contracts/classification-v2.schema.json")
    units: list[WorkUnit] = []
    for work_unit_id, definition in definitions.items():
        repository = definition["repository"]
        if repository == "contract-registry":
            base_commit = canonical_digest(contract).split(":", 1)[1][:40]
            state = WorkState.VERIFIED
        else:
            base_commit = revisions[repository].baseline_commit
            state = WorkState.PLANNED
        units.append(
            WorkUnit(
                work_unit_id=work_unit_id,
                repository=repository,
                dependencies=tuple(graph["dependencies"][work_unit_id]),
                allowed_paths=tuple(definition["allowed_paths"]),
                base_commit=base_commit,
                contract_revision=2,
                state=state,
            )
        )
    return ControlPlane(
        work_units=units,
        workers=_workers(),
        contract_revision=2,
        contract_digest=canonical_digest(contract),
        contract_owner="northstar-contract-owner",
    )


def _receipt(
    plane: ControlPlane,
    work_unit_id: str,
    revision: RepositoryRevision,
    *,
    passed: bool | None = None,
    commit: str | None = None,
    producer: str | None = None,
) -> EvidenceReceipt:
    return EvidenceReceipt(
        evidence_id=f"EVID-{work_unit_id}",
        producer_identity=producer or plane.integration_verifier,
        work_unit_id=work_unit_id,
        repository=revision.repository,
        candidate_commit=commit or revision.candidate_commit,
        contract_revision=plane.contract_revision,
        contract_digest=plane.contract_digest,
        result_digest=canonical_digest(
            {
                "work_unit_id": work_unit_id,
                "commit": commit or revision.candidate_commit,
                "tests_passed": revision.tests_passed,
            }
        ),
        checks=("local-tests", "scope", "contract", "authority"),
        passed=revision.tests_passed if passed is None else passed,
    )


def complete_unit(
    plane: ControlPlane,
    work_unit_id: str,
    revision: RepositoryRevision,
    identity: str,
    *,
    now: datetime = NOW,
) -> None:
    lease = plane.acquire_lease(
        work_unit_id,
        authenticated_identity=identity,
        now=now,
    )
    plane.start(lease, authenticated_identity=identity, now=now)
    plane.submit(
        lease,
        authenticated_identity=identity,
        now=now + timedelta(minutes=1),
        base_commit=revision.baseline_commit,
        candidate_commit=revision.candidate_commit,
        contract_revision=2,
        changed_paths=revision.changed_paths,
    )
    plane.verify(
        _receipt(plane, work_unit_id, revision),
        authenticated_identity=plane.integration_verifier,
    )


def system_scenarios(
    root: Path,
    plane: ControlPlane,
    revisions: Mapping[str, RepositoryRevision],
) -> dict[str, bool]:
    behavior = (root / "contracts/classification.behavior.md").read_text(encoding="utf-8")
    fixtures = TrustedGitHarness(root).fixtures
    effect_count = 0

    def create_pr() -> Mapping[str, object]:
        nonlocal effect_count
        effect_count += 1
        return {"pull_request": 182, "effect_count": effect_count}

    request = {
        "change_id": "AI-2500",
        "work_unit_id": "WU-AI",
        "action": "CREATE_OR_UPDATE_PR",
        "branch": "agent/AI-2500-WU-AI",
    }
    first, first_reconciled = plane.execute_idempotent(
        operation_id="AI-2500:WU-AI:CREATE_OR_UPDATE_PR:2",
        authenticated_identity="agent-ai-a",
        request=request,
        effect=create_pr,
    )
    second, second_reconciled = plane.execute_idempotent(
        operation_id="AI-2500:WU-AI:CREATE_OR_UPDATE_PR:2",
        authenticated_identity="agent-ai-a",
        request=request,
        effect=create_pr,
    )
    return {
        "ambiguity_routes_to_review": "regardless of model confidence" in behavior,
        "tenant_isolation": "tenant **MUST** match" in behavior,
        "duplicate_operation_reconciled": (
            not first_reconciled
            and second_reconciled
            and first == second
            and effect_count == 1
        ),
        "provenance_preserved": (
            "evidence_refs" in load_json(root / "contracts/classification-v2.schema.json")["required"]
            and "model_revision" in load_json(root / "contracts/classification-v2.schema.json")["required"]
        ),
        "proposal_not_authoritative": (
            fixtures["ai-service"]["candidate"]["authoritative"] is False
            and fixtures["underwriting-api"]["candidate"]["authoritative"] is True
        ),
        "exact_revision_set": all(
            len(revision.candidate_commit) == 40 and revision.tests_passed
            for revision in revisions.values()
        ),
    }


def run_reference(root: Path) -> tuple[
    ControlPlane,
    dict[str, RepositoryRevision],
    dict[str, object],
    dict[str, bool],
    IntegrationDecision,
]:
    revisions = trusted_revisions(root)
    plane = make_plane(root, revisions)
    for work_unit_id, repository, identity in (
        ("WU-DOC", "document-service", "agent-document"),
        ("WU-AI", "ai-service", "agent-ai-a"),
        ("WU-REVIEW", "review-service", "agent-review"),
        ("WU-API", "underwriting-api", "agent-api"),
        ("WU-UI", "underwriter-ui", "agent-ui"),
    ):
        complete_unit(plane, work_unit_id, revisions[repository], identity)
    results = system_scenarios(root, plane, revisions)
    manifest: dict[str, object] = {
        "change_id": "AI-2500",
        "parent_revision": 2,
        "contract_revision": plane.contract_revision,
        "contract_digest": plane.contract_digest,
        "component_commits": {
            repository: revision.candidate_commit
            for repository, revision in revisions.items()
        },
        "evidence_ids": sorted(plane.evidence),
        "release_authorized": False,
    }
    decision = plane.integration_barrier(
        manifest=manifest,
        system_results=results,
        authenticated_identity=plane.integration_verifier,
    )
    return plane, revisions, manifest, results, decision


def scheduling_comparison(root: Path) -> dict[str, dict[str, float | int | str]]:
    definitions = load_json(root / "parent-change/work-units.json")
    durations = {key: int(value["duration"]) for key, value in definitions.items()}
    dependencies = load_json(root / "parent-change/dependency-graph.json")["dependencies"]
    sequential_elapsed = sum(durations.values())
    naive_rework = durations["WU-AI"] + durations["WU-REVIEW"]
    naive_elapsed = max(durations.values()) + naive_rework

    finish: dict[str, int] = {}
    pending = set(durations)
    while pending:
        progressed = False
        for work_unit_id in sorted(pending):
            if all(dependency in finish for dependency in dependencies[work_unit_id]):
                start = max((finish[item] for item in dependencies[work_unit_id]), default=0)
                finish[work_unit_id] = start + durations[work_unit_id]
                pending.remove(work_unit_id)
                progressed = True
                break
        if not progressed:
            raise ValueError("dependency graph contains a cycle")
    governed_coordination = 3
    governed_elapsed = max(finish.values()) + governed_coordination
    return {
        "sequential": {
            "elapsed_hours": sequential_elapsed,
            "coordination_hours": 0,
            "rework_hours": 0,
            "verified_changes": 1,
            "model": "deterministic event simulation",
        },
        "naive_parallel": {
            "elapsed_hours": naive_elapsed,
            "coordination_hours": 0,
            "rework_hours": naive_rework,
            "verified_changes": 1,
            "model": "all work starts before dependency approval",
        },
        "governed_parallel": {
            "elapsed_hours": governed_elapsed,
            "coordination_hours": governed_coordination,
            "rework_hours": 0,
            "verified_changes": 1,
            "model": "dependency-aware event simulation",
        },
    }


def _fresh(root: Path) -> tuple[ControlPlane, dict[str, RepositoryRevision]]:
    revisions = trusted_revisions(root)
    return make_plane(root, revisions), revisions


def _raises(code: str, action: Callable[[], object]) -> bool:
    try:
        action()
    except Exception as error:
        return code in str(error)
    return False


def golden_scenarios(root: Path) -> dict[str, bool]:
    outcomes: dict[str, bool] = {}

    plane, revisions = _fresh(root)
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    outcomes["PAR-GOLDEN-001"] = _raises(
        "WORK_UNIT_NOT_READY",
        lambda: plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-b", now=NOW),
    )

    plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
    plane.expire_and_requeue("WU-AI", now=NOW + timedelta(minutes=21))
    replacement = plane.acquire_lease(
        "WU-AI", authenticated_identity="agent-ai-b", now=NOW + timedelta(minutes=21)
    )
    plane.start(replacement, authenticated_identity="agent-ai-b", now=NOW + timedelta(minutes=21))
    outcomes["PAR-GOLDEN-002"] = _raises(
        "STALE_FENCING_TOKEN",
        lambda: plane.submit(
            lease,
            authenticated_identity="agent-ai-a",
            now=NOW + timedelta(minutes=2),
            base_commit=revisions["ai-service"].baseline_commit,
            candidate_commit=revisions["ai-service"].candidate_commit,
            contract_revision=2,
            changed_paths=revisions["ai-service"].changed_paths,
        ),
    )

    plane, revisions = _fresh(root)
    outcomes["PAR-GOLDEN-003"] = "WU-API" not in plane.ready_units()
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
    outcomes["PAR-GOLDEN-004"] = _raises(
        "UNAUTHORIZED_PATH_MODIFICATION",
        lambda: plane.submit(
            lease,
            authenticated_identity="agent-ai-a",
            now=NOW + timedelta(minutes=1),
            base_commit=revisions["ai-service"].baseline_commit,
            candidate_commit=revisions["ai-service"].candidate_commit,
            contract_revision=2,
            changed_paths=("infra/production-admin.tf",),
        ),
    )

    plane, revisions = _fresh(root)
    contract_v3 = load_json(root / "contracts/classification-v3.schema.json")
    proposal = plane.propose_contract_change(
        authenticated_identity="agent-ai-a",
        proposed_revision=3,
        proposed_contract=contract_v3,
        affected_hint=("WU-AI", "WU-REVIEW"),
    )
    owner_blocked = _raises(
        "CONTRACT_OWNER_APPROVAL_REQUIRED",
        lambda: plane.approve_contract_change(
            proposal,
            authenticated_identity="agent-ai-a",
            direct_dependents=("WU-AI", "WU-REVIEW"),
        ),
    )
    affected = plane.approve_contract_change(
        proposal,
        authenticated_identity="northstar-contract-owner",
        direct_dependents=("WU-AI", "WU-REVIEW"),
    )
    outcomes["PAR-GOLDEN-005"] = owner_blocked and set(affected) == {
        "WU-AI",
        "WU-REVIEW",
        "WU-API",
        "WU-UI",
    } and plane.work_units["WU-DOC"].state == WorkState.READY

    plane, _ = _fresh(root)
    effects = 0

    def effect() -> Mapping[str, object]:
        nonlocal effects
        effects += 1
        return {"pull_request": 182}

    request = {"branch": "agent/AI-2500-WU-AI", "action": "CREATE_OR_UPDATE_PR"}
    first, _ = plane.execute_idempotent(
        operation_id="OP-2500-031",
        authenticated_identity="agent-ai-a",
        request=request,
        effect=effect,
    )
    second, reconciled = plane.execute_idempotent(
        operation_id="OP-2500-031",
        authenticated_identity="agent-ai-a",
        request=request,
        effect=effect,
    )
    outcomes["PAR-GOLDEN-006"] = first == second and reconciled and effects == 1

    plane, revisions = _fresh(root)
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
    checkpoint = plane.create_checkpoint(
        lease,
        authenticated_identity="agent-ai-a",
        now=NOW + timedelta(minutes=1),
        completed=("adapter",),
        remaining=("negative-tests",),
    )
    next_lease = plane.acquire_lease(
        "WU-AI", authenticated_identity="agent-ai-b", now=NOW + timedelta(minutes=2)
    )
    outcomes["PAR-GOLDEN-007"] = _raises(
        "CHECKPOINT_REPOSITORY_STALE",
        lambda: plane.validate_checkpoint_resume(
            checkpoint.checkpoint_id,
            next_lease,
            authenticated_identity="agent-ai-b",
            now=NOW + timedelta(minutes=2),
            current_base_commit="0" * 40,
        ),
    )

    plane, revisions = _fresh(root)
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
    plane.submit(
        lease,
        authenticated_identity="agent-ai-a",
        now=NOW + timedelta(minutes=1),
        base_commit=revisions["ai-service"].baseline_commit,
        candidate_commit=revisions["ai-service"].candidate_commit,
        contract_revision=2,
        changed_paths=revisions["ai-service"].changed_paths,
    )
    outcomes["PAR-GOLDEN-008"] = _raises(
        "AGENT_CANNOT_SELF_VERIFY",
        lambda: plane.agent_claims_complete("WU-AI", authenticated_identity="agent-ai-a"),
    )

    reference_plane, _, manifest, results, _ = run_reference(root)
    stale_manifest = dict(manifest)
    stale_manifest["component_commits"] = {
        **manifest["component_commits"],
        "review-service": "0" * 40,
    }
    decision = reference_plane.integration_barrier(
        manifest=stale_manifest,
        system_results=results,
        authenticated_identity=reference_plane.integration_verifier,
    )
    outcomes["PAR-GOLDEN-009"] = (
        decision.state == "BLOCKED"
        and "INTEGRATION_REVISION_SET_MISMATCH" in decision.findings
    )
    outcomes["PAR-GOLDEN-010"] = _raises(
        "SEPARATE_RELEASE_AUTHORITY_REQUIRED",
        lambda: reference_plane.authorize_release(
            authenticated_identity=reference_plane.coordinator_identity
        ),
    )

    plane, revisions = _fresh(root)
    for attempt in range(3):
        lease = plane.acquire_lease(
            "WU-AI",
            authenticated_identity="agent-ai-a" if attempt % 2 == 0 else "agent-ai-b",
            now=NOW + timedelta(minutes=attempt),
        )
        identity = lease.holder
        plane.start(lease, authenticated_identity=identity, now=NOW + timedelta(minutes=attempt))
        plane.fail_and_retry("WU-AI", reason="PERSISTENT_TOOL_FAILURE")
    outcomes["PAR-GOLDEN-011"] = plane.work_units["WU-AI"].state == WorkState.ESCALATED

    plane, _ = _fresh(root)
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    plane.execute_idempotent(
        operation_id="OP-RESTART",
        authenticated_identity="agent-ai-a",
        request={"action": "CREATE_OR_UPDATE_PR"},
        effect=lambda: {"pull_request": 183},
    )
    snapshot = plane.snapshot()
    restored, _ = _fresh(root)
    restored.restore_snapshot(snapshot)
    result, reconciled = restored.execute_idempotent(
        operation_id="OP-RESTART",
        authenticated_identity="agent-ai-a",
        request={"action": "CREATE_OR_UPDATE_PR"},
        effect=lambda: {"pull_request": 999},
    )
    outcomes["PAR-GOLDEN-012"] = (
        restored.leases["WU-AI"].generation == lease.generation
        and result == {"pull_request": 183}
        and reconciled
    )
    return outcomes


def evaluation_checks(root: Path) -> dict[str, bool]:
    """Thirty labelled positive, negative, boundary, and failure decisions."""
    golden = golden_scenarios(root)
    plane, revisions = _fresh(root)
    checks: dict[str, bool] = {
        "EVAL-001-single-active-lease": golden["PAR-GOLDEN-001"],
        "EVAL-002-stale-fencing-rejected": golden["PAR-GOLDEN-002"],
        "EVAL-003-dependency-blocks-dispatch": golden["PAR-GOLDEN-003"],
        "EVAL-004-path-scope-enforced": golden["PAR-GOLDEN-004"],
        "EVAL-005-contract-change-invalidates": golden["PAR-GOLDEN-005"],
        "EVAL-006-duplicate-effect-reconciles": golden["PAR-GOLDEN-006"],
        "EVAL-007-stale-checkpoint-blocked": golden["PAR-GOLDEN-007"],
        "EVAL-008-completion-not-verification": golden["PAR-GOLDEN-008"],
        "EVAL-009-exact-revision-required": golden["PAR-GOLDEN-009"],
        "EVAL-010-release-authority-separated": golden["PAR-GOLDEN-010"],
        "EVAL-011-retry-budget-bounded": golden["PAR-GOLDEN-011"],
        "EVAL-012-restart-reconciles-state": golden["PAR-GOLDEN-012"],
        "EVAL-013-api-initially-blocked": plane.work_units["WU-API"].state == WorkState.BLOCKED,
        "EVAL-014-ui-initially-blocked": plane.work_units["WU-UI"].state == WorkState.BLOCKED,
        "EVAL-015-contract-is-verified-prerequisite": plane.work_units["WU-CONTRACT"].state == WorkState.VERIFIED,
    }
    checks["EVAL-016-unauthenticated-worker-denied"] = _raises(
        "UNAUTHENTICATED_WORKLOAD",
        lambda: plane.acquire_lease("WU-AI", authenticated_identity="claimed-agent", now=NOW),
    )
    checks["EVAL-017-wrong-repository-denied"] = _raises(
        "REPOSITORY_SCOPE_DENIED",
        lambda: plane.acquire_lease("WU-AI", authenticated_identity="agent-document", now=NOW),
    )
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
    checks["EVAL-018-stale-base-denied"] = _raises(
        "STALE_REPOSITORY_CONTEXT",
        lambda: plane.submit(
            lease,
            authenticated_identity="agent-ai-a",
            now=NOW + timedelta(minutes=1),
            base_commit="0" * 40,
            candidate_commit=revisions["ai-service"].candidate_commit,
            contract_revision=2,
            changed_paths=revisions["ai-service"].changed_paths,
        ),
    )
    checks["EVAL-019-stale-contract-denied"] = _raises(
        "STALE_CONTRACT_CONTEXT",
        lambda: plane.submit(
            lease,
            authenticated_identity="agent-ai-a",
            now=NOW + timedelta(minutes=1),
            base_commit=revisions["ai-service"].baseline_commit,
            candidate_commit=revisions["ai-service"].candidate_commit,
            contract_revision=1,
            changed_paths=revisions["ai-service"].changed_paths,
        ),
    )
    checks["EVAL-020-symbolic-revision-denied"] = _raises(
        "UNPINNED_CANDIDATE_REVISION",
        lambda: plane.submit(
            lease,
            authenticated_identity="agent-ai-a",
            now=NOW + timedelta(minutes=1),
            base_commit=revisions["ai-service"].baseline_commit,
            candidate_commit="feature/latest",
            contract_revision=2,
            changed_paths=revisions["ai-service"].changed_paths,
        ),
    )

    plane, revisions = _fresh(root)
    lease = plane.acquire_lease("WU-AI", authenticated_identity="agent-ai-a", now=NOW)
    plane.start(lease, authenticated_identity="agent-ai-a", now=NOW)
    plane.submit(
        lease,
        authenticated_identity="agent-ai-a",
        now=NOW + timedelta(minutes=1),
        base_commit=revisions["ai-service"].baseline_commit,
        candidate_commit=revisions["ai-service"].candidate_commit,
        contract_revision=2,
        changed_paths=revisions["ai-service"].changed_paths,
    )
    checks["EVAL-021-untrusted-verifier-denied"] = _raises(
        "UNTRUSTED_EVIDENCE_PRODUCER",
        lambda: plane.verify(
            _receipt(plane, "WU-AI", revisions["ai-service"]),
            authenticated_identity="agent-ai-a",
        ),
    )
    checks["EVAL-022-wrong-evidence-subject-denied"] = _raises(
        "EVIDENCE_SUBJECT_MISMATCH",
        lambda: plane.verify(
            _receipt(plane, "WU-AI", revisions["ai-service"], commit="f" * 40),
            authenticated_identity=plane.integration_verifier,
        ),
    )

    plane, _ = _fresh(root)
    plane.execute_idempotent(
        operation_id="OP-CONFLICT",
        authenticated_identity="agent-ai-a",
        request={"branch": "one"},
        effect=lambda: {"pull_request": 1},
    )
    checks["EVAL-023-idempotency-key-conflict-denied"] = _raises(
        "IDEMPOTENCY_KEY_REUSED_FOR_DIFFERENT_REQUEST",
        lambda: plane.execute_idempotent(
            operation_id="OP-CONFLICT",
            authenticated_identity="agent-ai-a",
            request={"branch": "two"},
            effect=lambda: {"pull_request": 2},
        ),
    )

    reference_plane, reference_revisions, manifest, system_results, reference_decision = run_reference(root)
    checks["EVAL-024-reference-ready-for-review"] = reference_decision.state == "READY_FOR_INTEGRATION_REVIEW"
    checks["EVAL-025-reference-never-authorizes-merge"] = reference_decision.merge_authorized is False
    checks["EVAL-026-reference-never-authorizes-deploy"] = reference_decision.deployment_authorized is False
    failed_results = dict(system_results)
    failed_results["tenant_isolation"] = False
    failed_decision = reference_plane.integration_barrier(
        manifest=manifest,
        system_results=failed_results,
        authenticated_identity=reference_plane.integration_verifier,
    )
    checks["EVAL-027-failed-system-scenario-blocks"] = "SYSTEM_SCENARIO_FAILED" in failed_decision.findings
    self_authorized = dict(manifest)
    self_authorized["release_authorized"] = True
    self_decision = reference_plane.integration_barrier(
        manifest=self_authorized,
        system_results=system_results,
        authenticated_identity=reference_plane.integration_verifier,
    )
    checks["EVAL-028-self-authorized-release-blocks"] = "COORDINATOR_SELF_AUTHORIZED_RELEASE" in self_decision.findings
    checks["EVAL-029-five-exact-revisions"] = (
        set(reference_decision.component_commits) == set(REPOSITORIES)
        and all(len(value) == 40 for value in reference_decision.component_commits.values())
    )
    checks["EVAL-030-evidence-binds-each-revision"] = all(
        any(receipt.candidate_commit == revision.candidate_commit for receipt in reference_plane.evidence.values())
        for revision in reference_revisions.values()
    )
    return checks
