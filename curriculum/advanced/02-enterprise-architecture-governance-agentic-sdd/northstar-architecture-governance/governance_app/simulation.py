"""Real-Git Northstar scenarios, adversarial evaluations, and metrics."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from .control_plane import ArchitectureControlPlane
from .exceptions import exception_subject_digest
from .models import ArchitectureError, ConformanceReport, Observation
from .registry import current_head, sign_payload

NOW = "2026-11-03T18:00:00Z"
FUTURE = "2026-12-31T23:59:59Z"


def _run(repo: Path, *args: str) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-11-03T10:00:00-08:00",
        "GIT_COMMITTER_DATE": "2026-11-03T10:00:00-08:00",
    }
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def initialize_repository(root: Path, destination: Path) -> tuple[str, str]:
    shutil.copytree(root / "repositories" / "ai-service", destination)
    _run(destination, "init", "-q", "-b", "main")
    _run(destination, "config", "user.name", "Course 26 Fixture")
    _run(destination, "config", "user.email", "course26@example.invalid")
    _run(destination, "add", ".")
    _run(destination, "commit", "-q", "-m", "baseline architecture")
    baseline = current_head(destination)
    _write(destination, "docs/change-note.md", "Candidate change derived from a governed work unit.\n")
    _run(destination, "add", ".")
    _run(destination, "commit", "-q", "-m", "clean candidate")
    return baseline, current_head(destination)


def _direct_provider(repo: Path) -> None:
    _write(
        repo,
        "src/classification/provider.py",
        '"""Forbidden direct provider integration."""\nimport provider_sdk\n\ndef classify(text):\n    return provider_sdk.classify(text)\n',
    )


def _generic_http(repo: Path) -> None:
    _write(
        repo,
        "src/classification/provider.py",
        '"""Destination is assembled at runtime and requires egress evidence."""\nimport httpx\n\ndef classify(url, text):\n    return httpx.post(url, json={"text": text})\n',
    )
    _write(
        repo,
        "config/egress-evidence.json",
        '{"verified": true, "producer": "candidate-self-report"}\n',
    )


def _endpoint_bypass(repo: Path) -> None:
    _write(
        repo,
        "src/classification/provider.py",
        'import httpx\nENDPOINT = "https://model-provider.example/v1/classify"\n\ndef classify(text):\n    return httpx.post(ENDPOINT, json={"text": text})\n',
    )


def _layer_violation(repo: Path) -> None:
    _write(repo, "src/domain/risk.py", "from src.infrastructure.database import connection\n\ndef assess():\n    return connection()\n")


def _private_database(repo: Path) -> None:
    _write(repo, "src/classification/private_data.py", "import underwriting_database\n\ndef load():\n    return underwriting_database.read_all()\n")


def _unapproved_vector(repo: Path) -> None:
    path = repo / "requirements.txt"
    path.write_text(path.read_text(encoding="utf-8") + "pinecone-client==5.0.0\n", encoding="utf-8")


def _policy_shadow(repo: Path) -> None:
    _write(repo, "architecture-policy.json", '{"EA-001": "disabled by candidate"}\n')


def _conflicting_adr(repo: Path) -> None:
    _write(
        repo,
        "architecture/adr-proposal.json",
        json.dumps(
            {
                "id": "ADR-LOCAL-900",
                "decision_type": "dependency_selection",
                "capability": "model_inference",
                "selected_dependency": "provider_sdk",
                "boundary": "model_provider_access",
                "status": "PROPOSED",
                "scope": "solution",
                "decision": "call provider directly",
                "conflicts_with": ["EA-001"],
            },
            indent=2,
        ) + "\n",
    )


def _superseded_adr(repo: Path) -> None:
    _write(repo, "architecture/context.json", '{"adr_refs": ["ADR-027"]}\n')


def _cycle(repo: Path) -> None:
    _write(
        repo,
        "service-dependencies.json",
        json.dumps(
            {
                "edges": [
                    {"source": "ai-service", "target": "document-service", "mode": "async"},
                    {"source": "document-service", "target": "audit-service", "mode": "async"},
                    {"source": "audit-service", "target": "ai-service", "mode": "async"},
                ]
            },
            indent=2,
        ) + "\n",
    )


MUTATIONS: dict[str, Callable[[Path], None]] = {
    "clean": lambda repo: None,
    "direct_provider": _direct_provider,
    "endpoint_bypass": _endpoint_bypass,
    "generic_http": _generic_http,
    "layer_violation": _layer_violation,
    "private_database": _private_database,
    "unapproved_vector": _unapproved_vector,
    "policy_shadow": _policy_shadow,
    "conflicting_adr": _conflicting_adr,
    "superseded_adr": _superseded_adr,
    "cycle": _cycle,
}


def mutate_and_commit(repo: Path, mutation: str) -> str:
    MUTATIONS[mutation](repo)
    if mutation != "clean":
        _run(repo, "add", ".")
        _run(repo, "commit", "-q", "-m", f"candidate: {mutation}")
    return current_head(repo)


def exception_for(
    plane: ArchitectureControlPlane,
    observation: Observation,
    finding_index: int = 0,
    *,
    environment: str | None = None,
    expires_at: str = FUTURE,
    status: str = "APPROVED",
    resource: str | None = None,
    subject_digest: str | None = None,
) -> dict[str, Any]:
    preliminary = plane.evaluate(observation, NOW)
    finding = [item for item in preliminary.findings if item.disposition == "BLOCK"][finding_index]
    payload = {
        "exception_id": "ARCH-EX-2601",
        "rule_id": finding.rule_id,
        "resource": resource or finding.resource,
        "environment": environment or observation.environment,
        "approved_subject_digest": subject_digest or exception_subject_digest(observation, finding),
        "issued_at": "2026-11-01T00:00:00Z",
        "expires_at": expires_at,
        "status": status,
        "authority_key_id": "architecture-board-v1",
        "compensating_controls": [
            {"control": "egress allowlist", "evidence_id": "NET-EGRESS-2601"},
            {"control": "daily access review", "evidence_id": "REVIEW-2601"},
        ],
    }
    return {
        "payload": payload,
        "signature": sign_payload(payload, plane.exception_keys["architecture-board-v1"]),
    }


def control_evidence_for(
    plane: ArchitectureControlPlane,
    observation: Observation,
    exception_record: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create training-only signed receipts from an authority separate from the approver."""

    exception_payload = exception_record["payload"]
    records = []
    for control in exception_payload["compensating_controls"]:
        payload = {
            "evidence_id": control["evidence_id"],
            "producer": plane.control_evidence_producer,
            "control": control["control"],
            "exception_id": exception_payload["exception_id"],
            "rule_id": exception_payload["rule_id"],
            "resource": exception_payload["resource"],
            "environment": observation.environment,
            "approved_subject_digest": exception_payload["approved_subject_digest"],
            "result": "PASS",
            "issued_at": "2026-11-02T00:00:00Z",
            "expires_at": FUTURE,
        }
        records.append(
            {"payload": payload, "signature": sign_payload(payload, plane.control_evidence_key)}
        )
    return records


