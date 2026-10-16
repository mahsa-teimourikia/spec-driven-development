"""Executable quality gates for Course 15."""

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

COURSE = Path(__file__).resolve().parents[1] / "curriculum" / "intermediate" / "05-enterprise-pdlc-ci-cd-integration"
SCENARIO = COURSE / "northstar-sdd-delivery"
SPEC = importlib.util.spec_from_file_location("course15_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course15Tests(unittest.TestCase):
    def setUp(self):
        self.control = lab.load_control_plane()
        self.reference = lab.load_reference()

    def evaluate(self, package=None, control=None):
        return lab.evaluate_delivery(package or self.reference, control or self.control)

    def codes(self, package=None, control=None):
        return lab.finding_codes(self.evaluate(package, control))

    def test_reference_is_eligible_for_review_not_authorized(self):
        gates = self.evaluate()
        self.assertEqual(lab.aggregate(gates), "ELIGIBLE_FOR_INTEGRATION_REVIEW")
        self.assertEqual(lab.finding_codes(gates), set())
        self.assertFalse(self.reference["integration"]["requested"])
        self.assertFalse(self.reference["deployment"]["requested"])

    def test_all_nine_gates_are_explicit(self):
        gates = self.evaluate()
        self.assertEqual(tuple(gate.gate for gate in gates), lab.REQUIRED_GATES)
        self.assertEqual(len(gates), 9)
        self.assertTrue(all(gate.status in lab.STATUSES for gate in gates))

    def test_not_applicable_is_not_pass(self):
        status = {gate.gate: gate.status for gate in self.evaluate()}
        self.assertEqual(status["integration_authorization"], "NOT_APPLICABLE")
        self.assertEqual(status["deployment_authorization"], "NOT_APPLICABLE")
        self.assertEqual(status["runtime_conformance"], "NOT_APPLICABLE")

    def test_missing_gate_set_fails_closed(self):
        self.assertEqual(lab.aggregate(self.evaluate()[:-1]), "BLOCKED_INCOMPLETE_GATE_SET")

    def test_unsafe_candidate_is_blocked_while_technical_gate_passes(self):
        gates = self.evaluate(lab.load_candidate(), lab.load_candidate_control())
        status = {gate.gate: gate.status for gate in gates}
        self.assertEqual(lab.aggregate(gates), "BLOCKED")
        self.assertEqual(status["technical_quality"], "PASS")
        self.assertGreaterEqual(len(lab.finding_codes(gates)), 10)

    def test_unsafe_candidate_exposes_required_enterprise_failures(self):
        expected = {
            "SPEC_REVISION_STALE",
            "AWU_SCOPE_VIOLATION",
            "UNAUTHORIZED_REQUIREMENT_CHANGE",
            "EVIDENCE_RECORD_NOT_FOUND",
            "UNTRUSTED_EVIDENCE_ASSERTION",
            "CONTROL_PROVENANCE_CLAIM_MISMATCH",
            "SYSTEM_REVISION_DIGEST_INVALID",
            "SEMANTIC_MERGE_CONFLICT",
            "INVALID_INTEGRATION_AUTHORIZATION",
            "INTEGRATION_PREREQUISITE_FAILED",
            "DEPLOYMENT_PREREQUISITE_FAILED",
            "DEPLOYMENT_ARTIFACT_MISMATCH",
        }
        self.assertTrue(expected.issubset(self.codes(lab.load_candidate(), lab.load_candidate_control())))

    def test_requirement_hash_is_checked_independently_of_tests(self):
        package = copy.deepcopy(self.reference)
        package["requirements"]["semantic_hashes"]["REQ-AI-2310-01"] = "weakened"
        self.assertEqual(package["technical_results"]["unit_tests"], "PASS")
        self.assertIn("UNAUTHORIZED_REQUIREMENT_CHANGE", self.codes(package))

    def test_authoritative_diff_crossing_scope_is_rejected(self):
        control = copy.deepcopy(self.control)
        control["source_control"]["changed_paths"].append("src/auth/authorization.py")
        self.assertIn("AWU_SCOPE_VIOLATION", self.codes(control=control))

    def test_package_cannot_hide_authoritative_changed_path(self):
        control = copy.deepcopy(self.control)
        control["source_control"]["changed_paths"].append("src/auth/authorization.py")
        package = copy.deepcopy(self.reference)
        self.assertNotIn("src/auth/authorization.py", package["pull_request"]["changed_paths"])
        codes = self.codes(package, control)
        self.assertIn("PR_DIFF_CLAIM_MISMATCH", codes)
        self.assertIn("AWU_SCOPE_VIOLATION", codes)

    def test_evidence_is_bound_to_exact_commit(self):
        control = copy.deepcopy(self.control)
        control["evidence_registry"]["EVID-CLASS-001"]["subject"]["commit"] = "old"
        codes = self.codes(control=control)
        self.assertIn("EVIDENCE_SUBJECT_MISMATCH", codes)
        self.assertIn("REQUIRED_EVIDENCE_MISSING", codes)

    def test_self_attestation_does_not_satisfy_claim(self):
        package = copy.deepcopy(self.reference)
        record = package["evidence_manifest"]["records"][0]
        record["producer"] = package["pull_request"]["author"]
        record["result"] = "PASS"
        codes = self.codes(package)
        self.assertIn("UNTRUSTED_EVIDENCE_ASSERTION", codes)

    def test_forged_allowlisted_producer_name_does_not_establish_trust(self):
        package = copy.deepcopy(self.reference)
        record = package["evidence_manifest"]["records"][0]
        record.update({"producer": "northstar/evaluation-service@8", "result": "PASS", "independent": True})
        self.assertIn("UNTRUSTED_EVIDENCE_ASSERTION", self.codes(package))

    def test_effective_ai_system_revision_has_all_operational_components(self):
        components = set(self.reference["effective_ai_system_revision"]["components"])
        self.assertEqual(components, {"application", "model", "prompt", "retrieval", "tools", "policy", "runtime_config"})

    def test_effective_ai_system_digest_is_canonically_recomputed(self):
        system = self.reference["effective_ai_system_revision"]
        self.assertEqual(system["digest"], lab.canonical_system_digest(system["components"]))
        package = copy.deepcopy(self.reference)
        package["effective_ai_system_revision"]["components"]["prompt"] = "prompt-bundle@99"
        codes = self.codes(package)
        self.assertIn("SYSTEM_REVISION_DIGEST_INVALID", codes)
        self.assertIn("SYSTEM_COMPONENT_IDENTITY_UNVERIFIED", codes)
        self.assertIn("EVIDENCE_SUBJECT_MISMATCH", codes)

    def test_pr_cannot_supply_its_own_control_revision(self):
        package = copy.deepcopy(self.reference)
        package["control_provenance"]["source"] = "pull-request-head"
        self.assertIn("CONTROL_PROVENANCE_CLAIM_MISMATCH", self.codes(package))

    def test_validator_execution_identity_is_independently_attested(self):
        control = copy.deepcopy(self.control)
        control["execution_attestation"]["attestation_verified"] = False
        self.assertIn("CONTROL_PROVENANCE_INVALID", self.codes(control=control))

    def test_workflow_change_is_control_and_scope_failure(self):
        control = copy.deepcopy(self.control)
        control["source_control"]["changed_paths"].append(".github/workflows/release.yml")
        codes = self.codes(control=control)
        self.assertIn("AWU_SCOPE_VIOLATION", codes)
        self.assertIn("CONTROL_PROVENANCE_INVALID", codes)

    def test_textually_mergeable_semantic_conflict_is_blocked(self):
        package = copy.deepcopy(self.reference)
        package["merge_queue"]["semantic_conflicts"] = ["shared invariant"]
        self.assertIn("SEMANTIC_MERGE_CONFLICT", self.codes(package))

    def test_queue_candidate_must_be_revalidated(self):
        package = copy.deepcopy(self.reference)
        package["merge_queue"]["revalidation_status"] = "NOT_RUN"
        self.assertIn("MERGE_QUEUE_REVALIDATION_MISSING", self.codes(package))

    def test_valid_integration_receipt_is_exact_subject(self):
        package = copy.deepcopy(self.reference)
        package["integration"] = {"requested": True, "receipt_id": "INT-AI2310-001"}
        self.assertEqual(lab.verify_receipt(package, self.control, "INT-AI2310-001", kind="INTEGRATION"), [])

    def test_integration_receipt_is_single_use(self):
        package = copy.deepcopy(self.reference)
        control = copy.deepcopy(self.control)
        package["integration"] = {"requested": True, "receipt_id": "INT-AI2310-001"}
        consumed = lab.consume_receipt(package, control, "INT-AI2310-001", kind="INTEGRATION")
        self.assertEqual(consumed["state"], "USED")
        self.assertEqual(consumed["version"], 2)
        self.assertTrue(lab.integration_completed(package, control))
        with self.assertRaisesRegex(ValueError, "INVALID_INTEGRATION_AUTHORIZATION"):
            lab.consume_receipt(package, control, "INT-AI2310-001", kind="INTEGRATION")

    def test_integration_receipt_cannot_bypass_failed_upstream_gate(self):
        package = copy.deepcopy(self.reference)
        control = copy.deepcopy(self.control)
        package["integration"] = {"requested": True, "receipt_id": "INT-AI2310-001"}
        package["change_manifest"]["specification_revision"] = "AI-2310-spec@6"
        statuses = {gate.gate: gate.status for gate in self.evaluate(package, control)}
        self.assertEqual(statuses["integration_authorization"], "BLOCK")
        with self.assertRaisesRegex(ValueError, "INTEGRATION_PREREQUISITE_FAILED"):
            lab.consume_receipt(package, control, "INT-AI2310-001", kind="INTEGRATION")

    def test_receipt_for_other_kind_cannot_authorize_integration(self):
        package = copy.deepcopy(self.reference)
        findings = lab.verify_receipt(package, self.control, "DEP-AI2310-001", kind="INTEGRATION")
        self.assertEqual(findings[0].code, "INVALID_INTEGRATION_AUTHORIZATION")

    def test_deployment_requires_trusted_build_provenance(self):
        package = copy.deepcopy(self.reference)
        package["deployment"].update({"requested": True, "receipt_id": "DEP-AI2310-001"})
        package["build"]["provenance"]["builder_id"] = "local-untrusted"
        self.assertIn("BUILD_PROVENANCE_INVALID", self.codes(package))

    def test_deployment_artifact_must_match_tested_artifact(self):
        package = copy.deepcopy(self.reference)
        package["deployment"].update({"requested": True, "receipt_id": "DEP-AI2310-001", "artifact_digest": "substituted"})
        self.assertIn("DEPLOYMENT_ARTIFACT_MISMATCH", self.codes(package))

    def test_deployment_requires_consumed_exact_subject_integration(self):
        package = copy.deepcopy(self.reference)
        control = copy.deepcopy(self.control)
        package["integration"] = {"requested": True, "receipt_id": "INT-AI2310-001"}
        package["deployment"].update({"requested": True, "receipt_id": "DEP-AI2310-001"})
        self.assertIn("DEPLOYMENT_PREREQUISITE_FAILED", self.codes(package, control))
        with self.assertRaisesRegex(ValueError, "DEPLOYMENT_PREREQUISITE_FAILED"):
            lab.consume_receipt(package, control, "DEP-AI2310-001", kind="DEPLOYMENT")
        lab.consume_receipt(package, control, "INT-AI2310-001", kind="INTEGRATION")
        package["integration"] = {"requested": False, "receipt_id": None}
        deployment_gate = next(gate for gate in self.evaluate(package, control) if gate.gate == "deployment_authorization")
        self.assertEqual(deployment_gate.status, "PASS")
        consumed = lab.consume_receipt(package, control, "DEP-AI2310-001", kind="DEPLOYMENT")
        self.assertEqual(consumed["state"], "USED")

    def test_runtime_zero_requires_healthy_instrumentation_and_denominator(self):
        package = copy.deepcopy(self.reference)
        package["runtime"].update({"observed": True, "instrumentation_health": "UNHEALTHY", "applicable_population": 0})
        self.assertIn("RUNTIME_EVIDENCE_INCOMPLETE", self.codes(package))

    def test_runtime_system_revision_is_exact(self):
        package = copy.deepcopy(self.reference)
        package["runtime"].update({"observed": True, "system_revision": "old-system"})
        self.assertIn("RUNTIME_SUBJECT_MISMATCH", self.codes(package))

    def test_runtime_requires_complete_rollout_slice_and_window_coverage(self):
        package = copy.deepcopy(self.reference)
        package["runtime"].update({"observed": True, "covered_population_slices": ["english_pdf"]})
        self.assertIn("RUNTIME_COVERAGE_INCOMPLETE", self.codes(package))
        package = copy.deepcopy(self.reference)
        package["runtime"].update({"observed": True, "monitoring_window_id": "old-window"})
        self.assertIn("RUNTIME_WINDOW_STALE", self.codes(package))

    def test_all_eleven_golden_scenarios_match(self):
        cases = json.loads((SCENARIO / "conformance-suite.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 11)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(lab.classify_scenario(case), case["expected"])

    def test_conformance_suite_reports_eleven_of_eleven(self):
        result = lab.run_conformance_suite()
        self.assertEqual((result["passed"], result["total"]), (11, 11))
        self.assertIn("not production", result["claim"])

    def test_all_68_labelled_mutations_are_detected(self):
        cases = lab._expanded_evaluation_cases()
        self.assertEqual(len(cases), 68)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case["expected"], lab.mutation_findings(case))

    def test_evaluation_report_does_not_claim_benchmark_status(self):
        result = lab.run_evaluation()
        self.assertEqual((result["passed"], result["total"]), (68, 68))
        self.assertIn("not a benchmark", result["claim"])

    def test_notebook_has_no_stored_outputs(self):
        notebook = json.loads((SCENARIO / "enterprise_pdlc_delivery.ipynb").read_text(encoding="utf-8"))
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertGreaterEqual(len(code_cells), 8)
        self.assertTrue(all(cell.get("execution_count") is None and cell.get("outputs") == [] for cell in code_cells))


if __name__ == "__main__":
    unittest.main()
