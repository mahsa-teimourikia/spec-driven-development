"""Focused verification for Course 20 multi-repository SDD."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/intermediate/10-multi-repository-spec-driven-development-with-ai-coding-agents"
SCENARIO = LESSON / "northstar-multirepo"
SPEC = importlib.util.spec_from_file_location("course20_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
sys.path.insert(0, str(SCENARIO))
SPEC.loader.exec_module(lab)

from multirepo_app.control_plane import dependency_order, direct_agent_baseline  # noqa: E402
from multirepo_app.git_harness import REPOSITORIES, canonical_digest  # noqa: E402


class Course20Tests(unittest.TestCase):
    def codes(self, mutations):
        decision, _ = lab.assess_candidate(lab.build_candidate(mutations))
        return {finding.code for finding in decision.findings}

    def test_reference_change_stops_at_integration_review(self):
        decision, _ = lab.assess_candidate(lab.build_candidate())
        self.assertEqual(decision.state, "READY_FOR_INTEGRATION_REVIEW")

    def test_five_real_repository_revisions_are_pinned(self):
        _, context = lab.assess_candidate(lab.build_candidate())
        self.assertEqual(set(context.repositories), set(REPOSITORIES))
        for revision in context.repositories.values():
            self.assertEqual(len(revision.baseline_commit), 40)
            self.assertEqual(len(revision.candidate_commit), 40)

    def test_git_diff_is_derived_for_each_repository(self):
        _, context = lab.assess_candidate(lab.build_candidate())
        self.assertEqual(
            set(context.repositories["ai-service"].changed_paths),
            {"config.json", "spec/child-change.json", "src/classifier.py", "tests/test_contract.py"},
        )
        self.assertEqual(context.repositories["document-service"].changed_paths, ())

    def test_parent_child_revision_drift_blocks(self):
        self.assertIn("STALE_PARENT_REVISION", self.codes(["stale_parent"]))

    def test_parent_child_semantic_conflict_blocks(self):
        self.assertIn("PARENT_CHILD_SEMANTIC_CONFLICT", self.codes(["semantic_bypass"]))

    def test_missing_child_blocks(self):
        self.assertIn("CHILD_SET_INCOMPLETE", self.codes(["missing_child"]))

    def test_every_parent_requirement_needs_a_repository_owner(self):
        self.assertIn("REQUIREMENT_ALLOCATION_INCOMPLETE", self.codes(["missing_requirement_allocation"]))

    def test_contract_owner_is_not_a_repository_agent(self):
        self.assertIn("CONTRACT_OWNER_MISMATCH", self.codes(["wrong_contract_owner"]))

    def test_protected_contract_digest_detects_drift(self):
        self.assertIn("CANONICAL_CONTRACT_DRIFT", self.codes(["contract_drift"]))
        contract = json.loads((SCENARIO / "contracts/classification-v2.schema.json").read_text())
        self.assertTrue(canonical_digest(contract).startswith("sha256:"))

    def test_dependency_order_is_contract_first_and_integration_last(self):
        graph = json.loads((SCENARIO / "parent-change/dependency-graph.json").read_text())
        order = dependency_order(graph)
        self.assertEqual(order[0], "AI-2500-CONTRACT")
        self.assertEqual(order[-1], "AI-2500-INTEGRATION")

    def test_dependency_cycle_blocks(self):
        self.assertIn("CHANGE_GRAPH_INVALID", self.codes(["dependency_cycle"]))

    def test_missing_contract_dependency_blocks(self):
        self.assertIn("DEPENDENCY_PLAN_INCOMPLETE", self.codes(["missing_contract_dependency"]))

    def test_work_unit_is_bound_to_real_baseline_commit(self):
        candidate = lab.build_candidate()
        _, context = lab.assess_candidate(candidate)
        self.assertEqual(
            candidate["work_units"]["ai-service"]["base_commit"],
            context.repositories["ai-service"].baseline_commit,
        )

    def test_stale_repository_context_blocks(self):
        self.assertIn("STALE_REPOSITORY_CONTEXT", self.codes(["stale_repo_context"]))

    def test_work_unit_cannot_widen_decision_authority(self):
        self.assertIn("WORK_UNIT_AUTHORITY_WIDENED", self.codes(["widened_authority"]))

    def test_actual_git_diff_cannot_hide_outside_work_unit(self):
        self.assertIn("CROSS_REPOSITORY_SCOPE_EXPANSION", self.codes(["scope_expansion"]))

    def test_compatibility_matrix_is_executed(self):
        _, context = lab.assess_candidate(lab.build_candidate())
        self.assertEqual(
            dict(context.compatibility_matrix),
            {
                "ai-v1/review-v1": True,
                "ai-v1/review-v2": True,
                "ai-v2/review-v1": False,
                "ai-v2/review-v2": True,
            },
        )

    def test_matrix_overclaim_blocks(self):
        self.assertIn("COMPATIBILITY_OVERCLAIM", self.codes(["matrix_overclaim"]))

    def test_consumer_first_rollout_is_required(self):
        self.assertIn("UNSAFE_DEPLOYMENT_ORDER", self.codes(["unsafe_rollout"]))

    def test_rollback_compatibility_is_derived_not_self_asserted(self):
        codes = self.codes(["new_consumer_rejects_v1"])
        self.assertIn("ROLLBACK_COMPATIBILITY_UNVERIFIED", codes)
        self.assertIn("SYSTEM_INTEGRATION_FAILED", codes)

    def test_integration_manifest_matches_exact_commits(self):
        candidate = lab.build_candidate()
        _, context = lab.assess_candidate(candidate)
        expected = {name: revision.candidate_commit for name, revision in context.repositories.items()}
        self.assertEqual(candidate["integration_manifest"]["component_commits"], expected)

    def test_stale_or_symbolic_manifest_blocks(self):
        self.assertIn("INTEGRATION_MANIFEST_STALE", self.codes(["stale_manifest"]))
        self.assertIn("UNPINNED_COMPONENT_REVISION", self.codes(["unpinned_manifest"]))

    def test_trusted_scenarios_include_negative_paths(self):
        _, context = lab.assess_candidate(lab.build_candidate())
        self.assertEqual(len(context.scenario_results), 11)
        self.assertTrue(all(context.scenario_results.values()))
        for name in ("cross_tenant_reference", "duplicate_event", "stale_approval", "single_authority"):
            self.assertIn(name, context.scenario_results)

    def test_cross_tenant_leak_blocks_despite_green_local_ci(self):
        candidate = lab.build_candidate(["cross_tenant_leak"])
        self.assertTrue(all(candidate["local_ci"].values()))
        self.assertEqual(direct_agent_baseline(candidate).state, "READY_FOR_INTEGRATION_REVIEW")
        decision, _ = lab.assess_candidate(candidate)
        self.assertEqual(decision.state, "BLOCKED")

    def test_duplicate_effect_blocks(self):
        self.assertIn("SYSTEM_INTEGRATION_FAILED", self.codes(["duplicate_effect"]))

    def test_missing_provenance_blocks(self):
        self.assertIn("SYSTEM_INTEGRATION_FAILED", self.codes(["missing_provenance_accepted"]))

    def test_review_outage_fails_closed(self):
        self.assertIn("SYSTEM_INTEGRATION_FAILED", self.codes(["unsafe_review_outage"]))

    def test_ai_service_cannot_become_authoritative(self):
        self.assertIn("SYSTEM_INTEGRATION_FAILED", self.codes(["dual_write_authority"]))

    def test_candidate_report_is_compared_with_execution(self):
        self.assertIn(
            "INTEGRATION_REPORT_MISMATCH",
            self.codes(["cross_tenant_leak", "false_integration_report"]),
        )

    def test_evidence_registry_binds_exact_commits(self):
        _, context = lab.assess_candidate(lab.build_candidate())
        receipt = context.evidence_registry["INT-RUN-AI2500"]
        expected = {name: revision.candidate_commit for name, revision in context.repositories.items()}
        self.assertEqual(dict(receipt.component_commits), expected)
        self.assertEqual(receipt.contract_revision, 2)

    def test_untrusted_and_old_evidence_block(self):
        self.assertIn("UNTRUSTED_INTEGRATION_EVIDENCE", self.codes(["untrusted_evidence"]))
        self.assertIn("STALE_CONTRACT_EVIDENCE", self.codes(["old_evidence"]))

    def test_current_integration_evidence_is_required(self):
        self.assertIn("INTEGRATION_EVIDENCE_MISSING", self.codes(["missing_evidence"]))

    def test_contract_gap_routes_through_owner_and_replanning(self):
        self.assertIn("CONTRACT_CHANGE_NOT_APPROVED", self.codes(["direct_contract_change"]))
        self.assertIn("AFFECTED_WORK_UNITS_NOT_INVALIDATED", self.codes(["work_units_not_invalidated"]))

    def test_local_ci_never_becomes_system_evidence(self):
        self.assertIn("LOCAL_CI_TREATED_AS_SYSTEM_EVIDENCE", self.codes(["local_ci_as_system_evidence"]))

    def test_package_cannot_self_authorize_release(self):
        self.assertIn("SELF_AUTHORIZED_RELEASE", self.codes(["self_authorized_release"]))

    def test_mutation_labels_are_not_evaluator_inputs(self):
        candidate = lab.build_candidate()
        candidate["mutation_labels"] = ["cross_tenant_leak", "self_authorized_release"]
        decision, _ = lab.assess_candidate(candidate)
        self.assertEqual(decision.state, "READY_FOR_INTEGRATION_REVIEW")

    def test_lab_report_is_complete_and_bounded(self):
        report = lab.build_report()
        self.assertEqual(report["course_validation"]["status"], "PASS")
        self.assertEqual(report["candidate_assessment"]["status"], "READY_FOR_INTEGRATION_REVIEW")
        self.assertFalse(report["candidate_assessment"]["merge_authorized"])
        self.assertFalse(report["candidate_assessment"]["deployment_authorized"])
        self.assertEqual((report["conformance"]["passed"], report["conformance"]["total"]), (16, 16))
        self.assertEqual((report["evaluation"]["passed"], report["evaluation"]["total"]), (40, 40))
        self.assertEqual((report["integration_scenarios"]["passed"], report["integration_scenarios"]["total"]), (11, 11))

    def test_openspec_package_preserves_release_boundary(self):
        proposal = (SCENARIO / "openspec/changes/AI-2500/proposal.md").read_text()
        tasks = (SCENARIO / "openspec/changes/AI-2500/tasks.md").read_text()
        self.assertIn("does not approve", proposal)
        self.assertIn("[ ] Obtain accountable deployment", tasks)

    def test_starter_retains_six_learner_decisions(self):
        starter = (SCENARIO / "workshop/starter/integration-package.json").read_text()
        self.assertEqual(starter.count("TODO:"), 6)

    def test_notebook_is_clean(self):
        notebook = json.loads((SCENARIO / "multirepo_sdd.ipynb").read_text())
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertTrue(code_cells)
        self.assertTrue(all(cell.get("execution_count") is None and not cell.get("outputs") for cell in code_cells))

    def test_diagram_is_reproducible(self):
        renderer = SCENARIO / "assets/render_diagram.py"
        output = SCENARIO / "assets/multirepo-control-plane.svg"
        before = output.read_text()
        subprocess.run([sys.executable, str(renderer)], cwd=renderer.parent, check=True, capture_output=True)
        self.assertEqual(before, output.read_text())


if __name__ == "__main__":
    unittest.main()
