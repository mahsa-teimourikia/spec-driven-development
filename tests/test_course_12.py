"""Regression tests for Course 12's framework-selection operating model."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "02-sdd-framework-landscape-enterprise-operating-model"
MODULE_SPEC = importlib.util.spec_from_file_location("course12_lab", LESSON / "lab.py")
assert MODULE_SPEC and MODULE_SPEC.loader
lab = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = lab
MODULE_SPEC.loader.exec_module(lab)


class Course12FrameworkLandscapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = lab.load_bundle()
        self.candidate = lab.load_bundle(candidate=True)

    @staticmethod
    def codes(findings):
        return {item.code if hasattr(item, "code") else item["code"] for item in findings}

    def test_fixture_is_explicitly_fictional(self):
        self.assertEqual("fictional_training_scenario", lab.run_demo()["fixture_status"])

    def test_landscape_snapshot_is_dated(self):
        self.assertEqual("2026-09-28", self.reference["model"]["observed_at"])

    def test_reference_is_ready_only_for_owner_review(self):
        report = lab.review_operating_model(self.reference)
        self.assertEqual([], report["findings"])
        self.assertEqual("READY_FOR_OWNER_REVIEW", lab.selection_state(report))

    def test_reference_does_not_claim_vendor_certification(self):
        report = lab.review_operating_model(self.reference)
        self.assertIn("not_vendor_certification", report["claim"])

    def test_candidate_is_blocked(self):
        report = lab.review_operating_model(self.candidate)
        self.assertEqual("OPERATING_MODEL_BLOCKED", lab.selection_state(report))
        self.assertGreaterEqual(report["counts"]["blocking"], 10)

    def test_candidate_exposes_framework_as_governance(self):
        self.assertIn("FRAMEWORK_AS_GOVERNANCE", self.codes(lab.review_operating_model(self.candidate)["findings"]))

    def test_all_variants_receive_identical_source_package(self):
        self.assertEqual([], lab.validate_source_equivalence(self.reference["source"], self.reference["model"]))

    def test_changed_context_is_detected(self):
        model = copy.deepcopy(self.reference["model"])
        model["variants"][0]["source_context_id"] = "stale"
        self.assertIn("SOURCE_CONTEXT_DRIFT", self.codes(lab.validate_source_equivalence(self.reference["source"], model)))

    def test_missing_source_artifact_is_detected(self):
        model = copy.deepcopy(self.reference["model"])
        model["variants"][0]["source_ids"] = []
        self.assertIn("SOURCE_PACKAGE_NOT_EQUIVALENT", self.codes(lab.validate_source_equivalence(self.reference["source"], model)))

    def test_variants_preserve_stable_requirement_identity(self):
        expected = {item["id"] for item in self.reference["model"]["enterprise_requirements"]}
        for variant in self.reference["model"]["variants"]:
            self.assertEqual(expected, set(variant["requirement_ids"]))

    def test_requirement_identity_loss_blocks(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["requirement_ids"] = []
        self.assertIn("REQUIREMENT_IDENTITY_LOST", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_policy_sources_remain_external_and_revisioned(self):
        for variant in self.reference["model"]["variants"]:
            self.assertEqual(["AI-POLICY-042@7-training"], variant["policy_source_ids"])

    def test_policy_provenance_loss_blocks(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["policy_source_ids"] = []
        self.assertIn("POLICY_PROVENANCE_LOST", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_open_authorization_question_is_preserved(self):
        for variant in self.reference["model"]["variants"]:
            self.assertIn("Q-AUTH-2310", variant["open_question_ids"])

    def test_collapsed_open_question_blocks(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["open_question_ids"] = []
        self.assertIn("OPEN_QUESTION_COLLAPSED", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_requirements_do_not_silently_choose_architecture(self):
        self.assertTrue(all(not item["requirements_contain_architecture"] for item in self.reference["model"]["variants"]))

    def test_architecture_in_requirement_is_review_finding(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["requirements_contain_architecture"] = True
        self.assertIn("ARCHITECTURE_MIXED_WITH_REQUIREMENTS", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_autonomous_tasks_are_enriched_into_work_units(self):
        for variant in self.reference["model"]["variants"]:
            self.assertTrue(variant["execution"]["agent_work_unit_enrichment"])

    def test_plain_autonomous_tasks_block(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["execution"]["agent_work_unit_enrichment"] = False
        self.assertIn("TASK_AUTHORITY_TOO_BROAD", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_evidence_is_revision_bound(self):
        for variant in self.reference["model"]["variants"]:
            self.assertTrue(variant["evidence"]["manifest"])
            self.assertTrue(variant["evidence"]["subject_revision_binding"])

    def test_evidence_without_revision_binding_blocks(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["evidence"]["subject_revision_binding"] = False
        self.assertIn("EVIDENCE_MODEL_MISSING", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_current_truth_and_change_are_explicit(self):
        for variant in self.reference["model"]["variants"]:
            self.assertTrue(variant["change_semantics"]["current_truth"])
            self.assertTrue(variant["change_semantics"]["proposed_change"])

    def test_implicit_change_semantics_are_detected(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["change_semantics"]["current_truth"] = None
        self.assertIn("CHANGE_SEMANTICS_IMPLICIT", self.codes(lab.validate_variant(variant, self.reference["model"]["enterprise_requirements"])))

    def test_capability_profiles_have_no_overall_ranking(self):
        profiles = lab.capability_profiles(self.reference["model"])
        self.assertIsNone(profiles["overall_ranking"])
        self.assertEqual(4, len(profiles["profiles"]))

    def test_profiles_expose_extension_and_external_cost(self):
        profiles = lab.capability_profiles(self.reference["model"])["profiles"]
        self.assertTrue(all(item["extension"] for item in profiles))
        self.assertTrue(all(item["external"] for item in profiles))

    def test_canonical_registry_contains_required_types(self):
        self.assertEqual([], lab.validate_artifact_registry(self.reference["model"]))
        types = {item["type"] for item in self.reference["model"]["canonical_artifact_registry"]}
        self.assertEqual(lab.REQUIRED_CANONICAL_TYPES, types)

    def test_task_is_not_business_normative(self):
        task = next(item for item in self.reference["model"]["canonical_artifact_registry"] if item["type"] == "task")
        self.assertEqual("non_normative", task["normative_scope"])

    def test_invalid_artifact_authority_domain_blocks(self):
        model = copy.deepcopy(self.reference["model"])
        model["canonical_artifact_registry"][0]["authority_domain"] = "TOOL"
        self.assertIn("ARTIFACT_AUTHORITY_DOMAIN_INVALID", self.codes(lab.validate_artifact_registry(model)))

    def test_every_transformation_has_validators(self):
        self.assertEqual([], lab.validate_command_authority(self.reference["model"]))
        stages = {item["stage"] for item in self.reference["model"]["command_authority_matrix"]}
        self.assertEqual(lab.TRANSFORMATIONS, stages)

    def test_framework_command_cannot_self_approve(self):
        model = copy.deepcopy(self.reference["model"])
        model["command_authority_matrix"][0]["may_approve"] = True
        self.assertIn("FRAMEWORK_COMMAND_SELF_APPROVES", self.codes(lab.validate_command_authority(model)))

    def test_transformation_assurance_is_stage_specific(self):
        self.assertEqual(
            ["dependency", "stop_conditions", "work_unit_enrichment"],
            lab.transformation_assurance("tasks", {"checks": ["scope", "justification"]}),
        )

    def test_unknown_transformation_is_rejected(self):
        with self.assertRaises(ValueError):
            lab.transformation_assurance("approve", {"checks": []})

    def test_each_authoritative_capability_has_one_owner(self):
        self.assertEqual([], lab.validate_extension_boundary(self.reference["model"]))

    def test_duplicate_capability_owner_blocks(self):
        model = copy.deepcopy(self.reference["model"])
        model["authoritative_capability_owners"].append(copy.deepcopy(model["authoritative_capability_owners"][0]))
        self.assertIn("AUTHORITATIVE_OWNER_AMBIGUOUS", self.codes(lab.validate_extension_boundary(model)))

    def test_manual_policy_copy_blocks(self):
        model = copy.deepcopy(self.reference["model"])
        model["extension_boundary"]["policy_propagation"] = "manual_copy"
        self.assertIn("MANUAL_POLICY_COPY", self.codes(lab.validate_extension_boundary(model)))

    def test_framework_fork_cost_is_visible(self):
        model = copy.deepcopy(self.reference["model"])
        model["extension_boundary"]["framework_fork_required"] = True
        self.assertIn("DEEP_FRAMEWORK_FORK", self.codes(lab.validate_extension_boundary(model)))

    def test_selection_dispositions_every_requirement(self):
        requirements = self.reference["model"]["enterprise_requirements"]
        self.assertEqual([], lab.validate_selection_decision(
            self.reference["decision"], requirements, self.reference["model"]["selection_evidence"]
        ))

    def test_selection_evidence_ids_resolve_to_provenance_records(self):
        model = copy.deepcopy(self.reference["model"])
        model["selection_evidence"] = model["selection_evidence"][:-1]
        findings = lab.validate_selection_decision(
            self.reference["decision"], model["enterprise_requirements"], model["selection_evidence"]
        )
        self.assertIn("SELECTION_EVIDENCE_UNRESOLVED", self.codes(findings))

    def test_selection_uses_no_overall_winner_score(self):
        self.assertIsNone(self.reference["decision"]["overall_score"])
        self.assertIn("not_best_framework", self.reference["decision"]["claim"])

    def test_overall_winner_score_is_a_review_finding(self):
        decision = copy.deepcopy(self.reference["decision"])
        decision["overall_score"] = 99
        self.assertIn("FRAMEWORK_WINNER_SCORE", self.codes(lab.validate_selection_decision(decision, self.reference["model"]["enterprise_requirements"])))

    def test_selection_has_assumptions_and_reconsideration_triggers(self):
        decision = self.reference["decision"]
        self.assertTrue(decision["assumptions"])
        self.assertTrue(decision["reconsideration_triggers"])

    def test_synthetic_decision_cannot_claim_approval(self):
        decision = copy.deepcopy(self.reference["decision"])
        decision["status"] = "approved"
        self.assertIn("SYNTHETIC_DECISION_OVERCLAIMS_APPROVAL", self.codes(lab.validate_selection_decision(decision, self.reference["model"]["enterprise_requirements"])))

    def test_risk_tiers_route_proportionally(self):
        self.assertEqual(1, lab.route_risk_tier({})["tier"])
        self.assertEqual(2, lab.route_risk_tier({"shared_contract": True})["tier"])
        self.assertEqual(3, lab.route_risk_tier({"regulated_ai": True})["tier"])
        self.assertEqual(4, lab.route_risk_tier({"cross_repository": True})["tier"])

    def test_risk_route_does_not_select_one_global_framework(self):
        self.assertEqual("context_specific_not_global", lab.route_risk_tier({"regulated_ai": True})["framework_selection"])

    def test_critical_semantics_survive_framework_removal(self):
        for variant in self.reference["model"]["variants"]:
            result = lab.migration_survivability(variant)
            self.assertEqual("PORTABLE", result["decision"])
            self.assertEqual([], result["lost"])

    def test_missing_authority_requires_migration_review(self):
        variant = copy.deepcopy(self.reference["model"]["variants"][0])
        variant["portable_semantics"].remove("authority")
        self.assertEqual("MIGRATION_REVIEW_REQUIRED", lab.migration_survivability(variant)["decision"])

    def test_upgrade_assurance_is_versioned(self):
        self.assertEqual([], lab.validate_upgrade_record(self.reference["model"]))
        upgrade = self.reference["model"]["framework_upgrade_assurance"]
        self.assertTrue(upgrade["baseline_version"] and upgrade["candidate_version"])
        self.assertTrue(upgrade["prompt_template_versions"])

    def test_unversioned_prompts_block_upgrade(self):
        model = copy.deepcopy(self.reference["model"])
        model["framework_upgrade_assurance"]["prompt_template_versions"] = []
        self.assertIn("FRAMEWORK_PROMPTS_UNVERSIONED", self.codes(lab.validate_upgrade_record(model)))

    def test_golden_conformance_suite_passes(self):
        result = lab.run_conformance_suite(self.reference["conformance"])
        self.assertEqual((6, 6, 0), (result["passed"], result["population"], result["failed"]))

    def test_conformance_suite_discloses_its_boundary(self):
        self.assertIn("not_production", lab.run_conformance_suite(self.reference["conformance"])["claim"])

    def test_changed_golden_outcome_fails(self):
        suite = copy.deepcopy(self.reference["conformance"])
        suite["scenarios"][0]["expected_outcome"] = "default_authorization"
        self.assertEqual(1, lab.run_conformance_suite(suite)["failed"])

    def test_labelled_rule_evaluation_is_exact(self):
        evaluation = lab.evaluate_rules()
        self.assertEqual((30, 30, 0, 0), (
            evaluation["population"], evaluation["true_positive"],
            evaluation["false_positive"], evaluation["false_negative"],
        ))
        self.assertEqual({"numerator": 30, "denominator": 30}, evaluation["exact_matches"])

    def test_rule_evaluation_does_not_claim_general_quality(self):
        self.assertIn("not_general", lab.evaluate_rules()["claim"])


if __name__ == "__main__":
    unittest.main()
