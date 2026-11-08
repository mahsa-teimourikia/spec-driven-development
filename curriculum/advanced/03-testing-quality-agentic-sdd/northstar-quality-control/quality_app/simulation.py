"""Course 27 golden scenarios and adversarial quality-gate evaluation."""

from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator

from .behavior_harness import execute_protected_checks
from .control_plane import QualityControlPlane
from .evaluation_engine import compare_models
from .evidence_registry import NOW, build_evidence, subject_for
from .models import QualityError, SubjectObservation
from .oracle_registry import OracleRegistry
from .registry import digest_payload, sign_payload
from .repository_harness import RevisionFixture, create_revision_fixture


GOLDEN = {
    "clean-candidate": "CONFORMANT",
    "ambiguity-bypass": "BLOCKED",
    "tenant-leak": "BLOCKED",
    "unauthorized-state-mutation": "BLOCKED",
    "duplicate-concurrent-event": "BLOCKED",
    "idempotency-conflict-accepted": "BLOCKED",
    "expired-approval-accepted": "BLOCKED",
    "missing-provenance": "BLOCKED",
    "unsupported-citation": "BLOCKED",
    "oracle-weakened": "INSUFFICIENT_EVIDENCE",
    "mandatory-test-deleted": "INSUFFICIENT_EVIDENCE",
    "stale-subject": "STALE_EVIDENCE",
    "protected-slice-regression": "BLOCKED",
    "unknown-impact": "INSUFFICIENT_EVIDENCE",
    "flaky-protected-test": "REVIEW_REQUIRED",
}

EXTRA_SCENARIOS = {
    "forged-evidence": "INSUFFICIENT_EVIDENCE",
    "candidate-only": "INSUFFICIENT_EVIDENCE",
    "stale-suite": "STALE_EVIDENCE",
    "missing-failure-experiment": "INSUFFICIENT_EVIDENCE",
    "unsafe-review-outage": "BLOCKED",
    "malformed-evidence": "INSUFFICIENT_EVIDENCE",
    "stale-policy": "STALE_EVIDENCE",
    "unknown-requirement": "BLOCKED",
    "evidence-id-collision": "BLOCKED",
}

ADVERSARIAL_CASES = [
    ("ADV-001", "clean-candidate"),
    ("ADV-002", "clean-candidate"),
    ("ADV-003", "clean-candidate"),
    ("ADV-004", "ambiguity-bypass"),
    ("ADV-005", "ambiguity-bypass"),
    ("ADV-006", "ambiguity-bypass"),
    ("ADV-007", "tenant-leak"),
    ("ADV-008", "tenant-leak"),
    ("ADV-009", "tenant-leak"),
    ("ADV-010", "unauthorized-state-mutation"),
    ("ADV-011", "unauthorized-state-mutation"),
    ("ADV-012", "unauthorized-state-mutation"),
    ("ADV-013", "duplicate-concurrent-event"),
    ("ADV-014", "duplicate-concurrent-event"),
    ("ADV-015", "duplicate-concurrent-event"),
    ("ADV-016", "idempotency-conflict-accepted"),
    ("ADV-017", "idempotency-conflict-accepted"),
    ("ADV-018", "idempotency-conflict-accepted"),
    ("ADV-019", "expired-approval-accepted"),
    ("ADV-020", "expired-approval-accepted"),
    ("ADV-021", "expired-approval-accepted"),
    ("ADV-022", "missing-provenance"),
    ("ADV-023", "missing-provenance"),
    ("ADV-024", "missing-provenance"),
    ("ADV-025", "unsupported-citation"),
    ("ADV-026", "unsupported-citation"),
    ("ADV-027", "unsupported-citation"),
    ("ADV-028", "oracle-weakened"),
    ("ADV-029", "mandatory-test-deleted"),
    ("ADV-030", "stale-subject"),
    ("ADV-031", "protected-slice-regression"),
    ("ADV-032", "unknown-impact"),
    ("ADV-033", "flaky-protected-test"),
    ("ADV-034", "forged-evidence"),
    ("ADV-035", "candidate-only"),
    ("ADV-036", "stale-suite"),
    ("ADV-037", "missing-failure-experiment"),
    ("ADV-038", "unsafe-review-outage"),
    ("ADV-039", "malformed-evidence"),
    ("ADV-040", "stale-policy"),
    ("ADV-041", "unknown-requirement"),
    ("ADV-042", "evidence-id-collision"),
]

