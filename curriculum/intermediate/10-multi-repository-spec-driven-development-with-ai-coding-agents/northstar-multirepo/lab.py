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
        "repository_dispositions": load_json(
            ROOT / "parent-change/repository-dispositions.json"
        ),
        "rollout_transitions": load_json(ROOT / "integration/rollout-transitions.json"),
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
    candidate["local_ci"] = dict(context.local_ci_results)
    candidate["work_units"] = _work_units(context)
    candidate["declared_compatibility"] = dict(context.compatibility_matrix)
    candidate["integration_manifest"] = {
        "change_id": "AI-2500",
        "contract_revision": 2,
        "contract_digest": canonical_digest(HARNESS.canonical_contract),
        "component_commits": {
            repository: revision.candidate_commit
            for repository, revision in context.repositories.items()
        },
        "result_artifact_digest": context.evidence_registry[
            "INT-RUN-AI2500"
        ].result_artifact_digest,
    }
    candidate["submitted_scenario_results"] = dict(context.scenario_results)
    for mutation in mutations:
        _apply_claim_mutation(candidate, mutation)
    return candidate


def _apply_source_mutation(candidate: dict[str, object], mutation: str) -> None:
    if mutation == "cross_tenant_leak":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            '''        proposal_tenant = proposal.get("tenant_id", authorized_tenant)\n        if proposal_tenant != authorized_tenant:\n            raise PermissionError("proposal tenant does not match authenticated tenant")\n        for evidence_ref in proposal.get("evidence_refs", []):\n            if evidence_tenants.get(str(evidence_ref)) != authorized_tenant:\n                raise PermissionError("evidence is missing or belongs to another tenant")\n''',
            '''        # Unsafe mutation: tenant and evidence ownership are trusted without verification.\n''',
        )
        candidate["repository_extra_files"]["review-service"]["tests/test_contract.py"] = (
            "import unittest\n\n"
            "class ShallowLocalTest(unittest.TestCase):\n"
            "    def test_configuration_exists(self):\n"
            "        self.assertTrue(True)\n"
        )
    elif mutation == "duplicate_effect":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            'return {**existing[1], "duplicate": True, "side_effect_count": 0}',
            'return {**existing[1], "duplicate": True, "side_effect_count": 1}',
        )
        candidate["repository_extra_files"]["review-service"]["tests/test_contract.py"] = (
            "import unittest\n\n"
            "class ShallowLocalTest(unittest.TestCase):\n"
            "    def test_configuration_exists(self):\n"
            "        self.assertTrue(True)\n"
        )
    elif mutation == "missing_provenance_accepted":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            '        "model_provenance",\n',
            "",
        )
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            '        and bool(proposal["model_provenance"])\n',
            "        and True\n",
        )
        candidate["repository_extra_files"]["review-service"]["tests/test_contract.py"] = (
            "import unittest\n\n"
            "class ShallowLocalTest(unittest.TestCase):\n"
            "    def test_configuration_exists(self):\n"
            "        self.assertTrue(True)\n"
        )
    elif mutation == "unsafe_review_outage":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            "            if not review_available:\n",
            "            if False and not review_available:\n",
        )
    elif mutation == "review_bypass_behavior":
        _replace_source(
            candidate,
            "ai-service",
            "src/classifier.py",
            '        "review_required": ambiguity_status in {"AMBIGUOUS", "UNSUPPORTED"},',
            '        "review_required": False,',
        )
    elif mutation == "stale_approval_accepted":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            "            if expires_at <= now.astimezone(timezone.utc):\n",
            "            if False and expires_at <= now.astimezone(timezone.utc):\n",
        )
    elif mutation == "dual_write_authority":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            '            "authoritative_mutation_count": 0,',
            '            "authoritative_mutation_count": 1,',
        )
    elif mutation == "new_consumer_rejects_v1":
        _replace_source(
            candidate,
            "review-service",
            "src/review.py",
            "    return contract_revision in {1, 2}\n",
            "    return contract_revision == 2\n",
        )
    elif mutation == "scope_expansion":
        candidate["repository_extra_files"]["ai-service"]["src/unapproved.py"] = "SIDE_EFFECT = True\n"
    elif mutation == "unchanged_dependency_modified":
        candidate["repository_extra_files"]["document-service"]["src/unplanned.py"] = (
            "UNPLANNED_CHANGE = True\n"
        )


def _replace_source(
    candidate: dict[str, object],
    repository: str,
    relative_path: str,
    old: str,
    new: str,
) -> None:
    extras = candidate["repository_extra_files"][repository]
    content = extras.get(relative_path)
    if content is None:
        content = (
            ROOT / "repositories" / repository / "candidate" / relative_path
        ).read_text(encoding="utf-8")
    if old not in content:
        raise ValueError(f"mutation target not found in {repository}/{relative_path}")
    extras[relative_path] = content.replace(old, new, 1)


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
    elif mutation == "failed_consumer_deploy":
        candidate["rollout_transitions"]["transitions"][0]["observed_status"] = "FAILED"
    elif mutation == "activation_without_disable_control":
        candidate["rollout_transitions"]["activation_controls"][
            "new_behavior_disable_control_verified"
        ] = False
    elif mutation == "self_authorized_activation":
        candidate["rollout_transitions"]["activation_controls"][
            "activation_authorized"
        ] = True
    elif mutation == "rollback_unverified":
        candidate["rollback_compatibility_verified"] = False
    elif mutation == "stale_manifest":
        candidate["integration_manifest"]["component_commits"]["ai-service"] = "1" * 40
    elif mutation == "unpinned_manifest":
        candidate["integration_manifest"]["component_commits"]["ai-service"] = "main"
    elif mutation == "wrong_integration_subject":
        candidate["integration_manifest"]["change_id"] = "AI-2499"
    elif mutation == "stale_result_digest":
        candidate["integration_manifest"]["result_artifact_digest"] = "sha256:" + "0" * 64
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
    elif mutation == "missing_repository_disposition":
        candidate["repository_dispositions"].pop("underwriter-ui")


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
