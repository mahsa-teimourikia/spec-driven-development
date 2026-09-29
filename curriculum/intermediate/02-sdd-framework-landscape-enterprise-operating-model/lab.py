"""Deterministic Course 12 framework-selection and operating-model lab.

The fixtures compare simplified workflow *styles*. They do not execute or benchmark
the named products discussed in the chapter. Framework outputs remain proposals;
trusted application controls validate semantics and accountable owners decide.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


LESSON_DIR = Path(__file__).resolve().parent
SCENARIO_DIR = LESSON_DIR / "northstar-framework-selection"
SOURCE_DIR = SCENARIO_DIR / "source"
REFERENCE_DIR = SCENARIO_DIR / "reference"
CANDIDATE_DIR = SCENARIO_DIR / "candidate"
EVALUATION_PATH = SCENARIO_DIR / "evaluation-cases.json"

REQUIRED_CANONICAL_TYPES = {
    "requirement",
    "architecture_decision",
    "implementation_plan",
    "task",
    "agent_work_unit",
    "evidence",
    "exception",
}
AUTHORITY_DOMAINS = {"BUSINESS", "POLICY", "ARCHITECTURE", "EXECUTION", "EVIDENCE", "RELEASE"}
TRANSFORMATIONS = {"specify", "plan", "tasks", "implement"}
CONTROL_BOUNDARY = (
    "framework_and_agent_outputs_are_proposals; trusted_controls_validate_and_owners_authorize"
)


class Severity(str, Enum):
    BLOCKING = "blocking"
    REVIEW = "review"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    subject: str
    message: str
    owner: str
    repair: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_bundle(*, candidate: bool = False) -> dict[str, Any]:
    directory = CANDIDATE_DIR if candidate else REFERENCE_DIR
    return {
        "source": load_json(SOURCE_DIR / "source-manifest.json"),
        "model": load_json(directory / "operating-model.json"),
        "decision": load_json(directory / "selection-decision.json"),
        "conformance": load_json(REFERENCE_DIR / "conformance-suite.json"),
    }


def _finding(
    code: str,
    severity: Severity,
    subject: str,
    message: str,
    owner: str,
    repair: str,
) -> Finding:
    return Finding(code, severity, subject, message, owner, repair)


def validate_source_equivalence(source: dict[str, Any], model: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    expected_context = source.get("context_id")
    expected_sources = {item.get("id") for item in source.get("artifacts", [])}
    for variant in model.get("variants", []):
        variant_id = str(variant.get("id", "variant"))
        if variant.get("source_context_id") != expected_context:
            findings.append(_finding(
                "SOURCE_CONTEXT_DRIFT", Severity.BLOCKING, variant_id,
                "The workflow style was evaluated with a different source context.",
                "Framework evaluation owner", "Run every variant against the same revision-bound source package.",
            ))
        if set(variant.get("source_ids", [])) != expected_sources:
            findings.append(_finding(
                "SOURCE_PACKAGE_NOT_EQUIVALENT", Severity.BLOCKING, variant_id,
                "The workflow style did not receive the same source artifacts as its peers.",
                "Framework evaluation owner", "Preserve the complete source manifest for an apples-to-apples comparison.",
            ))
    return findings


def validate_variant(variant: dict[str, Any], requirements: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    variant_id = str(variant.get("id", "variant"))
    required_ids = {item.get("id") for item in requirements}
    if set(variant.get("requirement_ids", [])) != required_ids:
        findings.append(_finding(
            "REQUIREMENT_IDENTITY_LOST", Severity.BLOCKING, variant_id,
            "Stable enterprise requirement identity was not preserved through the workflow.",
            "Requirements owner", "Carry every applicable requirement ID through specifications, plans, and evidence.",
        ))
    if not variant.get("policy_source_ids"):
        findings.append(_finding(
            "POLICY_PROVENANCE_LOST", Severity.BLOCKING, variant_id,
            "Policy text is present without authoritative source identity and revision.",
            "Policy owner", "Resolve policy externally and pass immutable source references into the workflow.",
        ))
    if not variant.get("open_question_ids"):
        findings.append(_finding(
            "OPEN_QUESTION_COLLAPSED", Severity.BLOCKING, variant_id,
            "An unresolved authorization question disappeared during transformation.",
            "Product and risk owner", "Keep uncertainty explicit and block affected work until an owner decides.",
        ))
    if variant.get("requirements_contain_architecture"):
        findings.append(_finding(
            "ARCHITECTURE_MIXED_WITH_REQUIREMENTS", Severity.REVIEW, variant_id,
            "A generated requirement silently selects technical architecture.",
            "Architecture owner", "Move the choice into a proposal or ADR and preserve the behavioral requirement.",
        ))
    execution = variant.get("execution", {})
    if execution.get("autonomous_tasks") and not execution.get("agent_work_unit_enrichment"):
        findings.append(_finding(
            "TASK_AUTHORITY_TOO_BROAD", Severity.BLOCKING, variant_id,
            "Checklist tasks are being treated as safe autonomous execution boundaries.",
            "Execution-platform owner", "Enrich tasks with scope, authority, dependencies, evidence, and stop conditions.",
        ))
    evidence = variant.get("evidence", {})
    if not evidence.get("manifest") or not evidence.get("subject_revision_binding"):
        findings.append(_finding(
            "EVIDENCE_MODEL_MISSING", Severity.BLOCKING, variant_id,
            "The workflow cannot bind conformance claims to evidence and exact subject revisions.",
            "Quality owner", "Add a provenance-bearing evidence manifest outside model self-reporting.",
        ))
    change = variant.get("change_semantics", {})
    if not change.get("current_truth") or not change.get("proposed_change"):
        findings.append(_finding(
            "CHANGE_SEMANTICS_IMPLICIT", Severity.REVIEW, variant_id,
            "Current truth and proposed change cannot be distinguished deterministically.",
            "Specification owner", "Add a change registry or explicit current-state and delta artifacts.",
        ))
    portable = set(variant.get("portable_semantics", []))
    critical = {"requirements", "authority", "decisions", "evidence", "change_history"}
    if not variant.get("critical_semantics_survive_framework_removal") or critical - portable:
        findings.append(_finding(
            "FRAMEWORK_LOCK_IN_HIGH", Severity.REVIEW, variant_id,
            "Removing the framework would erase normative meaning or decision provenance.",
            "Developer-platform owner", "Keep critical semantics in portable canonical artifacts and isolate adapters.",
        ))
    if not variant.get("agent_boundary", {}).get("may_not_decide"):
        findings.append(_finding(
            "AGENT_BOUNDARY_MISSING", Severity.BLOCKING, variant_id,
            "The framework workflow does not preserve protected decisions for accountable owners.",
            "Governance owner", "Declare what agents may generate, may propose, and cannot approve.",
        ))
    return findings


def validate_artifact_registry(model: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    registry = {item.get("type"): item for item in model.get("canonical_artifact_registry", [])}
    missing = REQUIRED_CANONICAL_TYPES - set(registry)
    if missing:
        findings.append(_finding(
            "CANONICAL_ARTIFACT_TYPE_MISSING", Severity.BLOCKING, "artifact-registry",
            f"Canonical artifact types are missing: {sorted(missing)}.",
            "SDD platform owner", "Define the minimum portable enterprise artifact vocabulary.",
        ))
    for artifact_type, artifact in registry.items():
        if artifact.get("authority_domain") not in AUTHORITY_DOMAINS:
            findings.append(_finding(
                "ARTIFACT_AUTHORITY_DOMAIN_INVALID", Severity.BLOCKING, str(artifact_type),
                "The artifact has no recognized authority domain.",
                "Governance owner", "Map the artifact to business, policy, architecture, execution, evidence, or release authority.",
            ))
    task = registry.get("task", {})
    if task.get("normative_scope") not in {"non_normative", "derived_execution_input"}:
        findings.append(_finding(
            "TASK_MISTAKEN_FOR_BUSINESS_AUTHORITY", Severity.BLOCKING, "task",
            "A generated task is being allowed to redefine business or architecture intent.",
            "Planning owner", "Keep tasks downstream of requirements and approved architecture.",
        ))
    return findings


def validate_command_authority(model: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    commands = {item.get("stage"): item for item in model.get("command_authority_matrix", [])}
    for missing in TRANSFORMATIONS - set(commands):
        findings.append(_finding(
            "TRANSFORMATION_CONTROL_MISSING", Severity.BLOCKING, str(missing),
            "A framework transformation has no explicit authority and validation contract.",
            "SDD platform owner", "Define outputs, prohibited approvals, and validators for every transformation.",
        ))
    for stage, command in commands.items():
        if command.get("may_approve"):
            findings.append(_finding(
                "FRAMEWORK_COMMAND_SELF_APPROVES", Severity.BLOCKING, str(stage),
                "A generation command is permitted to approve its own consequential output.",
                "Governance owner", "Keep generated artifacts proposed until independent controls and owners accept them.",
            ))
        if not command.get("validators"):
            findings.append(_finding(
                "TRANSFORMATION_VALIDATION_MISSING", Severity.REVIEW, str(stage),
                "A generated artifact can flow downstream without semantic checks.",
                "Quality owner", "Attach the appropriate authority, consistency, coverage, and evidence validators.",
            ))
    return findings


def validate_extension_boundary(model: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    owners = Counter(item.get("capability") for item in model.get("authoritative_capability_owners", []))
    duplicated = sorted(capability for capability, count in owners.items() if count != 1)
    if duplicated:
        findings.append(_finding(
            "AUTHORITATIVE_OWNER_AMBIGUOUS", Severity.BLOCKING, "capability-owners",
            f"Capabilities lack exactly one authoritative owner: {duplicated}.",
            "Operating-model owner", "Assign one system of record and make all framework copies derived.",
        ))
    boundary = model.get("extension_boundary", {})
    if boundary.get("policy_propagation") == "manual_copy":
        findings.append(_finding(
            "MANUAL_POLICY_COPY", Severity.BLOCKING, "extension-boundary",
            "Enterprise policy is copied into framework files without provenance or refresh semantics.",
            "Policy platform owner", "Generate revision-bound effective context from authoritative sources.",
        ))
    if boundary.get("framework_fork_required"):
        findings.append(_finding(
            "DEEP_FRAMEWORK_FORK", Severity.REVIEW, "extension-boundary",
            "The operating model depends on a permanent fork of framework internals.",
            "Developer-platform owner", "Prefer adapters, supported extensions, and external gates; record unavoidable fork cost.",
        ))
    return findings


def validate_selection_decision(
    decision: dict[str, Any],
    requirements: list[dict[str, Any]],
    evidence_catalog: list[dict[str, Any]] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    decision_id = str(decision.get("id", "selection-decision"))
    required_ids = {item.get("id") for item in requirements}
    dispositions = {item.get("requirement_id") for item in decision.get("requirement_dispositions", [])}
    if dispositions != required_ids:
        findings.append(_finding(
            "SELECTION_REQUIREMENT_DISPOSITION_INCOMPLETE", Severity.BLOCKING, decision_id,
            "The framework decision does not disposition every enterprise requirement.",
            "Operating-model owner", "Record native, extension, external, or unsupported disposition with evidence.",
        ))
    if evidence_catalog is not None:
        evidence = {item.get("id"): item for item in evidence_catalog}
        referenced = {
            evidence_id
            for item in decision.get("requirement_dispositions", [])
            for evidence_id in item.get("evidence_ids", [])
        }
        if referenced - set(evidence):
            findings.append(_finding(
                "SELECTION_EVIDENCE_UNRESOLVED", Severity.BLOCKING, decision_id,
                "The decision cites evidence IDs that do not exist in the evidence catalog.",
                "Evidence owner", "Register every cited item with subject revision, producer, result, and fixture boundary.",
            ))
        invalid = [
            evidence_id for evidence_id in referenced & set(evidence)
            if not all(evidence[evidence_id].get(field) for field in ("subject_revision", "producer", "result"))
        ]
        if invalid:
            findings.append(_finding(
                "SELECTION_EVIDENCE_INVALID", Severity.BLOCKING, decision_id,
                f"Selection evidence lacks provenance or result fields: {sorted(invalid)}.",
                "Evidence owner", "Bind each evidence item to its exact subject, producer, and observed result.",
            ))
    if decision.get("overall_score") is not None or decision.get("claim") == "best_framework":
        findings.append(_finding(
            "FRAMEWORK_WINNER_SCORE", Severity.REVIEW, decision_id,
            "A single score hides mandatory gaps and context-specific trade-offs.",
            "Architecture review board", "Use capability profiles, mandatory gates, and explicit trade-offs instead.",
        ))
    if len(decision.get("alternatives", [])) < 2:
        findings.append(_finding(
            "SELECTION_ALTERNATIVES_MISSING", Severity.REVIEW, decision_id,
            "The selection record does not compare credible alternatives.",
            "Architecture review board", "Record options, strengths, gaps, extension cost, and rejection rationale.",
        ))
    if not decision.get("assumptions"):
        findings.append(_finding(
            "SELECTION_ASSUMPTIONS_MISSING", Severity.REVIEW, decision_id,
            "The decision omits assumptions that bound its validity.",
            "Operating-model owner", "Record repository, policy, Git, agent, and review assumptions.",
        ))
    if not decision.get("reconsideration_triggers"):
        findings.append(_finding(
            "RECONSIDERATION_TRIGGERS_MISSING", Severity.REVIEW, decision_id,
            "The framework choice has no observable review triggers.",
            "Developer-platform owner", "Define maintenance, portability, overhead, and architecture triggers.",
        ))
    if decision.get("framework_authority") not in {"workflow_harness_only", "project_change_layer"}:
        findings.append(_finding(
            "FRAMEWORK_AS_GOVERNANCE", Severity.BLOCKING, decision_id,
            "The framework is being treated as the source of enterprise authority.",
            "Governance owner", "Keep policy, ownership, exceptions, and release authority organization-owned.",
        ))
    if decision.get("status") != "ready_for_owner_review":
        findings.append(_finding(
            "SYNTHETIC_DECISION_OVERCLAIMS_APPROVAL", Severity.BLOCKING, decision_id,
            "The training fixture claims an authenticated enterprise approval it cannot possess.",
            "Accountable decision owner", "Keep the fixture ready for review, not approved or adopted.",
        ))
    return findings


def validate_upgrade_record(model: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    upgrade = model.get("framework_upgrade_assurance", {})
    if not upgrade.get("baseline_version") or not upgrade.get("candidate_version"):
        findings.append(_finding(
            "UPGRADE_BASELINE_MISSING", Severity.BLOCKING, "framework-upgrade",
            "A framework upgrade has no exact before/after versions.",
            "Developer-platform owner", "Pin both framework versions and representative project revisions.",
        ))
    if not upgrade.get("prompt_template_versions"):
        findings.append(_finding(
            "FRAMEWORK_PROMPTS_UNVERSIONED", Severity.BLOCKING, "framework-upgrade",
            "Prompts or templates can change artifact semantics without reviewable identity.",
            "SDD platform owner", "Version commands, prompts, templates, and adapter mappings as code.",
        ))
    if not upgrade.get("golden_scenario_ids"):
        findings.append(_finding(
            "UPGRADE_CONFORMANCE_NOT_RUN", Severity.REVIEW, "framework-upgrade",
            "No representative scenarios guard against semantic drift during upgrade.",
            "Quality owner", "Run simple, brownfield, regulated, conflict, and multi-agent fixtures before rollout.",
        ))
    return findings


def review_operating_model(bundle: dict[str, Any]) -> dict[str, Any]:
    model = bundle["model"]
    requirements = model.get("enterprise_requirements", [])
    findings = (
        validate_source_equivalence(bundle["source"], model)
        + [finding for variant in model.get("variants", []) for finding in validate_variant(variant, requirements)]
        + validate_artifact_registry(model)
        + validate_command_authority(model)
        + validate_extension_boundary(model)
        + validate_selection_decision(bundle["decision"], requirements, model.get("selection_evidence", []))
        + validate_upgrade_record(model)
    )
    counts = Counter(item.severity.value for item in findings)
    return {
        "findings": [asdict(item) for item in findings],
        "counts": dict(counts),
        "claim": "deterministic_fixture_review_not_vendor_certification_or_enterprise_approval",
        "control_boundary": CONTROL_BOUNDARY,
    }


def selection_state(report: dict[str, Any]) -> str:
    if report["counts"].get("blocking", 0):
        return "OPERATING_MODEL_BLOCKED"
    if report["counts"].get("review", 0):
        return "OPERATING_MODEL_REVIEW_REQUIRED"
    return "READY_FOR_OWNER_REVIEW"


def capability_profiles(model: dict[str, Any]) -> dict[str, Any]:
    profiles = []
    for variant in model.get("variants", []):
        capabilities = variant.get("capabilities", {})
        profiles.append({
            "id": variant.get("id"),
            "native": sorted(key for key, value in capabilities.items() if value == "native"),
            "extension": sorted(key for key, value in capabilities.items() if value == "extension"),
            "external": sorted(key for key, value in capabilities.items() if value == "external"),
            "unsupported": sorted(key for key, value in capabilities.items() if value == "unsupported"),
        })
    return {
        "profiles": profiles,
        "overall_ranking": None,
        "interpretation": "capability dispositions expose trade-offs; they are not an overall vendor score",
    }


def route_risk_tier(change: dict[str, Any]) -> dict[str, Any]:
    if change.get("multi_agent") or change.get("cross_repository") or change.get("irreversible"):
        tier = 4
    elif change.get("regulated_ai") or change.get("policy_exception") or change.get("sensitive_data"):
        tier = 3
    elif change.get("shared_contract") or change.get("product_behavior") or change.get("architecture_change"):
        tier = 2
    else:
        tier = 1
    modes = {
        1: "direct_or_lightweight_repo_native",
        2: "structured_spec_plan_and_bounded_work_unit",
        3: "enterprise_context_evidence_and_specialist_review",
        4: "full_orchestration_identity_contract_and_runtime_controls",
    }
    return {"tier": tier, "mode": modes[tier], "framework_selection": "context_specific_not_global"}


def transformation_assurance(stage: str, artifact: dict[str, Any]) -> list[str]:
    checks = {
        "specify": ["authority", "ambiguity", "conflicts", "open_questions", "provenance"],
        "plan": ["requirement_coverage", "orphan_work", "architecture_invention", "protected_decisions"],
        "tasks": ["scope", "justification", "dependency", "work_unit_enrichment", "stop_conditions"],
        "implement": ["subject_revision", "independent_evidence", "scope_conformance", "unresolved_risk"],
    }
    if stage not in checks:
        raise ValueError(f"unknown transformation: {stage}")
    declared = set(artifact.get("checks", []))
    return sorted(set(checks[stage]) - declared)


def _execute_golden_scenario(case: dict[str, Any]) -> str:
    inputs = case.get("inputs", {})
    kind = case.get("kind")
    if kind == "unresolved_authorization":
        return "preserve_open_question_and_block_affected_execution" if not inputs.get("authority_resolved") else "continue"
    if kind == "policy_conflict":
        return "surface_conflict_and_route_owner" if inputs.get("policy_value") != inputs.get("feature_value") else "continue"
    if kind == "architecture_invention":
        return "architecture_proposal_not_approval" if not inputs.get("approved_adr") else "continue"
    if kind == "plain_task":
        return "enrich_or_block_agent_dispatch" if not inputs.get("work_unit_boundary") else "dispatch"
    if kind == "brownfield_truth_changed":
        return "invalidate_affected_plan_and_evidence" if inputs.get("planned_revision") != inputs.get("current_revision") else "retain"
    if kind == "prompt_semantic_change":
        baseline = stable_digest(inputs.get("baseline_template", ""))
        candidate = stable_digest(inputs.get("candidate_template", ""))
        return "stop_rollout_and_review_semantic_diff" if baseline != candidate else "continue_rollout"
    return "unsupported_scenario"


def run_conformance_suite(suite: dict[str, Any]) -> dict[str, Any]:
    cases = suite.get("scenarios", [])
    results = []
    for case in cases:
        observed = _execute_golden_scenario(case)
        passed = observed == case.get("expected_outcome")
        results.append({"id": case.get("id"), "observed": observed, "passed": passed})
    passed = sum(1 for item in results if item["passed"])
    return {
        "population": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
        "claim": "synthetic_golden_scenarios_not_production_framework_certification",
    }


def migration_survivability(variant: dict[str, Any]) -> dict[str, Any]:
    retained = set(variant.get("portable_semantics", []))
    critical = {"requirements", "authority", "decisions", "evidence", "change_history"}
    lost = sorted(critical - retained)
    return {
        "retained": sorted(retained & critical),
        "lost": lost,
        "decision": "PORTABLE" if not lost else "MIGRATION_REVIEW_REQUIRED",
    }


def _mutated_bundle(case: dict[str, Any]) -> dict[str, Any]:
    bundle = copy.deepcopy(load_bundle())
    model = bundle["model"]
    decision = bundle["decision"]
    mutation = case["mutation"]
    variant = model["variants"][0]
    if mutation == "drop_source_context":
        variant["source_context_id"] = "CTX-OTHER"
    elif mutation == "drop_source_artifact":
        variant["source_ids"] = variant["source_ids"][:-1]
    elif mutation == "drop_requirement_ids":
        variant["requirement_ids"] = []
    elif mutation == "drop_policy_sources":
        variant["policy_source_ids"] = []
    elif mutation == "collapse_open_question":
        variant["open_question_ids"] = []
    elif mutation == "mix_architecture":
        variant["requirements_contain_architecture"] = True
    elif mutation == "autonomous_plain_tasks":
        variant["execution"].update(autonomous_tasks=True, agent_work_unit_enrichment=False)
    elif mutation == "drop_evidence_manifest":
        variant["evidence"]["manifest"] = False
    elif mutation == "drop_revision_binding":
        variant["evidence"]["subject_revision_binding"] = False
    elif mutation == "hide_current_truth":
        variant["change_semantics"]["current_truth"] = None
    elif mutation == "framework_only_semantics":
        variant["critical_semantics_survive_framework_removal"] = False
    elif mutation == "drop_agent_boundary":
        variant["agent_boundary"]["may_not_decide"] = []
    elif mutation == "remove_registry_type":
        model["canonical_artifact_registry"] = model["canonical_artifact_registry"][:-1]
    elif mutation == "invalid_authority_domain":
        model["canonical_artifact_registry"][0]["authority_domain"] = "FRAMEWORK"
    elif mutation == "task_business_normative":
        next(item for item in model["canonical_artifact_registry"] if item["type"] == "task")["normative_scope"] = "business"
    elif mutation == "command_self_approves":
        model["command_authority_matrix"][0]["may_approve"] = True
    elif mutation == "command_has_no_validators":
        model["command_authority_matrix"][0]["validators"] = []
    elif mutation == "duplicate_capability_owner":
        model["authoritative_capability_owners"].append(copy.deepcopy(model["authoritative_capability_owners"][0]))
    elif mutation == "manual_policy_copy":
        model["extension_boundary"]["policy_propagation"] = "manual_copy"
    elif mutation == "deep_fork":
        model["extension_boundary"]["framework_fork_required"] = True
    elif mutation == "overall_winner_score":
        decision["overall_score"] = 94
    elif mutation == "remove_alternatives":
        decision["alternatives"] = []
    elif mutation == "remove_assumptions":
        decision["assumptions"] = []
    elif mutation == "remove_reconsideration":
        decision["reconsideration_triggers"] = []
    elif mutation == "framework_is_governance":
        decision["framework_authority"] = "enterprise_governance"
    elif mutation == "claim_approval":
        decision["status"] = "approved"
    elif mutation == "drop_disposition":
        decision["requirement_dispositions"] = decision["requirement_dispositions"][:-1]
    elif mutation == "drop_upgrade_baseline":
        model["framework_upgrade_assurance"]["baseline_version"] = None
    elif mutation == "unversion_prompts":
        model["framework_upgrade_assurance"]["prompt_template_versions"] = []
    elif mutation == "skip_golden_scenarios":
        model["framework_upgrade_assurance"]["golden_scenario_ids"] = []
    else:
        raise ValueError(f"unknown mutation: {mutation}")
    return bundle


def evaluate_rules() -> dict[str, Any]:
    evaluation = load_json(EVALUATION_PATH)
    true_positive = false_positive = false_negative = exact = 0
    details = []
    for case in evaluation.get("cases", []):
        report = review_operating_model(_mutated_bundle(case))
        actual = {item["code"] for item in report["findings"]}
        expected = set(case.get("expected_codes", []))
        true_positive += len(actual & expected)
        false_positive += len(actual - expected)
        false_negative += len(expected - actual)
        exact += actual == expected
        details.append({"id": case["id"], "expected": sorted(expected), "actual": sorted(actual)})
    population = len(details)
    return {
        "population": population,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "exact_matches": {"numerator": exact, "denominator": population},
        "details": details,
        "claim": "labelled_mutation_fixture_coverage_not_general_framework_quality_accuracy",
    }


def run_demo() -> dict[str, Any]:
    reference = load_bundle()
    candidate = load_bundle(candidate=True)
    reference_report = review_operating_model(reference)
    candidate_report = review_operating_model(candidate)
    return {
        "fixture_status": "fictional_training_scenario",
        "observed_at": reference["model"].get("observed_at"),
        "reference": {"state": selection_state(reference_report), **reference_report},
        "candidate": {"state": selection_state(candidate_report), **candidate_report},
        "capability_profiles": capability_profiles(reference["model"]),
        "conformance": run_conformance_suite(reference["conformance"]),
        "evaluation": evaluate_rules(),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, default=str))