MUTANT_SCENARIOS = {
    "ambiguity-bypass": ("IGNORE_AMBIGUITY", "CASE-QI001-PROPERTY"),
    "tenant-leak": ("REMOVE_TENANT_FILTER", "CASE-QI002-SECURITY"),
    "unauthorized-state-mutation": ("ALLOW_AI_STATE_MUTATION", "CASE-QI003-NEGATIVE"),
    "duplicate-concurrent-event": ("DROP_IDEMPOTENCY_KEY", "CASE-QI004-CONCURRENCY"),
    "idempotency-conflict-accepted": ("DROP_IDEMPOTENCY_KEY", "CASE-QI004-RECOVERY"),
    "expired-approval-accepted": ("ACCEPT_EXPIRED_APPROVAL", "CASE-QI003-INTEGRATION"),
    "missing-provenance": ("DROP_EVIDENCE_REFERENCES", "CASE-QI005-CONTRACT"),
}


@contextmanager
def quality_context(root: Path) -> Iterator[dict[str, Any]]:
    plane = QualityControlPlane(root)
    registry = OracleRegistry(root)
    evaluation = compare_models(root)
    with TemporaryDirectory(prefix="course27-revisions-") as directory:
        fixture = create_revision_fixture(root, Path(directory))
        subject = subject_for(plane, fixture, registry, evaluation)
        evidence, observations = build_evidence(plane, subject, fixture, evaluation)
        yield {
            "plane": plane,
            "registry": registry,
            "evaluation": evaluation,
            "fixture": fixture,
            "subject": subject,
            "evidence": evidence,
            "observations": observations,
        }


def _resign(context: dict[str, Any], record: dict[str, Any]) -> None:
    record["signature"] = sign_payload(record["payload"], context["plane"].evidence_key)


def _fail_case(record: dict[str, Any], case_id: str) -> None:
    case = next(item for item in record["payload"]["cases"] if item["case_id"] == case_id)
    case["result"] = "FAIL"
    case["runs"] = ["FAIL"]


def _changed_subject(context: dict[str, Any]) -> SubjectObservation:
    subject = replace(
        context["subject"],
        revision="sha256:post-evidence-revision",
        component_commits=tuple(
            (service, ("f" * 40 if service == "review-service" else revision))
            for service, revision in context["subject"].component_commits
        ),
    )
    return replace(subject, signature=sign_payload(subject.payload(), context["plane"].observation_key))


