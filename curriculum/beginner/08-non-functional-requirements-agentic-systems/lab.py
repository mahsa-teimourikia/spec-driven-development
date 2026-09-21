"""Deterministic Course 08 lab for measurable agentic-system NFRs.

The fixtures are synthetic and credential-free. They teach how to define,
measure, and govern non-functional requirements; they are not production
telemetry, capacity proof, model-quality evidence, or deployment approval.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

LESSON_ROOT = Path(__file__).resolve().parent
SCENARIO_ROOT = LESSON_ROOT / "northstar-broker-nfrs"
REFERENCE_ROOT = SCENARIO_ROOT / "reference"
CONTRACT_PATH = REFERENCE_ROOT / "nfr-contract.json"
WORKLOAD_PATH = SCENARIO_ROOT / "workload-profiles.json"
RUNTIME_PATH = SCENARIO_ROOT / "synthetic-runtime-events.json"
QUALITY_PATH = SCENARIO_ROOT / "synthetic-quality-cases.json"
TARGET_DECISIONS_PATH = REFERENCE_ROOT / "target-decisions.json"
MEASUREMENT_PLAN_PATH = REFERENCE_ROOT / "measurement-plan.json"
DEGRADATION_POLICY_PATH = REFERENCE_ROOT / "degradation-policy.json"
AGENT_BUDGET_PATH = REFERENCE_ROOT / "agent-budget.json"


class Severity(str, Enum):
    REVIEW = "review"
    STOP = "stop"


class GateDecision(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_MEASURED = "not_measured"


@dataclass(frozen=True)
class Finding:
    code: str
    subject_id: str
    message: str
    severity: Severity = Severity.STOP


@dataclass(frozen=True)
class GateResult:
    requirement_id: str
    decision: GateDecision
    reason_codes: tuple[str, ...]
    observed: float | int | None = None
    target: float | int | None = None
    numerator: int | None = None
    denominator: int | None = None


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract() -> dict[str, Any]:
    return load_json(CONTRACT_PATH)


def load_workloads() -> dict[str, Any]:
    return load_json(WORKLOAD_PATH)


def load_runtime_events() -> list[dict[str, Any]]:
    return load_json(RUNTIME_PATH)["events"]


def load_quality_cases() -> list[dict[str, Any]]:
    return load_json(QUALITY_PATH)["cases"]


def load_target_decisions() -> dict[str, Any]:
    return load_json(TARGET_DECISIONS_PATH)


def nearest_rank(values: Iterable[float], percentile: float) -> float | None:
    """Return the nearest-rank percentile for a finite observed population."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in (0, 100]")
    rank = max(1, math.ceil(percentile / 100 * len(ordered)))
    return ordered[rank - 1]


def validate_workload_profiles(workloads: dict[str, Any] | None = None) -> tuple[Finding, ...]:
    workloads = workloads or load_workloads()
    findings: list[Finding] = []
    profiles = workloads.get("profiles", [])
    identifiers = [str(item.get("id")) for item in profiles]
    if len(identifiers) != len(set(identifiers)):
        findings.append(Finding("WORKLOAD_ID_DUPLICATE", "profiles", "Workload profile IDs must be unique."))
    if "W1" not in identifiers:
        findings.append(Finding("WORKLOAD_W1_MISSING", "profiles", "The pilot workload W1 is required."))
    for profile in profiles:
        identifier = str(profile.get("id", "unknown"))
        required = {
            "id", "status", "source", "requests_per_minute", "concurrency",
            "response_mix", "eligible_population", "limitations",
        }
        missing = sorted(required - set(profile))
        if missing:
            findings.append(Finding("WORKLOAD_FIELDS_MISSING", identifier, f"Missing: {', '.join(missing)}."))
            continue
        rates = profile["requests_per_minute"]
        concurrency = profile["concurrency"]
        if rates.get("sustained", 0) <= 0 or rates.get("peak", 0) < rates.get("sustained", 0):
            findings.append(Finding("WORKLOAD_RATE_INVALID", identifier, "Peak must be at least sustained and both must be positive."))
        if concurrency.get("typical", 0) <= 0 or concurrency.get("peak", 0) < concurrency.get("typical", 0):
            findings.append(Finding("WORKLOAD_CONCURRENCY_INVALID", identifier, "Peak concurrency must be at least typical concurrency."))
        mix_total = sum(float(value) for value in profile.get("response_mix", {}).values())
        if not math.isclose(mix_total, 1.0, abs_tol=1e-9):
            findings.append(Finding("WORKLOAD_MIX_INVALID", identifier, f"Response mix sums to {mix_total:.3f}, not 1.0."))
    return tuple(findings)


