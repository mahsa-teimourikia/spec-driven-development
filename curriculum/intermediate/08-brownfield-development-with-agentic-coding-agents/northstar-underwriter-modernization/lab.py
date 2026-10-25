#!/usr/bin/env python3
"""Run the credential-free Course 18 brownfield modernization lab."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from brownfield_app.contracts import BehaviorRecord, ExecutionContext, Submission
from brownfield_app.discovery import (
    required_regression_tests,
    validate_behavior_records,
    validate_discovery_manifest,
)
from brownfield_app.governance import (
    EXPECTED_REPOSITORY_REVISION,
    EXPECTED_SPECIFICATION_REVISION,
    PROTECTED_TESTS,
    check_v1_semantics,
    direct_agent_baseline,
    evaluate_case,
    select_summary_provider,
    validate_context,
    validate_proposal,
)
from brownfield_app.legacy import AISummaryProvider, legacy_v1_response
from brownfield_app.migration import ProposalStore


HERE = Path(__file__).resolve().parent


def load_json(relative: str) -> dict[str, object]:
    return json.loads((HERE / relative).read_text(encoding="utf-8"))


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def run_conformance() -> dict[str, object]:
    suite = load_json("conformance-suite.json")["cases"]
    results = []
    for case in suite:
        decision = evaluate_case(case["input"])
        passed = decision.state == case["expected_state"] and [f.code for f in decision.findings] == case["expected_codes"]
        results.append({"id": case["id"], "passed": passed, "actual_state": decision.state})
    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results}


def run_mutation_evaluation() -> dict[str, object]:
    cases = load_json("evaluation-cases.json")["cases"]
    results = []
    for case in cases:
        decision = evaluate_case(case["input"])
        detected = decision.state == case["expected_state"] and set(case["expected_codes"]).issubset({f.code for f in decision.findings})
        results.append({"id": case["id"], "mutation": case["mutation"], "detected": detected})
    return {"passed": sum(item["detected"] for item in results), "total": len(results), "results": results}


def run_experiments() -> dict[str, object]:
    discovery = load_json("fixtures/discovery-manifest.json")
    valid_discovery = validate_discovery_manifest(
        discovery, actual_repository_revision=EXPECTED_REPOSITORY_REVISION
    )
    stale_discovery = dict(discovery, repository_revision="stale")
    stale_result = validate_discovery_manifest(
        stale_discovery, actual_repository_revision=EXPECTED_REPOSITORY_REVISION
    )

    behavior_records = [
        BehaviorRecord("BEH-RISK-010", "PRESERVE", "Underwriting Risk", ("TEST-RISK-010",), "REQ-RISK-010"),
        BehaviorRecord("BEH-LOG-009", "UNKNOWN", None, ("TRACE-LOG-009",), None),
    ]
    behavior_result = validate_behavior_records(behavior_records)

    mapped = {
        "CHANGED_COMPONENT": {"test_summary_provider"},
        "SubmissionAPIv1": {"test_v1_contract"},
        "NightlyRiskBatch": {"test_batch_contract"},
    }
    selected = required_regression_tests(
        impacted_consumers={"SubmissionAPIv1", "NightlyRiskBatch"},
        mapped_tests=mapped,
        protected_tests=PROTECTED_TESTS,
    )

    submission = Submission("SUB-2410-001", 91, ("DOC-11@4", "DOC-12@2"))
    context = ExecutionContext(
        EXPECTED_REPOSITORY_REVISION,
        EXPECTED_SPECIFICATION_REVISION,
        "underwriter-17",
        frozenset({submission.submission_id}),
        frozenset({"ai_risk_summary"}),
        frozenset({"create_summary_proposal"}),
    )
    provider, provider_decision = select_summary_provider(context, authorized=True)
    assert provider is not None
    proposal = provider.generate(submission)
    proposal_decision = validate_proposal(proposal, submission)

    unauthorized_context = ExecutionContext(
        EXPECTED_REPOSITORY_REVISION,
        EXPECTED_SPECIFICATION_REVISION,
        "observer-3",
        frozenset({submission.submission_id}),
        frozenset({"ai_risk_summary"}),
        frozenset(),
    )
    _, flag_decision = select_summary_provider(unauthorized_context, authorized=True)

    semantic_result = check_v1_semantics(
        submission,
        {"submission_id": submission.submission_id, "risk_category": "HIGH", "review_required": False},
    )

    store = ProposalStore()
    first_insert = store.migrate(proposal, "legacy-summary@7")
    retry_insert = store.migrate(proposal, "legacy-summary@7")

    shadow_decision = evaluate_case(
        {
            "repository_revision": EXPECTED_REPOSITORY_REVISION,
            "specification_revision": EXPECTED_SPECIFICATION_REVISION,
            "shadow_divergence": True,
        }
    )
    rollback_decision = evaluate_case(
        {
            "repository_revision": EXPECTED_REPOSITORY_REVISION,
            "specification_revision": EXPECTED_SPECIFICATION_REVISION,
            "rollback_unavailable": True,
        }
    )

    results = {
        "current_discovery": {"passed": valid_discovery.state == "PASS", "state": valid_discovery.state},
        "stale_discovery": {"passed": stale_result.state == "BLOCKED", "state": stale_result.state},
        "unknown_behavior": {"passed": behavior_result.state == "BLOCKED", "state": behavior_result.state},
        "selective_regression": {"passed": PROTECTED_TESTS.issubset(selected), "selected": sorted(selected)},
        "additive_proposal": {
            "passed": provider_decision.state == proposal_decision.state == "PASS" and proposal.authoritative is False,
            "source": proposal.source,
        },
        "flag_is_not_authorization": {"passed": flag_decision.state == "BLOCKED", "state": flag_decision.state},
        "semantic_compatibility": {"passed": semantic_result.state == "BLOCKED", "state": semantic_result.state},
        "idempotent_migration": {
            "passed": first_insert and not retry_insert and store.count() == 1 and store.authoritative_count() == 0,
            "records": store.count(),
        },
        "shadow_divergence": {"passed": shadow_decision.state == "REVIEW_REQUIRED", "state": shadow_decision.state},
        "rollback_gate": {"passed": rollback_decision.state == "BLOCKED", "state": rollback_decision.state},
    }
    return {"passed": sum(item["passed"] for item in results.values()), "total": len(results), "results": results}


def run_baseline_comparison() -> dict[str, object]:
    cases = load_json("evaluation-cases.json")["cases"][:12]
    governed_correct = 0
    baseline_correct = 0
    for case in cases:
        governed = evaluate_case(case["input"])
        baseline = direct_agent_baseline(case["input"])
        governed_correct += governed.state == case["expected_state"]
        baseline_correct += baseline.state == case["expected_state"]
    return {
        "population": len(cases),
        "governed_correct": governed_correct,
        "direct_baseline_correct": baseline_correct,
        "claim": "Deterministic teaching cases only; no production-agent quality claim.",
    }


def build_report() -> dict[str, object]:
    conformance = run_conformance()
    evaluation = run_mutation_evaluation()
    experiments = run_experiments()
    baseline = run_baseline_comparison()
    reference = load_json("reference/modernization-package.json")
    all_pass = (
        conformance["passed"] == conformance["total"]
        and evaluation["passed"] == evaluation["total"]
        and experiments["passed"] == experiments["total"]
    )
    state = "READY_FOR_INTEGRATION_REVIEW" if all_pass else "BLOCKED"
    evidence = {
        "subject": {
            "change_id": "AI-2410",
            "repository_revision": EXPECTED_REPOSITORY_REVISION,
            "specification_revision": EXPECTED_SPECIFICATION_REVISION,
        },
        "results": {
            "conformance": digest(conformance),
            "mutation_evaluation": digest(evaluation),
            "experiments": digest(experiments),
        },
        "limitations": [
            "Credential-free deterministic fixtures are not production telemetry.",
            "No real AI model, enterprise identity provider, migration database, or release system is evaluated.",
        ],
    }
    return {
        "course": 18,
        "change_id": "AI-2410",
        "reference": {
            "state": state,
            "integration_review_eligible": all_pass,
            "merge_authorized": False,
            "deployment_authorized": False,
            "legacy_retirement_authorized": False,
            "business_outcome_proven": False,
        },
        "target_equation": "T = accepted baseline + approved delta - authorized retirements",
        "conformance": conformance,
        "evaluation": evaluation,
        "experiments": experiments,
        "baseline_comparison": baseline,
        "protected_invariants": sorted(PROTECTED_TESTS),
        "reference_package_state": reference["state"],
        "evidence_manifest": evidence,
    }


def main() -> None:
    print(json.dumps(build_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
