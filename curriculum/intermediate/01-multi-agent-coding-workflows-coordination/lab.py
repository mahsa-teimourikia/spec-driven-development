"""Deterministic Course 11 lab: governed multi-agent coding coordination.

The fixture models a control plane around fictional coding-agent work. It does
not start agents, grant credentials, approve architecture, merge code, or prove
production readiness.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

LESSON_ROOT = Path(__file__).resolve().parent
SCENARIO_ROOT = LESSON_ROOT / "northstar-multi-agent-delivery"
REFERENCE_ROOT = SCENARIO_ROOT / "reference"
CANDIDATE_ROOT = SCENARIO_ROOT / "candidate"
POLICY_PATH = SCENARIO_ROOT / "coordination-policy.json"
REFERENCE_WORKFLOW_PATH = REFERENCE_ROOT / "workflow.json"
CANDIDATE_WORKFLOW_PATH = CANDIDATE_ROOT / "workflow.json"
EVENT_LOG_PATH = REFERENCE_ROOT / "event-log.json"
HANDOFF_PATH = REFERENCE_ROOT / "handoff.json"
INTEGRATION_PATH = REFERENCE_ROOT / "integration-manifest.json"
RECOVERY_PATH = REFERENCE_ROOT / "recovery-record.json"
REVIEW_PACKAGE_PATH = REFERENCE_ROOT / "review-package.json"
EVALUATION_PATH = SCENARIO_ROOT / "evaluation-cases.json"


class Severity(str, Enum):
    BLOCKING = "blocking"
    REVIEW = "review"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    subject_id: str
    message: str
    owner: str
    repair: str


ALLOWED_EVENTS = {
    "WORK_UNIT_READY",
    "WORK_UNIT_STARTED",
    "WORK_UNIT_COMPLETED",
    "WORK_UNIT_VERIFIED",
    "CONTRACT_CHANGE_REQUESTED",
    "CONTRACT_CHANGE_APPROVED",
    "DISCOVERY_PUBLISHED",
    "CONTEXT_INVALIDATED",
    "INTEGRATION_FAILED",
    "WORK_UNIT_PAUSED",
    "WORK_UNIT_CANCELLED",
}
AUTHORITATIVE_EVENTS = {"WORK_UNIT_VERIFIED", "CONTRACT_CHANGE_APPROVED"}
TERMINAL_DENIALS = {"policy_denied", "authorization_denied", "scope_denied"}
CONTROL_PLANE_CLAIM = (
    "training_control_plane_only_not_agent_identity_permission_grant_merge_approval_or_release_authority"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_bundle(*, candidate: bool = False) -> dict[str, Any]:
    return {
        "policy": load_json(POLICY_PATH),
        "workflow": load_json(CANDIDATE_WORKFLOW_PATH if candidate else REFERENCE_WORKFLOW_PATH),
        "event_log": {"events": []} if candidate else load_json(EVENT_LOG_PATH),
        "handoff": {} if candidate else load_json(HANDOFF_PATH),
        "integration": {} if candidate else load_json(INTEGRATION_PATH),
        "recovery": {} if candidate else load_json(RECOVERY_PATH),
        "review_package": {} if candidate else load_json(REVIEW_PACKAGE_PATH),
    }


def _finding(
    code: str,
    severity: Severity,
    subject_id: str,
    message: str,
    owner: str,
    repair: str,
) -> Finding:
    return Finding(code, severity, subject_id, message, owner, repair)


def _path_overlaps(left: str, right: str) -> bool:
    left = left.rstrip("*/")
    right = right.rstrip("*/")
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def dependency_graph(workflow: dict[str, Any]) -> dict[str, set[str]]:
    return {
        str(item.get("id")): {str(value) for value in item.get("depends_on", [])}
        for item in workflow.get("work_units", [])
    }


def topological_waves(workflow: dict[str, Any]) -> dict[str, Any]:
    graph = dependency_graph(workflow)
    remaining = {node: set(dependencies) for node, dependencies in graph.items()}
    completed: set[str] = set()
    waves: list[list[str]] = []
    while remaining:
        ready = sorted(node for node, dependencies in remaining.items() if dependencies <= completed)
        if not ready:
            return {"acyclic": False, "waves": waves, "cycle_nodes": sorted(remaining)}
        waves.append(ready)
        completed.update(ready)
        for node in ready:
            del remaining[node]
    return {"acyclic": True, "waves": waves, "cycle_nodes": []}


def validate_strategy(workflow: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    workflow_id = str(workflow.get("id", "workflow"))
    decision = workflow.get("multi_agent_decision", {})
    if workflow.get("mode") == "multi_agent" and (
        not decision.get("why_multiple_agents")
        or not decision.get("single_agent_baseline")
        or not decision.get("coordination_costs")
    ):
        findings.append(_finding(
            "MULTI_AGENT_JUSTIFICATION_MISSING", Severity.REVIEW, workflow_id,
            "Multi-agent execution is selected without a single-agent baseline and explicit coordination trade-offs.",
            "Planning owner", "Record separability, expected useful concurrency, coordination costs, and the simpler baseline.",
        ))
    budgets = workflow.get("budgets", {})
    required_budgets = {"max_parallel", "max_handoffs", "max_replans", "max_delegation_depth"}
    if not required_budgets <= set(budgets) or any(int(budgets.get(item, 0)) < 1 for item in required_budgets):
        findings.append(_finding(
            "COORDINATION_BUDGETS_MISSING", Severity.BLOCKING, workflow_id,
            "Parallelism, handoffs, replans, or delegation depth are unbounded.",
            "Orchestration owner", "Define positive explicit limits and terminal behavior when a budget is exhausted.",
        ))
    flow_limits = {"max_units_waiting_for_review", "max_shared_contract_changes_in_flight", "max_execution_attempts"}
    if not flow_limits <= set(budgets) or any(int(budgets.get(item, 0)) < 1 for item in flow_limits):
        findings.append(_finding(
            "FLOW_LIMITS_MISSING", Severity.REVIEW, workflow_id,
            "The plan bounds agents but not review queues, contract churn, or retry work in progress.",
            "Delivery-system owner", "Set evidence-based WIP limits and tune them with operating data.",
        ))
    scheduling = workflow.get("scheduling_policy", {})
    if scheduling.get("mode") != "pull" or not scheduling.get("dispatch_requires"):
        findings.append(_finding(
            "PUSH_SCHEDULING_UNBOUNDED", Severity.REVIEW, workflow_id,
            "Ready work is pushed to agents without checking downstream and human review capacity.",
            "Orchestration owner", "Pull work only when dependency, implementation, integration, and typed-review capacity exists.",
        ))
    schedule = topological_waves(workflow)
    if not schedule["acyclic"]:
        findings.append(_finding(
            "WORK_GRAPH_CYCLE", Severity.BLOCKING, workflow_id,
            "The work graph contains a dependency cycle.",
            "Planning owner", "Repair the dependency graph before assignments are issued.",
        ))
        return findings
    declared_waves = {str(item.get("id")): int(item.get("wave", 0)) for item in workflow.get("work_units", [])}
    graph = dependency_graph(workflow)
    for unit_id, dependencies in graph.items():
        if declared_waves.get(unit_id, 0) < 1:
            findings.append(_finding(
                "WORK_UNIT_WAVE_MISSING", Severity.BLOCKING, unit_id,
                "A work unit has no positive execution wave.",
                "Orchestration owner", "Assign a wave consistent with verified dependencies.",
            ))
        for dependency in dependencies:
            if dependency not in declared_waves:
                findings.append(_finding(
                    "WORK_UNIT_DEPENDENCY_UNKNOWN", Severity.BLOCKING, unit_id,
                    f"Dependency {dependency} does not exist.",
                    "Planning owner", "Repair the dependency reference.",
                ))
            elif declared_waves[dependency] >= declared_waves.get(unit_id, 0):
                findings.append(_finding(
                    "DEPENDENCY_WAVE_VIOLATION", Severity.BLOCKING, unit_id,
                    "A consumer is scheduled no later than its producer.",
                    "Orchestration owner", "Start the consumer only after the producer output is verified.",
                ))
    for unit in workflow.get("work_units", []):
        if not unit.get("required_review_queues"):
            findings.append(_finding(
                "REVIEW_ROUTING_MISSING", Severity.REVIEW, str(unit.get("id")),
                "A work unit has no typed reviewer-capacity requirement.",
                "Delivery-system owner", "Route normal and specialist review from scope, contracts, risk, and protected decisions.",
            ))
    observed_parallel = max(Counter(declared_waves.values()).values(), default=0)
    if observed_parallel > int(budgets.get("max_parallel", 0)):
        findings.append(_finding(
            "PARALLELISM_BUDGET_EXCEEDED", Severity.BLOCKING, workflow_id,
            f"A wave schedules {observed_parallel} units beyond the parallelism budget.",
            "Orchestration owner", "Reduce work in process or authorize a new bounded plan.",
        ))
    return findings


def validate_assignments(workflow: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    units = {item.get("id"): item for item in workflow.get("work_units", [])}
    identities = {item.get("id"): item for item in workflow.get("identity_registry", [])}
    assignments = workflow.get("assignments", [])
    assignment_counts = Counter(item.get("work_unit_id") for item in assignments)
    for unit_id, count in assignment_counts.items():
        if count != 1:
            findings.append(_finding(
                "DUPLICATE_WORK_UNIT_ASSIGNMENT", Severity.BLOCKING, str(unit_id),
                "A work unit has multiple assignment identities.",
                "Orchestration owner", "Use one stable assignment ID and reconcile duplicate delivery idempotently.",
            ))
    for unit_id in units:
        if assignment_counts.get(unit_id, 0) == 0:
            findings.append(_finding(
                "WORK_UNIT_UNASSIGNED", Severity.BLOCKING, str(unit_id),
                "A work unit has no accountable execution assignment.",
                "Orchestration owner", "Create one work-unit-bound assignment before dispatch.",
            ))
    for assignment in assignments:
        assignment_id = str(assignment.get("id", "assignment"))
        unit_id = assignment.get("work_unit_id")
        identity = identities.get(assignment.get("agent_identity"))
        unit = units.get(unit_id, {})
        if not identity or identity.get("kind") != "workload_identity":
            findings.append(_finding(
                "AGENT_IDENTITY_UNVERIFIED", Severity.BLOCKING, assignment_id,
                "The assignment relies on a role label rather than a registered workload identity.",
                "Identity control-plane owner", "Bind the assignment to an authenticated, short-lived execution identity.",
            ))
        permissions = assignment.get("permissions", {})
        if (
            permissions.get("lifecycle") != "assignment_bound_temporary"
            or permissions.get("self_provisioned") is not False
            or set(permissions.get("write_paths", [])) != set(unit.get("writable_paths", []))
        ):
            findings.append(_finding(
                "ASSIGNMENT_PERMISSION_INVALID", Severity.BLOCKING, assignment_id,
                "Assignment permissions are permanent, self-provisioned, or wider than the work unit.",
                "Execution control-plane owner", "Use external provisioning with exact paths, expiry, and revocation.",
            ))
        lease = assignment.get("lease", {})
        if not lease.get("id") or not lease.get("expires_at") or not lease.get("heartbeat_policy"):
            findings.append(_finding(
                "EXECUTION_LEASE_INCOMPLETE", Severity.BLOCKING, assignment_id,
                "The assignment cannot be safely recovered because its lease lifecycle is incomplete.",
                "Orchestration owner", "Add a lease ID, expiry, heartbeat policy, and recovery transition.",
            ))
    return findings


def validate_branches_locks_and_context(workflow: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    units = workflow.get("work_units", [])
    assignments = {item.get("work_unit_id"): item for item in workflow.get("assignments", [])}
    branch_counts = Counter(item.get("branch") for item in units)
    for branch, count in branch_counts.items():
        if not branch or count > 1:
            findings.append(_finding(
                "SHARED_EXECUTION_BRANCH", Severity.BLOCKING, str(branch or "missing-branch"),
                "Multiple autonomous work units share a branch or a branch is absent.",
                "Repository owner", "Use one branch/worktree per work unit and make dependency topology explicit.",
            ))
    locks = workflow.get("locks", [])
    lock_by_unit = defaultdict(list)
    for lock in locks:
        lock_by_unit[lock.get("work_unit_id")].append(lock)
        assignment = assignments.get(lock.get("work_unit_id"), {})
        if (
            lock.get("assignment_id") != assignment.get("id")
            or not lock.get("lease_id")
            or lock.get("state") not in {"RESERVED", "ACTIVE", "RELEASED"}
        ):
            findings.append(_finding(
                "WRITE_LOCK_LIFECYCLE_INVALID", Severity.BLOCKING, str(lock.get("id", "lock")),
                "A logical write lock is not bound to the assignment lease and governed lifecycle.",
                "Orchestration owner", "Bind lock owner, work unit, assignment, lease, state, and recovery behavior.",
            ))
    for unit in units:
        covered = {path for lock in lock_by_unit.get(unit.get("id"), []) for path in lock.get("paths", [])}
        if set(unit.get("writable_paths", [])) - covered:
            findings.append(_finding(
                "WRITE_LOCK_MISSING", Severity.BLOCKING, str(unit.get("id")),
                "A writable path has no work-unit-bound logical lock.",
                "Orchestration owner", "Reserve the minimal write surface before dispatch.",
            ))
    for index, left in enumerate(units):
        for right in units[index + 1:]:
            if left.get("wave") != right.get("wave"):
                continue
            overlap = any(
                _path_overlaps(a, b)
                for a in left.get("writable_paths", [])
                for b in right.get("writable_paths", [])
            )
            if overlap:
                findings.append(_finding(
                    "PARALLEL_WRITE_COLLISION", Severity.BLOCKING,
                    f"{left.get('id')}|{right.get('id')}",
                    "Work units in the same wave have overlapping write ownership.",
                    "Planning owner", "Partition the paths or sequence the work through a stable contract.",
                ))
    shared_by_wave: dict[int, dict[str, str]] = {}
    for unit in units:
        wave = int(unit.get("wave", 0))
        shared = unit.get("context_manifest", {}).get("shared", {})
        if wave in shared_by_wave and shared != shared_by_wave[wave]:
            findings.append(_finding(
                "SHARED_CONTEXT_DIVERGENCE", Severity.BLOCKING, str(unit.get("id")),
                "Work units in one wave pin different shared requirements, ADRs, or contracts.",
                "Context owner", "Align shared source revisions while preserving legitimate local context.",
            ))
        shared_by_wave.setdefault(wave, shared)
        if not unit.get("pinned_base_revision") or not unit.get("context_digest"):
            findings.append(_finding(
                "EXECUTION_CONTEXT_UNPINNED", Severity.BLOCKING, str(unit.get("id")),
                "The work unit lacks a pinned repository base or effective context digest.",
                "Context owner", "Bind the wave to exact repository, requirement, ADR, and contract revisions.",
            ))
    return findings


def validate_delegation_and_independence(workflow: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    assignments = {item.get("id"): item for item in workflow.get("assignments", [])}
    max_depth = int(workflow.get("budgets", {}).get("max_delegation_depth", 0))
    for delegation in workflow.get("delegations", []):
        parent = assignments.get(delegation.get("parent_assignment_id"), {})
        delegation_id = str(delegation.get("id", "delegation"))
        child = set(delegation.get("child_permissions", {}).get("write_paths", []))
        parent_write = set(parent.get("permissions", {}).get("write_paths", []))
        if not child <= parent_write or delegation.get("depth", 0) > max_depth:
            findings.append(_finding(
                "DELEGATION_AUTHORITY_AMPLIFIED", Severity.BLOCKING, delegation_id,
                "A child receives authority outside its parent or beyond allowed depth.",
                "Orchestration owner", "Attenuate child capabilities and enforce child/depth budgets.",
            ))
        if delegation.get("allowed_role") == "read_only_researcher" and child:
            findings.append(_finding(
                "READ_ONLY_DELEGATE_CAN_WRITE", Severity.BLOCKING, delegation_id,
                "A delegated research role receives write authority.",
                "Execution control-plane owner", "Remove write capability from the research delegation.",
            ))
    verification = workflow.get("verification", {})
    if (
        verification.get("independent") is not True
        or verification.get("spawned_by_implementer") is not False
        or verification.get("receives_implementer_reasoning") is not False
    ):
        findings.append(_finding(
            "VERIFICATION_INDEPENDENCE_WEAK", Severity.BLOCKING, "verification",
            "Verification inherits implementation control or persuasive reasoning.",
            "Quality owner", "Dispatch verification independently with requirements, revisions, interfaces, and evidence obligations.",
        ))
    integration_authority = workflow.get("integration_authority", {})
    forbidden = {
        "rewrite_component_behavior", "change_shared_contract", "weaken_acceptance_criteria",
        "change_authorization_semantics", "approve_architecture_change",
    }
    if (
        forbidden & set(integration_authority.get("may_decide", []))
        or not forbidden <= set(integration_authority.get("may_not_decide", []))
    ):
        findings.append(_finding(
            "INTEGRATION_AUTHORITY_TOO_BROAD", Severity.BLOCKING, "integration-authority",
            "The integration role can rewrite owned components or decide protected semantics.",
            "Integration owner", "Permit diagnosis and proposals while routing repairs to the owning work unit or decision owner.",
        ))
    return findings


def validate_events(workflow: dict[str, Any], event_log: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    known_units = {item.get("id") for item in workflow.get("work_units", [])}
    identities = {item.get("id") for item in workflow.get("identity_registry", [])}
    approvals = {item.get("id") for item in workflow.get("approval_artifacts", [])}
    seen: set[str] = set()
    for event in event_log.get("events", []):
        event_id = str(event.get("id", "event"))
        if event_id in seen:
            findings.append(_finding(
                "COORDINATION_EVENT_DUPLICATE", Severity.BLOCKING, event_id,
                "A coordination event ID is replayed as a new transition.",
                "Orchestration owner", "Deduplicate by stable event ID and make handlers idempotent.",
            ))
        seen.add(event_id)
        event_type = event.get("type")
        if event_type not in ALLOWED_EVENTS:
            findings.append(_finding(
                "COORDINATION_EVENT_UNKNOWN", Severity.REVIEW, event_id,
                "An event has no governed coordination meaning.",
                "Orchestration owner", "Use the event taxonomy or add an owned transition contract.",
            ))
        if event.get("subject_work_unit_id") not in known_units:
            findings.append(_finding(
                "COORDINATION_EVENT_SUBJECT_UNKNOWN", Severity.BLOCKING, event_id,
                "The event targets an unknown work unit.",
                "Orchestration owner", "Bind the event to a current work-unit registry entry.",
            ))
        if event.get("producer_identity") not in identities:
            findings.append(_finding(
                "COORDINATION_EVENT_PRODUCER_UNVERIFIED", Severity.BLOCKING, event_id,
                "The event producer is a role label or unknown identity.",
                "Identity control-plane owner", "Authenticate the event producer and record its execution identity.",
            ))
        if event_type in AUTHORITATIVE_EVENTS and event.get("authority_artifact_id") not in approvals:
            findings.append(_finding(
                "COORDINATION_EVENT_AUTHORITY_UNPROVEN", Severity.BLOCKING, event_id,
                "An authoritative label is not backed by an authorized verification or approval artifact.",
                "Control-plane owner", "Validate the external artifact before applying the state transition.",
            ))
        if not event.get("repository_revision") or not event.get("timestamp"):
            findings.append(_finding(
                "COORDINATION_EVENT_PROVENANCE_MISSING", Severity.REVIEW, event_id,
                "The event cannot be replayed against an exact repository state and time.",
                "Orchestration owner", "Record immutable subject revision, producer, timestamp, and related artifact.",
            ))
    return findings


def validate_integration(workflow: dict[str, Any], integration: dict[str, Any]) -> list[Finding]:
    if not integration:
        return []
    findings: list[Finding] = []
    manifest_id = str(integration.get("id", "integration"))
    authority = integration.get("agent_authority", {})
    forbidden = {
        "rewrite_component_behavior", "change_shared_contract", "weaken_acceptance_criteria",
        "change_authorization_semantics", "approve_architecture_change",
    }
    if forbidden & set(authority.get("may_decide", [])) or not forbidden <= set(authority.get("may_not_decide", [])):
        findings.append(_finding(
            "INTEGRATION_AUTHORITY_TOO_BROAD", Severity.BLOCKING, manifest_id,
            "The integration agent can rewrite independently owned semantics or approve consequential changes.",
            "Integration owner", "Limit it to assembly, diagnostics, fixtures, evidence, and routed proposals.",
        ))
    expected = {item.get("id"): item.get("expected_revision") for item in workflow.get("component_registry", [])}
    components = integration.get("components", {})
    for component_id, revision in expected.items():
        component = components.get(component_id, {})
        if component.get("revision") != revision or not component.get("evidence_ids"):
            findings.append(_finding(
                "INTEGRATION_MANIFEST_STALE", Severity.BLOCKING, component_id,
                "Integration evidence is absent or bound to a stale component revision.",
                "Integration owner", "Reassemble exact component revisions and regenerate integration evidence.",
            ))
    if not integration.get("cross_component_invariants") or not integration.get("evidence", {}).get("revision_digest"):
        findings.append(_finding(
            "INTEGRATION_EVIDENCE_INCOMPLETE", Severity.BLOCKING, manifest_id,
            "The manifest lacks cross-component invariants or revision-bound evidence.",
            "System evidence owner", "Test boundary behavior and bind evidence to the full component set.",
        ))
    return findings


def validate_handoff(workflow: dict[str, Any], handoff: dict[str, Any]) -> list[Finding]:
    if not handoff:
        return []
    required = {"id", "from_work_unit", "to_work_units", "outputs", "evidence_ids", "unresolved", "boundary"}
    if not required <= set(handoff) or not handoff.get("evidence_ids"):
        return [_finding(
            "HANDOFF_PACKAGE_INCOMPLETE", Severity.BLOCKING, str(handoff.get("id", "handoff")),
            "The handoff omits revisioned outputs, evidence, unresolved items, or the downstream boundary.",
            "Producing work-unit owner", "Publish the minimum precise artifact package needed for safe consumption.",
        )]
    contracts = {item.get("id"): item for item in workflow.get("contract_registry", [])}
    for contract_id, output in handoff.get("outputs", {}).items():
        if contracts.get(contract_id, {}).get("revision") != output.get("revision"):
            return [_finding(
                "HANDOFF_CONTRACT_REVISION_STALE", Severity.BLOCKING, str(handoff.get("id")),
                "The handoff names a contract revision different from the coordination registry.",
                "Contract owner", "Regenerate the handoff against the approved contract revision.",
            )]
    return []


def validate_recovery(workflow: dict[str, Any], recovery: dict[str, Any]) -> list[Finding]:
    if not recovery:
        return []
    findings: list[Finding] = []
    recovery_id = str(recovery.get("id", "recovery"))
    required = {
        "work_unit_id", "assignment_id", "last_commit", "completed", "remaining",
        "discoveries", "blockers", "evidence", "context", "inspection", "resume_decision",
    }
    if not required <= set(recovery):
        findings.append(_finding(
            "RECOVERY_ARTIFACT_INCOMPLETE", Severity.BLOCKING, recovery_id,
            "Recovery state cannot reconstruct the partial engineering attempt.",
            "Orchestration owner", "Record checkpoint, remaining work, discoveries, blockers, evidence, and pinned context.",
        ))
        return findings
    if recovery.get("inspection", {}).get("partial_work_treated_as_trusted") is not False or not recovery.get("inspection", {}).get("checks_run"):
        findings.append(_finding(
            "RECOVERY_BLIND_RESUME", Severity.BLOCKING, recovery_id,
            "A replacement agent resumes partial work without independent inspection and current checks.",
            "Recovery owner", "Inspect, compare scope, validate revisions, run checks, then continue, repair, discard, or replan.",
        ))
    current_contracts = {item.get("id"): item.get("revision") for item in workflow.get("contract_registry", [])}
    recovered_contracts = recovery.get("context", {}).get("contracts", {})
    if any(current_contracts.get(key) != value for key, value in recovered_contracts.items()):
        findings.append(_finding(
            "RECOVERY_CONTEXT_STALE", Severity.BLOCKING, recovery_id,
            "The recovered attempt is pinned to an obsolete shared contract.",
            "Planning owner", "Replan or revalidate before continuing from the checkpoint.",
        ))
    if recovery.get("private_reasoning"):
        findings.append(_finding(
            "RECOVERY_PRIVATE_REASONING_PERSISTED", Severity.REVIEW, recovery_id,
            "Hidden reasoning is treated as required durable project state.",
            "Orchestration owner", "Persist observable engineering state, decisions, discoveries, and evidence instead.",
        ))
    return findings


def validate_review_package(workflow: dict[str, Any], package: dict[str, Any]) -> list[Finding]:
    if not package:
        return []
    required = {
        "work_unit_id", "requirements", "changed_paths", "contracts", "evidence_ids",
        "deviations", "unresolved", "base_revision", "specification_digest",
    }
    if not required <= set(package):
        return [_finding(
            "REVIEW_PACKAGE_INCOMPLETE", Severity.REVIEW, str(package.get("id", "review-package")),
            "The reviewer lacks scope, provenance, contract, evidence, or deviation context.",
            "Implementation owner", "Generate the review package from durable work-unit and completion artifacts.",
        )]
    unit = next((item for item in workflow.get("work_units", []) if item.get("id") == package.get("work_unit_id")), {})
    if set(package.get("changed_paths", [])) - set(unit.get("writable_paths", [])):
        return [_finding(
            "REVIEW_PACKAGE_SCOPE_VIOLATION", Severity.BLOCKING, str(package.get("id")),
            "The declared diff exceeds work-unit write authority.",
            "Repository owner", "Stop and route a scope-expansion request before review continues.",
        )]
    return []


def review_workflow(bundle: dict[str, Any]) -> dict[str, Any]:
    workflow = bundle["workflow"]
    findings = (
        validate_strategy(workflow)
        + validate_assignments(workflow)
        + validate_branches_locks_and_context(workflow)
        + validate_delegation_and_independence(workflow)
        + validate_events(workflow, bundle.get("event_log", {"events": []}))
        + validate_integration(workflow, bundle.get("integration", {}))
        + validate_handoff(workflow, bundle.get("handoff", {}))
        + validate_recovery(workflow, bundle.get("recovery", {}))
        + validate_review_package(workflow, bundle.get("review_package", {}))
    )
    return {
        "claim": CONTROL_PLANE_CLAIM,
        "findings": [asdict(item) for item in findings],
        "counts": dict(Counter(item.severity.value for item in findings)),
        "schedule": topological_waves(workflow),
        "workflow_digest": stable_digest(workflow),
    }


def coordination_decision(report: dict[str, Any]) -> dict[str, Any]:
    blocking = report.get("counts", {}).get("blocking", 0)
    review = report.get("counts", {}).get("review", 0)
    if blocking:
        state = "COORDINATION_BLOCKED"
    elif review:
        state = "COORDINATION_REVIEW_REQUIRED"
    else:
        state = "COORDINATION_READY"
    return {
        "state": state,
        "ready_for_bounded_dispatch": state == "COORDINATION_READY",
        "boundary": "Readiness does not provision identities, grant permissions, approve merge, or authorize release.",
    }


def ready_work_units(workflow: dict[str, Any], states: dict[str, str]) -> list[str]:
    graph = dependency_graph(workflow)
    return sorted(
        unit_id
        for unit_id, dependencies in graph.items()
        if states.get(unit_id) in {"PROPOSED", "READY"}
        and all(states.get(dependency) == "VERIFIED" for dependency in dependencies)
    )


def pull_dispatch(
    workflow: dict[str, Any],
    states: dict[str, str],
    *,
    active_count: int,
    review_queue_depths: dict[str, int],
    review_capacities: dict[str, int],
) -> dict[str, Any]:
    """Select bounded ready work only when implementation and reviewer capacity exist."""
    budget = int(workflow.get("budgets", {}).get("max_parallel", 0))
    available_slots = max(0, budget - active_count)
    units = {item["id"]: item for item in workflow.get("work_units", [])}
    ready = ready_work_units(workflow, states)
    dispatchable: list[str] = []
    waiting: dict[str, list[str]] = {}
    for unit_id in ready:
        queues = units[unit_id].get("required_review_queues", [])
        blocked = [
            queue for queue in queues
            if review_queue_depths.get(queue, 0) >= review_capacities.get(queue, 0)
        ]
        if blocked:
            waiting[unit_id] = blocked
        elif len(dispatchable) < available_slots:
            dispatchable.append(unit_id)
    return {
        "dispatchable": dispatchable,
        "waiting_for_review_capacity": waiting,
        "available_implementation_slots": available_slots,
        "claim": "fixture pull decision using explicit capacities, not an AI priority score",
    }


def classify_execution_failure(failure_class: str, attempt: int, policy: dict[str, Any]) -> dict[str, Any]:
    retry_policy = policy.get("retry_policy", {})
    if failure_class in retry_policy.get("not_retryable", []) or failure_class in TERMINAL_DENIALS:
        return {"action": "STOP_AND_ROUTE", "reason": "non_retryable_failure"}
    if failure_class in retry_policy.get("refresh_then_retry", []):
        return {"action": "REFRESH_REPLAN", "reason": "context_must_change_before_retry"}
    if failure_class in retry_policy.get("retryable", []) and attempt < int(retry_policy.get("attempt_limit", 0)):
        return {"action": "BOUNDED_RETRY", "reason": "transient_with_budget"}
    return {"action": "ESCALATE", "reason": "retry_budget_exhausted_or_unknown_failure"}


def analyze_execution_history(history: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    limit = int(policy.get("retry_policy", {}).get("attempt_limit", 0))
    repeated = Counter(item.get("failure_class") for item in history if item.get("failure_class"))
    changes = [item.get("semantic_change") for item in history if item.get("semantic_change")]
    oscillation = len(changes) >= 3 and changes[-3:] in (["A_TO_B", "B_TO_A", "A_TO_B"], ["B_TO_A", "A_TO_B", "B_TO_A"])
    return {
        "attempts": len(history),
        "budget_exhausted": len(history) >= limit,
        "repeated_failure_classes": sorted(key for key, count in repeated.items() if count > 1),
        "repair_oscillation": oscillation,
        "action": "SYSTEMIC_PROBLEM_SUSPECTED" if oscillation or any(count > 1 for count in repeated.values()) else "CONTINUE_BOUNDED_PROCESS",
    }


def contract_change_blast_radius(
    workflow: dict[str, Any],
    contract_id: str,
    states: dict[str, str],
    evidence_by_unit: dict[str, list[str]],
) -> dict[str, Any]:
    registry = next(item for item in workflow.get("contract_registry", []) if item.get("id") == contract_id)
    producer = registry.get("producer")
    graph = dependency_graph(workflow)
    affected: set[str] = set()
    queue = deque([producer])
    while queue:
        current = queue.popleft()
        for unit_id, dependencies in graph.items():
            if current in dependencies and unit_id not in affected:
                affected.add(unit_id)
                queue.append(unit_id)
    return {
        "change": f"{contract_id}@{registry.get('revision')} -> proposed_revision",
        "active": sorted(item for item in affected if states.get(item) in {"ASSIGNED", "IN_PROGRESS"}),
        "completed": sorted(item for item in affected if states.get(item) in {"COMPLETED", "VERIFIED", "INTEGRATED"}),
        "evidence_invalidated": sorted({evidence for unit in affected for evidence in evidence_by_unit.get(unit, [])}),
        "action": "pause_active_consumers_and_revalidate_completed_consumers",
        "approval_boundary": "impact analysis is not contract approval",
    }


def process_assignment_delivery(state: dict[str, Any], assignment: dict[str, Any]) -> dict[str, Any]:
    """Idempotently accept duplicate delivery of one stable logical assignment."""
    result = copy.deepcopy(state)
    assignment_id = assignment["id"]
    existing = result.setdefault("assignments", {}).get(assignment_id)
    if existing:
        return {"state": result, "outcome": "duplicate_delivery_reconciled", "started": False}
    result["assignments"][assignment_id] = copy.deepcopy(assignment)
    return {"state": result, "outcome": "assignment_registered", "started": True}


def recover_expired_lease(assignment: dict[str, Any], *, now: str) -> dict[str, Any]:
    lease = assignment.get("lease", {})
    expired = bool(lease.get("expires_at") and lease["expires_at"] <= now)
    return {
        "assignment_id": assignment.get("id"),
        "expired": expired,
        "next_state": "RECOVERY_REQUIRED" if expired else assignment.get("state", "PLANNED"),
        "may_reassign": expired and lease.get("recovery_policy") == "inspect_before_reassign",
    }


def invalidate_integration_evidence(integration: dict[str, Any], changed_component: str, new_revision: str) -> dict[str, Any]:
    result = copy.deepcopy(integration)
    current = result.get("components", {}).get(changed_component, {}).get("revision")
    if current == new_revision:
        return {"state": "current", "stale_evidence_ids": []}
    return {
        "state": "REVALIDATION_REQUIRED",
        "changed_component": changed_component,
        "from_revision": current,
        "to_revision": new_revision,
        "stale_evidence_ids": list(result.get("evidence", {}).get("evidence_ids", [])),
    }


def compare_execution_models() -> dict[str, Any]:
    """Transparent fixture observations, not a general productivity benchmark."""
    models = [
        {"name": "single_agent", "lead_time_units": 22, "total_work_units": 22, "review_units": 10, "integration_failures": 0, "rework_units": 1, "forbidden_attempts": 0},
        {"name": "unsafe_parallel", "lead_time_units": 11, "total_work_units": 30, "review_units": 21, "integration_failures": 3, "rework_units": 9, "forbidden_attempts": 2},
        {"name": "governed_multi_agent", "lead_time_units": 15, "total_work_units": 25, "review_units": 12, "integration_failures": 1, "rework_units": 2, "forbidden_attempts": 0},
    ]
    return {
        "claim": "synthetic_fixture_comparison_not_productivity_benchmark",
        "models": models,
        "interpretation": "The fastest fixture path is not automatically best; review load, rework, integration health, and forbidden attempts remain visible.",
    }


def _evaluation_findings(case: dict[str, Any]) -> list[Finding]:
    bundle = load_bundle()
    target = case["target"]
    mutation = case.get("mutation", {})
    if target == "workflow":
        workflow = copy.deepcopy(bundle["workflow"])
        section = mutation.get("section")
        if section == "root":
            workflow.update(mutation.get("changes", {}))
        elif section == "work_unit":
            item = next(value for value in workflow["work_units"] if value["id"] == mutation["id"])
            item.update(mutation.get("changes", {}))
        elif section == "assignment":
            item = next(value for value in workflow["assignments"] if value["id"] == mutation["id"])
            item.update(mutation.get("changes", {}))
        elif section == "append_assignment":
            workflow["assignments"].append(mutation["value"])
        elif section == "verification":
            workflow["verification"].update(mutation.get("changes", {}))
        elif section == "delegation":
            workflow["delegations"][0].update(mutation.get("changes", {}))
        elif section == "lock":
            workflow["locks"][0].update(mutation.get("changes", {}))
        return (
            validate_strategy(workflow)
            + validate_assignments(workflow)
            + validate_branches_locks_and_context(workflow)
            + validate_delegation_and_independence(workflow)
        )
    if target == "events":
        log = copy.deepcopy(bundle["event_log"])
        if mutation.get("append"):
            log["events"].append(mutation["append"])
        if mutation.get("duplicate_first"):
            log["events"].append(copy.deepcopy(log["events"][0]))
        return validate_events(bundle["workflow"], log)
    if target == "integration":
        integration = copy.deepcopy(bundle["integration"])
        integration.update(mutation.get("changes", {}))
        if mutation.get("component"):
            integration["components"][mutation["component"]].update(mutation.get("component_changes", {}))
        return validate_integration(bundle["workflow"], integration)
    if target == "handoff":
        handoff = copy.deepcopy(bundle["handoff"])
        handoff.update(mutation.get("changes", {}))
        return validate_handoff(bundle["workflow"], handoff)
    if target == "recovery":
        recovery = copy.deepcopy(bundle["recovery"])
        recovery.update(mutation.get("changes", {}))
        if mutation.get("inspection_changes"):
            recovery["inspection"].update(mutation["inspection_changes"])
        if mutation.get("context_changes"):
            recovery["context"].update(mutation["context_changes"])
        return validate_recovery(bundle["workflow"], recovery)
    if target == "review_package":
        package = copy.deepcopy(bundle["review_package"])
        package.update(mutation.get("changes", {}))
        return validate_review_package(bundle["workflow"], package)
    raise ValueError(f"unknown evaluation target: {target}")


def evaluate_coordination_rules(cases: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    population = list(cases or load_json(EVALUATION_PATH)["cases"])
    results: list[dict[str, Any]] = []
    true_positive = false_positive = false_negative = 0
    for case in population:
        expected = set(case.get("expected_codes", []))
        predicted = {item.code for item in _evaluation_findings(case)}
        true_positive += len(expected & predicted)
        false_positive += len(predicted - expected)
        false_negative += len(expected - predicted)
        results.append({
            "id": case["id"],
            "expected": sorted(expected),
            "predicted": sorted(predicted),
            "exact_match": expected == predicted,
        })
    return {
        "claim": "labelled_fixture_rule_coverage_not_general_orchestrator_correctness",
        "population": len(results),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "exact_matches": {
            "numerator": sum(item["exact_match"] for item in results),
            "denominator": len(results),
        },
        "results": results,
    }


def run_demo() -> dict[str, Any]:
    reference = load_bundle()
    candidate = load_bundle(candidate=True)
    reference_report = review_workflow(reference)
    candidate_report = review_workflow(candidate)
    return {
        "fixture_status": "fictional_training_fixture_not_live_agent_or_repository_execution",
        "reference": {
            "review": reference_report,
            "decision": coordination_decision(reference_report),
            "initial_ready": ready_work_units(
                reference["workflow"],
                {item["id"]: "PROPOSED" for item in reference["workflow"]["work_units"]},
            ),
        },
        "candidate": {
            "review": candidate_report,
            "decision": coordination_decision(candidate_report),
        },
        "model_comparison": compare_execution_models(),
        "evaluation": evaluate_coordination_rules(),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, default=str))
