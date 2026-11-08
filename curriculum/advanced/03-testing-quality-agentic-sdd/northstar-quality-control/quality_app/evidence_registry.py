"""Build authenticated quality evidence from observed service behavior."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .behavior_harness import (
    execute_fault_experiments,
    execute_protected_checks,
    metamorphic_population,
    property_population,
)
from .control_plane import QualityControlPlane
from .evaluation_engine import compare_models
from .models import SubjectObservation
from .mutation_runner import execute_mutations
from .oracle_registry import OracleRegistry
from .registry import digest_payload, load_json, sign_payload
from .repository_harness import RevisionFixture


NOW = "2026-11-08T18:00:00Z"
FUTURE = "2026-12-31T23:59:59Z"


def subject_for(
    plane: QualityControlPlane,
    fixture: RevisionFixture,
    oracle_registry: OracleRegistry,
    evaluation: dict[str, Any],
) -> SubjectObservation:
    contracts = {
        path.name: load_json(path)
        for path in sorted((plane.root / "contracts").glob("*.schema.json"))
    }
    subject = SubjectObservation(
        change_id="AI-2605",
        repository="northstar-revision-set",
        revision=digest_payload(fixture.commits),
        specification_revision=oracle_registry.change["specification_revision"],
        implementation_digest=digest_payload(fixture.commits),
        policy_version=plane.policy_version,
        producer=plane.observation_producer,
        issued_at=NOW,
        component_commits=tuple(sorted(fixture.commits.items())),
        contract_digest=digest_payload(contracts),
        dataset_digest=evaluation["holdout_digest"],
        oracle_digest=oracle_registry.digest,
    )
    return replace(subject, signature=sign_payload(subject.payload(), plane.observation_key))


def _case(
    case_id: str,
    kind: str,
    requirement_id: str,
    passed: bool,
    oracle_source: str,
) -> dict[str, Any]:
    result = "PASS" if passed else "FAIL"
    return {
        "case_id": case_id,
        "kind": kind,
        "requirement_ids": [requirement_id],
        "oracle_source": oracle_source,
        "result": result,
        "runs": [result],
    }


def observed_cases(
    fixture: RevisionFixture,
    evaluation: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    behavior = execute_protected_checks(fixture)
    properties = property_population(fixture)
    metamorphic = metamorphic_population(fixture)
    checks = behavior["checks"]
    v1_safe = evaluation["holdout"]["v1"]["decision"] == "CONFORMANT"
    cases = [
        _case("CASE-QI001-UNIT", "unit", "QI-001", checks["ambiguous_requires_review"], "specification"),
        _case("CASE-QI001-PROPERTY", "property", "QI-001", properties["passed"], "independent_reference"),
        _case("CASE-QI001-METAMORPHIC", "metamorphic", "QI-001", metamorphic["passed"], "specification"),
        _case("CASE-QI001-INTEGRATION", "integration", "QI-001", checks["ambiguous_requires_review"], "contract"),
        _case("CASE-QI001-NEGATIVE", "negative", "QI-001", checks["ambiguous_requires_review"], "specification"),
        _case("CASE-QI002-SECURITY", "security", "QI-002", checks["cross_tenant_denied"], "specification"),
        _case("CASE-QI002-NEGATIVE", "negative", "QI-002", checks["cross_tenant_denied"], "specification"),
        _case("CASE-QI002-INTEGRATION", "integration", "QI-002", checks["cross_tenant_denied"], "contract"),
        _case("CASE-QI003-CONTRACT", "contract", "QI-003", checks["ai_cannot_mutate_state"], "contract"),
        _case("CASE-QI003-NEGATIVE", "negative", "QI-003", checks["ai_cannot_mutate_state"], "specification"),
        _case("CASE-QI003-INTEGRATION", "integration", "QI-003", checks["expired_approval_rejected"], "contract"),
        _case("CASE-QI004-CONCURRENCY", "concurrency", "QI-004", checks["duplicate_effect_is_single"], "independent_reference"),
        _case("CASE-QI004-FAILURE", "failure", "QI-004", checks["review_outage_holds_safely"], "specification"),
        _case("CASE-QI004-RECOVERY", "recovery", "QI-004", checks["conflicting_idempotency_payload_rejected"], "specification"),
        _case("CASE-QI005-CONTRACT", "contract", "QI-005", checks["evidence_provenance_preserved"], "contract"),
        _case("CASE-QI005-EVALUATION", "evaluation", "QI-005", v1_safe, "protected_dataset"),
        _case("CASE-QI005-NEGATIVE", "negative", "QI-005", checks["unsupported_evidence_rejected"], "specification"),
    ]
    return cases, {
        "behavior": behavior,
        "property": properties,
        "metamorphic": metamorphic,
    }


def build_evidence(
    plane: QualityControlPlane,
    subject: SubjectObservation,
    fixture: RevisionFixture,
    evaluation: dict[str, Any],
    *,
    producer: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cases, observations = observed_cases(fixture, evaluation)
    mutations = execute_mutations(fixture)
    faults = execute_fault_experiments(fixture)
    payload = {
        "evidence_id": "QUALITY-EVIDENCE-AI2605-001",
        "producer": producer or plane.evidence_producer,
        "subject_digest": digest_payload(subject.payload()),
        "policy_version": plane.policy_version,
        "suite_revision": plane.policy["suite_revision"],
        "issued_at": "2026-11-08T17:00:00Z",
        "expires_at": FUTURE,
        "cases": cases,
        "mutations": mutations,
        "fault_experiments": faults,
        "execution": {
            "run_id": "trusted-quality-ci/course27/reference",
            "environment_digest": digest_payload({"python": "stdlib", "sqlite": "transactional"}),
            "component_commits": dict(subject.component_commits),
            "dataset_digest": subject.dataset_digest,
            "oracle_digest": subject.oracle_digest,
        },
    }
    key = plane.evidence_key if payload["producer"] == plane.evidence_producer else "candidate-key"
    return {"payload": payload, "signature": sign_payload(payload, key)}, {
        **observations,
        "mutations": mutations,
        "fault_experiments": faults,
        "evaluation": evaluation,
    }
