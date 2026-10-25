#!/usr/bin/env python3
"""Executable Course 19 lab: proportional controls for small agentic changes."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Iterable

from bugfix_app.api import identity_normalizer, off_by_one_normalizer
from bugfix_app.contracts import ChangeRisk, DiffEntry, TestObservation
from bugfix_app.risk_engine import classify_risk_buggy, classify_risk_fixed
from bugfix_app.workflow import (
    EXPECTED_REPOSITORY_REVISION,
    build_evidence_receipt,
    canonical_digest,
    direct_agent_baseline,
    evaluate_candidate,
    investigate_operator_hypothesis,
    observe_test,
    select_workflow_mode,
)

ROOT = Path(__file__).resolve().parent
BASELINE_REVISION = "baseline:bug-2415"
CANDIDATE_REVISION = "candidate:operator-boundary-fix"


def load_json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def _boundary_results(classifier=classify_risk_fixed) -> dict[int, str]:
    return {score: classifier(score) for score in (0, 49, 50, 79, 80, 81, 100)}


def build_candidate(mutations: Iterable[str] = ()) -> dict[str, object]:
    """Create a candidate from observable artifacts, then apply test mutations."""
    trusted_contract = load_json("specs/BUG-2415/acceptance-contract.json")
    work_unit = load_json("specs/BUG-2415/work-unit.json")
    before = observe_test(
        test_id="REG-RISK-80",
        revision=BASELINE_REVISION,
        classifier=classify_risk_buggy,
        score=80,
        expected="HIGH",
    )
    after = observe_test(
        test_id="REG-RISK-80",
        revision=CANDIDATE_REVISION,
        classifier=classify_risk_fixed,
        score=80,
        expected="HIGH",
    )
    candidate: dict[str, object] = {
        "repository_revision": EXPECTED_REPOSITORY_REVISION,
        "specification_revision": 3,
        "baseline_revision": BASELINE_REVISION,
        "candidate_revision": CANDIDATE_REVISION,
        "trusted_acceptance_contract": trusted_contract,
        "candidate_acceptance_contract": copy.deepcopy(trusted_contract),
        "writable_paths": work_unit["writable_paths"],
        "protected_paths": work_unit["protected_paths"],
        "allowed_purposes": work_unit["allowed_purposes"],
        "diff_entries": [
            DiffEntry("M", "app/risk_engine.py", "app/risk_engine.py", "correct_boundary_condition"),
            DiffEntry("A", None, "tests/test_regression.py", "add_regression_test"),
        ],
        "root_cause_evidence": investigate_operator_hypothesis(
            buggy_classifier=classify_risk_buggy,
            fixed_classifier=classify_risk_fixed,
        ),
        "before_observation": before,
        "after_observation": after,
        "boundary_results": _boundary_results(),
        "classifier": classify_risk_fixed,
        "normalizer": identity_normalizer,
        "requirements": {"REQ-RISK-010@3": "HIGH_STARTS_AT_80"},
        "risk": ChangeRisk(1, 1, 1, 1, 1, 1),
        "declared_mode": "STRUCTURED",
        "mandatory_mode": None,
        "agent_tests_passed": True,
        "mutation_labels": list(mutations),
    }
    candidate["evidence_receipt"] = build_evidence_receipt(
        bug_id="BUG-2415",
        baseline_revision=BASELINE_REVISION,
        candidate_revision=CANDIDATE_REVISION,
        acceptance_contract=trusted_contract,
        before=before,
        after=after,
    )

    for mutation in mutations:
        _apply_mutation(candidate, mutation)
    return candidate


def _apply_mutation(candidate: dict[str, object], mutation: str) -> None:
    if mutation == "stale_repository":
        candidate["repository_revision"] = "stale:repository"
    elif mutation == "stale_specification":
        candidate["specification_revision"] = 2
    elif mutation == "weaken_oracle":
        contract = copy.deepcopy(candidate["candidate_acceptance_contract"])
        contract["expectations"][4]["category"] = "MEDIUM"
        candidate["candidate_acceptance_contract"] = contract
    elif mutation == "scope_expansion":
        candidate["diff_entries"].append(DiffEntry("M", "app/decision_service.py", "app/decision_service.py", "correct_boundary_condition"))
    elif mutation == "root_cause_mismatch":
        candidate["normalizer"] = off_by_one_normalizer
    elif mutation == "protected_path_change":
        candidate["diff_entries"].append(DiffEntry("M", "app/authorization.py", "app/authorization.py", "correct_boundary_condition"))
    elif mutation == "requirement_conflict":
        candidate["requirements"] = {"REQ-RISK-010@3": "HIGH_STARTS_AT_85"}
    elif mutation == "replay_old_evidence":
        receipt = candidate["evidence_receipt"]
        candidate["evidence_receipt"] = replace(receipt, candidate_revision="candidate:old-fix")
    elif mutation == "missing_reproduction":
        passing_before = observe_test(test_id="REG-RISK-80", revision=BASELINE_REVISION, classifier=classify_risk_fixed, score=80, expected="HIGH")
        candidate["before_observation"] = passing_before
        candidate["evidence_receipt"] = replace(candidate["evidence_receipt"], before=passing_before)
    elif mutation == "opportunistic_refactor":
        candidate["diff_entries"].append(DiffEntry("M", "app/risk_engine.py", "app/risk_engine.py", "architecture_refactor"))
    elif mutation == "risk_downgrade":
        candidate["declared_mode"] = "LIGHTWEIGHT"
    elif mutation == "untrusted_evidence":
        candidate["evidence_receipt"] = replace(candidate["evidence_receipt"], producer="agent-self-report")
    elif mutation == "stale_acceptance_evidence":
        candidate["evidence_receipt"] = replace(candidate["evidence_receipt"], acceptance_digest="sha256:stale")
    elif mutation == "invalid_changed_path":
        candidate["diff_entries"].append(DiffEntry("M", "../secrets.txt", "../secrets.txt", "correct_boundary_condition"))
    elif mutation == "bad_boundary_result":
        results = dict(candidate["boundary_results"])
        results[79] = "LOW"
        candidate["boundary_results"] = results
    elif mutation == "unconfirmed_hypothesis":
        evidence = candidate["root_cause_evidence"]
        candidate["root_cause_evidence"] = replace(evidence, status="UNRESOLVED")
    elif mutation == "fix_not_verified":
        failing_after = TestObservation("REG-RISK-80", CANDIDATE_REVISION, "HIGH", "MEDIUM", "FAIL")
        candidate["after_observation"] = failing_after
        candidate["evidence_receipt"] = replace(candidate["evidence_receipt"], after=failing_after)
    else:
        raise ValueError(f"unknown mutation: {mutation}")


def _case_result(case: dict[str, object]) -> dict[str, object]:
    candidate = build_candidate(case["mutations"])
    decision = evaluate_candidate(candidate)
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
        decision = evaluate_candidate(build_candidate(mutations))
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
    ready = (
        conformance["passed"] == conformance["total"] == 12
        and evaluation["passed"] == evaluation["total"] == 30
        and sum(row["passed"] for row in experiments) == 10
        and all(row["passed"] for row in triage)
    )
    return {
        "state": "READY_FOR_INTEGRATION_REVIEW" if ready else "BLOCKED",
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
    return 0 if report["state"] == "READY_FOR_INTEGRATION_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
