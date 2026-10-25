#!/usr/bin/env python3
"""Run the credential-free Course 18 brownfield modernization lab."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from brownfield_app.contracts import (
    AuthorizationGrant,
    BehaviorRecord,
    ExecutionContext,
    RollbackEvidence,
    Submission,
)
from brownfield_app.discovery import (
    required_regression_tests,
    validate_behavior_records,
    validate_discovery_manifest,
)
from brownfield_app.governance import (
    EXPECTED_REPOSITORY_REVISION,
    EXPECTED_SPECIFICATION_REVISION,
    POLICY_REVISION,
    PROTECTED_TESTS,
    TrustedAuthorizationRegistry,
    check_v1_semantics,
    compare_shadow_outputs,
    conflicting_proposal,
    direct_agent_baseline,
    evaluate_candidate,
    exercise_rollback,
    persist_proposal,
    select_summary_provider,
    validate_proposal,
)
from brownfield_app.legacy import AISummaryProvider, LegacySummaryProvider, legacy_v1_response
from brownfield_app.migration import ProposalStore


HERE = Path(__file__).resolve().parent


def load_json(relative: str) -> dict[str, object]:
    return json.loads((HERE / relative).read_text(encoding="utf-8"))


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def trusted_registry(submission_id: str) -> TrustedAuthorizationRegistry:
    return TrustedAuthorizationRegistry(
        {
            AuthorizationGrant(
                "underwriter-17",
                submission_id,
                operation,
                POLICY_REVISION,
            )
            for operation in ("create_summary_proposal", "persist_summary_proposal")
        }
    )


def build_candidate(mutations: list[str] | tuple[str, ...] = ()) -> dict[str, object]:
    """Build actual candidate artifacts, then apply named fixture mutations to them."""
    submission = Submission("SUB-2410-001", 91, ("DOC-11@4", "DOC-12@2"))
    context = ExecutionContext(
        EXPECTED_REPOSITORY_REVISION,
        EXPECTED_SPECIFICATION_REVISION,
        "underwriter-17",
        frozenset({"ai_risk_summary"}),
        frozenset({"create_summary_proposal", "persist_summary_proposal"}),
    )
    registry = trusted_registry(submission.submission_id)
    proposal = AISummaryProvider().generate(submission)
    legacy_shadow = LegacySummaryProvider().generate(submission)
    discovery = load_json("fixtures/discovery-manifest.json")
    trusted_dependencies = load_json("fixtures/trusted-dependency-evidence.json")
    contract = load_json("specs/AI-2410/v1-compatibility-contract.json")
    rollback = exercise_rollback(
        submission=submission,
        context=context,
        registry=registry,
        store=ProposalStore(),
        source_revision="rollback-rehearsal@1",
    )
    candidate: dict[str, object] = {
        "context": context,
        "submission": submission,
        "authorization_registry": registry,
        "behavior_records": [
            {
                "behavior_id": "BEH-LOG-009",
                "observed_confidence": "UNKNOWN",
                "observed_kind": "QUIRK",
                "disposition": "UNKNOWN",
            },
            {
                "behavior_id": "BEH-ERR-004",
                "observed_confidence": "CONFIRMED",
                "observed_kind": "DEFECT",
                "disposition": "DEFECT",
            },
        ],
        "discovery_manifest": discovery,
        "trusted_dependency_evidence": trusted_dependencies,
        "candidate_v1_response": legacy_v1_response(submission),
        "v1_contract": contract,
        "proposal": proposal,
        "impacted_consumers": {
            "SubmissionAPIv1",
            "NightlyRiskBatch",
            "LegacyPortal",
            "RiskReporting",
        },
        "critical_consumers": set(trusted_dependencies["critical_consumers"]),
        "mapped_tests": {
            "CHANGED_COMPONENT": {"test_summary_provider"},
            "SubmissionAPIv1": {"test_v1_contract"},
            "NightlyRiskBatch": {"test_batch_contract"},
            "LegacyPortal": {"test_legacy_portal_pact"},
            "RiskReporting": {"test_reporting_contract"},
        },
        "protected_tests": set(PROTECTED_TESTS),
        "migration_store": ProposalStore(),
        "migration_attempts": [
            {"proposal": proposal, "source_revision": "legacy-summary@7"},
            {"proposal": proposal, "source_revision": "legacy-summary@7"},
        ],
        "legacy_shadow": legacy_shadow,
        "candidate_shadow": proposal,
        "approved_shadow_differences": {"source", "text"},
        "rollback_evidence": rollback,
        "agent_tests_passed": True,
    }

    for mutation in mutations:
        if mutation == "stale_repository":
            candidate["context"] = replace(candidate["context"], repository_revision="old-revision")
        elif mutation == "stale_specification":
            candidate["context"] = replace(candidate["context"], specification_revision=3)
        elif mutation == "unknown_retirement":
            candidate["behavior_records"][0]["disposition"] = "RETIRE"
        elif mutation == "missed_consumer":
            findings = candidate["discovery_manifest"]["findings"]
            findings[0]["consumers"].remove("NightlyRiskBatch")
        elif mutation == "characterized_defect":
            candidate["behavior_records"][1]["disposition"] = "PRESERVE"
        elif mutation == "semantic_break":
            candidate["candidate_v1_response"]["review_required"] = False
        elif mutation == "flag_as_auth":
            candidate["context"] = replace(candidate["context"], actor="observer-3")
        elif mutation == "duplicate_effect":
            candidate["migration_attempts"][1]["proposal"] = conflicting_proposal(proposal)
        elif mutation == "missing_protected_test":
            candidate["protected_tests"].remove("test_underwriting_authority_unchanged")
        elif mutation == "no_rollback":
            candidate["rollback_evidence"] = replace(
                candidate["rollback_evidence"],
                legacy_path_restored=False,
            )
        elif mutation == "authority_escalation":
            candidate["proposal"] = replace(proposal, authoritative=True)
        elif mutation == "shadow_divergence":
            candidate["candidate_shadow"] = replace(
                proposal,
                submission_id="SUB-WRONG",
            )
        else:
            raise ValueError(f"Unknown fixture mutation: {mutation}")
    return candidate


def run_conformance() -> dict[str, object]:
    suite = load_json("conformance-suite.json")["cases"]
    results = []
    for case in suite:
        decision = evaluate_candidate(build_candidate(case["mutations"]))
        actual_codes = {finding.code for finding in decision.findings}
        passed = decision.state == case["expected_state"] and set(case["expected_codes"]) == actual_codes
        results.append(
            {
                "id": case["id"],
                "passed": passed,
                "actual_state": decision.state,
                "actual_codes": sorted(actual_codes),
            }
        )
    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results}


def run_mutation_evaluation() -> dict[str, object]:
    cases = load_json("evaluation-cases.json")["cases"]
    results = []
    for case in cases:
        decision = evaluate_candidate(build_candidate(case["mutations"]))
        detected = decision.state == case["expected_state"] and set(case["expected_codes"]) == (
            {finding.code for finding in decision.findings}
        )
        results.append({"id": case["id"], "mutation": case["mutation"], "detected": detected})
    return {"passed": sum(item["detected"] for item in results), "total": len(results), "results": results}


def run_experiments() -> dict[str, object]:
    discovery = load_json("fixtures/discovery-manifest.json")
    trusted_dependencies = load_json("fixtures/trusted-dependency-evidence.json")
    valid_discovery = validate_discovery_manifest(
        discovery,
        actual_repository_revision=EXPECTED_REPOSITORY_REVISION,
        trusted_dependency_evidence=trusted_dependencies,
    )
    omitted_discovery = deepcopy(discovery)
    omitted_discovery["findings"][0]["consumers"].remove("NightlyRiskBatch")
    omitted_result = validate_discovery_manifest(
        omitted_discovery,
        actual_repository_revision=EXPECTED_REPOSITORY_REVISION,
        trusted_dependency_evidence=trusted_dependencies,
    )

    behavior_result = validate_behavior_records(
        [
            BehaviorRecord(
                "BEH-RISK-010",
                "PRESERVE",
                "Underwriting Risk",
                ("TEST-RISK-010",),
                "REQ-RISK-010",
            ),
            BehaviorRecord("BEH-LOG-009", "UNKNOWN", None, ("TRACE-LOG-009",), None),
        ]
    )

    complete_plan = required_regression_tests(
        impacted_consumers={"SubmissionAPIv1", "NightlyRiskBatch"},
        mapped_tests={
            "CHANGED_COMPONENT": {"test_summary_provider"},
            "SubmissionAPIv1": {"test_v1_contract"},
            "NightlyRiskBatch": {"test_batch_contract"},
        },
        protected_tests=PROTECTED_TESTS,
        critical_consumers={"SubmissionAPIv1", "NightlyRiskBatch"},
    )
    incomplete_plan = required_regression_tests(
        impacted_consumers={"SubmissionAPIv1", "LegacyPortal"},
        mapped_tests={"SubmissionAPIv1": {"test_v1_contract"}},
        protected_tests=PROTECTED_TESTS,
        critical_consumers={"SubmissionAPIv1", "LegacyPortal"},
    )

    submission = Submission("SUB-2410-001", 91, ("DOC-11@4", "DOC-12@2"))
    context = ExecutionContext(
        EXPECTED_REPOSITORY_REVISION,
        EXPECTED_SPECIFICATION_REVISION,
        "underwriter-17",
        frozenset({"ai_risk_summary"}),
        frozenset({"create_summary_proposal", "persist_summary_proposal"}),
    )
    registry = trusted_registry(submission.submission_id)
    provider, provider_decision = select_summary_provider(context, submission, registry)
    assert provider is not None
    proposal = provider.generate(submission)
    proposal_decision = validate_proposal(proposal, submission)

    unauthorized_context = replace(context, actor="observer-3")
    _, flag_decision = select_summary_provider(unauthorized_context, submission, registry)

    contract = load_json("specs/AI-2410/v1-compatibility-contract.json")
    compatible_addition = legacy_v1_response(submission) | {"trace_id": "TRACE-2410"}
    compatible_result = check_v1_semantics(submission, compatible_addition, contract)
    semantic_result = check_v1_semantics(
        submission,
        {
            "submission_id": submission.submission_id,
            "risk_category": "HIGH",
            "review_required": False,
        },
        contract,
    )

    store = ProposalStore()
    first_insert, first_decision = persist_proposal(
        context=context,
        submission=submission,
        proposal=proposal,
        source_revision="legacy-summary@7",
        registry=registry,
        store=store,
    )
    retry_insert, retry_decision = persist_proposal(
        context=context,
        submission=submission,
        proposal=proposal,
        source_revision="legacy-summary@7",
        registry=registry,
        store=store,
    )
    conflict_insert, conflict_decision = persist_proposal(
        context=context,
        submission=submission,
        proposal=conflicting_proposal(proposal),
        source_revision="legacy-summary@7",
        registry=registry,
        store=store,
    )

    shadow_result = compare_shadow_outputs(
        LegacySummaryProvider().generate(submission),
        proposal,
        approved_differences={"source", "text"},
    )
    unsafe_shadow = compare_shadow_outputs(
        LegacySummaryProvider().generate(submission),
        replace(proposal, authoritative=True),
        approved_differences={"source", "text"},
    )
    rollback_result = exercise_rollback(
        submission=submission,
        context=context,
        registry=registry,
        store=ProposalStore(),
        source_revision="rollback-rehearsal@1",
    )

    results = {
        "independent_discovery": {
            "passed": valid_discovery.state == "PASS" and omitted_result.state == "BLOCKED",
            "omitted_state": omitted_result.state,
        },
        "unknown_behavior": {"passed": behavior_result.state == "BLOCKED", "state": behavior_result.state},
        "regression_obligations": {
            "passed": complete_plan.state == "PASS"
            and incomplete_plan.state == "BLOCKED"
            and incomplete_plan.unmapped_consumers == frozenset({"LegacyPortal"}),
            "unmapped": sorted(incomplete_plan.unmapped_consumers),
        },
        "trusted_authorization": {
            "passed": provider_decision.state == proposal_decision.state == "PASS"
            and flag_decision.state == "BLOCKED"
            and proposal.authoritative is False,
            "unauthorized_state": flag_decision.state,
        },
        "contract_aware_compatibility": {
            "passed": compatible_result.state == "PASS" and semantic_result.state == "BLOCKED",
            "semantic_break_state": semantic_result.state,
        },
        "transactional_idempotency": {
            "passed": first_decision.state == retry_decision.state == conflict_decision.state == "PASS"
            and first_insert == "APPLIED"
            and retry_insert == "ALREADY_APPLIED"
            and conflict_insert == "IDEMPOTENCY_CONFLICT"
            and store.count() == 1
            and store.authoritative_count() == 0,
            "statuses": [first_insert, retry_insert, conflict_insert],
        },
        "measured_shadow": {
            "passed": shadow_result.classification == "EXPECTED"
            and unsafe_shadow.classification == "UNEXPECTED",
            "classifications": [shadow_result.classification, unsafe_shadow.classification],
        },
        "executed_rollback": {
            "passed": rollback_result.passed,
            "checks": {
                "ai_path_observed": rollback_result.ai_path_observed,
                "legacy_path_restored": rollback_result.legacy_path_restored,
                "authoritative_state_unchanged": rollback_result.authoritative_state_unchanged,
                "legacy_reads_preserved": rollback_result.legacy_reads_preserved,
            },
        },
        "behavior_driven_reference": {
            "passed": evaluate_candidate(build_candidate()).state == "PASS",
            "state": evaluate_candidate(build_candidate()).state,
        },
        "behavior_driven_mutation": {
            "passed": evaluate_candidate(build_candidate(["semantic_break"])).state == "BLOCKED",
            "state": evaluate_candidate(build_candidate(["semantic_break"])).state,
        },
    }
    return {"passed": sum(item["passed"] for item in results.values()), "total": len(results), "results": results}


def run_baseline_comparison() -> dict[str, object]:
    cases = load_json("evaluation-cases.json")["cases"][:12]
    governed_correct = 0
    baseline_correct = 0
    for case in cases:
        candidate = build_candidate(case["mutations"])
        governed = evaluate_candidate(candidate)
        baseline = direct_agent_baseline(candidate)
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
