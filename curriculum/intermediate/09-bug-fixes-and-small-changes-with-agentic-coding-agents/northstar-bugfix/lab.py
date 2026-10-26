#!/usr/bin/env python3
"""Executable Course 19 lab: proportional controls for small agentic changes."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from bugfix_app.contracts import ChangeRisk
from bugfix_app.risk_engine import classify_risk_buggy
from bugfix_app.trusted_harness import (
    FIXED_RISK_SOURCE,
    OFF_BY_ONE_API_SOURCE,
    TrustedBugfixHarness,
)
from bugfix_app.workflow import (
    EXPECTED_REPOSITORY_REVISION,
    canonical_digest,
    direct_agent_baseline,
    evaluate_candidate,
    select_workflow_mode,
)

ROOT = Path(__file__).resolve().parent
HARNESS = TrustedBugfixHarness(ROOT)
_TRUSTED_CONTEXT_CACHE: dict[str, object] = {}


def load_json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _context_key(candidate: dict[str, object]) -> str:
    return canonical_digest({"files": candidate["files"], "purposes": candidate["purpose_declarations"]})


def trusted_context(candidate: dict[str, object]):
    """Resolve trusted observations outside the candidate payload and cache by source content."""
    key = _context_key(candidate)
    if key not in _TRUSTED_CONTEXT_CACHE:
        _TRUSTED_CONTEXT_CACHE[key] = HARNESS.observe(candidate)
    return _TRUSTED_CONTEXT_CACHE[key]


def assess_candidate(candidate: dict[str, object]):
    context = trusted_context(candidate)
    return evaluate_candidate(candidate, context), context


def build_candidate(mutations: Iterable[str] = ()) -> dict[str, object]:
    """Create source artifacts and agent declarations; trusted observations remain external."""
    files = dict(HARNESS.baseline_files)
    files["app/risk_engine.py"] = FIXED_RISK_SOURCE
    files["tests/test_regression.py"] = (
        "from app.risk_engine import classify_risk\n\n"
        "def test_score_80_is_high():\n"
        "    assert classify_risk(80) == 'HIGH'\n"
    )
    candidate: dict[str, object] = {
        "repository_revision": EXPECTED_REPOSITORY_REVISION,
        "specification_revision": 3,
        "files": files,
        "purpose_declarations": {
            "app/risk_engine.py": "correct_boundary_condition",
            "tests/test_regression.py": "add_regression_test",
        },
        "proposed_hypothesis_id": "HYP-OPERATOR",
        "requirements": {"REQ-RISK-010@3": "HIGH_STARTS_AT_80"},
        "declared_mode": "STRUCTURED",
        "evidence_references": ["CI-RUN-BUG-2415"],
        "agent_tests_passed": True,
        "mutation_labels": list(mutations),
    }
    for mutation in mutations:
        _apply_source_or_claim_mutation(candidate, mutation)

    context = trusted_context(candidate)
    candidate["submitted_before_observation"] = context.before_observation
    candidate["submitted_after_observation"] = context.after_observation
    candidate["submitted_boundary_results"] = dict(context.boundary_results)
    for mutation in mutations:
        _apply_report_mutation(candidate, mutation)
    return candidate


def _apply_source_or_claim_mutation(candidate: dict[str, object], mutation: str) -> None:
    if mutation == "stale_repository":
        candidate["repository_revision"] = "stale:repository"
    elif mutation == "stale_specification":
        candidate["specification_revision"] = 2
    elif mutation == "weaken_oracle":
        contract = json.loads(candidate["files"]["specs/BUG-2415/acceptance-contract.json"])
        contract["expectations"][4]["category"] = "MEDIUM"
        candidate["files"]["specs/BUG-2415/acceptance-contract.json"] = json.dumps(contract, indent=2) + "\n"
        candidate["purpose_declarations"]["specs/BUG-2415/acceptance-contract.json"] = "weaken_acceptance_oracle"
    elif mutation == "scope_expansion":
        candidate["files"]["app/decision_service.py"] = "# unrelated service edit\n"
        candidate["purpose_declarations"]["app/decision_service.py"] = "correct_boundary_condition"
    elif mutation == "root_cause_mismatch":
        candidate["files"]["app/api.py"] = OFF_BY_ONE_API_SOURCE
        candidate["purpose_declarations"]["app/api.py"] = "correct_boundary_condition"
    elif mutation == "protected_path_change":
        candidate["files"]["app/authorization.py"] = "REVIEW_REQUIRED = False\n"
        candidate["purpose_declarations"]["app/authorization.py"] = "correct_boundary_condition"
    elif mutation == "requirement_conflict":
        candidate["requirements"] = {"REQ-RISK-010@3": "HIGH_STARTS_AT_85"}
    elif mutation == "replay_old_evidence":
        candidate["evidence_references"].append("CI-RUN-OLD-CANDIDATE")
    elif mutation == "opportunistic_refactor":
        candidate["files"]["app/risk_engine.py"] += "\n# unrelated architecture cleanup\n"
        candidate["purpose_declarations"]["app/risk_engine.py"] = "architecture_refactor"
    elif mutation == "risk_downgrade":
        candidate["declared_mode"] = "LIGHTWEIGHT"
    elif mutation == "untrusted_evidence":
        candidate["evidence_references"].append("agent-self-report")
    elif mutation == "stale_acceptance_evidence":
        candidate["evidence_references"].append("CI-RUN-STALE-ORACLE")
    elif mutation == "invalid_changed_path":
        candidate["purpose_declarations"]["../secrets.txt"] = "correct_boundary_condition"
    elif mutation == "bad_boundary_result":
        candidate["files"]["app/risk_engine.py"] = FIXED_RISK_SOURCE.replace(
            "def classify_risk(score):\n    validate_score(score)",
            "def classify_risk(score):\n    validate_score(score)\n    if score == 79:\n        return 'LOW'",
        )
    elif mutation == "unconfirmed_hypothesis":
        candidate["proposed_hypothesis_id"] = "HYP-CACHE"
    elif mutation == "fix_not_verified":
        candidate["files"]["app/risk_engine.py"] = HARNESS.baseline_files["app/risk_engine.py"]
    elif mutation != "missing_reproduction":
        raise ValueError(f"unknown mutation: {mutation}")


def _apply_report_mutation(candidate: dict[str, object], mutation: str) -> None:
    if mutation == "missing_reproduction":
        before = candidate["submitted_before_observation"]
        candidate["submitted_before_observation"] = replace(before, actual="HIGH", result="PASS")


def _case_result(case: dict[str, object]) -> dict[str, object]:
    candidate = build_candidate(case["mutations"])
    decision, _ = assess_candidate(candidate)
    codes = {finding.code for finding in decision.findings}
    expected_state = case.get("expected_state", case.get("state"))
    required_codes = set(case.get("required_codes", case.get("codes", [])))
    passed = decision.state == expected_state and required_codes <= codes
    return {
        "id": case["id"],
        "passed": passed,
        "expected_state": expected_state,
        "actual_state": decision.state,
        "required_codes": sorted(required_codes),
        "actual_codes": sorted(codes),
    }


def run_cases(relative: str) -> dict[str, object]:
    results = [_case_result(case) for case in load_json(relative)["cases"]]
    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results}


def run_triage() -> list[dict[str, object]]:
    rows = []
    for request in load_json("fixtures/change-requests.json")["requests"]:
        selected = select_workflow_mode(ChangeRisk(**request["risk"]))
        rows.append({"id": request["id"], "expected": request["expected_mode"], "selected": selected, "passed": selected == request["expected_mode"]})
    return rows


def run_experiments() -> list[dict[str, object]]:
    experiments = [
        ("minimal-fix", [], None),
        ("boundary-regression", ["bad_boundary_result"], "SURROUNDING_BEHAVIOR_REGRESSION"),
        ("test-weakening", ["weaken_oracle"], "TEST_ORACLE_CHANGED"),
        ("scope-expansion", ["scope_expansion"], "SCOPE_EXPANSION"),
        ("root-cause-mismatch", ["root_cause_mismatch"], "ROOT_CAUSE_MISMATCH"),
        ("stale-spec", ["stale_specification"], "STALE_SPECIFICATION"),
        ("protected-authorization", ["protected_path_change"], "PROTECTED_PATH_CHANGE"),
        ("conflicting-requirements", ["requirement_conflict"], "NORMATIVE_CONFLICT"),
        ("replayed-evidence", ["replay_old_evidence"], "STALE_EVIDENCE"),
    ]
    rows = [{
        "experiment": "original-defect",
        "passed": classify_risk_buggy(80) == "MEDIUM",
        "state": "OBSERVED",
        "codes": ["BASELINE_BOUNDARY_DEFECT"],
    }]
    for name, mutations, expected_code in experiments:
        decision, _ = assess_candidate(build_candidate(mutations))
        codes = {finding.code for finding in decision.findings}
        passed = decision.state == "PASS" if expected_code is None else expected_code in codes
        rows.append({"experiment": name, "passed": passed, "state": decision.state, "codes": sorted(codes)})
    return rows


def build_report() -> dict[str, object]:
    conformance = run_cases("conformance-suite.json")
    evaluation = run_cases("evaluation-cases.json")
    experiments = run_experiments()
    comparison_cases = load_json("conformance-suite.json")["cases"]
    baseline_accepted = sum(direct_agent_baseline(build_candidate(case["mutations"])).state == "PASS" for case in comparison_cases)
    governed_correct = sum(_case_result(case)["passed"] for case in comparison_cases)
    triage = run_triage()
    course_ready = (
        conformance["passed"] == conformance["total"] == 12
        and evaluation["passed"] == evaluation["total"] == 30
        and sum(row["passed"] for row in experiments) == 10
        and all(row["passed"] for row in triage)
    )
    reference_candidate = build_candidate()
    reference_decision, reference_context = assess_candidate(reference_candidate)
    candidate_status = "READY_FOR_INTEGRATION_REVIEW" if reference_decision.state == "PASS" else "BLOCKED"
    return {
        "course_validation": {"status": "PASS" if course_ready else "FAIL"},
        "candidate_assessment": {
            "status": candidate_status,
            "subject": {
                "baseline_commit": reference_context.baseline_commit,
                "candidate_commit": reference_context.candidate_commit,
                "specification_revision": reference_candidate["specification_revision"],
                "acceptance_digest": canonical_digest(dict(reference_context.acceptance_contract)),
            },
            "finding_codes": [item.code for item in reference_decision.findings],
            "merge_authorized": False,
            "deployment_authorized": False,
        },
        "conformance": conformance,
        "evaluation": evaluation,
        "experiments": {"passed": sum(row["passed"] for row in experiments), "total": 10, "results": experiments},
        "triage": triage,
        "comparison": {
            "baseline_cases_accepted": baseline_accepted,
            "governed_cases_correct": governed_correct,
            "total": len(comparison_cases),
        },
        "evidence": {
            "acceptance_digest": canonical_digest(load_json("specs/BUG-2415/acceptance-contract.json")),
            "conformance_digest": canonical_digest(load_json("conformance-suite.json")),
            "evaluation_digest": canonical_digest(load_json("evaluation-cases.json")),
            "producer": "northstar-ci",
        },
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2))
    ready = report["course_validation"]["status"] == "PASS" and report["candidate_assessment"]["status"] == "READY_FOR_INTEGRATION_REVIEW"
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
