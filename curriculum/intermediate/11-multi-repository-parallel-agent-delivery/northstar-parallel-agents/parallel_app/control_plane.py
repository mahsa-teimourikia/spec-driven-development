"""Trusted scheduling, ownership, recovery, and integration controls.

The model/agent may propose work, edits, checkpoints, or contract changes. This
module represents the application-owned boundary that authenticates identities,
issues leases, enforces fencing and scope, records evidence, and decides whether
an exact revision set is eligible for integration review.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Callable, Iterable, Mapping


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class WorkState(str, Enum):
    PLANNED = "PLANNED"
    BLOCKED = "BLOCKED"
    READY = "READY"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    SUBMITTED = "SUBMITTED"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    INTEGRATED = "INTEGRATED"
    FAILED = "FAILED"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    INVALIDATED = "INVALIDATED"
    ESCALATED = "ESCALATED"


ACTIVE_STATES = {
    WorkState.LEASED,
    WorkState.RUNNING,
    WorkState.PAUSED,
    WorkState.SUBMITTED,
    WorkState.VERIFYING,
}


@dataclass
class WorkerPrincipal:
    identity: str
    repositories: tuple[str, ...]
    permissions: tuple[str, ...] = (
        "read_repository",
        "write_bounded_branch",
        "run_tests",
    )
    roles: tuple[str, ...] = ("coding-worker",)


@dataclass
class WorkUnit:
    work_unit_id: str
    repository: str
    dependencies: tuple[str, ...]
    allowed_paths: tuple[str, ...]
    base_commit: str
    contract_revision: int
    state: WorkState = WorkState.PLANNED
    generation: int = 0
    candidate_commit: str | None = None
    evidence_ids: tuple[str, ...] = ()
    retry_count: int = 0
    retry_budget: int = 2
    blocked_reason: str | None = None


@dataclass(frozen=True)
class Lease:
    lease_id: str
    work_unit_id: str
    holder: str
    repository: str
    generation: int
    base_commit: str
    contract_revision: int
    permissions: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    work_unit_id: str
    holder: str
    generation: int
    base_commit: str
    contract_revision: int
    candidate_commit: str | None
    completed: tuple[str, ...]
    remaining: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    discoveries: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceReceipt:
    evidence_id: str
    producer_identity: str
    work_unit_id: str
    repository: str
    candidate_commit: str
    contract_revision: int
    contract_digest: str
    result_digest: str
    checks: tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class IntegrationDecision:
    state: str
    findings: tuple[str, ...]
    component_commits: Mapping[str, str]
    contract_revision: int
    revision_set_digest: str | None
    merge_authorized: bool = False
    deployment_authorized: bool = False
    release_authorized: bool = False


TRANSITIONS: dict[WorkState, set[WorkState]] = {
    WorkState.PLANNED: {WorkState.BLOCKED, WorkState.READY, WorkState.INVALIDATED},
    WorkState.BLOCKED: {WorkState.READY, WorkState.INVALIDATED},
    WorkState.READY: {WorkState.LEASED, WorkState.INVALIDATED, WorkState.ESCALATED},
    WorkState.LEASED: {WorkState.RUNNING, WorkState.LEASE_EXPIRED, WorkState.INVALIDATED},
    WorkState.RUNNING: {
        WorkState.PAUSED,
        WorkState.SUBMITTED,
        WorkState.FAILED,
        WorkState.LEASE_EXPIRED,
        WorkState.INVALIDATED,
    },
    WorkState.PAUSED: {WorkState.READY, WorkState.INVALIDATED, WorkState.ESCALATED},
    WorkState.SUBMITTED: {WorkState.VERIFYING, WorkState.REWORK_REQUIRED, WorkState.INVALIDATED},
    WorkState.VERIFYING: {WorkState.VERIFIED, WorkState.REWORK_REQUIRED, WorkState.INVALIDATED},
    WorkState.VERIFIED: {WorkState.INTEGRATED, WorkState.INVALIDATED, WorkState.REWORK_REQUIRED},
    WorkState.REWORK_REQUIRED: {WorkState.READY, WorkState.ESCALATED, WorkState.INVALIDATED},
    WorkState.FAILED: {WorkState.READY, WorkState.ESCALATED, WorkState.INVALIDATED},
    WorkState.LEASE_EXPIRED: {WorkState.READY, WorkState.ESCALATED, WorkState.INVALIDATED},
    WorkState.INVALIDATED: {WorkState.BLOCKED, WorkState.READY},
    WorkState.ESCALATED: {WorkState.READY, WorkState.INVALIDATED},
    WorkState.INTEGRATED: {WorkState.INVALIDATED},
}


class ControlPlane:
    """Deterministic application-owned orchestration boundary."""

    def __init__(
        self,
        *,
        work_units: Iterable[WorkUnit],
        workers: Iterable[WorkerPrincipal],
        contract_revision: int,
        contract_digest: str,
        contract_owner: str,
        integration_verifier: str = "northstar-integration-ci",
        coordinator_identity: str = "northstar-coordinator",
    ):
        self.work_units = {item.work_unit_id: copy.deepcopy(item) for item in work_units}
        self.workers = {item.identity: copy.deepcopy(item) for item in workers}
        self.contract_revision = contract_revision
        self.contract_digest = contract_digest
        self.contract_owner = contract_owner
        self.integration_verifier = integration_verifier
        self.coordinator_identity = coordinator_identity
        self.leases: dict[str, Lease] = {}
        self.checkpoints: dict[str, Checkpoint] = {}
        self.evidence: dict[str, EvidenceReceipt] = {}
        self.operations: dict[str, dict[str, object]] = {}
        self.contract_proposals: dict[str, dict[str, object]] = {}
        self.events: list[dict[str, object]] = []
        self._lock = threading.RLock()
        self.refresh_readiness()

    def _event(self, event_type: str, **details: object) -> None:
        self.events.append({"sequence": len(self.events) + 1, "type": event_type, **details})

    def _transition(self, unit: WorkUnit, target: WorkState, reason: str | None = None) -> None:
        if target not in TRANSITIONS.get(unit.state, set()):
            raise ValueError(f"INVALID_TRANSITION:{unit.state.value}->{target.value}")
        previous = unit.state
        unit.state = target
        unit.blocked_reason = reason
        self._event(
            "WORK_UNIT_TRANSITION",
            work_unit_id=unit.work_unit_id,
            previous=previous.value,
            current=target.value,
            reason=reason,
        )

    def refresh_readiness(self) -> tuple[str, ...]:
        made_ready: list[str] = []
        changed = True
        while changed:
            changed = False
            for unit in self.work_units.values():
                if unit.state not in {WorkState.PLANNED, WorkState.BLOCKED}:
                    continue
                ready = all(
                    self.work_units[dependency].state in {WorkState.VERIFIED, WorkState.INTEGRATED}
                    for dependency in unit.dependencies
                )
                target = WorkState.READY if ready else WorkState.BLOCKED
                if unit.state != target:
                    self._transition(unit, target, None if ready else "UNMET_DEPENDENCY")
                    changed = True
                    if ready:
                        made_ready.append(unit.work_unit_id)
        return tuple(made_ready)

    def ready_units(self) -> tuple[str, ...]:
        self.refresh_readiness()
        return tuple(sorted(key for key, unit in self.work_units.items() if unit.state == WorkState.READY))

    def acquire_lease(
        self,
        work_unit_id: str,
        *,
        authenticated_identity: str,
        now: datetime,
        ttl: timedelta = timedelta(minutes=20),
    ) -> Lease:
        with self._lock:
            principal = self.workers.get(authenticated_identity)
            if principal is None:
                raise PermissionError("UNAUTHENTICATED_WORKLOAD")
            unit = self.work_units[work_unit_id]
            if unit.state != WorkState.READY:
                raise ValueError("WORK_UNIT_NOT_READY")
            if unit.repository not in principal.repositories:
                raise PermissionError("REPOSITORY_SCOPE_DENIED")
            unit.generation += 1
            lease = Lease(
                lease_id=f"LEASE-{work_unit_id}-{unit.generation}",
                work_unit_id=work_unit_id,
                holder=principal.identity,
                repository=unit.repository,
                generation=unit.generation,
                base_commit=unit.base_commit,
                contract_revision=unit.contract_revision,
                permissions=principal.permissions,
                issued_at=now.astimezone(timezone.utc),
                expires_at=(now + ttl).astimezone(timezone.utc),
            )
            self.leases[work_unit_id] = lease
            self._transition(unit, WorkState.LEASED)
            self._event("LEASE_ISSUED", lease_id=lease.lease_id, holder=lease.holder)
            return lease

    def _assert_current_lease(
        self,
        lease: Lease,
        *,
        authenticated_identity: str,
        now: datetime,
    ) -> WorkUnit:
        current = self.leases.get(lease.work_unit_id)
        unit = self.work_units[lease.work_unit_id]
        if authenticated_identity != lease.holder:
            raise PermissionError("LEASE_IDENTITY_MISMATCH")
        if current is None or current.generation != lease.generation:
            raise PermissionError("STALE_FENCING_TOKEN")
        if unit.generation != lease.generation:
            raise PermissionError("STALE_FENCING_TOKEN")
        if now.astimezone(timezone.utc) >= lease.expires_at:
            raise PermissionError("LEASE_EXPIRED")
        return unit

    def start(self, lease: Lease, *, authenticated_identity: str, now: datetime) -> None:
        unit = self._assert_current_lease(
            lease, authenticated_identity=authenticated_identity, now=now
        )
        self._transition(unit, WorkState.RUNNING)

    def expire_and_requeue(self, work_unit_id: str, *, now: datetime) -> None:
        with self._lock:
            lease = self.leases[work_unit_id]
            if now.astimezone(timezone.utc) < lease.expires_at:
                raise ValueError("LEASE_STILL_ACTIVE")
            unit = self.work_units[work_unit_id]
            self._transition(unit, WorkState.LEASE_EXPIRED)
            unit.retry_count += 1
            if unit.retry_count > unit.retry_budget:
                self._transition(unit, WorkState.ESCALATED, "RETRY_BUDGET_EXHAUSTED")
            else:
                self._transition(unit, WorkState.READY)
            self._event("LEASE_REVOKED", work_unit_id=work_unit_id, generation=lease.generation)

    @staticmethod
    def _path_allowed(path: str, allowed_paths: tuple[str, ...]) -> bool:
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            return False
        text = normalized.as_posix()
        return any(text == prefix.rstrip("/") or text.startswith(prefix.rstrip("/") + "/") for prefix in allowed_paths)

    def submit(
        self,
        lease: Lease,
        *,
        authenticated_identity: str,
        now: datetime,
        base_commit: str,
        candidate_commit: str,
        contract_revision: int,
        changed_paths: Iterable[str],
    ) -> None:
        unit = self._assert_current_lease(
            lease, authenticated_identity=authenticated_identity, now=now
        )
        if unit.state != WorkState.RUNNING:
            raise ValueError("WORK_UNIT_NOT_RUNNING")
        if base_commit != unit.base_commit:
            raise ValueError("STALE_REPOSITORY_CONTEXT")
        if contract_revision != self.contract_revision or contract_revision != unit.contract_revision:
            raise ValueError("STALE_CONTRACT_CONTEXT")
        if not FULL_SHA.fullmatch(candidate_commit):
            raise ValueError("UNPINNED_CANDIDATE_REVISION")
        if any(not self._path_allowed(path, unit.allowed_paths) for path in changed_paths):
            raise PermissionError("UNAUTHORIZED_PATH_MODIFICATION")
        unit.candidate_commit = candidate_commit
        self._transition(unit, WorkState.SUBMITTED)
        self._event(
            "CANDIDATE_SUBMITTED",
            work_unit_id=unit.work_unit_id,
            candidate_commit=candidate_commit,
            generation=lease.generation,
        )

    def agent_claims_complete(self, work_unit_id: str, *, authenticated_identity: str) -> None:
        unit = self.work_units[work_unit_id]
        lease = self.leases.get(work_unit_id)
        if lease is None or lease.holder != authenticated_identity:
            raise PermissionError("AGENT_NOT_CURRENT_HOLDER")
        if unit.state == WorkState.SUBMITTED:
            raise PermissionError("AGENT_CANNOT_SELF_VERIFY")
        raise ValueError("WORK_UNIT_NOT_SUBMITTED")

    def verify(
        self,
        receipt: EvidenceReceipt,
        *,
        authenticated_identity: str,
    ) -> None:
        if authenticated_identity != self.integration_verifier:
            raise PermissionError("UNTRUSTED_EVIDENCE_PRODUCER")
        unit = self.work_units[receipt.work_unit_id]
        if unit.state != WorkState.SUBMITTED:
            raise ValueError("WORK_UNIT_NOT_SUBMITTED")
        self._transition(unit, WorkState.VERIFYING)
        matches = (
            receipt.producer_identity == authenticated_identity
            and receipt.repository == unit.repository
            and receipt.candidate_commit == unit.candidate_commit
            and receipt.contract_revision == self.contract_revision
            and receipt.contract_digest == self.contract_digest
            and receipt.passed
            and bool(receipt.checks)
        )
        if not matches:
            self._transition(unit, WorkState.REWORK_REQUIRED, "EVIDENCE_SUBJECT_MISMATCH")
            raise ValueError("EVIDENCE_SUBJECT_MISMATCH")
        self.evidence[receipt.evidence_id] = receipt
        unit.evidence_ids = tuple(sorted(set((*unit.evidence_ids, receipt.evidence_id))))
        self._transition(unit, WorkState.VERIFIED)
        self.refresh_readiness()

    def fail_and_retry(self, work_unit_id: str, *, reason: str) -> None:
        unit = self.work_units[work_unit_id]
        if unit.state not in {WorkState.RUNNING, WorkState.REWORK_REQUIRED, WorkState.FAILED}:
            raise ValueError("WORK_UNIT_NOT_RETRYABLE")
        if unit.state == WorkState.RUNNING:
            self._transition(unit, WorkState.FAILED, reason)
        unit.retry_count += 1
        if unit.retry_count > unit.retry_budget:
            self._transition(unit, WorkState.ESCALATED, "RETRY_BUDGET_EXHAUSTED")
        else:
            self._transition(unit, WorkState.READY)

    def create_checkpoint(
        self,
        lease: Lease,
        *,
        authenticated_identity: str,
        now: datetime,
        completed: Iterable[str],
        remaining: Iterable[str],
        evidence_ids: Iterable[str] = (),
        discoveries: Iterable[str] = (),
        unresolved: Iterable[str] = (),
    ) -> Checkpoint:
        unit = self._assert_current_lease(
            lease, authenticated_identity=authenticated_identity, now=now
        )
        if unit.state != WorkState.RUNNING:
            raise ValueError("WORK_UNIT_NOT_RUNNING")
        checkpoint = Checkpoint(
            checkpoint_id=f"CHECKPOINT-{unit.work_unit_id}-{lease.generation}",
            work_unit_id=unit.work_unit_id,
            holder=authenticated_identity,
            generation=lease.generation,
            base_commit=unit.base_commit,
            contract_revision=unit.contract_revision,
            candidate_commit=unit.candidate_commit,
            completed=tuple(completed),
            remaining=tuple(remaining),
            evidence_ids=tuple(evidence_ids),
            discoveries=tuple(discoveries),
            unresolved=tuple(unresolved),
        )
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
        self._transition(unit, WorkState.PAUSED)
        self._transition(unit, WorkState.READY)
        return checkpoint

    def validate_checkpoint_resume(
        self,
        checkpoint_id: str,
        new_lease: Lease,
        *,
        authenticated_identity: str,
        now: datetime,
        current_base_commit: str,
    ) -> Checkpoint:
        checkpoint = self.checkpoints[checkpoint_id]
        unit = self._assert_current_lease(
            new_lease, authenticated_identity=authenticated_identity, now=now
        )
        if checkpoint.work_unit_id != unit.work_unit_id:
            raise ValueError("CHECKPOINT_WORK_UNIT_MISMATCH")
        if checkpoint.contract_revision != self.contract_revision:
            raise ValueError("CHECKPOINT_CONTRACT_STALE")
        if checkpoint.base_commit != current_base_commit or current_base_commit != unit.base_commit:
            raise ValueError("CHECKPOINT_REPOSITORY_STALE")
        if new_lease.generation <= checkpoint.generation:
            raise ValueError("CHECKPOINT_GENERATION_NOT_ADVANCED")
        self._transition(unit, WorkState.RUNNING)
        self._event("CHECKPOINT_RESUMED", checkpoint_id=checkpoint_id, holder=authenticated_identity)
        return checkpoint

    def execute_idempotent(
        self,
        *,
        operation_id: str,
        authenticated_identity: str,
        request: Mapping[str, object],
        effect: Callable[[], Mapping[str, object]],
    ) -> tuple[Mapping[str, object], bool]:
        principal = self.workers.get(authenticated_identity)
        if principal is None:
            raise PermissionError("UNAUTHENTICATED_WORKLOAD")
        request_digest = canonical_digest(request)
        with self._lock:
            existing = self.operations.get(operation_id)
            if existing:
                if existing["request_digest"] != request_digest:
                    raise ValueError("IDEMPOTENCY_KEY_REUSED_FOR_DIFFERENT_REQUEST")
                return copy.deepcopy(existing["result"]), True
            result = dict(effect())
            self.operations[operation_id] = {
                "identity": authenticated_identity,
                "request_digest": request_digest,
                "result": result,
            }
            self._event("IDEMPOTENT_EFFECT_RECORDED", operation_id=operation_id)
            return copy.deepcopy(result), False

    def propose_contract_change(
        self,
        *,
        authenticated_identity: str,
        proposed_revision: int,
        proposed_contract: Mapping[str, object],
        affected_hint: Iterable[str],
    ) -> str:
        if authenticated_identity not in self.workers:
            raise PermissionError("UNAUTHENTICATED_WORKLOAD")
        if proposed_revision <= self.contract_revision:
            raise ValueError("CONTRACT_REVISION_NOT_ADVANCED")
        proposal_id = f"CONTRACT-PROPOSAL-{proposed_revision}"
        self.contract_proposals[proposal_id] = {
            "proposer": authenticated_identity,
            "revision": proposed_revision,
            "contract": copy.deepcopy(dict(proposed_contract)),
            "digest": canonical_digest(proposed_contract),
            "affected_hint": tuple(sorted(affected_hint)),
            "state": "PROPOSED",
        }
        return proposal_id

    def approve_contract_change(
        self,
        proposal_id: str,
        *,
        authenticated_identity: str,
        direct_dependents: Iterable[str],
    ) -> tuple[str, ...]:
        if authenticated_identity != self.contract_owner:
            raise PermissionError("CONTRACT_OWNER_APPROVAL_REQUIRED")
        proposal = self.contract_proposals[proposal_id]
        proposal["state"] = "OWNER_APPROVED"
        self.contract_revision = int(proposal["revision"])
        self.contract_digest = str(proposal["digest"])
        affected = set(direct_dependents)
        changed = True
        while changed:
            changed = False
            for unit in self.work_units.values():
                if unit.work_unit_id in affected:
                    continue
                if any(dependency in affected for dependency in unit.dependencies):
                    affected.add(unit.work_unit_id)
                    changed = True
        for work_unit_id in sorted(affected):
            unit = self.work_units[work_unit_id]
            if unit.state != WorkState.INVALIDATED:
                self._transition(unit, WorkState.INVALIDATED, "APPROVED_CONTRACT_REVISION")
            unit.contract_revision = self.contract_revision
            unit.candidate_commit = None
            for evidence_id in unit.evidence_ids:
                self.evidence.pop(evidence_id, None)
            unit.evidence_ids = ()
        self._event(
            "CONTRACT_REVISION_APPROVED",
            proposal_id=proposal_id,
            revision=self.contract_revision,
            affected=tuple(sorted(affected)),
        )
        return tuple(sorted(affected))

    def replan_invalidated(self, work_unit_ids: Iterable[str]) -> None:
        for work_unit_id in work_unit_ids:
            unit = self.work_units[work_unit_id]
            if unit.state != WorkState.INVALIDATED:
                raise ValueError("WORK_UNIT_NOT_INVALIDATED")
            unit.state = WorkState.PLANNED
            unit.blocked_reason = None
        self.refresh_readiness()

    def integration_barrier(
        self,
        *,
        manifest: Mapping[str, object],
        system_results: Mapping[str, bool],
        authenticated_identity: str,
    ) -> IntegrationDecision:
        findings: list[str] = []
        if authenticated_identity != self.integration_verifier:
            findings.append("UNTRUSTED_INTEGRATION_VERIFIER")
        component_units = [unit for unit in self.work_units.values() if unit.repository != "contract-registry"]
        for unit in component_units:
            if unit.state != WorkState.VERIFIED:
                findings.append(f"WORK_UNIT_NOT_VERIFIED:{unit.work_unit_id}")
        expected_commits = {
            unit.repository: unit.candidate_commit
            for unit in component_units
            if unit.candidate_commit is not None
        }
        supplied_commits = dict(manifest.get("component_commits", {}))
        if supplied_commits != expected_commits or any(not FULL_SHA.fullmatch(str(value)) for value in supplied_commits.values()):
            findings.append("INTEGRATION_REVISION_SET_MISMATCH")
        if manifest.get("contract_revision") != self.contract_revision:
            findings.append("INTEGRATION_CONTRACT_REVISION_MISMATCH")
        if manifest.get("contract_digest") != self.contract_digest:
            findings.append("INTEGRATION_CONTRACT_DIGEST_MISMATCH")
        required_evidence = set(manifest.get("evidence_ids", []))
        actual_evidence = {evidence_id for unit in component_units for evidence_id in unit.evidence_ids}
        if required_evidence != actual_evidence or not required_evidence:
            findings.append("INTEGRATION_EVIDENCE_SET_MISMATCH")
        for evidence_id in required_evidence:
            receipt = self.evidence.get(evidence_id)
            if receipt is None or receipt.candidate_commit not in supplied_commits.values():
                findings.append(f"STALE_OR_UNKNOWN_EVIDENCE:{evidence_id}")
        if not system_results or not all(system_results.values()):
            findings.append("SYSTEM_SCENARIO_FAILED")
        if manifest.get("release_authorized") is True:
            findings.append("COORDINATOR_SELF_AUTHORIZED_RELEASE")
        digest = None
        if not findings:
            digest = canonical_digest(
                {
                    "change_id": manifest.get("change_id"),
                    "component_commits": supplied_commits,
                    "contract_revision": self.contract_revision,
                    "contract_digest": self.contract_digest,
                    "evidence_ids": sorted(required_evidence),
                    "system_results": dict(system_results),
                }
            )
        return IntegrationDecision(
            state="READY_FOR_INTEGRATION_REVIEW" if not findings else "BLOCKED",
            findings=tuple(findings),
            component_commits=supplied_commits,
            contract_revision=self.contract_revision,
            revision_set_digest=digest,
        )

    def authorize_release(self, *, authenticated_identity: str) -> None:
        if authenticated_identity in {self.coordinator_identity, self.integration_verifier}:
            raise PermissionError("SEPARATE_RELEASE_AUTHORITY_REQUIRED")
        raise PermissionError("RELEASE_AUTHORITY_OUTSIDE_COURSE_FIXTURE")

    def snapshot(self) -> dict[str, object]:
        return {
            "contract_revision": self.contract_revision,
            "contract_digest": self.contract_digest,
            "work_units": {
                key: {
                    **asdict(value),
                    "state": value.state.value,
                }
                for key, value in self.work_units.items()
            },
            "leases": {
                key: {
                    **asdict(value),
                    "issued_at": value.issued_at.isoformat(),
                    "expires_at": value.expires_at.isoformat(),
                }
                for key, value in self.leases.items()
            },
            "operations": copy.deepcopy(self.operations),
            "events": copy.deepcopy(self.events),
        }

    def restore_snapshot(self, snapshot: Mapping[str, object]) -> None:
        if int(snapshot["contract_revision"]) != self.contract_revision:
            raise ValueError("SNAPSHOT_CONTRACT_REVISION_MISMATCH")
        if snapshot["contract_digest"] != self.contract_digest:
            raise ValueError("SNAPSHOT_CONTRACT_DIGEST_MISMATCH")
        restored_units: dict[str, WorkUnit] = {}
        for key, value in dict(snapshot["work_units"]).items():
            item = dict(value)
            item["state"] = WorkState(item["state"])
            for field_name in ("dependencies", "allowed_paths", "evidence_ids"):
                item[field_name] = tuple(item[field_name])
            restored_units[key] = WorkUnit(**item)
        self.work_units = restored_units
        restored_leases: dict[str, Lease] = {}
        for key, value in dict(snapshot["leases"]).items():
            item = dict(value)
            item["permissions"] = tuple(item["permissions"])
            item["issued_at"] = datetime.fromisoformat(item["issued_at"])
            item["expires_at"] = datetime.fromisoformat(item["expires_at"])
            restored_leases[key] = Lease(**item)
        self.leases = restored_leases
        self.operations = copy.deepcopy(dict(snapshot["operations"]))
        self.events = copy.deepcopy(list(snapshot["events"]))