def validate_nfr_contract(
    contract: dict[str, Any] | None = None,
    decisions: dict[str, Any] | None = None,
) -> tuple[Finding, ...]:
    contract = contract or load_contract()
    decisions = decisions or load_target_decisions()
    findings: list[Finding] = []
    requirements = contract.get("requirements", [])
    identifiers = [str(item.get("id")) for item in requirements]
    if len(identifiers) != len(set(identifiers)):
        findings.append(Finding("NFR_ID_DUPLICATE", "contract", "NFR IDs must be unique."))

    decision_index = {str(item.get("id")): item for item in decisions.get("decisions", [])}
    allowed_statuses = {"target_approved", "target_unresolved", "invariant"}
    allowed_directions = {"maximum", "minimum", "exact", "prohibited"}
    vague_only = {"fast", "scalable", "secure", "reliable", "cost-effective", "highly available"}
    required = {
        "id", "characteristic", "statement", "population", "measurement",
        "target", "owner", "criticality", "failure_behavior", "evidence_methods",
    }
    for item in requirements:
        identifier = str(item.get("id", "unknown"))
        missing = sorted(required - set(item))
        if missing:
            findings.append(Finding("NFR_FIELDS_MISSING", identifier, f"Missing: {', '.join(missing)}."))
            continue
        if str(item.get("statement", "")).strip().lower() in vague_only:
            findings.append(Finding("NFR_VAGUE", identifier, "A quality adjective is not a measurable contract."))
        if not item.get("population"):
            findings.append(Finding("NFR_POPULATION_MISSING", identifier, "Measurement population is required."))
        measurement = item.get("measurement", {})
        for field in ("metric", "unit", "method", "window"):
            if not measurement.get(field):
                findings.append(Finding("NFR_MEASUREMENT_INCOMPLETE", identifier, f"Measurement field {field} is required."))
        target = item.get("target", {})
        status = target.get("status")
        if status not in allowed_statuses:
            findings.append(Finding("NFR_TARGET_STATUS_UNKNOWN", identifier, "Target status is not controlled."))
        if target.get("direction") not in allowed_directions:
            findings.append(Finding("NFR_TARGET_DIRECTION_UNKNOWN", identifier, "Target direction is not controlled."))
        if status == "target_unresolved":
            if target.get("value") is not None or target.get("decision_id") is not None:
                findings.append(Finding("NFR_UNRESOLVED_TARGET_HAS_VALUE", identifier, "An unresolved target cannot smuggle in a value or approval."))
        else:
            decision_id = target.get("decision_id")
            decision = decision_index.get(str(decision_id))
            if target.get("value") is None:
                findings.append(Finding("NFR_TARGET_VALUE_MISSING", identifier, "Approved targets and invariants need an explicit value."))
            if not decision or decision.get("status") != "approved":
                findings.append(Finding("NFR_TARGET_AUTHORITY_MISSING", identifier, "The target lacks an approved owner decision."))
            elif (
                decision.get("requirement_id") != identifier
                or decision.get("value") != target.get("value")
                or decision.get("unit") != target.get("unit")
            ):
                findings.append(Finding("NFR_TARGET_DECISION_MISMATCH", identifier, "The target does not match its approved decision."))
            elif not decision.get("owner") or not decision.get("rationale") or not decision.get("evidence_ids"):
                findings.append(Finding("NFR_TARGET_PROVENANCE_INCOMPLETE", identifier, "The target decision needs owner, rationale, and evidence."))
        owner = item.get("owner", {})
        if not all(owner.get(role) for role in ("decision", "measurement", "response")):
            findings.append(Finding("NFR_OWNER_INCOMPLETE", identifier, "Decision, measurement, and response ownership must be explicit."))
    return tuple(findings)


