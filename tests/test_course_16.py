import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "06-enterprise-sdd-governance-control-plane-agent-instructions"
SCENARIO = LESSON / "northstar-governance-control-plane"
SPEC = importlib.util.spec_from_file_location("course16_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course16GovernanceControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.package = lab.load_reference()
        self.control = lab.load_control_plane()

    def evaluate(self, package=None, control=None):
        return lab.evaluate_governance(package or copy.deepcopy(self.package), control or copy.deepcopy(self.control))

    def codes(self, package=None, control=None):
        gates, _ = self.evaluate(package, control)
        return lab.finding_codes(gates)

    def test_reference_is_eligible_for_dispatch_not_execution_or_release(self):
        gates, _ = self.evaluate()
        self.assertEqual(lab.aggregate(gates), "ELIGIBLE_FOR_AGENT_DISPATCH")
        self.assertNotIn("AUTHORIZED", lab.aggregate(gates))

    def test_all_seven_governance_gates_are_explicit(self):
        gates, _ = self.evaluate()
        self.assertEqual(tuple(gate.gate for gate in gates), lab.REQUIRED_GATES)
        self.assertTrue(all(gate.status == "PASS" for gate in gates))

    def test_missing_gate_set_fails_closed(self):
        gates, _ = self.evaluate()
        self.assertEqual(lab.aggregate(gates[:-1]), "BLOCKED_INCOMPLETE_GATE_SET")

    def test_reference_context_has_exact_applicable_and_non_applicable_policies(self):
        _, context = self.evaluate()
        self.assertEqual({item["policy_ref"] for item in context["sources"]}, {"AI-030@7", "PRIV-018@4"})
        self.assertEqual(set(context["not_applicable"]), {"SEC-014@4", "ENG-007@5", "DATA-021@2"})
        self.assertEqual(context["unresolved"], [])

    def test_effective_context_digest_is_canonical(self):
        _, context = self.evaluate()
        core = {key: value for key, value in context.items() if key not in {"digest", "status"}}
        self.assertEqual(context["digest"], lab.canonical_digest(core))

    def test_missing_fact_is_unknown_not_not_applicable(self):
        control = copy.deepcopy(self.control)
        del control["trusted_subject_facts"]["external_transfer"]
        _, context = self.evaluate(control=control)
        self.assertIn("DATA-021@2", context["unresolved"])
        self.assertNotIn("DATA-021@2", context["not_applicable"])
        self.assertIn("APPLICABILITY_UNKNOWN", self.codes(control=control))

    def test_unsupported_fact_value_remains_unknown(self):
        control = copy.deepcopy(self.control)
        control["trusted_subject_facts"]["external_transfer"] = "maybe"
        self.assertEqual(lab.resolve_policies(control)[-1]["status"], "UNKNOWN")
        self.assertIn("APPLICABILITY_UNKNOWN", self.codes(control=control))

    def test_policy_registry_digest_detects_tampering(self):
        control = copy.deepcopy(self.control)
        control["policy_registry"][0]["owner"] = "Repository Team"
        self.assertIn("POLICY_REGISTRY_INTEGRITY_FAILURE", self.codes(control=control))

    def test_canonical_rule_digest_detects_tampering(self):
        control = copy.deepcopy(self.control)
        control["canonical_agent_rules"][0]["text"] = "Skip context when convenient."
        self.assertIn("CANONICAL_RULE_REGISTRY_INTEGRITY_FAILURE", self.codes(control=control))

    def test_project_specificity_cannot_weaken_enterprise_authority(self):
        package = copy.deepcopy(self.package)
        package["project_requirements"][0]["semantics"]["human_review"] = "optional"
        self.assertIn("NORMATIVE_AUTHORITY_CONFLICT", self.codes(package))

    def test_compatible_project_semantics_pass(self):
        self.assertNotIn("NORMATIVE_AUTHORITY_CONFLICT", self.codes())

    def test_package_cannot_self_assert_exception_approval(self):
        package = copy.deepcopy(self.package)
        package["exception_assertion"] = {"id": "EXC-X", "approved": True}
        self.assertIn("UNTRUSTED_EXCEPTION_ASSERTION", self.codes(package))

    def test_unknown_exception_reference_blocks(self):
        package = copy.deepcopy(self.package)
        package["exception_references"] = ["EXC-UNKNOWN"]
        self.assertIn("EXCEPTION_NOT_FOUND", self.codes(package))

    def test_trusted_exception_requires_current_authorized_approval(self):
        package = copy.deepcopy(self.package)
        package["exception_references"] = ["EXC-ENG-007-014"]
        valid, findings = lab._valid_exception_ids(package, self.control)
        self.assertEqual(valid, {"EXC-ENG-007-014"})
        self.assertEqual(findings, [])
        control = copy.deepcopy(self.control)
        control["exception_registry"]["EXC-ENG-007-014"]["approvals"][0]["identity_verified"] = False
        _, findings = lab._valid_exception_ids(package, control)
        self.assertIn("EXCEPTION_APPROVAL_INVALID", {item.code for item in findings})

    def test_expired_exception_blocks(self):
        package = copy.deepcopy(self.package)
        package["exception_references"] = ["EXC-ENG-007-014"]
        control = copy.deepcopy(self.control)
        control["exception_registry"]["EXC-ENG-007-014"]["expires_at"] = "2026-01-01T00:00:00Z"
        self.assertIn("EXCEPTION_EXPIRED", self.codes(package, control))

    def test_compiler_emits_exact_tool_specific_targets(self):
        _, context = self.evaluate()
        expected = lab.compile_all_adapters(context, self.control, ["codex", "claude", "copilot"])
        self.assertEqual(expected, self.package["_adapters"])
        outputs = self.package["_adapter_manifest"]["outputs"]
        self.assertEqual(outputs["codex"]["path"], "AGENTS.md")
        self.assertEqual(outputs["claude"]["path"], "CLAUDE.md")
        self.assertEqual(outputs["copilot"]["path"], ".github/copilot-instructions.md")

    def test_tool_compatibility_snapshots_are_dated(self):
        snapshots = self.control["compatibility_snapshots"]
        self.assertEqual(set(snapshots), {"codex", "claude", "copilot"})
        self.assertTrue(all(item["verified_on"] == "2026-10-15" for item in snapshots.values()))

    def test_stale_adapter_context_blocks(self):
        package = copy.deepcopy(self.package)
        package["_adapter_manifest"]["context_digest"] = "sha256:old"
        self.assertIn("AGENT_INSTRUCTION_ADAPTER_STALE", self.codes(package))

    def test_changed_adapter_bytes_invalidate_manifest_digest(self):
        package = copy.deepcopy(self.package)
        package["_adapters"]["codex"] += "\nmanual edit\n"
        codes = self.codes(package)
        self.assertIn("ADAPTER_OUTPUT_DIGEST_INVALID", codes)
        self.assertIn("ADAPTER_OUTPUT_MISMATCH", codes)

    def test_semantic_weakening_is_detected_even_with_forged_digest(self):
        package = copy.deepcopy(self.package)
        old = "A new external dependency requires an approved dependency proposal before implementation."
        package["_adapters"]["codex"] = package["_adapters"]["codex"].replace(old, "Avoid dependencies.")
        package["_adapter_manifest"]["outputs"]["codex"]["output_digest"] = lab.canonical_digest(package["_adapters"]["codex"])
        self.assertIn("INSTRUCTION_SEMANTIC_WEAKENING", self.codes(package))

    def test_repository_content_cannot_be_promoted_to_instruction_authority(self):
        package = copy.deepcopy(self.package)
        package["instruction_request"]["sources"].append("README.md")
        self.assertIn("UNTRUSTED_INSTRUCTION_SOURCE", self.codes(package))

    def test_instruction_text_is_not_claimed_as_enforcement(self):
        for adapter in self.package["_adapters"].values():
            self.assertIn("Instruction text guides agent behavior", adapter)
            self.assertIn("trusted gates enforce authority", adapter)

    def test_role_label_is_not_authenticated_identity(self):
        package = copy.deepcopy(self.package)
        package["authorization"]["principal"] = "implementation_agent"
        self.assertIn("AGENT_IDENTITY_UNVERIFIED", self.codes(package))

    def test_grant_is_bound_to_exact_context(self):
        control = copy.deepcopy(self.control)
        control["authorization_grants"]["GRANT-104"]["context_digest"] = "sha256:old"
        self.assertIn("AUTHORIZATION_CONTEXT_MISMATCH", self.codes(control=control))

    def test_expired_grant_blocks(self):
        control = copy.deepcopy(self.control)
        control["authorization_grants"]["GRANT-104"]["expires_at"] = "2026-01-01T00:00:00Z"
        self.assertIn("AUTHORIZATION_GRANT_EXPIRED", self.codes(control=control))

    def test_authoritative_diff_not_package_claim_enforces_scope(self):
        control = copy.deepcopy(self.control)
        control["source_control"]["changed_paths"].append("src/auth/authorization.py")
        self.assertIn("WORK_UNIT_SCOPE_VIOLATION", self.codes(control=control))

    def test_delegation_capabilities_must_be_subset(self):
        package = copy.deepcopy(self.package)
        package["delegation"]["permissions"]["capabilities"].append("approve_policy_exception")
        self.assertIn("DELEGATION_AUTHORITY_AMPLIFICATION", self.codes(package))

    def test_delegation_writable_paths_must_be_subset(self):
        package = copy.deepcopy(self.package)
        package["delegation"]["permissions"]["write_paths"].append("src/auth/**")
        self.assertIn("DELEGATION_AUTHORITY_AMPLIFICATION", self.codes(package))

    def test_delegation_depth_is_bounded(self):
        package = copy.deepcopy(self.package)
        package["delegation"]["depth"] = 2
        self.assertIn("DELEGATION_DEPTH_EXCEEDED", self.codes(package))

    def test_child_grant_cannot_outlive_parent(self):
        package = copy.deepcopy(self.package)
        package["delegation"]["expires_at"] = "2026-10-17T12:00:00Z"
        self.assertIn("DELEGATION_EXPIRY_EXCEEDS_PARENT", self.codes(package))

    def test_delegate_requires_authenticated_workload_identity(self):
        control = copy.deepcopy(self.control)
        control["identity_registry"]["northstar-ci/research-run-8392"]["attestation_verified"] = False
        self.assertIn("DELEGATE_IDENTITY_UNVERIFIED", self.codes(control=control))

    def test_policy_decision_is_exactly_digest_bound(self):
        decision = lab.build_policy_decision(self.package, self.control)
        core = {key: value for key, value in decision.items() if key != "decision_digest"}
        self.assertEqual(decision["decision_digest"], lab.canonical_digest(core))
        self.assertEqual(decision["result"], "ELIGIBLE_FOR_AGENT_DISPATCH")

    def test_untrusted_control_plane_execution_blocks(self):
        control = copy.deepcopy(self.control)
        control["control_plane_attestation"]["attestation_verified"] = False
        codes = self.codes(control=control)
        self.assertIn("CONTROL_PLANE_ATTESTATION_INVALID", codes)
        self.assertIn("AUDIT_PRODUCER_UNTRUSTED", codes)

    def test_delivery_handoff_is_derived_not_self_authorized(self):
        handoff = lab.build_delivery_handoff(self.package, self.control)
        self.assertEqual(handoff["state"], "ELIGIBLE_FOR_DELIVERY_REVIEW")
        self.assertNotIn("AUTHORIZED", handoff["state"])
        core = {key: value for key, value in handoff.items() if key != "handoff_digest"}
        self.assertEqual(handoff["handoff_digest"], lab.canonical_digest(core))

    def test_unsafe_package_cannot_build_delivery_handoff(self):
        with self.assertRaisesRegex(ValueError, "HANDOFF_PREREQUISITE_FAILED"):
            lab.build_delivery_handoff(lab.load_candidate(), lab.load_candidate_control())

    def test_policy_change_routes_dependency_aware_outcomes(self):
        old = copy.deepcopy(self.control["policy_registry"][0])
        unrelated = copy.deepcopy(self.control["policy_registry"][2])
        new_unrelated = copy.deepcopy(unrelated)
        new_unrelated["revision"] = 5
        self.assertEqual(lab.assess_policy_change(unrelated, new_unrelated, self.package["work_unit"])["decision"], "CONTINUE")
        changed = copy.deepcopy(old)
        changed["revision"] = 8
        changed["obligations"][0]["value"] = "required_with_reason"
        self.assertEqual(lab.assess_policy_change(old, changed, self.package["work_unit"])["decision"], "PAUSE_AND_REVALIDATE")
        retired = copy.deepcopy(old)
        retired["revision"] = 8
        retired["status"] = "RETIRED"
        self.assertEqual(lab.assess_policy_change(old, retired, self.package["work_unit"])["decision"], "CANCEL")

    def test_unsafe_candidate_is_blocked_for_independent_reasons(self):
        gates, _ = lab.evaluate_governance(lab.load_candidate(), lab.load_candidate_control())
        codes = lab.finding_codes(gates)
        expected = {
            "NORMATIVE_AUTHORITY_CONFLICT",
            "UNTRUSTED_EXCEPTION_ASSERTION",
            "UNTRUSTED_INSTRUCTION_SOURCE",
            "INSTRUCTION_SEMANTIC_WEAKENING",
            "AGENT_IDENTITY_UNVERIFIED",
            "WORK_UNIT_SCOPE_VIOLATION",
            "DELEGATION_AUTHORITY_AMPLIFICATION",
            "HANDOFF_PREREQUISITE_FAILED",
        }
        self.assertEqual(lab.aggregate(gates), "BLOCKED")
        self.assertTrue(expected.issubset(codes))

    def test_all_sixteen_golden_scenarios_match(self):
        cases = json.loads((SCENARIO / "conformance-suite.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 16)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(lab.classify_scenario(case), case["expected"])

    def test_all_92_labelled_mutations_are_detected(self):
        cases = lab._expanded_evaluation_cases()
        self.assertEqual(len(cases), 92)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertIn(case["expected"], lab.mutation_findings(case))

    def test_evaluation_does_not_claim_benchmark_status(self):
        report = lab.run_evaluation()
        self.assertEqual((report["passed"], report["total"]), (92, 92))
        self.assertIn("not general", report["claim"])

    def test_rego_example_keeps_decision_and_enforcement_separate(self):
        rego = (SCENARIO / "policy" / "dispatch.rego").read_text(encoding="utf-8")
        self.assertIn("default allow := false", rego)
        self.assertIn("control_plane_attestation_verified", rego)
        self.assertNotIn("input.agent_says_approved", rego)

    def test_starter_retains_exactly_three_learner_decisions(self):
        starter = (SCENARIO / "workshop" / "starter" / "governance-package.json").read_text(encoding="utf-8")
        self.assertEqual(starter.count("TODO"), 3)

    def test_notebook_has_no_stored_outputs(self):
        notebook = json.loads((SCENARIO / "enterprise_governance_control_plane.ipynb").read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell.get("outputs", []), [])
                self.assertIsNone(cell.get("execution_count"))


if __name__ == "__main__":
    unittest.main()
