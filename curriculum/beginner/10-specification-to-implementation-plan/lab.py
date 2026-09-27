"""Deterministic Course 10 lab: specification to bounded agent work units.

The lab models planning mechanics on fictional, versioned fixtures. It does not
inspect a live repository, approve architecture, authorize an agent, or prove
that implementation evidence exists.
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
SCENARIO_ROOT = LESSON_ROOT / "northstar-implementation-plan"
CANDIDATE_ROOT = SCENARIO_ROOT / "candidate"
REFERENCE_ROOT = SCENARIO_ROOT / "reference"
SPECIFICATION_PATH = SCENARIO_ROOT / "approved-specification.json"
REPOSITORY_PATH = SCENARIO_ROOT / "repository-snapshot.json"
ARCHITECTURE_PATH = SCENARIO_ROOT / "architecture-context.json"
CANDIDATE_PLAN_PATH = CANDIDATE_ROOT / "plan.json"
REFERENCE_DISCOVERY_PATH = REFERENCE_ROOT / "discovery.json"
REFERENCE_PLAN_PATH = REFERENCE_ROOT / "plan.json"
REFERENCE_WORK_UNITS_PATH = REFERENCE_ROOT / "work-units.json"
EVALUATION_PATH = SCENARIO_ROOT / "evaluation-cases.json"


class Severity(str, Enum):
    BLOCKING = "blocking"
    REVIEW = "review"


class PlanState(str, Enum):
    READY = "PLAN_READY"
    BLOCKED = "PLAN_BLOCKED"
    REQUIRES_ARCHITECTURE = "PLAN_REQUIRES_ARCHITECTURE"
    REQUIRES_CLARIFICATION = "PLAN_REQUIRES_CLARIFICATION"
    REQUIRES_SCOPE_EXPANSION = "PLAN_REQUIRES_SCOPE_EXPANSION"


class WorkUnitState(str, Enum):
    PROPOSED = "PROPOSED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    INTEGRATED = "INTEGRATED"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    SCOPE_EXPANSION_REQUIRED = "SCOPE_EXPANSION_REQUIRED"
    REVALIDATION_REQUIRED = "REVALIDATION_REQUIRED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    subject_id: str
    message: str
    owner: str
    repair: str


ALLOWED_DISPOSITIONS = {
    "implement", "already_satisfied", "blocked", "deferred", "not_applicable"
}
REQUIRED_STOP_CONDITIONS = {
    "contract_change_required",
    "protected_path_change_required",
    "requirement_conflict",
    "architecture_change_required",
    "new_external_dependency_required",
    "authorization_behavior_change_required",
}
PLANNING_ONLY_CLAIM = (
    "planning_fixture_only_not_agent_authorization_implementation_evidence_or_release_approval"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_bundle(*, candidate: bool = False) -> dict[str, Any]:
    plan = load_json(CANDIDATE_PLAN_PATH if candidate else REFERENCE_PLAN_PATH)
    if not candidate:
        plan = dict(plan)
        plan["discovery"] = load_json(REFERENCE_DISCOVERY_PATH)
        work_unit_package = load_json(REFERENCE_WORK_UNITS_PATH)
        plan["work_units"] = work_unit_package["work_units"]
        plan["readiness_evidence_catalog"] = work_unit_package["readiness_evidence_catalog"]
    return {
        "specification": load_json(SPECIFICATION_PATH),
        "repository": load_json(REPOSITORY_PATH),
        "architecture": load_json(ARCHITECTURE_PATH),
        "plan": plan,
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


def validate_discovery(discovery: dict[str, Any], repository: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    identifier = str(discovery.get("id", "discovery"))
    if discovery.get("mode") == "read_everything" or not discovery.get("guided_by_requirement_ids"):
        findings.append(_finding(
            "DISCOVERY_NOT_REQUIREMENTS_GUIDED", Severity.REVIEW, identifier,
            "Repository discovery is unbounded or has no requirement-guided search basis.",
            "Planning owner", "Declare requirement, invariant, security, and architecture search seeds.",
        ))
    allowed_states = {"CONFIRMED", "LIKELY", "UNKNOWN", "CONFLICT"}
    for observation in discovery.get("observations", []):
        observation_id = str(observation.get("id", "observation"))
        if observation.get("classification") not in allowed_states:
            findings.append(_finding(
                "DISCOVERY_CONFIDENCE_UNCLASSIFIED", Severity.REVIEW, observation_id,
                "A repository observation has no explicit confidence class.",
                "Planning owner", "Classify the observation as CONFIRMED, LIKELY, UNKNOWN, or CONFLICT.",
            ))
        if not observation.get("evidence_paths"):
            findings.append(_finding(
                "DISCOVERY_EVIDENCE_MISSING", Severity.REVIEW, observation_id,
                "A repository observation has no inspectable path evidence.",
                "Planning owner", "Attach exact repository paths and symbols or keep the statement unknown.",
            ))
        if observation.get("classification") == "CONFLICT" and not observation.get("resolution"):
            findings.append(_finding(
                "REPOSITORY_ARCHITECTURE_CONFLICT_UNRESOLVED", Severity.BLOCKING, observation_id,
                "Repository reality conflicts with approved architecture and has no owned resolution.",
                "Architecture owner", "Resolve the conflict or record an approved ADR before task generation.",
            ))
    repository_paths = {item["path"] for item in repository.get("components", [])}
    observed_paths = {
        path
        for item in discovery.get("observations", [])
        for path in item.get("evidence_paths", [])
    }
    if observed_paths - repository_paths:
        findings.append(_finding(
            "DISCOVERY_PATH_NOT_IN_SNAPSHOT", Severity.REVIEW, identifier,
            "Discovery cites paths absent from the bound repository snapshot.",
            "Planning owner", "Refresh discovery against the exact repository revision.",
        ))
    return findings


def validate_plan_provenance(
    plan: dict[str, Any],
    specification: dict[str, Any],
    repository: dict[str, Any],
    architecture: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    plan_id = str(plan.get("id", "plan"))
    expected_spec_digest = stable_digest(specification)
    bound_spec = plan.get("specification", {})
    if (
        bound_spec.get("id") != specification.get("id")
        or bound_spec.get("digest") != expected_spec_digest
    ):
        findings.append(_finding(
            "PLAN_SPECIFICATION_BINDING_INVALID", Severity.BLOCKING, plan_id,
            "The plan is not bound to the exact approved specification content.",
            "Planning owner", "Regenerate the plan binding from the approved specification ID and digest.",
        ))
    if plan.get("repository_revision") != repository.get("revision"):
        findings.append(_finding(
            "PLAN_REPOSITORY_REVISION_STALE", Severity.REVIEW, plan_id,
            "The plan repository revision differs from the discovery snapshot.",
            "Planning owner", "Perform affected-path analysis and targeted re-discovery before execution.",
        ))
    approved_adrs = {item["id"] for item in architecture.get("decisions", [])}
    for decision in plan.get("architecture_decisions", []):
        if decision not in approved_adrs:
            findings.append(_finding(
                "UNAPPROVED_ARCHITECTURE_INVENTED", Severity.BLOCKING, str(decision),
                "The plan relies on an architecture decision absent from the approved context.",
                "Architecture owner", "Stop and route the proposal through an ADR decision before planning resumes.",
            ))
    return findings


def assess_plan_staleness(plan: dict[str, Any], repository: dict[str, Any]) -> dict[str, Any]:
    """Invalidate only plan regions touched by semantic repository drift."""
    if plan.get("repository_revision") == repository.get("revision"):
        return {
            "state": "current",
            "affected_work_units": [],
            "changed_paths": [],
            "action": "continue",
        }
    changed = set(repository.get("changed_paths_since_plan", []))
    affected: list[str] = []
    for work_unit in plan.get("work_units", []):
        relevant = set(
            work_unit.get("writable_paths", [])
            + work_unit.get("read_only_paths", [])
            + work_unit.get("contract_paths", [])
        )
        if changed & relevant:
            affected.append(str(work_unit.get("id")))
    return {
        "state": "stale_relevant" if affected else "stale_unrelated",
        "affected_work_units": sorted(affected),
        "changed_paths": sorted(changed),
        "action": "targeted_rediscovery" if affected else "continue_with_revision_note",
    }


def validate_requirement_dispositions(
    plan: dict[str, Any], specification: dict[str, Any]
) -> list[Finding]:
    findings: list[Finding] = []
    required_ids = {
        item["id"] for item in specification.get("requirements", [])
        if item.get("in_scope") is True
    }
    work_units = {item["id"] for item in plan.get("work_units", [])}
    dispositions = {
        item.get("requirement_id"): item
        for item in plan.get("requirement_dispositions", [])
    }
    for requirement_id in sorted(required_ids):
        disposition = dispositions.get(requirement_id)
        if disposition is None:
            findings.append(_finding(
                "UNPLANNED_REQUIREMENT", Severity.BLOCKING, requirement_id,
                "An in-scope requirement has no explicit planning disposition.",
                "Planning owner", "Mark it implement, already satisfied, blocked, deferred, or not applicable with evidence.",
            ))
            continue
        state = disposition.get("disposition")
        if state not in ALLOWED_DISPOSITIONS:
            findings.append(_finding(
                "REQUIREMENT_DISPOSITION_INVALID", Severity.BLOCKING, requirement_id,
                "The requirement uses an unknown planning disposition.",
                "Planning owner", "Use one governed disposition and retain its rationale and evidence.",
            ))
        if state == "implement":
            mapped = set(disposition.get("work_unit_ids", []))
            if not mapped or not mapped <= work_units:
                findings.append(_finding(
                    "IMPLEMENT_DISPOSITION_WITHOUT_WORK_UNIT", Severity.BLOCKING, requirement_id,
                    "An implementation disposition has no valid work-unit mapping.",
                    "Planning owner", "Map the requirement to one or more existing bounded work units.",
                ))
        if state == "already_satisfied" and not disposition.get("evidence_ids"):
            findings.append(_finding(
                "ALREADY_SATISFIED_WITHOUT_EVIDENCE", Severity.BLOCKING, requirement_id,
                "The plan claims no change is necessary without current conformance evidence.",
                "Requirement and evidence owners", "Link current evidence for the exact repository and requirement revision.",
            ))
        if state in {"blocked", "deferred", "not_applicable"} and not disposition.get("owner"):
            findings.append(_finding(
                "DISPOSITION_OWNER_MISSING", Severity.REVIEW, requirement_id,
                "A non-implementation disposition has no accountable owner.",
                "Planning owner", "Record the owner, reason, evidence, and review trigger.",
            ))
    unknown = sorted(set(dispositions) - required_ids)
    if unknown:
        findings.append(_finding(
            "DISPOSITION_REQUIREMENT_UNKNOWN", Severity.REVIEW, "requirement-dispositions",
            f"Dispositions name requirements outside the approved in-scope set: {', '.join(unknown)}.",
            "Planning owner", "Correct the IDs or obtain an approved scope change.",
        ))
    return findings


def _path_overlaps(left: str, right: str) -> bool:
    left = left.rstrip("*/")
    right = right.rstrip("*/")
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def validate_work_units(
    plan: dict[str, Any], specification: dict[str, Any], repository: dict[str, Any]
) -> list[Finding]:
    findings: list[Finding] = []
    requirement_ids = {item["id"] for item in specification.get("requirements", [])}
    protected = repository.get("protected_paths", [])
    work_units = plan.get("work_units", [])
    work_unit_ids = {item.get("id") for item in work_units}
    readiness_evidence = {
        item.get("id"): item for item in plan.get("readiness_evidence_catalog", [])
    }
    blocked_capabilities = {
        item["id"] for item in specification.get("capabilities", [])
        if item.get("implementation_readiness") == "BLOCKED"
    }

    for unit in work_units:
        unit_id = str(unit.get("id", "work-unit"))
        if not unit.get("accountability_team") or not unit.get("required_reviewers"):
            findings.append(_finding(
                "WORK_UNIT_ACCOUNTABILITY_MISSING", Severity.BLOCKING, unit_id,
                "Execution assignment is not separated from accountable team ownership and review.",
                "Planning owner", "Name the accountable team and required human/team review independently of the agent assignment.",
            ))
        if not unit.get("protected_decisions"):
            findings.append(_finding(
                "WORK_UNIT_PROTECTED_DECISIONS_MISSING", Severity.BLOCKING, unit_id,
                "The work unit does not identify decisions the execution agent must not redefine.",
                "Accountable owner", "List protected product, policy, architecture, security, and authorization decisions.",
            ))
        evidence_ids = unit.get("readiness_evidence_ids", [])
        if not evidence_ids:
            findings.append(_finding(
                "WORK_UNIT_READINESS_EVIDENCE_MISSING", Severity.BLOCKING, unit_id,
                "Execution readiness is asserted without linked evidence records.",
                "Planning owner", "Link current specification, repository, instruction, permission, and verification records.",
            ))
        else:
            bad_evidence = [
                str(identifier) for identifier in evidence_ids
                if identifier not in readiness_evidence
                or readiness_evidence[identifier].get("status") != "current"
            ]
            if bad_evidence:
                findings.append(_finding(
                    "WORK_UNIT_READINESS_EVIDENCE_INVALID", Severity.BLOCKING, unit_id,
                    f"Readiness evidence is missing or not current: {', '.join(bad_evidence)}.",
                    "Planning owner", "Resolve the evidence relationships before scheduling the unit.",
                ))
        if not unit.get("goal") or not unit.get("deliverable"):
            findings.append(_finding(
                "WORK_UNIT_NOT_COHESIVE", Severity.REVIEW, unit_id,
                "The work unit lacks a coherent goal or meaningful reviewable increment.",
                "Planning owner", "Define one responsibility, stable contract, bounded files, and a reviewable deliverable.",
            ))
        if not unit.get("requirement_ids") or not set(unit.get("requirement_ids", [])) <= requirement_ids:
            findings.append(_finding(
                "WORK_UNIT_REQUIREMENT_BASIS_INVALID", Severity.BLOCKING, unit_id,
                "The work unit has no valid approved requirement basis.",
                "Planning owner", "Link only approved requirements or record an owned scope-expansion request.",
            ))
        writable = unit.get("writable_paths", [])
        if not writable or "*" in writable or "**" in writable:
            findings.append(_finding(
                "WORK_UNIT_WRITE_SCOPE_UNBOUNDED", Severity.BLOCKING, unit_id,
                "The work unit grants wildcard or empty write scope.",
                "Implementation owner", "Declare narrow writable, read-only, and prohibited paths.",
            ))
        if any(_path_overlaps(path, protected_path) for path in writable for protected_path in protected):
            findings.append(_finding(
                "PROTECTED_PATH_WRITE_ATTEMPT", Severity.BLOCKING, unit_id,
                "The work unit writes a repository-protected path.",
                "Repository owner", "Remove the path or route a separately authorized scope expansion.",
            ))
        if set(writable) & set(unit.get("read_only_paths", [])):
            findings.append(_finding(
                "PATH_PERMISSION_CONTRADICTION", Severity.BLOCKING, unit_id,
                "The same exact path is both writable and read-only.",
                "Planning owner", "Resolve the path authority before agent dispatch.",
            ))
        if not REQUIRED_STOP_CONDITIONS <= set(unit.get("stop_conditions", [])):
            findings.append(_finding(
                "WORK_UNIT_STOP_CONDITIONS_INCOMPLETE", Severity.BLOCKING, unit_id,
                "The agent can continue through consequential discovery without required stop conditions.",
                "Implementation owner", "Add contract, protected-path, requirement, architecture, dependency, and authorization stops.",
            ))
        authority = unit.get("agent_authority", {})
        if not authority.get("may_decide") or not authority.get("may_propose") or not authority.get("may_not_decide"):
            findings.append(_finding(
                "WORK_UNIT_AUTHORITY_UNDEFINED", Severity.BLOCKING, unit_id,
                "Decision authority is not separated into may decide, may propose, and may not decide.",
                "Planning owner", "Bound local autonomy and preserve accountable product, policy, architecture, and release decisions.",
            ))
        verification = unit.get("verification", {})
        if not verification.get("acceptance_ids") or not verification.get("required_checks"):
            findings.append(_finding(
                "WORK_UNIT_VERIFICATION_INCOMPLETE", Severity.BLOCKING, unit_id,
                "Completion lacks acceptance and executable evidence obligations.",
                "Quality owner", "Link acceptance criteria and name required checks and evidence outputs.",
            ))
        if unit.get("capability") in blocked_capabilities:
            findings.append(_finding(
                "BLOCKED_CAPABILITY_SCHEDULED", Severity.BLOCKING, unit_id,
                "The plan schedules a capability whose implementation readiness is blocked.",
                "Capability owner", "Remove it from execution until its specification gate changes state.",
            ))
        unknown_dependencies = set(unit.get("depends_on", [])) - work_unit_ids
        if unknown_dependencies:
            findings.append(_finding(
                "WORK_UNIT_DEPENDENCY_UNKNOWN", Severity.BLOCKING, unit_id,
                f"Dependencies do not exist: {', '.join(sorted(unknown_dependencies))}.",
                "Planning owner", "Repair dependency IDs before scheduling.",
            ))

    for index, left in enumerate(work_units):
        for right in work_units[index + 1:]:
            overlap = {
                left_path
                for left_path in left.get("writable_paths", [])
                for right_path in right.get("writable_paths", [])
                if _path_overlaps(left_path, right_path)
            }
            ordered = (
                right.get("id") in left.get("depends_on", [])
                or left.get("id") in right.get("depends_on", [])
            )
            if overlap and not ordered:
                findings.append(_finding(
                    "PARALLEL_WRITE_COLLISION", Severity.BLOCKING,
                    f"{left.get('id')}|{right.get('id')}",
                    "Nominally parallel work units have overlapping write ownership.",
                    "Planning owner", "Partition paths, stabilize a shared contract first, or add an explicit dependency.",
                ))
    return findings


def validate_tasks(plan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for task in plan.get("tasks", []):
        task_id = str(task.get("id", "task"))
        basis = task.get("basis", {})
        if not any(basis.get(field) for field in ("requirement_ids", "adr_ids", "contract_ids", "dependency_ids")):
            findings.append(_finding(
                "ORPHAN_TASK", Severity.REVIEW, task_id,
                "The task has no requirement, architecture, contract, or dependency basis.",
                "Planning owner", "Remove it or record the approved reason for the work.",
            ))
        if task.get("introduces_external_dependency") and not basis.get("adr_ids"):
            findings.append(_finding(
                "EXTERNAL_DEPENDENCY_UNAUTHORIZED", Severity.BLOCKING, task_id,
                "A new external dependency is scheduled without an approved architecture basis.",
                "Architecture owner", "Stop and evaluate the dependency through the approved decision process.",
            ))
    return findings


def dependency_graph(plan: dict[str, Any]) -> dict[str, set[str]]:
    return {
        str(unit.get("id")): {str(item) for item in unit.get("depends_on", [])}
        for unit in plan.get("work_units", [])
    }


def topological_waves(plan: dict[str, Any]) -> dict[str, Any]:
    graph = dependency_graph(plan)
    remaining = {node: set(dependencies) for node, dependencies in graph.items()}
    waves: list[list[str]] = []
    completed: set[str] = set()
    while remaining:
        ready = sorted(node for node, dependencies in remaining.items() if dependencies <= completed)
        if not ready:
            cycle_nodes = sorted(remaining)
            return {"acyclic": False, "waves": waves, "cycle_nodes": cycle_nodes}
        waves.append(ready)
        completed.update(ready)
        for node in ready:
            del remaining[node]
    return {"acyclic": True, "waves": waves, "cycle_nodes": []}


def validate_dependency_graph(plan: dict[str, Any]) -> list[Finding]:
    result = topological_waves(plan)
    if result["acyclic"]:
        return []
    return [_finding(
        "WORK_GRAPH_CYCLE", Severity.BLOCKING, "work-graph",
        f"The dependency graph cannot be scheduled: {', '.join(result['cycle_nodes'])}.",
        "Planning owner", "Remove circular ownership and identify a stable contract or sequencing boundary.",
    )]


def coordination_metrics(plan: dict[str, Any]) -> dict[str, Any]:
    """Compare total effort with dependency-aware elapsed waves without conflating them."""
    schedule = topological_waves(plan)
    estimates = {
        unit["id"]: int(unit.get("estimated_work_units", 1))
        for unit in plan.get("work_units", [])
    }
    total_work = sum(estimates.values())
    elapsed = None
    if schedule["acyclic"]:
        elapsed = sum(max(estimates[item] for item in wave) for wave in schedule["waves"])
    return {
        "total_work_units": total_work,
        "dependency_aware_elapsed_units": elapsed,
        "parallelism_ratio": total_work / elapsed if elapsed else None,
        "work_unit_count": len(estimates),
        "wave_count": len(schedule["waves"]),
        "interpretation": "Total work and dependency-aware elapsed time are different measures; parallel work is not free.",
    }


def disposition_metrics(plan: dict[str, Any], specification: dict[str, Any]) -> dict[str, Any]:
    applicable = {
        item["id"] for item in specification.get("requirements", [])
        if item.get("in_scope") is True
    }
    disposed = {
        item.get("requirement_id") for item in plan.get("requirement_dispositions", [])
        if item.get("requirement_id") in applicable
    }
    denominator = len(applicable)
    return {
        "requirements_with_disposition": {
            "numerator": len(disposed),
            "denominator": denominator,
            "value": len(disposed) / denominator if denominator else None,
        },
        "claim": "structural_disposition_coverage_not_plan_correctness",
    }


def implementation_traceability(plan: dict[str, Any], specification: dict[str, Any]) -> dict[str, Any]:
    """Trace to meaningful components and evidence, never brittle source lines."""
    required = {
        item["id"] for item in specification.get("requirements", [])
        if item.get("in_scope") is True
    }
    rows: list[dict[str, Any]] = []
    for task in plan.get("tasks", []):
        for requirement_id in task.get("basis", {}).get("requirement_ids", []):
            rows.append({
                "requirement_id": requirement_id,
                "work_unit_id": task.get("work_unit_id"),
                "task_id": task.get("id"),
                "implementation_units": task.get("code_paths", []),
                "evidence_ids": task.get("evidence_ids", []),
            })
    fully_traced = {
        row["requirement_id"] for row in rows
        if row["work_unit_id"] and row["task_id"] and row["implementation_units"] and row["evidence_ids"]
    }
    return {
        "rows": rows,
        "complete_requirement_chains": {
            "numerator": len(required & fully_traced),
            "denominator": len(required),
            "value": len(required & fully_traced) / len(required) if required else None,
        },
        "trace_granularity": "component_module_contract_control_and_evidence_not_source_lines",
    }


def ready_work_units(
    plan: dict[str, Any],
    *,
    completed_work_unit_ids: Iterable[str] = (),
) -> dict[str, Any]:
    completed = set(completed_work_unit_ids)
    evidence_index = {
        item.get("id"): item for item in plan.get("readiness_evidence_catalog", [])
    }
    ready: list[str] = []
    blocked: dict[str, list[str]] = {}
    for unit in plan.get("work_units", []):
        unit_id = str(unit.get("id"))
        if unit_id in completed:
            continue
        reasons: list[str] = []
        missing_dependencies = set(unit.get("depends_on", [])) - completed
        if missing_dependencies:
            reasons.append("dependencies_incomplete:" + ",".join(sorted(missing_dependencies)))
        invalid_evidence = [
            str(identifier) for identifier in unit.get("readiness_evidence_ids", [])
            if identifier not in evidence_index or evidence_index[identifier].get("status") != "current"
        ]
        if invalid_evidence:
            reasons.append("readiness_evidence_invalid:" + ",".join(invalid_evidence))
        if reasons:
            blocked[unit_id] = reasons
        else:
            ready.append(unit_id)
    return {
        "ready": sorted(ready),
        "blocked": blocked,
        "claim": "dependency_and_evidence_readiness_not_runtime_permission_provisioning",
    }


def downstream_work_units(plan: dict[str, Any], changed_work_unit_id: str) -> list[str]:
    reverse: dict[str, set[str]] = defaultdict(set)
    for unit in plan.get("work_units", []):
        for dependency in unit.get("depends_on", []):
            reverse[str(dependency)].add(str(unit.get("id")))
    affected: set[str] = set()
    queue = deque([changed_work_unit_id])
    while queue:
        current = queue.popleft()
        for consumer in reverse.get(current, set()):
            if consumer not in affected:
                affected.add(consumer)
                queue.append(consumer)
    return sorted(affected)


def validate_contract_change_request(request: dict[str, Any], plan: dict[str, Any]) -> list[Finding]:
    required = {
        "id", "discovered_by", "contract", "proposed_change", "reason_requirement_ids",
        "affected_work_unit_ids", "impact",
    }
    missing = sorted(field for field in required if request.get(field) in (None, "", []))
    findings: list[Finding] = []
    if missing:
        findings.append(_finding(
            "CONTRACT_CHANGE_REQUEST_INCOMPLETE", Severity.BLOCKING,
            str(request.get("id", "contract-change-request")),
            f"Contract change request lacks: {', '.join(missing)}.",
            "Contract owner", "Record provenance, requirement reason, downstream impact, and affected evidence before replanning.",
        ))
        return findings
    expected = set(downstream_work_units(plan, str(request["discovered_by"])))
    declared = set(request.get("affected_work_unit_ids", []))
    if not expected <= declared:
        findings.append(_finding(
            "CONTRACT_CHANGE_IMPACT_INCOMPLETE", Severity.BLOCKING, str(request["id"]),
            "The change request omits downstream work units from impact analysis.",
            "Planning owner", "Propagate the contract change through work units, tasks, and evidence dependencies.",
        ))
    return findings


def validate_completion_report(
    work_unit: dict[str, Any],
    report: dict[str, Any],
    *,
    actual_changed_paths: Iterable[str],
) -> list[Finding]:
    findings: list[Finding] = []
    unit_id = str(work_unit.get("id"))
    changed = list(actual_changed_paths)
    writable = work_unit.get("writable_paths", [])
    out_of_scope = [
        path for path in changed
        if not any(_path_overlaps(path, allowed) for allowed in writable)
    ]
    if out_of_scope:
        findings.append(_finding(
            "WORK_UNIT_SCOPE_VIOLATION", Severity.BLOCKING, unit_id,
            f"Changed paths exceed the declared write set: {', '.join(sorted(out_of_scope))}.",
            "Implementation and repository owners", "Stop, explain the deviation, and obtain scope expansion or revert it.",
        ))
    protected_actions = set(report.get("semantic_actions", [])) & set(work_unit.get("protected_decisions", []))
    if protected_actions:
        findings.append(_finding(
            "SEMANTIC_SCOPE_EXPANSION", Severity.BLOCKING, unit_id,
            f"Implementation attempts protected decisions: {', '.join(sorted(protected_actions))}.",
            "Accountable owner", "Stop and route the decision rather than hiding it inside an allowed file.",
        ))
    expected_evidence = set(work_unit.get("verification", {}).get("evidence_outputs", []))
    reported_evidence = set(report.get("evidence_ids", []))
    if not expected_evidence <= reported_evidence:
        findings.append(_finding(
            "COMPLETION_EVIDENCE_MISSING", Severity.BLOCKING, unit_id,
            "The completion report does not contain every planned evidence output.",
            "Quality owner", "Run independent checks and attach evidence for the exact implementation revision.",
        ))
    if report.get("status") == "COMPLETED" and report.get("unresolved"):
        findings.append(_finding(
            "COMPLETION_WITH_UNRESOLVED_BLOCKERS", Severity.BLOCKING, unit_id,
            "The agent claims completion while unresolved blockers remain.",
            "Implementation owner", "Use a typed blocked outcome and preserve unresolved items.",
        ))
    return findings


def transition_work_unit_state(
    current: WorkUnitState,
    target: WorkUnitState,
    *,
    verification_passed: bool = False,
    integration_passed: bool = False,
) -> WorkUnitState:
    allowed = {
        WorkUnitState.PROPOSED: {WorkUnitState.READY, WorkUnitState.BLOCKED, WorkUnitState.CANCELLED},
        WorkUnitState.READY: {WorkUnitState.IN_PROGRESS, WorkUnitState.BLOCKED, WorkUnitState.CANCELLED},
        WorkUnitState.IN_PROGRESS: {
            WorkUnitState.COMPLETED, WorkUnitState.PAUSED,
            WorkUnitState.SCOPE_EXPANSION_REQUIRED, WorkUnitState.CANCELLED,
        },
        WorkUnitState.COMPLETED: {
            WorkUnitState.VERIFIED, WorkUnitState.VERIFICATION_FAILED,
            WorkUnitState.REVALIDATION_REQUIRED,
        },
        WorkUnitState.VERIFIED: {WorkUnitState.INTEGRATED, WorkUnitState.REVALIDATION_REQUIRED},
        WorkUnitState.PAUSED: {WorkUnitState.IN_PROGRESS, WorkUnitState.CANCELLED},
        WorkUnitState.REVALIDATION_REQUIRED: {WorkUnitState.VERIFIED, WorkUnitState.VERIFICATION_FAILED},
        WorkUnitState.VERIFICATION_FAILED: {WorkUnitState.IN_PROGRESS, WorkUnitState.CANCELLED},
    }
    if target not in allowed.get(current, set()):
        raise ValueError(f"invalid work-unit transition: {current.value}->{target.value}")
    if target == WorkUnitState.VERIFIED and not verification_passed:
        raise ValueError("verification evidence must pass before VERIFIED")
    if target == WorkUnitState.INTEGRATED and not integration_passed:
        raise ValueError("integration evidence must pass before INTEGRATED")
    return target


def review_plan(bundle: dict[str, Any]) -> dict[str, Any]:
    specification = bundle["specification"]
    repository = bundle["repository"]
    architecture = bundle["architecture"]
    plan = bundle["plan"]
    findings: list[Finding] = []
    findings.extend(validate_discovery(plan.get("discovery", {}), repository))
    findings.extend(validate_plan_provenance(plan, specification, repository, architecture))
    findings.extend(validate_requirement_dispositions(plan, specification))
    findings.extend(validate_work_units(plan, specification, repository))
    findings.extend(validate_tasks(plan))
    findings.extend(validate_dependency_graph(plan))
    ordered = sorted(findings, key=lambda item: (item.severity.value, item.subject_id, item.code))
    return {
        "claim": PLANNING_ONLY_CLAIM,
        "findings": [asdict(item) for item in ordered],
        "counts": dict(sorted(Counter(item.severity.value for item in ordered).items())),
        "staleness": assess_plan_staleness(plan, repository),
        "schedule": topological_waves(plan),
        "metrics": coordination_metrics(plan),
        "disposition_metrics": disposition_metrics(plan, specification),
        "traceability": implementation_traceability(plan, specification),
        "initial_scheduler_view": ready_work_units(plan),
    }


def planning_decision(report: dict[str, Any]) -> dict[str, Any]:
    codes = {item["code"] for item in report.get("findings", [])}
    architecture_codes = {"UNAPPROVED_ARCHITECTURE_INVENTED", "EXTERNAL_DEPENDENCY_UNAUTHORIZED"}
    clarification_codes = {
        "REPOSITORY_ARCHITECTURE_CONFLICT_UNRESOLVED", "UNPLANNED_REQUIREMENT",
        "ALREADY_SATISFIED_WITHOUT_EVIDENCE",
    }
    scope_codes = {"PROTECTED_PATH_WRITE_ATTEMPT", "DISPOSITION_REQUIREMENT_UNKNOWN"}
    if codes & architecture_codes:
        state = PlanState.REQUIRES_ARCHITECTURE
    elif codes & scope_codes:
        state = PlanState.REQUIRES_SCOPE_EXPANSION
    elif codes & clarification_codes:
        state = PlanState.REQUIRES_CLARIFICATION
    elif any(item["severity"] == Severity.BLOCKING.value for item in report.get("findings", [])):
        state = PlanState.BLOCKED
    elif report.get("findings"):
        state = PlanState.BLOCKED
    else:
        state = PlanState.READY
    return {
        "state": state.value,
        "ready_for_dispatch": state == PlanState.READY,
        "finding_codes": sorted(codes),
        "claim": "plan_readiness_only_not_agent_authorization_or_implementation_completion",
    }


def generate_execution_context(bundle: dict[str, Any], work_unit_id: str) -> dict[str, Any]:
    """Generate a bounded context only after plan review; never an authority token."""
    report = review_plan(bundle)
    decision = planning_decision(report)
    if not decision["ready_for_dispatch"]:
        raise ValueError(f"plan is not dispatch-ready: {decision['state']}")
    plan = bundle["plan"]
    work_unit = next(
        (item for item in plan.get("work_units", []) if item.get("id") == work_unit_id),
        None,
    )
    if work_unit is None:
        raise KeyError(work_unit_id)
    requirement_index = {
        item["id"]: item for item in bundle["specification"].get("requirements", [])
    }
    evidence_index = {
        item.get("id"): item for item in plan.get("readiness_evidence_catalog", [])
    }
    return {
        "schema_version": "1.0-training",
        "work_unit_id": work_unit_id,
        "plan_id": plan["id"],
        "plan_digest": stable_digest(plan),
        "specification": plan["specification"],
        "repository_revision": plan["repository_revision"],
        "goal": work_unit["goal"],
        "requirement_ids": work_unit["requirement_ids"],
        "requirement_context": [
            requirement_index[identifier]
            for identifier in work_unit["requirement_ids"]
        ],
        "contracts": work_unit["contracts"],
        "contract_paths": work_unit["contract_paths"],
        "writable_paths": work_unit["writable_paths"],
        "read_only_paths": work_unit["read_only_paths"],
        "prohibited_paths": bundle["repository"]["protected_paths"],
        "verification": work_unit["verification"],
        "stop_conditions": work_unit["stop_conditions"],
        "agent_authority": work_unit["agent_authority"],
        "accountability_team": work_unit["accountability_team"],
        "execution_owner": work_unit["execution_owner"],
        "required_reviewers": work_unit["required_reviewers"],
        "protected_decisions": work_unit["protected_decisions"],
        "readiness_evidence": [
            evidence_index[identifier]
            for identifier in work_unit["readiness_evidence_ids"]
        ],
        "authority_boundary": "This context constrains execution; it does not grant production, policy, architecture, or exception authority.",
    }


def _evaluation_findings(case: dict[str, Any]) -> list[Finding]:
    bundle = load_bundle()
    kind = case["kind"]
    payload = case["input"]
    if kind == "discovery":
        return validate_discovery(payload, bundle["repository"])
    if kind == "provenance_mutation":
        plan = copy.deepcopy(bundle["plan"])
        plan.update(payload.get("changes", {}))
        return validate_plan_provenance(plan, bundle["specification"], bundle["repository"], bundle["architecture"])
    if kind == "disposition_mutation":
        plan = copy.deepcopy(bundle["plan"])
        if payload.get("remove_requirement_id"):
            plan["requirement_dispositions"] = [
                item for item in plan["requirement_dispositions"]
                if item.get("requirement_id") != payload["remove_requirement_id"]
            ]
        if payload.get("replace"):
            replacement = payload["replace"]
            plan["requirement_dispositions"] = [
                replacement if item.get("requirement_id") == replacement.get("requirement_id") else item
                for item in plan["requirement_dispositions"]
            ]
        return validate_requirement_dispositions(plan, bundle["specification"])
    if kind == "work_unit_mutation":
        plan = copy.deepcopy(bundle["plan"])
        target = next(item for item in plan["work_units"] if item["id"] == payload["unit_id"])
        target.update(payload.get("changes", {}))
        return validate_work_units(plan, bundle["specification"], bundle["repository"])
    if kind == "readiness_evidence_mutation":
        plan = copy.deepcopy(bundle["plan"])
        record = next(item for item in plan["readiness_evidence_catalog"] if item["id"] == payload["evidence_id"])
        record["status"] = payload["status"]
        return validate_work_units(plan, bundle["specification"], bundle["repository"])
    if kind == "tasks":
        return validate_tasks({"tasks": payload})
    if kind == "graph":
        return validate_dependency_graph({"work_units": payload})
    if kind == "contract_change":
        return validate_contract_change_request(payload, bundle["plan"])
    if kind == "completion":
        unit = next(item for item in bundle["plan"]["work_units"] if item["id"] == payload["unit_id"])
        return validate_completion_report(
            unit,
            payload["report"],
            actual_changed_paths=payload.get("actual_changed_paths", []),
        )
    raise ValueError(f"unknown evaluation kind: {kind}")


def evaluate_planning_rules(cases: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
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
        "claim": "labelled_fixture_rule_coverage_not_general_planner_accuracy",
        "population": len(results),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "exact_matches": {
            "numerator": sum(item["exact_match"] for item in results),
            "denominator": len(results),
        },
        "cases": results,
    }


def run_demo() -> dict[str, Any]:
    candidate = load_bundle(candidate=True)
    reference = load_bundle()
    candidate_report = review_plan(candidate)
    reference_report = review_plan(reference)
    return {
        "fixture_status": "fictional_offline_planning_fixture",
        "thesis": "an_approved_specification_is_not_an_implementation_plan_or_agent_authorization",
        "candidate": {
            "review": candidate_report,
            "decision": planning_decision(candidate_report),
        },
        "reference": {
            "review": reference_report,
            "decision": planning_decision(reference_report),
            "example_execution_context": generate_execution_context(reference, "AWU-BR-EXTRACTION"),
        },
        "evaluation": evaluate_planning_rules(),
    }


def main() -> None:
    print(json.dumps(run_demo(), indent=2, default=lambda value: value.value if isinstance(value, Enum) else value))


if __name__ == "__main__":
    main()