def validate_measurement_plan(
    contract: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
) -> tuple[Finding, ...]:
    contract = contract or load_contract()
    plan = plan or load_json(MEASUREMENT_PLAN_PATH)
    findings: list[Finding] = []
    requirement_ids = {str(item["id"]) for item in contract.get("requirements", [])}
    entries = plan.get("measurements", [])
    mapped = {str(item.get("requirement_id")) for item in entries}
    for missing in sorted(requirement_ids - mapped):
        findings.append(Finding("NFR_MEASUREMENT_UNMAPPED", missing, "No measurement-plan entry exists."))
    for entry in entries:
        identifier = str(entry.get("requirement_id", "unknown"))
        for field in ("signal", "population", "aggregation", "producer", "retention", "limitations"):
            if not entry.get(field):
                findings.append(Finding("MEASUREMENT_PLAN_INCOMPLETE", identifier, f"Missing {field}."))
        if entry.get("content_capture") not in {"none", "redacted", "allowlisted"}:
            findings.append(Finding("MEASUREMENT_CONTENT_POLICY_UNKNOWN", identifier, "Telemetry content policy must be controlled."))
    return tuple(findings)


def _eligible(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if event.get("eligible") and event.get("workload_profile") == "W1"]


def telemetry_event_findings(event: dict[str, Any]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    identifier = str(event.get("event_id", "unknown"))
    required = {
        "event_id", "request_id", "run_id", "workflow_version", "policy_version",
        "model_route", "outcome", "reason_code", "latency_ms", "attempts",
        "tool_calls", "model_turns", "input_tokens", "output_tokens", "cost_usd",
    }
    missing = sorted(field for field in required if event.get(field) in (None, ""))
    if missing:
        findings.append(Finding("TELEMETRY_REQUIRED_FIELD_MISSING", identifier, f"Missing: {', '.join(missing)}."))
    if event.get("raw_broker_content_logged"):
        findings.append(Finding("TELEMETRY_RAW_CONTENT_EXPOSED", identifier, "Raw broker content must not be recorded."))
    if event.get("secret_logged"):
        findings.append(Finding("TELEMETRY_SECRET_EXPOSED", identifier, "Secrets must not be recorded."))
    return tuple(findings)


def agent_budget_findings(
    event: dict[str, Any],
    budget: dict[str, Any] | None = None,
) -> tuple[Finding, ...]:
    budget = budget or load_json(AGENT_BUDGET_PATH)
    limits = budget["limits"]
    mapping = {
        "attempts": "provider_attempts",
        "tool_calls": "tool_calls",
        "model_turns": "model_turns",
        "latency_ms": "wall_clock_ms",
        "input_tokens": "input_tokens",
        "output_tokens": "output_tokens",
        "authoritative_mutations": "authoritative_mutations",
        "external_broker_messages": "external_broker_messages",
    }
    findings: list[Finding] = []
    for event_field, limit_field in mapping.items():
        limit = limits[limit_field]
        if limit.get("status") == "target_unresolved":
            continue
        if int(event.get(event_field, 0)) > int(limit["value"]):
            findings.append(
                Finding(
                    "AGENT_BUDGET_EXCEEDED",
                    str(event.get("event_id", "unknown")),
                    f"{event_field}={event.get(event_field)} exceeds {limit_field}={limit['value']}.",
                )
            )
    return tuple(findings)


def validate_agent_budget(
    budget: dict[str, Any] | None = None,
    decisions: dict[str, Any] | None = None,
) -> tuple[Finding, ...]:
    """Validate provenance and surface unresolved limits without inventing values."""
    budget = budget or load_json(AGENT_BUDGET_PATH)
    decisions = decisions or load_target_decisions()
    decision_index = {str(item.get("id")): item for item in decisions.get("decisions", [])}
    findings: list[Finding] = []
    for name, limit in budget.get("limits", {}).items():
        status = limit.get("status")
        if status == "target_unresolved":
            if limit.get("value") is not None or limit.get("decision_id") is not None:
                findings.append(Finding("AGENT_BUDGET_UNRESOLVED_HAS_VALUE", name, "An unresolved budget cannot contain a value or decision."))
            elif not limit.get("unit") or not limit.get("owner") or not limit.get("evidence_needed"):
                findings.append(Finding("AGENT_BUDGET_UNRESOLVED_PROVENANCE_INCOMPLETE", name, "An unresolved budget still needs a unit, decision owner, and evidence needed."))
            else:
                findings.append(
                    Finding(
                        "AGENT_BUDGET_TARGET_UNRESOLVED",
                        name,
                        "The budget is measured but not enforceable for production autonomy until its owner approves a value.",
                        Severity.REVIEW,
                    )
                )
            continue
        if status not in {"target_approved", "invariant"}:
            findings.append(Finding("AGENT_BUDGET_STATUS_UNKNOWN", name, "Budget status is not controlled."))
            continue
        decision = decision_index.get(str(limit.get("decision_id")))
        if (
            not decision
            or decision.get("status") != "approved"
            or decision.get("requirement_id") != limit.get("requirement_id")
            or decision.get("value") != limit.get("value")
            or decision.get("unit") != limit.get("unit")
            or decision.get("owner") != limit.get("owner")
            or not decision.get("rationale")
            or not decision.get("evidence_ids")
        ):
            findings.append(Finding("AGENT_BUDGET_DECISION_MISMATCH", name, "The governed budget lacks matching owner-decision provenance."))
    return tuple(findings)


def runtime_measurements(events: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    population = _eligible(events or load_runtime_events())
    good_outcomes = {"valid_proposal", "approved_graceful_degradation"}
    semantic_successes = [event for event in population if event.get("outcome") in good_outcomes]
    compliant = [
        event
        for event in semantic_successes
        if not telemetry_event_findings(event)
        and not agent_budget_findings(event)
    ]
    latency = [float(event["latency_ms"]) for event in population]
    traceable = [event for event in population if not telemetry_event_findings(event)]
    sensitive_events = [
        event for event in population
        if event.get("raw_broker_content_logged") or event.get("secret_logged")
    ]
    total_cost = sum(float(event["cost_usd"]) for event in population)
    stage_names = sorted({stage for event in population for stage in event.get("stage_latency_ms", {})})
    stage_means = {
        stage: round(sum(float(event.get("stage_latency_ms", {}).get(stage, 0)) for event in population) / len(population), 3)
        for stage in stage_names
    } if population else {}
    return {
        "evidence_status": "synthetic_training_fixture_not_production_evidence",
        "population": {"workload_profile": "W1", "eligible_events": len(population)},
        "end_to_end_latency_ms": {
            "p50": nearest_rank(latency, 50),
            "p95": nearest_rank(latency, 95),
            "p99": nearest_rank(latency, 99),
            "sample_size": len(latency),
            "denominator": len(latency),
            "source": "synthetic_course08_runtime_fixture",
            "boundary": "accepted_request_to_completed_proposal_response",
            "representativeness": "small_fixture_percentiles_are_pedagogical_not_statistically_representative",
        },
        "mean_stage_latency_ms": stage_means,
        "semantic_service_success_ratio": {
            "numerator": len(semantic_successes),
            "denominator": len(population),
            "value": len(semantic_successes) / len(population) if population else None,
            "semantic_success_definition": sorted(good_outcomes),
            "excludes_control_compliance": True,
        },
        "compliant_workflow_success_ratio": {
            "numerator": len(compliant),
            "denominator": len(population),
            "value": len(compliant) / len(population) if population else None,
            "definition": "semantic_service_success_and_all_governed_telemetry_privacy_and_agent_budget_controls_pass",
        },
        "control_violating_semantic_successes": {
            "numerator": len(semantic_successes) - len(compliant),
            "denominator": len(semantic_successes),
            "value": len(semantic_successes) - len(compliant),
        },
        "telemetry_completeness_ratio": {
            "numerator": len(traceable),
            "denominator": len(population),
            "value": len(traceable) / len(population) if population else None,
        },
        "budget_conformance_ratio": {
            "numerator": sum(not agent_budget_findings(event) for event in population),
            "denominator": len(population),
            "value": (sum(not agent_budget_findings(event) for event in population) / len(population)) if population else None,
            "scope": "governed_limits_only; unresolved limits are measured but not enforced",
        },
        "sensitive_telemetry_events": {
            "numerator": len(sensitive_events),
            "denominator": len(population),
            "value": len(sensitive_events),
        },
        "authoritative_mutations_per_workflow": {
            "maximum": max((int(event.get("authoritative_mutations", 0)) for event in population), default=None),
            "denominator": len(population),
        },
        "provider_attempts_per_workflow": {
            "maximum": max((int(event.get("attempts", 0)) for event in population), default=None),
            "denominator": len(population),
        },
        "cost_usd": {
            "total": round(total_cost, 6),
            "per_request": round(total_cost / len(population), 6) if population else None,
            "per_successful_compliant_workflow": round(total_cost / len(compliant), 6) if compliant else None,
            "successful_compliant_denominator": len(compliant),
            "attribution_boundary": "model_inference_and_declared_tool_api_costs_in_the_fixture",
            "included_components": ["model_inference", "declared_tool_api_calls"],
            "excluded_components": ["retrieval_infrastructure", "compute", "telemetry", "storage", "human_review"],
            "comparability_rule": "Compare cost results only when attribution boundaries match.",
        },
    }


def quality_measurements(cases: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    population = list(cases or load_quality_cases())
    passed = [case for case in population if case.get("governed_decision_correct")]
    slices: dict[str, dict[str, Any]] = {}
    for risk in sorted({str(case["risk_slice"]) for case in population}):
        members = [case for case in population if case["risk_slice"] == risk]
        numerator = sum(bool(case.get("governed_decision_correct")) for case in members)
        slices[risk] = {
            "numerator": numerator,
            "denominator": len(members),
            "value": numerator / len(members) if members else None,
        }
    return {
        "evaluation_mode": "fixed_prediction_pipeline_exercise",
        "claim": "pipeline_mechanics_only_not_model_quality",
        "overall": {
            "numerator": len(passed),
            "denominator": len(population),
            "value": len(passed) / len(population) if population else None,
        },
        "slices": slices,
    }


def simulate_provider_outage(
    requests: int = 100,
    *,
    retry_budget: int | None,
    circuit_breaker_threshold: int | None,
) -> dict[str, Any]:
    """Count provider attempts during a complete outage; no external calls occur."""
    if requests < 0:
        raise ValueError("requests cannot be negative")
    if retry_budget is None:
        attempts = requests * 6  # deliberately unsafe teaching baseline: initial + five retries
        return {
            "policy": "unsafe_unbounded_by_contract_baseline",
            "provider_attempts": attempts,
            "amplification_factor": attempts / requests if requests else 0,
            "circuit_state": "absent",
            "manual_routes": 0,
            "work_items_preserved": 0,
        }
    if retry_budget < 1 or circuit_breaker_threshold is None or circuit_breaker_threshold < 1:
        raise ValueError("governed policy needs positive attempt and circuit limits")
    maximum = requests * retry_budget
    attempts = min(maximum, circuit_breaker_threshold)
    return {
        "policy": "bounded_retry_with_circuit_breaker",
        "provider_attempts": attempts,
        "amplification_factor": attempts / requests if requests else 0,
        "circuit_state": "open" if requests and attempts >= circuit_breaker_threshold else "closed",
        "manual_routes": requests,
        "work_items_preserved": requests,
    }


def degradation_decision(
    dependency: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = policy or load_json(DEGRADATION_POLICY_PATH)
    rule = next((item for item in policy.get("dependencies", []) if item.get("dependency") == dependency), None)
    if rule is None:
        return {
            "dependency": dependency,
            "mode": "UNAVAILABLE",
            "automatic_mutation": False,
            "preserve_work_item": True,
            "reason_code": "DEPENDENCY_POLICY_UNKNOWN",
            "recovery_condition": {
                "predicate": "an accountable owner defines and verifies the dependency-specific recovery condition",
                "anti_flap": "manual restoration only",
                "preserved_work_re_evaluation": "required",
            },
        }
    return {
        "dependency": dependency,
        "mode": rule["failure_mode"],
        "automatic_mutation": bool(rule["automatic_mutation"]),
        "preserve_work_item": bool(rule["preserve_work_item"]),
        "reason_code": rule["reason_code"],
        "criticality": rule["criticality"],
        "continuation_condition": rule["continuation_condition"],
        "recovery_condition": rule["recovery_condition"],
    }


def target_gates(
    contract: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
    quality: dict[str, Any] | None = None,
    capacity_evidence: dict[str, Any] | None = None,
) -> tuple[GateResult, ...]:
    contract = contract or load_contract()
    runtime = runtime or runtime_measurements()
    quality = quality or quality_measurements()
    observed = {
        "end_to_end_latency_ms.p95": runtime["end_to_end_latency_ms"]["p95"],
        "semantic_service_success_ratio": runtime["semantic_service_success_ratio"]["value"],
        "provider_attempts.max": runtime["provider_attempts_per_workflow"]["maximum"],
        "authoritative_mutations_per_workflow.max": runtime["authoritative_mutations_per_workflow"]["maximum"],
        "telemetry_completeness_ratio": runtime["telemetry_completeness_ratio"]["value"],
        "cost_per_successful_compliant_workflow": runtime["cost_usd"]["per_successful_compliant_workflow"],
        "quality_safe_decision_ratio": quality["overall"]["value"],
        "model_facing_authoritative_credentials": 0,
        "model_facing_mutation_boundary_bypass_paths": 0,
        "sensitive_telemetry_events": runtime["sensitive_telemetry_events"]["value"],
        "sustained_requests_per_minute": capacity_evidence.get("sustained_requests_per_minute") if capacity_evidence else None,
    }
    results: list[GateResult] = []
    for item in contract.get("requirements", []):
        identifier = str(item["id"])
        target = item["target"]
        metric = str(item["measurement"]["metric"])
        value = observed.get(metric)
        ratio = runtime.get(metric, {}) if isinstance(runtime.get(metric), dict) else {}
        if target["status"] == "target_unresolved":
            results.append(GateResult(identifier, GateDecision.BLOCKED, ("TARGET_NOT_AUTHORIZED",), observed=value))
            continue
        if value is None:
            reason = "CAPACITY_LOAD_EVIDENCE_ABSENT" if identifier == "CAP-BR-001" else "MEASUREMENT_ABSENT"
            results.append(GateResult(identifier, GateDecision.NOT_MEASURED, (reason,), target=target["value"]))
            continue
        direction = target["direction"]
        threshold = target["value"]
        passed = {
            "maximum": value <= threshold,
            "minimum": value >= threshold,
            "exact": value == threshold,
            "prohibited": value == 0,
        }[direction]
        reason_codes = ("TARGET_MET",) if passed else ("TARGET_MISSED",)
        if identifier == "CAP-BR-001" and capacity_evidence:
            constraints = item["measurement"].get("required_constraint_results", [])
            supplied = capacity_evidence.get("constraint_results", {})
            failed_constraints = [requirement_id for requirement_id in constraints if supplied.get(requirement_id) != "pass"]
            if capacity_evidence.get("source_status") != "representative_load_test":
                passed = False
                reason_codes = ("CAPACITY_EVIDENCE_NOT_REPRESENTATIVE",)
            elif not passed:
                reason_codes = ("CAPACITY_DEMAND_NOT_MET",)
            elif failed_constraints:
                passed = False
                reason_codes = ("CAPACITY_QUALITY_CONSTRAINT_FAILED",)
        results.append(
            GateResult(
                identifier,
                GateDecision.PASS if passed else GateDecision.FAIL,
                reason_codes,
                observed=value,
                target=threshold,
                numerator=ratio.get("numerator"),
                denominator=ratio.get("denominator"),
            )
        )
    return tuple(results)


def release_assessment(
    gates: Iterable[GateResult] | None = None,
    budget_findings: Iterable[Finding] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate_list = tuple(gates or target_gates())
    budget_finding_list = tuple(budget_findings if budget_findings is not None else validate_agent_budget())
    runtime = runtime or runtime_measurements()
    counts = {decision.value: sum(gate.decision == decision for gate in gate_list) for decision in GateDecision}
    blockers = sorted(
        {
            reason
            for gate in gate_list
            if gate.decision in {GateDecision.FAIL, GateDecision.BLOCKED, GateDecision.NOT_MEASURED}
            for reason in gate.reason_codes
        }
        | {"SYNTHETIC_FIXTURE_NOT_PRODUCTION_EVIDENCE"}
    )
    capacity_gate = next((gate for gate in gate_list if gate.requirement_id == "CAP-BR-001"), None)
    if capacity_gate is None or capacity_gate.decision != GateDecision.PASS:
        blockers.append("CAPACITY_LOAD_TEST_NOT_EXECUTED")
    if any(item.code == "AGENT_BUDGET_TARGET_UNRESOLVED" for item in budget_finding_list):
        blockers.append("AGENT_BUDGET_TARGETS_UNRESOLVED")
    if runtime["control_violating_semantic_successes"]["value"]:
        blockers.append("CONTROL_VIOLATING_SEMANTIC_SUCCESS")
    blockers = sorted(set(blockers))
    return {
        "decision": "blocked_for_production",
        "production_ready": False,
        "claim": "nfr_contract_and_measurement_pipeline_exercised_only",
        "gate_counts": counts,
        "blockers": blockers,
        "interpretation": "Passing synthetic targets demonstrates contract mechanics, not deployed SLO attainment or production fitness.",
    }


def run_demo() -> dict[str, Any]:
    runtime = runtime_measurements()
    quality = quality_measurements()
    gates = target_gates(runtime=runtime, quality=quality)
    unsafe = simulate_provider_outage(retry_budget=None, circuit_breaker_threshold=None)
    governed = simulate_provider_outage(retry_budget=3, circuit_breaker_threshold=8)
    budget_policy_findings = validate_agent_budget()
    return {
        "fixture_status": "synthetic_training_fixture_not_production_evidence",
        "contract_findings": [asdict(item) for item in validate_nfr_contract()],
        "workload_findings": [asdict(item) for item in validate_workload_profiles()],
        "measurement_plan_findings": [asdict(item) for item in validate_measurement_plan()],
        "budget_policy_findings": [asdict(item) for item in budget_policy_findings],
        "runtime_measurements": runtime,
        "quality_measurements": quality,
        "resilience_experiment": {"unsafe": unsafe, "governed": governed},
        "degradation": {
            dependency: degradation_decision(dependency)
            for dependency in ("authorization", "model_provider", "policy_service", "analytics_export")
        },
        "target_gates": [asdict(item) for item in gates],
        "release_assessment": release_assessment(gates, budget_policy_findings, runtime),
    }


def main() -> None:
    print(json.dumps(run_demo(), indent=2))


if __name__ == "__main__":
    main()