def _scenario(
    root: Path,
    mutation: str,
    environment: str = "development",
    exception_variant: str | None = None,
) -> ConformanceReport:
    plane = ArchitectureControlPlane(root)
    with tempfile.TemporaryDirectory(prefix="course26-git-") as temporary:
        repo = Path(temporary) / "ai-service"
        base, clean_head = initialize_repository(root, repo)
        head = clean_head if mutation == "clean" else mutate_and_commit(repo, mutation)
        observation = plane.observe(repo, base, head, environment, NOW)
        exceptions: list[dict[str, Any]] = []
        control_evidence: list[dict[str, Any]] = []
        if exception_variant:
            options: dict[str, Any] = {}
            if exception_variant == "expired":
                options["expires_at"] = "2026-11-02T00:00:00Z"
            elif exception_variant == "wrong_environment":
                options["environment"] = "production"
            elif exception_variant == "wrong_subject":
                options["subject_digest"] = "sha256:wrong"
            elif exception_variant == "revoked":
                options["status"] = "REVOKED"
            record = exception_for(plane, observation, **options)
            exceptions.append(record)
            control_evidence.extend(control_evidence_for(plane, observation, record))
        return plane.evaluate(observation, NOW, exceptions, control_evidence)


GOLDEN_SCENARIOS = (
    ("clean-gateway", "clean", "development", None, "CONFORMANT"),
    ("direct-provider", "direct_provider", "development", None, "BLOCKED"),
    ("generic-http", "generic_http", "development", None, "INSUFFICIENT_EVIDENCE"),
    ("layer-violation", "layer_violation", "development", None, "BLOCKED"),
    ("private-database", "private_database", "development", None, "BLOCKED"),
    ("unapproved-vector", "unapproved_vector", "development", None, "REVIEW_REQUIRED"),
    ("valid-dev-exception", "direct_provider", "development", "valid", "CONFORMANT_WITH_EXCEPTION"),
    ("expired-exception", "direct_provider", "development", "expired", "BLOCKED"),
    ("wrong-environment", "direct_provider", "development", "wrong_environment", "BLOCKED"),
    ("policy-shadow", "policy_shadow", "development", None, "BLOCKED"),
    ("conflicting-adr", "conflicting_adr", "development", None, "REVIEW_REQUIRED"),
    ("superseded-adr", "superseded_adr", "development", None, "REASSESSMENT_REQUIRED"),
    ("new-cycle", "cycle", "development", None, "BLOCKED"),
)


