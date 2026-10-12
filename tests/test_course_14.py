"""Executable quality gates for Course 14."""

import copy
import importlib.util
import itertools
import json
import sys
import unittest
from pathlib import Path

COURSE = Path(__file__).resolve().parents[1] / "curriculum" / "intermediate" / "04-openspec-enterprise-change-driven-sdd"
LAB_PATH = COURSE / "northstar-openspec-change" / "lab.py"
SPEC = importlib.util.spec_from_file_location("course14_lab", LAB_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


def codes(findings):
    return {item.code for item in findings}


class Course14Tests(unittest.TestCase):
    def setUp(self):
        self.baseline = lab.load_baseline()
        self.context = lab.load_context()
        self.snapshot = lab.load_snapshot()
        self.reference = lab.load_reference()
        self.authority_map = lab.load_authority_map()
        self.control_plane = lab.load_control_plane()

    def review(self, package=None, snapshot=None, control_plane=None):
        return lab.review_bundle(
            self.baseline,
            self.context,
            snapshot or self.snapshot,
            package or self.reference,
            authority_map=self.authority_map,
            control_plane=control_plane or self.control_plane,
        )

    def test_reference_is_ready_only_for_owner_review(self):
        findings = self.review()
        self.assertEqual(findings, [])
        self.assertEqual(lab.selection_state(findings), "READY_FOR_OWNER_REVIEW")
        self.assertFalse(self.reference["integration"]["eligible"])
        self.assertFalse(self.reference["evidence_manifest"]["production_ready"])

    def test_unsafe_candidate_is_blocked_for_independent_reasons(self):
        candidate = lab.load_candidate()
        snapshot = candidate.pop("_candidate_snapshot")
        observed = codes(self.review(candidate, snapshot))
        self.assertEqual(lab.selection_state(self.review(candidate, snapshot)), "BLOCKED")
        self.assertGreaterEqual(len(observed), 14)
        self.assertIn("PROTECTED_AUTHORITY_MUTATION", observed)
        self.assertIn("CONCURRENT_CHANGE_CONFLICT_UNRECORDED", observed)
        self.assertIn("ARCHIVE_BEFORE_AUTHORIZATION", observed)

    def test_snapshot_is_pinned_observation_not_certification(self):
        self.assertEqual(self.snapshot["release"], "v1.14.1")
        self.assertEqual(self.snapshot["resolved_commit"], "87c3595ace6a2e22957f39ebe5b74c2f2316e0cb")
        self.assertEqual(set(self.snapshot["default_schema"]["delta_operations"]), lab.VALID_OPERATIONS)
        self.assertIn("not_vendor_certification", self.snapshot["claim"])

    def test_context_and_baseline_are_exactly_digest_bound(self):
        fixture = COURSE / "northstar-openspec-change"
        self.assertEqual(self.reference["context"]["digest"], lab.file_digest(fixture / "enterprise/effective-context.json"))
        self.assertEqual(self.reference["baseline"]["digest"], lab.file_digest(fixture / "baseline/baseline.json"))
        self.assertEqual(self.reference["baseline"]["content_digest"], lab.file_digest(fixture / "baseline/document-processing.md"))

    def test_change_artifacts_are_exactly_digest_bound(self):
        fixture = COURSE / "northstar-openspec-change"
        change = lab.primary_change(self.reference)
        self.assertEqual(change["proposal"]["digest"], lab.file_digest(fixture / "changes/AI-2310/proposal.md"))
        self.assertEqual(change["delta_artifact"]["digest"], lab.file_digest(fixture / change["delta_artifact"]["path"]))
        self.assertEqual(change["design"]["digest"], lab.file_digest(fixture / "changes/AI-2310/design.md"))
        self.assertEqual(change["tasks_digest"], lab.file_digest(fixture / "changes/AI-2310/tasks.md"))

    def test_apply_change_returns_candidate_without_mutating_baseline(self):
        original = copy.deepcopy(self.baseline)
        target = lab.apply_change(self.baseline, lab.primary_change(self.reference))
        self.assertEqual(self.baseline, original)
        self.assertEqual(target["revision"], "candidate-target-not-integrated")
        self.assertEqual(lab.requirement_index(target)["REQ-DOC-014"]["revision"], 4)
        self.assertIn("REQ-DOC-021", lab.requirement_index(target))
        self.assertIn("SEC-DOC-022", lab.requirement_index(target))

    def test_modified_delta_carries_complete_prior_state(self):
        current = lab.requirement_index(self.baseline)["REQ-DOC-014"]
        delta = lab.primary_change(self.reference)["deltas"][0]
        self.assertEqual(delta["base_requirement_revision"], current["revision"])
        self.assertEqual(delta["from_text"], current["text"])
        self.assertEqual(delta["from_scenarios"], current["scenarios"])

    def test_concurrent_change_conflicts_are_recorded_and_contained(self):
        types = {item["type"] for item in self.reference["conflicts"]}
        self.assertEqual(types, {"SHARED_REQUIREMENT_MODIFICATION", "AUTHORITY_CONFLICT"})
        self.assertEqual(lab.change_by_id(self.reference, "AI-2331")["state"], "BLOCKED_PENDING_REBASE")
        self.assertTrue(all(not item["agent_resolved"] for item in self.reference["conflicts"]))

    def test_open_question_blocks_only_affected_capability(self):
        change = lab.primary_change(self.reference)
        question = change["open_questions"][0]
        self.assertEqual(question["status"], "OPEN")
        self.assertEqual(change["capability_readiness"][question["blocks"][0]], "BLOCKED")
        self.assertEqual(change["capability_readiness"]["classification_proposal"], "READY_FOR_BOUNDED_IMPLEMENTATION")

    def test_every_task_has_change_and_delta_ancestry(self):
        change = lab.primary_change(self.reference)
        delta_ids = {item["id"] for item in change["deltas"]}
        for task in change["tasks"]:
            self.assertEqual(task["change"], change["revision"])
            self.assertTrue(set(task["delta_ids"]).issubset(delta_ids))
            self.assertTrue(task["required_evidence"])

    def test_each_task_maps_to_one_bounded_work_unit(self):
        tasks = {item["id"] for item in lab.primary_change(self.reference)["tasks"]}
        mapped = [task_id for unit in self.reference["work_units"] for task_id in unit["task_ids"]]
        self.assertEqual(set(mapped), tasks)
        self.assertEqual(len(mapped), len(set(mapped)))
        self.assertTrue(all(unit["writable_paths"] and unit["protected_paths"] and unit["stop_conditions"] for unit in self.reference["work_units"]))

    def test_work_units_justify_evidence_by_claim_ancestry_and_forbid_self_attestation(self):
        for unit in self.reference["work_units"]:
            self.assertEqual({item["kind"] for item in unit["evidence_obligations"]}, set(unit["required_evidence"]))
            self.assertTrue(all(item["requirement_id"] in unit["requirements"] for item in unit["evidence_obligations"]))
            self.assertTrue("not_attest" in unit["evidence_role"] or "never" in unit["evidence_role"] or "not_approval" in unit["evidence_role"])

    def test_evidence_covers_delta_and_regression_claims(self):
        independent = {item["kind"] for item in self.reference["evidence_manifest"]["records"] if item["independent"] and item["result"] == "PASS"}
        self.assertTrue(lab.DELTA_EVIDENCE.issubset(independent))
        self.assertTrue(lab.REGRESSION_EVIDENCE.issubset(independent))
        self.assertIn("agent_completion_report", {item["kind"] for item in self.reference["evidence_manifest"]["records"] if not item["independent"]})

    def test_multi_repository_children_cannot_override_parent(self):
        model = self.reference["multi_repository"]
        canonical = set(model["canonical_requirement_ids"])
        self.assertTrue(all(set(child["requirement_ids"]).issubset(canonical) for child in model["children"]))
        self.assertTrue(all(child["semantic_overrides"] == [] for child in model["children"]))

    def test_baseline_archive_and_release_remain_distinct(self):
        integration = self.reference["integration"]
        self.assertFalse(self.reference["baseline"]["mutated"])
        self.assertFalse(integration["requested"])
        self.assertIsNone(integration["archive_destination"])
        self.assertFalse(integration["release_authorized"])

    def test_each_golden_scenario_matches(self):
        fixture = COURSE / "northstar-openspec-change/conformance-suite.json"
        for case in json.loads(fixture.read_text(encoding="utf-8"))["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(lab.classify_scenario(case), case["expected"])

    def test_conformance_suite_reports_ten_of_ten(self):
        result = lab.run_conformance_suite()
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["total"], 10)
        self.assertIn("not_general", result["claim"])

    def test_each_labelled_mutation_is_detected(self):
        fixture = COURSE / "northstar-openspec-change/evaluation-cases.json"
        for case in json.loads(fixture.read_text(encoding="utf-8"))["cases"]:
            with self.subTest(case=case["id"]):
                self.assertIn(case["expected"], lab.mutation_findings(case["mutation"]))

    def test_mutation_suite_exceeds_course_13_depth(self):
        result = lab.run_evaluation()
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["total"], 61)
        self.assertIn("not_production_assurance", result["claim"])

    def test_each_evidence_obligation_matches_exact_claim_and_execution_subject(self):
        manifest = self.reference["evidence_manifest"]
        expected = {
            lab.evidence_key({
                **obligation,
                "implementation_revision": manifest["implementation_revision"],
                "specification_revision": manifest["specification_revision"],
            })
            for unit in self.reference["work_units"]
            for obligation in unit["evidence_obligations"]
        }
        observed = {
            lab.evidence_key(record)
            for record in manifest["records"]
            if record.get("independent") and record.get("result") == "PASS"
        }
        self.assertTrue(expected.issubset(observed))

    def test_same_evidence_kind_for_wrong_claim_does_not_satisfy_obligation(self):
        self.assertIn("EVIDENCE_SUBJECT_MISMATCH", lab.mutation_findings("evidence_wrong_claim_same_kind"))
        self.assertIn("DELTA_EVIDENCE_MISSING", lab.mutation_findings("evidence_wrong_claim_same_kind"))

    def test_receipt_verifier_checks_values_and_atomic_single_use(self):
        package = copy.deepcopy(self.reference)
        control_plane = copy.deepcopy(self.control_plane)
        package["integration"].update({
            "requested": True,
            "authorization_receipt_id": "RCP-AI2310-001",
            "receipt_version": 1,
        })
        self.assertEqual(lab.verify_integration_receipt(package, self.authority_map, control_plane), [])
        consumed = lab.consume_integration_receipt(package, self.authority_map, control_plane)
        self.assertEqual(consumed["state"], "USED")
        self.assertEqual(consumed["version"], 2)
        with self.assertRaisesRegex(ValueError, "INTEGRATION_RECEIPT_REPLAYED"):
            lab.consume_integration_receipt(package, self.authority_map, control_plane)

    def test_receipt_wrong_binding_expiry_and_replay_are_independent_failures(self):
        self.assertIn("INTEGRATION_RECEIPT_BINDING_MISMATCH", lab.mutation_findings("integration_receipt_unbound"))
        self.assertIn("INTEGRATION_RECEIPT_EXPIRED", lab.mutation_findings("integration_receipt_expired"))
        self.assertIn("INTEGRATION_RECEIPT_REPLAYED", lab.mutation_findings("integration_receipt_replayed"))

    def test_conflict_records_use_stable_change_identity_even_when_revision_labels_collide(self):
        package = copy.deepcopy(self.reference)
        for change in package["changes"]:
            change["revision"] = "revision-1"
        shared = package["conflicts"][0]
        for item in shared["changes"]:
            item["revision"] = "revision-1"
        shared["blocked_change"]["revision"] = "revision-1"
        findings = lab.validate_concurrency(package, self.baseline)
        self.assertNotIn("CONCURRENT_CHANGE_CONFLICT_UNRECORDED", codes(findings))
        shared["changes"][0]["id"] = "AI-OTHER"
        self.assertIn("CONCURRENT_CHANGE_CONFLICT_UNRECORDED", codes(lab.validate_concurrency(package, self.baseline)))

    def test_different_but_related_requirement_changes_create_review_candidate(self):
        findings = lab.mutation_findings("cross_requirement_semantic_candidate")
        self.assertIn("POTENTIAL_CROSS_REQUIREMENT_CONFLICT", findings)

    def test_registry_identity_prevents_actor_name_bypass(self):
        self.assertIn("AGENT_SELF_TRANSITION", lab.mutation_findings("actor_name_bypass_attempt"))

    def test_path_scope_uses_pattern_overlap_and_authoritative_changed_paths(self):
        self.assertTrue(lab.path_patterns_overlap("src/**", "src/auth/**"))
        self.assertFalse(lab.path_patterns_overlap("src/documents/**", "src/auth/**"))
        findings = lab.mutation_findings("awu_changed_path_outside_scope")
        self.assertIn("AWU_CHANGED_PATH_NOT_AUTHORIZED", findings)
        self.assertIn("AWU_PROTECTED_PATH_CHANGED", findings)

    def test_planning_validation_covers_non_primary_changes(self):
        findings = lab.mutation_findings("second_change_task_invalid")
        self.assertIn("TASK_CHANGE_ANCESTRY_MISSING", findings)
        self.assertIn("TASK_DELTA_UNKNOWN", findings)
        self.assertIn("TASK_REQUIREMENT_UNKNOWN", findings)

    def test_generated_delta_orders_preserve_baseline_and_candidate_meaning(self):
        change = copy.deepcopy(lab.primary_change(self.reference))
        original = copy.deepcopy(self.baseline)
        expected = lab.requirement_index(lab.apply_change(self.baseline, change))
        for ordering in itertools.permutations(change["deltas"]):
            candidate = copy.deepcopy(change)
            candidate["deltas"] = list(ordering)
            with self.subTest(order=[item["id"] for item in ordering]):
                self.assertEqual(lab.requirement_index(lab.apply_change(self.baseline, candidate)), expected)
                self.assertEqual(self.baseline, original)

    def test_generated_duplicate_delta_id_positions_are_rejected(self):
        for index in range(1, len(lab.primary_change(self.reference)["deltas"])):
            package = copy.deepcopy(self.reference)
            change = lab.primary_change(package)
            change["deltas"][index]["id"] = change["deltas"][0]["id"]
            with self.subTest(index=index):
                self.assertIn("DELTA_ID_DUPLICATE", codes(self.review(package)))

    def test_duplicate_portfolio_change_identity_is_rejected(self):
        package = copy.deepcopy(self.reference)
        package["changes"][1]["id"] = package["changes"][0]["id"]
        package["changes"][1]["revision"] = package["changes"][0]["revision"]
        self.assertIn("PORTFOLIO_CHANGE_IDENTITY_DUPLICATE", codes(lab.validate_concurrency(package, self.baseline)))

    def test_protected_enterprise_requirement_mutation_blocks(self):
        package = copy.deepcopy(self.reference)
        snapshot = copy.deepcopy(self.snapshot)
        lab.apply_mutation("protected_authority_mutation", package, snapshot)
        self.assertIn("PROTECTED_AUTHORITY_MUTATION", codes(self.review(package, snapshot)))

    def test_stale_baseline_requires_rebase(self):
        package = copy.deepcopy(self.reference)
        snapshot = copy.deepcopy(self.snapshot)
        lab.apply_mutation("stale_baseline_revision", package, snapshot)
        self.assertIn("STALE_BASELINE_REVISION", codes(self.review(package, snapshot)))

    def test_hidden_concurrency_conflict_blocks(self):
        package = copy.deepcopy(self.reference)
        snapshot = copy.deepcopy(self.snapshot)
        lab.apply_mutation("concurrent_conflict_hidden", package, snapshot)
        self.assertIn("CONCURRENT_CHANGE_CONFLICT_UNRECORDED", codes(self.review(package, snapshot)))

    def test_delta_only_evidence_is_insufficient(self):
        package = copy.deepcopy(self.reference)
        snapshot = copy.deepcopy(self.snapshot)
        lab.apply_mutation("regression_evidence_missing", package, snapshot)
        self.assertIn("REGRESSION_EVIDENCE_MISSING", codes(self.review(package, snapshot)))

    def test_archive_before_owner_authorization_blocks(self):
        package = copy.deepcopy(self.reference)
        snapshot = copy.deepcopy(self.snapshot)
        lab.apply_mutation("archive_before_owner_review", package, snapshot)
        self.assertIn("ARCHIVE_BEFORE_AUTHORIZATION", codes(self.review(package, snapshot)))

    def test_framework_semantic_drift_blocks(self):
        package = copy.deepcopy(self.reference)
        snapshot = copy.deepcopy(self.snapshot)
        lab.apply_mutation("snapshot_semantic_drift", package, snapshot)
        self.assertIn("SNAPSHOT_SEMANTIC_DRIFT", codes(self.review(package, snapshot)))

    def test_fixture_is_explicitly_synthetic(self):
        self.assertTrue(self.baseline["fixture_status"].startswith("synthetic_"))
        self.assertTrue(self.context["fixture_status"].startswith("synthetic_"))
        self.assertTrue(self.reference["fixture_status"].startswith("synthetic_"))

    def test_required_open_spec_style_artifacts_exist(self):
        root = COURSE / "northstar-openspec-change"
        required = [
            "changes/AI-2310/proposal.md",
            "changes/AI-2310/specs/document-processing/spec.md",
            "changes/AI-2310/design.md",
            "changes/AI-2310/tasks.md",
            "changes/AI-2331/proposal.md",
            "changes/AI-2331/specs/document-processing/spec.md",
        ]
        self.assertTrue(all((root / item).is_file() and (root / item).stat().st_size > 100 for item in required))


if __name__ == "__main__":
    unittest.main()
