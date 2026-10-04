"""Executable quality gates for Course 13."""

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

COURSE = Path(__file__).resolve().parents[1] / "curriculum" / "intermediate" / "03-github-spec-kit-enterprise-sdd"
LAB_PATH = COURSE / "northstar-spec-kit-adapter" / "lab.py"
SPEC = importlib.util.spec_from_file_location("course13_lab", LAB_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


def codes(findings):
    return {item.code for item in findings}


class Course13Tests(unittest.TestCase):
    def test_reference_package_is_ready_for_owner_review(self):
        findings = lab.review_bundle(lab.load_source(), lab.load_snapshot(), lab.load_reference())
        self.assertEqual(findings, [])
        self.assertEqual(lab.selection_state(findings), "READY_FOR_OWNER_REVIEW")

    def test_intentionally_unsafe_candidate_is_blocked(self):
        findings = lab.review_bundle(lab.load_source(), lab.load_snapshot(), lab.load_candidate())
        self.assertEqual(lab.selection_state(findings), "BLOCKED")
        self.assertGreaterEqual(len(codes(findings)), 25)

    def test_task_adapter_matches_reference_work_units(self):
        package = lab.load_reference()
        self.assertEqual(lab.validate_awu_adapter(package), [])
        self.assertEqual(lab.adapt_tasks_to_work_units(package), package["work_units"])

    def test_task_adapter_detects_drift(self):
        package = lab.load_reference()
        package["work_units"][0]["requirements"] = []
        self.assertEqual(codes(lab.validate_awu_adapter(package)), {"AWU_ADAPTER_DRIFT"})

    def test_risk_routing(self):
        cases = [
            (["documentation"], "lightweight_change"),
            (["shared_contract"], "standard_spec_driven"),
            (["persistent_data"], "standard_spec_driven"),
            (["public_api"], "standard_spec_driven"),
            (["regulated_data"], "governed_orchestrated"),
            (["security_boundary"], "governed_orchestrated"),
            (["cross_repository"], "governed_orchestrated"),
            (["ai_behavior_change"], "governed_orchestrated"),
        ]
        for signals, expected in cases:
            with self.subTest(signals=signals):
                self.assertEqual(lab.route_operating_mode(signals), expected)

    def test_snapshot_is_an_observation_not_a_certification_claim(self):
        snapshot = lab.load_snapshot()
        self.assertEqual(snapshot["release"], "v1.1.0")
        self.assertTrue(snapshot["resolved_commit"])
        self.assertIn("not_vendor_certification", snapshot["claim"])

    def test_spec_kit_markdown_artifacts_exist(self):
        base = COURSE / "northstar-spec-kit-adapter" / "reference"
        paths = [
            base / ".specify" / "memory" / "constitution.md",
            base / "specs" / "001-broker-document-classification" / "spec.md",
            base / "specs" / "001-broker-document-classification" / "plan.md",
            base / "specs" / "001-broker-document-classification" / "tasks.md",
        ]
        self.assertTrue(all(path.is_file() and path.stat().st_size > 300 for path in paths))

    def test_reference_spec_digest_binds_exact_content(self):
        spec_path = COURSE / "northstar-spec-kit-adapter" / "reference" / "specs" / "001-broker-document-classification" / "spec.md"
        observed = "sha256:" + hashlib.sha256(spec_path.read_bytes()).hexdigest()
        self.assertEqual(lab.load_reference()["specification"]["content_digest"], observed)

    def test_each_control_evaluation_case(self):
        cases_path = COURSE / "northstar-spec-kit-adapter" / "evaluation-cases.json"
        for case in json.loads(cases_path.read_text(encoding="utf-8"))["cases"]:
            with self.subTest(case=case["id"]):
                source = lab.load_source()
                snapshot = copy.deepcopy(lab.load_snapshot())
                package = copy.deepcopy(lab.load_reference())
                lab.apply_mutation(case["mutation"], package, snapshot)
                self.assertIn(case["expected"], codes(lab.review_bundle(source, snapshot, package)))

    def test_each_golden_conformance_scenario(self):
        suite_path = COURSE / "northstar-spec-kit-adapter" / "conformance-suite.json"
        for case in json.loads(suite_path.read_text(encoding="utf-8"))["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(lab.execute_scenario(case), case["expected"])

    def test_evaluation_suite_reports_full_detection(self):
        result = lab.run_evaluation()
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["total"], 36)

    def test_conformance_suite_reports_full_pass(self):
        result = lab.run_conformance_suite()
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["total"], 8)

    def test_demo_preserves_authority_boundary(self):
        demo = lab.run_demo()
        self.assertEqual(demo["reference"]["state"], "READY_FOR_OWNER_REVIEW")
        self.assertEqual(demo["candidate"]["state"], "BLOCKED")
        self.assertIn("trusted controls", demo["authority_boundary"])

    def test_fixture_is_explicitly_synthetic(self):
        self.assertEqual(lab.load_source()["fixture_status"], "synthetic_training_context")
        self.assertTrue(lab.load_reference()["fixture_status"].startswith("synthetic_"))

    def test_open_question_blocks_automatic_satisfaction(self):
        spec = lab.load_reference()["specification"]
        self.assertEqual(spec["open_questions"][0]["status"], "OPEN")
        self.assertEqual(spec["capability_gates"]["automatic_requirement_satisfaction"], "BLOCKED")

    def test_completion_report_is_not_release_evidence(self):
        evidence = lab.load_reference()["evidence_manifest"]
        report = next(record for record in evidence["records"] if record["kind"] == "completion_report")
        self.assertFalse(report["independent"])
        self.assertFalse(evidence["production_ready"])
        self.assertEqual(evidence["release_authority"], "delivery_control_plane")

    def test_child_specs_only_specialize_parent_requirements(self):
        model = lab.load_reference()["multi_repository"]
        parent = set(model["canonical_requirement_ids"])
        self.assertTrue(all(set(child["requirement_ids"]).issubset(parent) for child in model["children"]))
        self.assertTrue(all(child["semantic_overrides"] == [] for child in model["children"]))

    def test_agent_instruction_adapters_are_derived_and_semantics_free(self):
        adapters = lab.load_reference()["agent_instruction_adapters"]
        self.assertTrue(all(item["source_revision"] == adapters["canonical_revision"] for item in adapters["generated"]))
        self.assertFalse(adapters["feature_semantics_in_instructions"])

    def test_unvetted_extension_catalog_is_disabled(self):
        catalogs = lab.load_reference()["extension_trust"]["catalogs"]
        community = next(item for item in catalogs if item["id"] == "builtin-community")
        self.assertFalse(community["install_allowed"])
        self.assertTrue(community["artifact_digest_required"])

    def test_convergence_is_append_only_and_not_approval(self):
        convergence = lab.load_reference()["convergence"]
        self.assertEqual(convergence["mode"], "append_only_tasks")
        self.assertEqual(convergence["spec_mutations"], [])
        self.assertEqual(convergence["plan_mutations"], [])
        self.assertEqual(convergence["state"], "READY_FOR_OWNER_REVIEW")


if __name__ == "__main__":
    unittest.main()