def run_golden_scenarios(root: Path) -> list[dict[str, Any]]:
    results = []
    for scenario_id, mutation, environment, exception_variant, expected in GOLDEN_SCENARIOS:
        report = _scenario(root, mutation, environment, exception_variant)
        results.append(
            {
                "scenario_id": scenario_id,
                "expected": expected,
                "actual": report.decision,
                "passed": report.decision == expected,
                "finding_codes": [item.code for item in report.findings],
                "head_commit": report.head_commit,
                "policy_version": report.policy_version,
            }
        )
    return results


def run_adversarial_evaluations(root: Path) -> dict[str, Any]:
    cases = [
        ("clean-control", "clean", None, "CONFORMANT"),
        ("provider-import", "direct_provider", None, "BLOCKED"),
        ("provider-url", "endpoint_bypass", None, "BLOCKED"),
        ("ambiguous-http", "generic_http", None, "INSUFFICIENT_EVIDENCE"),
        ("domain-infra", "layer_violation", None, "BLOCKED"),
        ("private-db", "private_database", None, "BLOCKED"),
        ("new-database", "unapproved_vector", None, "REVIEW_REQUIRED"),
        ("valid-exception", "direct_provider", "valid", "CONFORMANT_WITH_EXCEPTION"),
        ("expired-exception", "direct_provider", "expired", "BLOCKED"),
        ("wrong-env-exception", "direct_provider", "wrong_environment", "BLOCKED"),
        ("wrong-subject-exception", "direct_provider", "wrong_subject", "BLOCKED"),
        ("revoked-exception", "direct_provider", "revoked", "BLOCKED"),
        ("candidate-policy", "policy_shadow", None, "BLOCKED"),
        ("enterprise-conflict", "conflicting_adr", None, "REVIEW_REQUIRED"),
        ("obsolete-adr", "superseded_adr", None, "REASSESSMENT_REQUIRED"),
        ("dependency-cycle", "cycle", None, "BLOCKED"),
    ]
    results = []
    for case_id, mutation, exception_variant, expected in cases:
        actual = _scenario(root, mutation, "development", exception_variant).decision
        results.append({"case_id": case_id, "expected": expected, "actual": actual, "passed": actual == expected})
    passed = sum(item["passed"] for item in results)
    known_violations = [item for item in results if item["expected"] != "CONFORMANT"]
    caught = sum(item["passed"] for item in known_violations)
    clean = [item for item in results if item["expected"] == "CONFORMANT"]
    false_positives = sum(item["actual"] != "CONFORMANT" for item in clean)
    return {
        "cases": results,
        "metrics": {
            "exact_decision_accuracy": passed / len(results),
            "known_violation_recall": caught / len(known_violations),
            "clean_control_false_positive_rate": false_positives / len(clean),
            "exception_validation_accuracy": sum(item["passed"] for item in results if "exception" in item["case_id"]) / 5,
            "counts": {"passed": passed, "total": len(results), "known_violations": len(known_violations)},
            "limitations": "Training-fixture metrics are not production performance claims.",
        },
    }


def demonstrate_stale_report(root: Path) -> str:
    plane = ArchitectureControlPlane(root)
    with tempfile.TemporaryDirectory(prefix="course26-stale-") as temporary:
        repo = Path(temporary) / "ai-service"
        base, head = initialize_repository(root, repo)
        report = plane.analyze(repo, base, head, "development", NOW)
        _write(repo, "docs/new-change.md", "This commit invalidates the previous report.\n")
        _run(repo, "add", ".")
        _run(repo, "commit", "-q", "-m", "advance head")
        try:
            plane.verify_report_binding(report, repo)
        except ArchitectureError as error:
            return error.code
    return "NOT_REJECTED"


def run_reference(root: Path) -> dict[str, Any]:
    golden = run_golden_scenarios(root)
    adversarial = run_adversarial_evaluations(root)
    plane = ArchitectureControlPlane(root)
    return {
        "course": 26,
        "policy_version": plane.policy_version,
        "golden_scenarios": golden,
        "golden_passed": all(item["passed"] for item in golden),
        "adversarial_evaluation": adversarial,
        "stale_report_result": demonstrate_stale_report(root),
        "retrieval_change_impact": plane.impact("ADR-028-RETRIEVAL-PLATFORM"),
    }
