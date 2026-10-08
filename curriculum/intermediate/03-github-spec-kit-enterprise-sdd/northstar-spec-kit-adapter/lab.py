"""Deterministic Course 13 lab: adapt Spec Kit artifacts to enterprise controls."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent
HEX_64 = re.compile(r"^[0-9a-f]{64}$")
REQ_ID = re.compile(r"^(REQ|SEC|PERF)-DOC-\d{3}$")
REQUIRED_COMMANDS = {
    "constitution", "specify", "clarify", "plan", "checklist", "tasks",
    "analyze", "implement", "converge",
}
REQUIRED_TEMPLATES = {
    "checklist-template.md", "constitution-template.md", "plan-template.md",
    "spec-template.md", "tasks-template.md",
}
EXPECTED_COMMAND_SEMANTICS = {
    "speckit.clarify": {"ask_targeted_questions", "encode_answered_clarifications_into_spec"},
    "speckit.analyze": {"check_cross_artifact_consistency", "internal_consistency_is_not_enterprise_conformance"},
    "speckit.converge": {"append_tasks_only", "no_spec_mutation", "no_plan_mutation", "no_code_mutation"},
}


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    message: str
    path: str
    severity: str = "BLOCK"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference() -> dict[str, Any]:
    return read_json(ROOT / "reference" / "control-package.json")


def load_candidate() -> dict[str, Any]:
    return read_json(ROOT / "candidate" / "control-package.json")


def load_snapshot() -> dict[str, Any]:
    return read_json(ROOT / "spec-kit-snapshot" / "manifest.json")


def load_source() -> dict[str, Any]:
    return read_json(ROOT / "source" / "source-manifest.json")


def stable_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def finding(code: str, path: str, message: str) -> Finding:
    return Finding(code=code, path=path, message=message)


def validate_snapshot(snapshot: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    if snapshot.get("release") in {None, "", "latest"}:
        out.append(finding("FRAMEWORK_VERSION_UNPINNED", "framework_snapshot.release", "Pin an observed release."))
    if not snapshot.get("official_source") or not snapshot.get("resolved_commit") or not snapshot.get("observed_at"):
        out.append(finding("SNAPSHOT_PROVENANCE_MISSING", "framework_snapshot", "Record source, commit, and observation date."))
    commands = {str(command).removeprefix("speckit.") for command in snapshot.get("core_commands", [])}
    if REQUIRED_COMMANDS - commands:
        out.append(finding("SNAPSHOT_COMMAND_MISSING", "framework_snapshot.commands", "The required workflow surface is incomplete."))
    templates = snapshot.get("template_digests", {})
    if REQUIRED_TEMPLATES - set(templates) or any(not HEX_64.fullmatch(str(v)) for v in templates.values()):
        out.append(finding("TEMPLATE_PROVENANCE_MISSING", "framework_snapshot.template_digests", "Template digests must be complete SHA-256 values."))
    contracts = snapshot.get("command_contracts", {})
    if {f"speckit.{command}" for command in REQUIRED_COMMANDS} - set(contracts):
        out.append(finding("COMMAND_CONTRACT_MISSING", "framework_snapshot.command_contracts", "Every required workflow command needs a pinned semantic contract."))
    elif any(not HEX_64.fullmatch(str(contract.get("digest", ""))) for contract in contracts.values()):
        out.append(finding("COMMAND_CONTRACT_DIGEST_INVALID", "framework_snapshot.command_contracts", "Command contracts require full SHA-256 digests."))
    if any(not contract.get("expected_semantics") for contract in contracts.values()):
        out.append(finding("COMMAND_SEMANTICS_MISSING", "framework_snapshot.command_contracts", "Command presence alone does not prove expected behavior."))
    if any(not expected.issubset(set(contracts.get(command, {}).get("expected_semantics", []))) for command, expected in EXPECTED_COMMAND_SEMANTICS.items()):
        out.append(finding("COMMAND_SEMANTIC_DRIFT", "framework_snapshot.command_contracts", "Critical command semantics changed from the tested enterprise contract."))
    return out


def validate_context(source: dict[str, Any], package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    context = package.get("context", {})
    if context.get("context_id") != source.get("context_id"):
        out.append(finding("SOURCE_CONTEXT_DRIFT", "context.context_id", "The package is not bound to the approved context."))
    expected_sources = {artifact.get("id") for artifact in source.get("artifacts", [])}
    if set(context.get("source_ids", [])) != expected_sources:
        out.append(finding("EFFECTIVE_CONTEXT_INCOMPLETE", "context.source_ids", "Effective context must include every required source."))
    refs = context.get("policy_references", [])
    if not refs or any("@" not in ref for ref in refs):
        out.append(finding("POLICY_PROVENANCE_MISSING", "context.policy_references", "Policies require revisioned references."))
    if context.get("source_manifest_digest") != file_digest(ROOT / "source" / "source-manifest.json"):
        out.append(finding("SOURCE_MANIFEST_DIGEST_INVALID", "context.source_manifest_digest", "Bind the package to the exact source manifest bytes."))
    requirement_sources = {
        str(requirement.get("source", "")).split("@", maxsplit=1)[0]
        for requirement in package.get("specification", {}).get("requirements", [])
        if requirement.get("source")
    }
    if not requirement_sources.issubset(set(context.get("source_ids", []))):
        out.append(finding("REQUIREMENT_SOURCE_OUTSIDE_CONTEXT", "specification.requirements", "Every requirement source must be visible in the effective context."))
    return out


def validate_constitution(package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    for i, principle in enumerate(package.get("constitution_principles", [])):
        path = f"constitution_principles[{i}]"
        if principle.get("authority") == "enterprise_policy" and principle.get("kind") == "PROJECT_OWNED":
            out.append(finding("CONSTITUTION_AUTHORITY_LAUNDERING", path, "Inherited policy cannot become project-owned authority."))
        if str(principle.get("owner", "")).lower() in {"spec kit", "coding agent", "framework"}:
            out.append(finding("FRAMEWORK_ACCOUNTABILITY_CLAIM", path + ".owner", "A framework cannot own an accountable decision."))
    return out


def requirement_ids(package: dict[str, Any]) -> set[str]:
    return {r.get("id", "") for r in package.get("specification", {}).get("requirements", [])}


def validate_specification(package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    spec = package.get("specification", {})
    ids = requirement_ids(package)
    for i, requirement in enumerate(spec.get("requirements", [])):
        path = f"specification.requirements[{i}]"
        if not REQ_ID.fullmatch(str(requirement.get("id", ""))):
            out.append(finding("REQUIREMENT_ID_INVALID", path + ".id", "Use a stable typed requirement identifier."))
        if not all(requirement.get(key) for key in ("owner", "source", "revision")):
            out.append(finding("REQUIREMENT_PROVENANCE_MISSING", path, "Requirement owner, source, and revision are required."))
        if requirement.get("implementation_choices"):
            out.append(finding("IMPLEMENTATION_LEAKAGE", path + ".implementation_choices", "Keep unjustified implementation choices out of the requirement."))
    questions = {q.get("id"): q for q in spec.get("open_questions", [])}
    if "Q-DOC-001" not in questions or questions["Q-DOC-001"].get("status") != "OPEN":
        out.append(finding("OPEN_QUESTION_COLLAPSED", "specification.open_questions", "Preserve the unresolved confidence policy decision."))
    if questions.get("Q-DOC-001", {}).get("status") == "OPEN" and spec.get("capability_gates", {}).get("automatic_requirement_satisfaction") != "BLOCKED":
        out.append(finding("BLOCKED_CAPABILITY_ENABLED", "specification.capability_gates", "An open policy decision must block automatic satisfaction."))
    if not spec.get("supported_population") or not spec.get("manual_review_population"):
        out.append(finding("SUPPORTED_POPULATION_MISSING", "specification.supported_population", "Define supported and manual-review populations."))
    for i, criterion in enumerate(spec.get("acceptance_criteria", [])):
        if not set(criterion.get("requirement_ids", [])).issubset(ids):
            out.append(finding("ACCEPTANCE_REQUIREMENT_UNKNOWN", f"specification.acceptance_criteria[{i}]", "Acceptance criteria must trace to known requirements."))
    return out


def assess_repository_freshness(source: dict[str, Any], plan: dict[str, Any]) -> str:
    freshness = plan.get("repository_freshness", {})
    observed = freshness.get("observed_revision", plan.get("repository_revision"))
    current = freshness.get("current_revision", source.get("repository_revision"))
    if observed == current == source.get("repository_revision"):
        return "CURRENT"
    changed_paths = freshness.get("changed_paths", [])
    if not changed_paths:
        return "FULL_REDISCOVERY_REQUIRED"
    if paths_intersect(changed_paths, freshness.get("discovery_scope", [])):
        return "TARGETED_REDISCOVERY_REQUIRED"
    return "DRIFT_OUTSIDE_DISCOVERY_SCOPE_RECORDED"


def validate_plan(source: dict[str, Any], package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    plan = package.get("plan", {})
    ids = requirement_ids(package)
    freshness = assess_repository_freshness(source, plan)
    if plan.get("repository_freshness", {}).get("decision") != freshness:
        out.append(finding("REPOSITORY_FRESHNESS_DECISION_INVALID", "plan.repository_freshness.decision", "Stored freshness decisions must match revision and path evidence."))
    if freshness == "TARGETED_REDISCOVERY_REQUIRED":
        out.append(finding("TARGETED_REDISCOVERY_REQUIRED", "plan.repository_freshness", "Repository changes intersect the discovery scope; refresh affected facts."))
    elif freshness == "FULL_REDISCOVERY_REQUIRED":
        out.append(finding("FULL_REDISCOVERY_REQUIRED", "plan.repository_freshness", "Repository drift lacks path evidence; refresh repository discovery."))
    disposed = {d.get("requirement_id") for d in plan.get("requirement_dispositions", [])}
    if disposed != ids:
        out.append(finding("UNPLANNED_REQUIREMENT", "plan.requirement_dispositions", "Every requirement needs an explicit disposition."))
    if any(not item.get("basis") or not item.get("justified") for item in plan.get("work_items", [])):
        out.append(finding("ORPHAN_WORK", "plan.work_items", "Plan work must trace to requirements and be justified."))
    if any(a.get("status") == "APPROVED" and str(a.get("approved_by", "")).lower() in {"spec kit", "coding agent", "framework"} for a in plan.get("architecture_changes", [])):
        out.append(finding("ARCHITECTURE_SELF_APPROVED", "plan.architecture_changes", "Generated plans may propose, not approve, architecture."))
    if plan.get("duplicate_capabilities"):
        out.append(finding("DUPLICATE_CAPABILITY", "plan.duplicate_capabilities", "Reuse or explicitly retire an existing capability."))
    if plan.get("protected_decision_changes"):
        out.append(finding("PROTECTED_DECISION_CHANGE", "plan.protected_decision_changes", "Protected decisions require their accountable approval path."))
    return out


def paths_intersect(writable: list[str], protected: list[str]) -> bool:
    for write in writable:
        for guard in protected:
            prefix = guard.removesuffix("/**")
            if write == guard or write.startswith(prefix + "/") or guard.startswith(write.removesuffix("/**") + "/"):
                return True
    return False


def validate_tasks(package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    ids = requirement_ids(package)
    for i, task in enumerate(package.get("tasks", [])):
        path = f"tasks[{i}]"
        basis = set(task.get("basis", []))
        if not basis:
            out.append(finding("ORPHAN_TASK", path + ".basis", "Tasks need requirement ancestry."))
        elif not basis.issubset(ids):
            out.append(finding("UNKNOWN_REQUIREMENT_REFERENCE", path + ".basis", "Task references an unknown requirement."))
        if task.get("requires_awu") and not task.get("work_unit_id"):
            out.append(finding("AWU_ENRICHMENT_REQUIRED", path + ".work_unit_id", "Consequential tasks require an agent work unit."))
        if task.get("requires_awu") and not task.get("required_evidence"):
            out.append(finding("TASK_EVIDENCE_MISSING", path + ".required_evidence", "Each work unit needs claim-specific evidence, not a global blanket."))
        if paths_intersect(task.get("writable_paths", []), task.get("protected_paths", [])):
            out.append(finding("TASK_PROTECTED_PATH", path + ".writable_paths", "Writable scope crosses a protected path."))
        if task.get("new_dependency") and not task.get("dependency_proposal_id"):
            out.append(finding("DEPENDENCY_PROPOSAL_REQUIRED", path, "A new dependency requires a governed proposal."))
    return out


def adapt_tasks_to_work_units(package: dict[str, Any]) -> list[dict[str, Any]]:
    policy = package.get("awu_policy", {})
    return [
        {
            "id": task["work_unit_id"],
            "task_ids": [task["id"]],
            "requirements": task["basis"],
            "writable_paths": task["writable_paths"],
            "protected_paths": task["protected_paths"],
            "may_not_decide": policy.get("may_not_decide", []),
            "stop_conditions": policy.get("stop_conditions", []),
            "required_evidence": task.get("required_evidence", []),
            "evidence_role": task.get("evidence_role"),
        }
        for task in package.get("tasks", [])
        if task.get("requires_awu") and task.get("work_unit_id")
    ]


def validate_awu_adapter(package: dict[str, Any]) -> list[Finding]:
    if adapt_tasks_to_work_units(package) != package.get("work_units", []):
        return [finding("AWU_ADAPTER_DRIFT", "work_units", "Generated work units differ from their task and policy inputs.")]
    return []


def validate_work_units(package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    for i, unit in enumerate(package.get("work_units", [])):
        path = f"work_units[{i}]"
        if not unit.get("stop_conditions"):
            out.append(finding("WORK_UNIT_STOP_CONDITIONS_MISSING", path + ".stop_conditions", "Work units must define when the agent stops."))
        if not unit.get("required_evidence"):
            out.append(finding("WORK_UNIT_EVIDENCE_MISSING", path + ".required_evidence", "Evidence obligations must support this unit's claims."))
        if unit.get("evidence_role") not in {"produce_test_inputs_not_attest_results", "author_harness_and_manifest_schema_never_self_attest"}:
            out.append(finding("WORK_UNIT_SELF_ATTESTATION_AMBIGUOUS", path + ".evidence_role", "State that implementation work cannot attest its own conformance."))
        forbidden = set(unit.get("may_not_decide", []))
        if not {"authorization_semantics", "release"}.issubset(forbidden):
            out.append(finding("WORK_UNIT_AUTHORITY_TOO_BROAD", path + ".may_not_decide", "Keep protected decisions outside agent authority."))
    evidence_sets = [tuple(unit.get("required_evidence", [])) for unit in package.get("work_units", []) if unit.get("required_evidence")]
    if len(evidence_sets) > 1 and len(set(evidence_sets)) == 1:
        out.append(finding("BLANKET_EVIDENCE_INHERITANCE", "work_units", "Assign evidence to the claim each work unit changes."))
    return out


def validate_evidence(package: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    evidence = package.get("evidence_manifest", {})
    revision = evidence.get("implementation_revision")
    records = evidence.get("records", [])
    if any(r.get("kind") == "completion_report" and r.get("result") in {"conformance_pass", "production_ready"} for r in records):
        out.append(finding("SELF_REPORTED_CONFORMANCE", "evidence_manifest.records", "Agent completion is not independent conformance evidence."))
    if any(r.get("independent") and r.get("subject_revision") != revision for r in records):
        out.append(finding("EVIDENCE_SUBJECT_STALE", "evidence_manifest.records", "Evidence must bind to the implementation under review."))
    if evidence.get("release_authority") in {"implementation_agent", "spec_kit", "framework"} or evidence.get("production_ready") is True:
        out.append(finding("RELEASE_AUTHORITY_BYPASSED", "evidence_manifest.release_authority", "Release remains external to the implementation workflow."))
    required_kinds = {kind for unit in package.get("work_units", []) for kind in unit.get("required_evidence", [])}
    independent_kinds = {record.get("kind") for record in records if record.get("independent") and record.get("result") in {"pass", "fixture_population_pass"}}
    if not required_kinds.issubset(independent_kinds):
        out.append(finding("CLAIM_EVIDENCE_MISSING", "evidence_manifest.records", "Independent evidence must cover every claim-specific work-unit obligation."))
    return out


def validate_convergence(package: dict[str, Any]) -> list[Finding]:
    convergence = package.get("convergence", {})
    out: list[Finding] = []
    if convergence.get("command_scope") != "speckit.converge" or convergence.get("mode") != "append_only_tasks" or convergence.get("spec_mutations") or convergence.get("plan_mutations"):
        out.append(finding("CONVERGENCE_MUTATES_INTENT", "convergence", "The speckit.converge command may append repair tasks; it does not rewrite spec or plan."))
    evolution = convergence.get("broader_specification_evolution", {})
    if evolution.get("model") != "controlled_flow_back" or not evolution.get("condition"):
        out.append(finding("SPEC_EVOLUTION_ROUTE_MISSING", "convergence.broader_specification_evolution", "Legitimate semantic discoveries need a separate owner-authorized specification evolution route."))
    return out


def validate_multi_repository(package: dict[str, Any]) -> list[Finding]:
    model = package.get("multi_repository", {})
    parent = set(model.get("canonical_requirement_ids", []))
    out: list[Finding] = []
    if any(not set(c.get("requirement_ids", [])).issubset(parent) or c.get("semantic_overrides") for c in model.get("children", [])):
        out.append(finding("CHILD_SPEC_CONTRADICTS_PARENT", "multi_repository.children", "Child specs may specialize, not weaken, parent semantics."))
    return out


def validate_agent_adapters(package: dict[str, Any]) -> list[Finding]:
    adapter = package.get("agent_instruction_adapters", {})
    out: list[Finding] = []
    if any(g.get("source_revision") != adapter.get("canonical_revision") for g in adapter.get("generated", [])):
        out.append(finding("AGENT_INSTRUCTION_ADAPTER_STALE", "agent_instruction_adapters.generated", "Regenerate agent-specific instructions from the canonical rule."))
    if adapter.get("feature_semantics_in_instructions"):
        out.append(finding("FEATURE_SEMANTICS_DUPLICATED_IN_AGENT_INSTRUCTIONS", "agent_instruction_adapters", "Feature semantics belong in the feature specification."))
    return out


def validate_extension_trust(package: dict[str, Any]) -> list[Finding]:
    catalogs = package.get("extension_trust", {}).get("catalogs", [])
    if any(not c.get("owner_vetted") and c.get("install_allowed") for c in catalogs):
        return [finding("UNVETTED_EXTENSION_SOURCE", "extension_trust.catalogs", "Unvetted catalogs cannot be installation sources.")]
    return []


def validate_risk_route(package: dict[str, Any]) -> list[Finding]:
    route = package.get("risk_route", {})
    valid_depth = route.get("governance_depth") in {"routine", "controlled", "consequential"}
    valid_topology = route.get("execution_topology") in {"single_agent", "multi_agent"}
    if route.get("determined_by") != "trusted_policy_engine" or not route.get("basis") or not valid_depth or not valid_topology:
        return [finding("AGENT_SELF_CLASSIFIES_RISK", "risk_route", "A trusted policy engine must select the operating mode.")]
    declared = {key: route.get(key) for key in ("governance_depth", "sdd_mode", "execution_topology")}
    if declared != route_operating_model(route.get("signals", [])):
        return [finding("RISK_ROUTE_INCONSISTENT", "risk_route", "Declared governance and execution axes must match trusted routing signals.")]
    return []


def validate_authority_boundary(package: dict[str, Any]) -> list[Finding]:
    boundary = package.get("authority_boundary", {})
    if boundary.get("framework_release_authority") is not False or "release" not in boundary.get("framework_may_not_approve", []):
        return [finding("FRAMEWORK_AS_RELEASE_AUTHORITY", "authority_boundary", "Spec Kit is a workflow harness, not release authority.")]
    return []


def review_bundle(source: dict[str, Any], snapshot: dict[str, Any], package: dict[str, Any]) -> list[Finding]:
    validators: tuple[Callable[[], list[Finding]], ...] = (
        lambda: validate_snapshot(snapshot),
        lambda: validate_context(source, package),
        lambda: validate_constitution(package),
        lambda: validate_specification(package),
        lambda: validate_plan(source, package),
        lambda: validate_tasks(package),
        lambda: validate_work_units(package),
        lambda: validate_evidence(package),
        lambda: validate_convergence(package),
        lambda: validate_multi_repository(package),
        lambda: validate_agent_adapters(package),
        lambda: validate_extension_trust(package),
        lambda: validate_risk_route(package),
        lambda: validate_authority_boundary(package),
    )
    return sorted((item for validator in validators for item in validator()), key=lambda item: (item.code, item.path))


def selection_state(findings: list[Finding]) -> str:
    return "BLOCKED" if findings else "READY_FOR_OWNER_REVIEW"


def route_operating_model(signals: list[str]) -> dict[str, str]:
    signal_set = set(signals)
    consequential = bool(signal_set & {"regulated_data", "security_boundary", "ai_behavior_change"})
    controlled = bool(signal_set & {"shared_contract", "persistent_data", "public_api", "cross_repository"})
    governance_depth = "consequential" if consequential else "controlled" if controlled else "routine"
    sdd_mode = "governed" if consequential else "standard" if controlled else "lightweight"
    execution_topology = "multi_agent" if signal_set & {"cross_repository", "parallel_contracts"} else "single_agent"
    return {"governance_depth": governance_depth, "sdd_mode": sdd_mode, "execution_topology": execution_topology}


def route_operating_mode(signals: list[str]) -> str:
    """Compatibility helper; prefer route_operating_model for separate control axes."""
    return route_operating_model(signals)["sdd_mode"]


def execute_scenario(case: dict[str, Any]) -> str:
    name, data = case["name"], case["input"]
    rules = {
        "unresolved_business_decision": lambda d: "preserve_open_and_block_capability" if not d["owner_decision"] else "continue",
        "policy_conflict": lambda d: "route_accountable_owner" if d["normative_conflict"] else "continue",
        "architecture_invention": lambda d: "architecture_proposal_required" if not d["approved_architecture_basis"] else "continue",
        "task_boundary": lambda d: "awu_enrichment_required" if not d["agent_work_unit_present"] else "continue",
        "repository_drift": lambda d: "targeted_rediscovery_required" if d["planned_revision"] != d["current_revision"] and d["affected_scope"] else "drift_outside_scope_recorded" if d["planned_revision"] != d["current_revision"] else "continue",
        "nfr_change": lambda d: "protected_target_change" if d["approved_target"] != d["generated_target"] else "continue",
        "evidence_laundering": lambda d: "completion_report_not_conformance" if not d["independent_evidence"] else "continue",
        "template_drift": lambda d: "template_semantic_regression_stop_rollout" if d["baseline_digest"] != d["candidate_digest"] or d["baseline_semantics"] != d["candidate_semantics"] else "continue",
    }
    return rules[name](data)


def run_conformance_suite() -> dict[str, Any]:
    suite = read_json(ROOT / "conformance-suite.json")
    results = [{"id": c["id"], "expected": c["expected"], "observed": execute_scenario(c)} for c in suite["cases"]]
    return {"passed": sum(r["expected"] == r["observed"] for r in results), "total": len(results), "results": results}


def apply_mutation(name: str, package: dict[str, Any], snapshot: dict[str, Any]) -> None:
    spec, plan, tasks = package["specification"], package["plan"], package["tasks"]
    mutations: dict[str, Callable[[], None]] = {
        "unpin_snapshot": lambda: snapshot.__setitem__("release", "latest"),
        "drop_snapshot_source": lambda: snapshot.__setitem__("official_source", None),
        "drop_command": lambda: snapshot.__setitem__("core_commands", [c for c in snapshot["core_commands"] if c != "speckit.clarify"]),
        "corrupt_digest": lambda: snapshot["template_digests"].__setitem__("spec-template.md", "bad"),
        "wrong_context": lambda: package["context"].__setitem__("context_id", "CTX-OLD"),
        "drop_source": lambda: package["context"].__setitem__("source_ids", package["context"]["source_ids"][:-1]),
        "unversion_policy": lambda: package["context"].__setitem__("policy_references", ["AI-030"]),
        "stale_plan_revision": lambda: plan["repository_freshness"].update({"observed_revision": "repo-docs@old", "current_revision": "repo-docs@a17-training", "changed_paths": ["src/documents/models.py"], "decision": "TARGETED_REDISCOVERY_REQUIRED"}),
        "constitution_launders_policy": lambda: package["constitution_principles"][2].__setitem__("kind", "PROJECT_OWNED"),
        "framework_owner": lambda: package["constitution_principles"][0].__setitem__("owner", "Spec Kit"),
        "invalid_req_id": lambda: spec["requirements"][0].__setitem__("id", "Requirement 1"),
        "req_missing_source": lambda: spec["requirements"][0].__setitem__("source", None),
        "collapse_open_question": lambda: spec.__setitem__("open_questions", []),
        "unblock_open_capability": lambda: spec["capability_gates"].__setitem__("automatic_requirement_satisfaction", "READY"),
        "drop_population": lambda: spec.__setitem__("supported_population", []),
        "unknown_acceptance_req": lambda: spec["acceptance_criteria"][0].__setitem__("requirement_ids", ["REQ-UNKNOWN"]),
        "drop_disposition": lambda: plan.__setitem__("requirement_dispositions", plan["requirement_dispositions"][:-1]),
        "orphan_plan_work": lambda: plan["work_items"][0].__setitem__("basis", []),
        "self_approve_arch": lambda: plan["architecture_changes"][0].update({"status": "APPROVED", "approved_by": "Spec Kit"}),
        "duplicate_ocr": lambda: plan.__setitem__("duplicate_capabilities", ["existing_ocr"]),
        "protected_plan_change": lambda: plan.__setitem__("protected_decision_changes", ["authorization_semantics"]),
        "unknown_task_req": lambda: tasks[0].__setitem__("basis", ["REQ-UNKNOWN"]),
        "orphan_task": lambda: tasks[0].__setitem__("basis", []),
        "missing_awu_link": lambda: tasks[0].__setitem__("work_unit_id", None),
        "task_protected_write": lambda: tasks[5].__setitem__("writable_paths", ["src/underwriting/submission.py"]),
        "new_dep_no_proposal": lambda: tasks[0].update({"new_dependency": True, "dependency_proposal_id": None}),
        "drop_wu_stop": lambda: package["work_units"][0].__setitem__("stop_conditions", []),
        "widen_wu_authority": lambda: package["work_units"][0].__setitem__("may_not_decide", ["policy_exception"]),
        "self_report_conformance": lambda: package["evidence_manifest"]["records"][0].__setitem__("result", "conformance_pass"),
        "stale_evidence": lambda: package["evidence_manifest"]["records"][1].__setitem__("subject_revision", "stale"),
        "converge_mutates_spec": lambda: package["convergence"].__setitem__("spec_mutations", ["weaken-review"]),
        "child_contradiction": lambda: package["multi_repository"]["children"][0].__setitem__("semantic_overrides", ["skip-review"]),
        "stale_agent_adapter": lambda: package["agent_instruction_adapters"]["generated"][0].__setitem__("source_revision", "old"),
        "enable_unvetted_catalog": lambda: package["extension_trust"]["catalogs"][1].__setitem__("install_allowed", True),
        "agent_risk": lambda: package["risk_route"].__setitem__("determined_by", "coding_agent"),
        "framework_release": lambda: package["authority_boundary"].__setitem__("framework_release_authority", True),
    }
    mutations[name]()


def run_evaluation() -> dict[str, Any]:
    source, base_snapshot, base_package = load_source(), load_snapshot(), load_reference()
    cases = read_json(ROOT / "evaluation-cases.json")["cases"]
    results = []
    for case in cases:
        snapshot, package = copy.deepcopy(base_snapshot), copy.deepcopy(base_package)
        apply_mutation(case["mutation"], package, snapshot)
        observed = {item.code for item in review_bundle(source, snapshot, package)}
        results.append({**case, "passed": case["expected"] in observed, "observed": sorted(observed)})
    return {"passed": sum(r["passed"] for r in results), "total": len(results), "results": results}


def run_demo() -> dict[str, Any]:
    source, snapshot = load_source(), load_snapshot()
    reference_findings = review_bundle(source, snapshot, load_reference())
    candidate_findings = review_bundle(source, snapshot, load_candidate())
    conformance, evaluation = run_conformance_suite(), run_evaluation()
    return {
        "reference": {"state": selection_state(reference_findings), "findings": [f.code for f in reference_findings]},
        "candidate": {"state": selection_state(candidate_findings), "finding_count": len(candidate_findings), "findings": sorted({f.code for f in candidate_findings})},
        "conformance": {"passed": conformance["passed"], "total": conformance["total"]},
        "evaluation": {"passed": evaluation["passed"], "total": evaluation["total"]},
        "authority_boundary": "Framework and agents propose; trusted controls validate, authorize, execute, produce evidence, and release.",
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
