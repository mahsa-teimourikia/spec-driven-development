#!/usr/bin/env python3
"""Course 20 lab: coordinate and verify an exact set of Git repository revisions."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from multirepo_app.control_plane import (
    direct_agent_baseline,
    evaluate_candidate,
    evidence_digest,
    load_json,
)
from multirepo_app.git_harness import TrustedGitHarness, canonical_digest


ROOT = Path(__file__).resolve().parent
HARNESS = TrustedGitHarness(ROOT)
_CONTEXT_CACHE: dict[str, object] = {}


def _context_key(candidate: dict[str, object]) -> str:
    return canonical_digest(
        {
            "configs": candidate["repository_configs"],
            "extra_files": candidate.get("repository_extra_files", {}),
        }
    )


def trusted_context(candidate: dict[str, object]):
    key = _context_key(candidate)
    if key not in _CONTEXT_CACHE:
        _CONTEXT_CACHE[key] = HARNESS.observe(candidate)
    return _CONTEXT_CACHE[key]


def _child_specs() -> dict[str, object]:
    result = {}
    for path in sorted((ROOT / "parent-change/children").glob("*.json")):
        payload = load_json(path)
        result[payload["id"]] = payload
    return result


def _work_units(context) -> dict[str, object]:
    units = load_json(ROOT / "parent-change/work-units.json")
    for repository, unit in units.items():
        unit["base_commit"] = context.repositories[repository].baseline_commit
    return units


def build_candidate(mutations: list[str] | tuple[str, ...] = ()) -> dict[str, object]:
    candidate: dict[str, object] = {
        "repository_configs": HARNESS.reference_configs(),
        "repository_extra_files": {repository: {} for repository in HARNESS.reference_configs()},
        "child_specs": _child_specs(),
        "contract_proposal": copy.deepcopy(HARNESS.canonical_contract),
        "contract_registry": {
            "id": "CONTRACT-CLASSIFICATION-001",
            "revision": 2,
            "owner": "Enterprise Integration Architecture",
            "digest": canonical_digest(HARNESS.canonical_contract),
        },
        "dependency_graph": load_json(ROOT / "parent-change/dependency-graph.json"),
        "rollout_order": [
            "deploy-review-v2",
            "verify-review-v2-accepts-ai-v1",
            "deploy-ai-v2-disabled",
            "verify-ai-v2-review-v2",
            "enable-bounded-traffic",
        ],
        "rollback_compatibility_verified": True,
        "contract_change_status": "OWNER_APPROVED",
        "affected_work_units_invalidated": True,
        "local_ci_is_system_evidence": False,
        "release_authorized": False,
        "local_ci": {repository: True for repository in HARNESS.reference_configs()},
        "evidence_references": ["INT-RUN-AI2500"],
        "mutation_labels": list(mutations),
    }
    for mutation in mutations:
        _apply_source_mutation(candidate, mutation)
    context = trusted_context(candidate)
    candidate["work_units"] = _work_units(context)
    candidate["declared_compatibility"] = dict(context.compatibility_matrix)
    candidate["integration_manifest"] = {
        "change_id": "AI-2500",
        "contract_revision": 2,
        "component_commits": {
            repository: revision.candidate_commit
            for repository, revision in context.repositories.items()
        },
    }
    candidate["submitted_scenario_results"] = dict(context.scenario_results)
    for mutation in mutations:
        _apply_claim_mutation(candidate, mutation)
    return candidate


def _apply_source_mutation(candidate: dict[str, object], mutation: str) -> None:
    configs = candidate["repository_configs"]
    if mutation == "cross_tenant_leak":
        configs["review-service"]["enforces_tenant_scope"] = False
    elif mutation == "duplicate_effect":
        configs["review-service"]["idempotent_submission"] = False
    elif mutation == "missing_provenance_accepted":
        configs["review-service"]["requires_evidence_refs"] = False
    elif mutation == "unsafe_review_outage":
        configs["ai-service"]["fail_closed_when_review_unavailable"] = False
    elif mutation == "review_bypass_behavior":
        configs["ai-service"]["ambiguous_requires_review"] = False
    elif mutation == "stale_approval_accepted":
        configs["review-service"]["rejects_stale_approval"] = False
    elif mutation == "dual_write_authority":
        configs["ai-service"]["writes_authoritative_state"] = True
    elif mutation == "new_consumer_rejects_v1":
        configs["review-service"]["accepted_contract_revisions"] = [2]
    elif mutation == "scope_expansion":
        candidate["repository_extra_files"]["ai-service"]["src/unapproved.py"] = "SIDE_EFFECT = True\n"


def _apply_claim_mutation(candidate: dict[str, object], mutation: str) -> None:
    if mutation == "stale_parent":
        candidate["child_specs"]["AI-2500-AI"]["parent_revision"] = 1
    elif mutation == "missing_child":
        candidate["child_specs"].pop("AI-2500-UI")
    elif mutation == "semantic_bypass":
        candidate["child_specs"]["AI-2500-AI"]["allows_review_bypass"] = True
    elif mutation == "wrong_contract_owner":
        candidate["contract_registry"]["owner"] = "Applied AI"
    elif mutation == "contract_drift":
        candidate["contract_proposal"]["required"].remove("evidence_refs")
    elif mutation == "stale_contract_record":
        candidate["contract_registry"]["revision"] = 1
    elif mutation == "missing_contract_dependency":
        candidate["dependency_graph"]["AI-2500-AI"] = []
    elif mutation == "dependency_cycle":
        candidate["dependency_graph"]["AI-2500-CONTRACT"] = ["AI-2500-INTEGRATION"]
    elif mutation == "stale_repo_context":
        candidate["work_units"]["ai-service"]["base_commit"] = "0" * 40
    elif mutation == "stale_work_unit_contract":
        candidate["work_units"]["review-service"]["contract_revision"] = 1
    elif mutation == "widened_authority":
        candidate["work_units"]["ai-service"]["may_not_decide"] = []
    elif mutation == "matrix_overclaim":
        candidate["declared_compatibility"]["ai-v2/review-v1"] = True
    elif mutation == "unsafe_rollout":
        candidate["rollout_order"][0] = "deploy-ai-v2-disabled"
    elif mutation == "rollback_unverified":
        candidate["rollback_compatibility_verified"] = False
    elif mutation == "stale_manifest":
        candidate["integration_manifest"]["component_commits"]["ai-service"] = "1" * 40
    elif mutation == "unpinned_manifest":
        candidate["integration_manifest"]["component_commits"]["ai-service"] = "main"
    elif mutation == "wrong_integration_subject":
        candidate["integration_manifest"]["change_id"] = "AI-2499"
    elif mutation == "false_integration_report":
        candidate["submitted_scenario_results"] = {
            key: True for key in candidate["submitted_scenario_results"]
        }
    elif mutation == "untrusted_evidence":
        candidate["evidence_references"].append("agent-self-report")
    elif mutation == "old_evidence":
        candidate["evidence_references"].append("INT-RUN-OLD")
    elif mutation == "direct_contract_change":
        candidate["contract_change_status"] = "DIRECTLY_APPLIED"
    elif mutation == "work_units_not_invalidated":
        candidate["affected_work_units_invalidated"] = False
    elif mutation == "local_ci_as_system_evidence":
        candidate["local_ci_is_system_evidence"] = True
    elif mutation == "self_authorized_release":
        candidate["release_authorized"] = True
    elif mutation == "missing_evidence":
        candidate["evidence_references"] = []
    elif mutation == "missing_requirement_allocation":
        candidate["child_specs"]["AI-2500-UNDERWRITING"]["implements"] = []


def assess_candidate(candidate: dict[str, object]):
    context = trusted_context(candidate)
    return evaluate_candidate(candidate, context), context


def _case_result(case: dict[str, object]) -> dict[str, object]:
    candidate = build_candidate(case.get("mutations", []))
    decision, _ = assess_candidate(candidate)
    codes = {finding.code for finding in decision.findings}
    required = set(case.get("required_codes", []))
    passed = decision.state == case["expected_state"] and required <= codes
    return {
        "id": case["id"],
        "passed": passed,
        "expected_state": case["expected_state"],
        "actual_state": decision.state,
        "required_codes": sorted(required),
        "actual_codes": sorted(codes),
    }


def run_cases(path: str) -> dict[str, object]:
    results = [_case_result(case) for case in load_json(ROOT / path)["cases"]]
    return {
        "passed": sum(result["passed"] for result in results),
        "total": len(results),
        "results": results,
    }


def build_report() -> dict[str, object]:
    conformance = run_cases("conformance-suite.json")
    evaluation = run_cases("evaluation-cases.json")
    reference = build_candidate()
    decision, context = assess_candidate(reference)
    compatibility = dict(context.compatibility_matrix)
    scenarios = dict(context.scenario_results)
    cases = load_json(ROOT / "conformance-suite.json")["cases"]
    baseline_accepted = sum(
        direct_agent_baseline(build_candidate(case.get("mutations", []))).state
        == "READY_FOR_INTEGRATION_REVIEW"
        for case in cases
    )
    return {
        "course_validation": {
            "status": "PASS"
            if conformance["passed"] == conformance["total"]
            and evaluation["passed"] == evaluation["total"]
            else "FAIL"
        },
        "candidate_assessment": {
            "status": decision.state,
            "finding_codes": [finding.code for finding in decision.findings],
            "subject": reference["integration_manifest"],
            "merge_authorized": False,
            "deployment_authorized": False,
        },
        "conformance": conformance,
        "evaluation": evaluation,
        "compatibility": compatibility,
        "integration_scenarios": {
            "passed": sum(scenarios.values()),
            "total": len(scenarios),
            "results": scenarios,
        },
        "comparison": {
            "baseline_cases_accepted": baseline_accepted,
            "governed_cases_correct": conformance["passed"],
            "total": conformance["total"],
        },
        "coordination": {
            "repository_count": len(context.repositories),
            "exact_commits": all(
                len(revision.candidate_commit) == 40
                for revision in context.repositories.values()
            ),
            "evidence_digest": evidence_digest(reference, context),
        },
    }


def main() -> int:
    report = build_report()
    print(json.dumps(report, indent=2))
    return 0 if (
        report["course_validation"]["status"] == "PASS"
        and report["candidate_assessment"]["status"] == "READY_FOR_INTEGRATION_REVIEW"
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
