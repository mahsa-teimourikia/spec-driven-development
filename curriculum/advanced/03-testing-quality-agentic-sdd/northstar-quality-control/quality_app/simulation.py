"""Deterministic Course 27 quality scenarios and adversarial evaluations."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .control_plane import QualityControlPlane
from .models import QualityError, SubjectObservation
from .registry import digest_payload, sign_payload

NOW = "2026-11-08T18:00:00Z"
FUTURE = "2026-12-31T23:59:59Z"


def subject_for(plane: QualityControlPlane) -> SubjectObservation:
    subject = SubjectObservation(
        change_id="AI-2700",
        repository="northstar-classification-service",
        revision="9c7a2d1" * 5 + "9c7a2"[:5],
        specification_revision="CLASSIFICATION-SPEC@7",
        implementation_digest="sha256:" + "a1" * 32,
        policy_version=plane.policy_version,
        producer=plane.observation_producer,
        issued_at=NOW,
    )
    return replace(subject, signature=sign_payload(subject.payload(), plane.observation_key))


def passing_cases() -> list[dict[str, Any]]:
    rows = [
        ("CASE-UNIT-001", "unit", ["REQ-QUALITY-001"], "specification"),
        ("CASE-PROPERTY-001", "property", ["REQ-QUALITY-001"], "independent_reference"),
        ("CASE-NEGATIVE-001", "negative", ["REQ-QUALITY-001"], "specification"),
        ("CASE-CONTRACT-001", "contract", ["REQ-QUALITY-002"], "contract"),
        ("CASE-INTEGRATION-001", "integration", ["REQ-QUALITY-002"], "contract"),
        ("CASE-NEGATIVE-002", "negative", ["REQ-QUALITY-002"], "specification"),
        ("CASE-FAILURE-001", "failure", ["REQ-QUALITY-003"], "specification"),
        ("CASE-RECOVERY-001", "recovery", ["REQ-QUALITY-003"], "specification"),
    ]
    return [
        {
            "case_id": case_id,
            "kind": kind,
            "requirement_ids": requirement_ids,
            "oracle_source": oracle,
            "result": "PASS",
            "runs": ["PASS"],
        }
        for case_id, kind, requirement_ids, oracle in rows
    ]


def evidence_for(
    plane: QualityControlPlane,
    subject: SubjectObservation,
    *,
    producer: str | None = None,
    subject_digest: str | None = None,
    suite_revision: str | None = None,
    cases: list[dict[str, Any]] | None = None,
    mutations: list[dict[str, str]] | None = None,
    faults: list[dict[str, str]] | None = None,
    expires_at: str = FUTURE,
) -> dict[str, Any]:
    payload = {
        "evidence_id": "QUALITY-EVIDENCE-2700",
        "producer": producer or plane.evidence_producer,
        "subject_digest": subject_digest or digest_payload(subject.payload()),
        "policy_version": plane.policy_version,
        "suite_revision": suite_revision or plane.policy["suite_revision"],
        "issued_at": "2026-11-08T17:00:00Z",
        "expires_at": expires_at,
        "cases": passing_cases() if cases is None else cases,
        "mutations": mutations if mutations is not None else [
            {"mutation_id": item, "outcome": "KILLED"}
            for item in plane.policy["required_mutations"]
        ],
        "fault_experiments": faults if faults is not None else [
            {"experiment_id": item, "outcome": "SAFE"}
            for item in plane.policy["required_fault_experiments"]
        ],
    }
    key = plane.evidence_key if payload["producer"] == plane.evidence_producer else "candidate-key"
    return {"payload": payload, "signature": sign_payload(payload, key)}


def run_scenario(root: Path, scenario_id: str) -> dict[str, Any]:
    plane = QualityControlPlane(root)
    subject = subject_for(plane)
    evidence = evidence_for(plane, subject)
    if scenario_id == "candidate-only":
        evidence = evidence_for(plane, subject, producer="candidate-agent")
    elif scenario_id == "forged":
        evidence["signature"] = "hmac-sha256:forged"
    elif scenario_id == "wrong-subject":
        evidence = evidence_for(plane, subject, subject_digest="sha256:wrong")
    elif scenario_id == "stale-suite":
        evidence = evidence_for(plane, subject, suite_revision="NORTHSTAR-QUALITY-SUITE@0")
    elif scenario_id == "failed-test":
        cases = passing_cases()
        cases[4] = {**cases[4], "result": "FAIL", "runs": ["FAIL"]}
        evidence = evidence_for(plane, subject, cases=cases)
    elif scenario_id == "missing-negative":
        cases = [case for case in passing_cases() if case["kind"] != "negative"]
        evidence = evidence_for(plane, subject, cases=cases)
    elif scenario_id == "surviving-mutant":
        mutations = [
            {"mutation_id": item, "outcome": "SURVIVED" if item == "REMOVE_AUTHORIZATION" else "KILLED"}
            for item in plane.policy["required_mutations"]
        ]
        evidence = evidence_for(plane, subject, mutations=mutations)
    elif scenario_id == "flaky":
        cases = passing_cases()
        cases[0] = {**cases[0], "runs": ["PASS", "FAIL"]}
        evidence = evidence_for(plane, subject, cases=cases)
    elif scenario_id == "unsafe-failure":
        faults = [
            {"experiment_id": item, "outcome": "UNSAFE" if item == "STALE_APPROVAL" else "SAFE"}
            for item in plane.policy["required_fault_experiments"]
        ]
        evidence = evidence_for(plane, subject, faults=faults)
    elif scenario_id == "missing-failure":
        evidence = evidence_for(plane, subject, faults=[])
    elif scenario_id == "unknown-requirement":
        cases = passing_cases()
        cases[0] = {**cases[0], "requirement_ids": ["REQ-UNKNOWN"]}
        evidence = evidence_for(plane, subject, cases=cases)
    report = plane.evaluate(subject, [evidence], NOW)
    return {
        "scenario_id": scenario_id,
        "decision": report.decision,
        "finding_codes": [item.code for item in report.findings],
        "coverage": report.coverage,
        "metrics": report.metrics,
        "release_authorized": report.release_authorized,
    }


GOLDEN = {
    "passing": "QUALITY_EVIDENCE_ACCEPTED",
    "candidate-only": "INSUFFICIENT_EVIDENCE",
    "forged": "INSUFFICIENT_EVIDENCE",
    "wrong-subject": "INSUFFICIENT_EVIDENCE",
    "stale-suite": "INSUFFICIENT_EVIDENCE",
    "failed-test": "BLOCKED",
    "missing-negative": "INSUFFICIENT_EVIDENCE",
    "surviving-mutant": "BLOCKED",
    "flaky": "REVIEW_REQUIRED",
    "unsafe-failure": "BLOCKED",
    "missing-failure": "INSUFFICIENT_EVIDENCE",
    "unknown-requirement": "BLOCKED",
}


def run_golden(root: Path) -> list[dict[str, Any]]:
    results = []
    for scenario_id, expected in GOLDEN.items():
        result = run_scenario(root, scenario_id)
        result["expected"] = expected
        result["passed"] = result["decision"] == expected
        results.append(result)
    return results


def run_evaluation(root: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    sequence = list(GOLDEN.items()) * 2
    for index, (scenario_id, expected) in enumerate(sequence, start=1):
        actual = run_scenario(root, scenario_id)["decision"]
        cases.append(
            {
                "case_id": f"EVAL-{index:03d}",
                "scenario": scenario_id,
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )
    passed = sum(item["passed"] for item in cases)
    unsafe_cases = [item for item in cases if item["expected"] == "BLOCKED"]
    return {
        "cases": cases,
        "metrics": {
            "exact_decision_accuracy": {
                "numerator": passed,
                "denominator": len(cases),
                "value": passed / len(cases),
            },
            "unsafe_case_recall": {
                "numerator": sum(item["passed"] for item in unsafe_cases),
                "denominator": len(unsafe_cases),
                "value": sum(item["passed"] for item in unsafe_cases) / len(unsafe_cases),
            },
            "claim": "labelled deterministic fixture coverage, not general production quality accuracy",
        },
    }


def demonstrate_subject_tamper(root: Path) -> str:
    plane = QualityControlPlane(root)
    tampered = replace(subject_for(plane), implementation_digest="sha256:tampered")
    try:
        plane.evaluate(tampered, [], NOW)
    except QualityError as error:
        return error.code
    return "NOT_REJECTED"


def run_reference(root: Path) -> dict[str, Any]:
    golden = run_golden(root)
    evaluation = run_evaluation(root)
    return {
        "course": 27,
        "thesis": "Passing tests become credible only when independent evidence is traceable, exact-subject, current, and capable of detecting specified failures.",
        "golden": golden,
        "golden_passed": all(item["passed"] for item in golden),
        "evaluation": evaluation,
        "subject_tamper_result": demonstrate_subject_tamper(root),
    }