def run_scenario_in_context(context: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    plane: QualityControlPlane = context["plane"]
    subject: SubjectObservation = context["subject"]
    record = deepcopy(context["evidence"])
    records = [record]

    if scenario_id in MUTANT_SCENARIOS:
        mutant, case_id = MUTANT_SCENARIOS[scenario_id]
        actual = execute_protected_checks(context["fixture"], mutant=mutant)
        _fail_case(record, case_id)
        mutation = next(
            item for item in record["payload"]["mutations"] if item["mutation_id"] == mutant
        )
        mutation["outcome"] = "SURVIVED"
        mutation["observed_checks"] = actual["checks"]
        _resign(context, record)
    elif scenario_id in {"unsupported-citation", "protected-slice-regression"}:
        _fail_case(record, "CASE-QI005-EVALUATION")
        _resign(context, record)
    elif scenario_id == "oracle-weakened":
        record["payload"]["cases"][0]["oracle_source"] = "candidate"
        _resign(context, record)
    elif scenario_id == "mandatory-test-deleted":
        record["payload"]["cases"] = [
            item for item in record["payload"]["cases"] if item["kind"] != "negative"
        ]
        _resign(context, record)
    elif scenario_id == "stale-subject":
        subject = _changed_subject(context)
    elif scenario_id == "unknown-impact":
        record["payload"]["cases"] = [
            item for item in record["payload"]["cases"] if item["kind"] not in {"integration", "failure"}
        ]
        _resign(context, record)
    elif scenario_id == "flaky-protected-test":
        record["payload"]["cases"][0]["runs"] = ["PASS", "FAIL", "PASS"]
        _resign(context, record)
    elif scenario_id == "forged-evidence":
        record["signature"] = "hmac-sha256:forged"
    elif scenario_id == "candidate-only":
        record["payload"]["producer"] = "candidate-agent"
        record["signature"] = sign_payload(record["payload"], "candidate-key")
    elif scenario_id == "stale-suite":
        record["payload"]["suite_revision"] = "NORTHSTAR-QUALITY-SUITE@1"
        _resign(context, record)
    elif scenario_id == "missing-failure-experiment":
        record["payload"]["fault_experiments"] = []
        _resign(context, record)
    elif scenario_id == "unsafe-review-outage":
        fault = next(
            item for item in record["payload"]["fault_experiments"]
            if item["experiment_id"] == "REVIEW_SERVICE_UNAVAILABLE"
        )
        fault["outcome"] = "UNSAFE"
        _resign(context, record)
    elif scenario_id == "malformed-evidence":
        record["payload"]["cases"] = "not-a-list"
        _resign(context, record)
    elif scenario_id == "stale-policy":
        record["payload"]["policy_version"] = "QUALITY-POLICY@1"
        _resign(context, record)
    elif scenario_id == "unknown-requirement":
        record["payload"]["cases"][0]["requirement_ids"] = ["QI-UNKNOWN"]
        _resign(context, record)
    elif scenario_id == "evidence-id-collision":
        conflicting = deepcopy(record)
        conflicting["payload"]["cases"][0]["runs"] = ["PASS", "PASS"]
        _resign(context, conflicting)
        records.append(conflicting)
    elif scenario_id != "clean-candidate":
        raise QualityError("SCENARIO_UNKNOWN", scenario_id)

    report = plane.evaluate(subject, records, NOW)
    return {
        "scenario_id": scenario_id,
        "decision": report.decision,
        "finding_codes": [item.code for item in report.findings],
        "coverage": report.coverage,
        "metrics": report.metrics,
        "delivery_state": report.delivery_state,
        "release_authorized": report.release_authorized,
    }


def run_scenario(root: Path, scenario_id: str) -> dict[str, Any]:
    with quality_context(root) as context:
        return run_scenario_in_context(context, scenario_id)


def run_golden(root: Path, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if context is None:
        with quality_context(root) as created:
            return run_golden(root, created)
    results = []
    for scenario_id, expected in GOLDEN.items():
        result = run_scenario_in_context(context, scenario_id)
        result["expected"] = expected
        result["passed"] = result["decision"] == expected
        results.append(result)
    return results


def run_evaluation(root: Path, context: dict[str, Any] | None = None) -> dict[str, Any]:
    if context is None:
        with quality_context(root) as created:
            return run_evaluation(root, created)
    cache: dict[str, str] = {}
    cases: list[dict[str, Any]] = []
    all_expected = {**GOLDEN, **EXTRA_SCENARIOS}
    for case_id, scenario_id in ADVERSARIAL_CASES:
        if scenario_id not in cache:
            cache[scenario_id] = run_scenario_in_context(context, scenario_id)["decision"]
        actual = cache[scenario_id]
        expected = all_expected[scenario_id]
        cases.append(
            {
                "case_id": case_id,
                "scenario": scenario_id,
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )
    passed = sum(item["passed"] for item in cases)
    critical = [item for item in cases if item["expected"] == "BLOCKED"]
    clean = [item for item in cases if item["expected"] == "CONFORMANT"]
    return {
        "cases": cases,
        "metrics": {
            "exact_decision_accuracy": {
                "numerator": passed,
                "denominator": len(cases),
                "value": passed / len(cases),
            },
            "protected_invariant_detection": {
                "numerator": sum(item["passed"] for item in critical),
                "denominator": len(critical),
                "value": sum(item["passed"] for item in critical) / len(critical),
            },
            "clean_control_false_positives": {
                "numerator": sum(item["actual"] != "CONFORMANT" for item in clean),
                "denominator": len(clean),
                "value": sum(item["actual"] != "CONFORMANT" for item in clean) / len(clean),
            },
            "claim": "42 labelled deterministic fixture decisions, not general defect-detection accuracy",
        },
    }


def demonstrate_subject_tamper(root: Path) -> str:
    with quality_context(root) as context:
        tampered = replace(context["subject"], implementation_digest="sha256:tampered")
        try:
            context["plane"].evaluate(tampered, [], NOW)
        except QualityError as error:
            return error.code
    return "NOT_REJECTED"


def run_reference(root: Path) -> dict[str, Any]:
    with quality_context(root) as context:
        report = context["plane"].evaluate(context["subject"], [context["evidence"]], NOW)
        golden = run_golden(root, context)
        evaluation = run_evaluation(root, context)
        return {
            "course": 27,
            "change_id": "AI-2605",
            "thesis": "Independent quality evidence must execute protected behavior against exact revisions without granting release authority.",
            "quality_decision": report.decision,
            "delivery_state": report.delivery_state,
            "release_authorized": report.release_authorized,
            "merge_authorized": report.merge_authorized,
            "deployment_authorized": report.deployment_authorized,
            "activation_authorized": report.activation_authorized,
            "revision_set": dict(context["subject"].component_commits),
            "subject_digest": digest_payload(context["subject"].payload()),
            "quality_report": report.payload(),
            "observations": context["observations"],
            "model_comparison": context["evaluation"],
            "golden": golden,
            "golden_passed": all(item["passed"] for item in golden),
            "adversarial_evaluation": evaluation,
            "subject_tamper_result": demonstrate_subject_tamper(root),
            "limitations": [
                "The Git, SQLite, mutation, and evaluation fixtures exercise selected behaviors only.",
                "Protected holdout separation is pedagogical because repository maintainers can inspect the file.",
                "READY_FOR_INTEGRATION_REVIEW is not merge, deployment, activation, or release authorization.",
            ],
        }
