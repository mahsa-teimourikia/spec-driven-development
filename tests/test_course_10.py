"""Regression tests for Course 10's deterministic planning model."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "beginner" / "10-specification-to-implementation-plan"
MODULE_SPEC = importlib.util.spec_from_file_location("course10_lab", LESSON / "lab.py")
assert MODULE_SPEC and MODULE_SPEC.loader
lab = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = lab
MODULE_SPEC.loader.exec_module(lab)


class Course10PlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = lab.load_bundle()
        self.candidate = lab.load_bundle(candidate=True)

    def finding_codes(self, findings):
        return {item.code if hasattr(item, "code") else item["code"] for item in findings}

    def test_fixture_is_explicitly_fictional(self):
        self.assertIn("fictional", lab.run_demo()["fixture_status"])

    def test_reference_plan_is_ready(self):
        report = lab.review_plan(self.reference)
        self.assertEqual([], report["findings"])
        self.assertEqual("PLAN_READY", lab.planning_decision(report)["state"])

    def test_reference_plan_does_not_claim_agent_authorization(self):
        report = lab.review_plan(self.reference)
        self.assertIn("not_agent_authorization", report["claim"])

    def test_candidate_requires_architecture(self):
        report = lab.review_plan(self.candidate)
        self.assertEqual("PLAN_REQUIRES_ARCHITECTURE", lab.planning_decision(report)["state"])

    def test_candidate_invents_architecture(self):
        self.assertIn("UNAPPROVED_ARCHITECTURE_INVENTED", self.finding_codes(lab.review_plan(self.candidate)["findings"]))

    def test_candidate_schedules_blocked_capability(self):
        self.assertIn("BLOCKED_CAPABILITY_SCHEDULED", self.finding_codes(lab.review_plan(self.candidate)["findings"]))

    def test_reference_specification_digest_is_exact(self):
        plan = self.reference["plan"]
        self.assertEqual(lab.stable_digest(self.reference["specification"]), plan["specification"]["digest"])

    def test_changed_specification_breaks_binding(self):
        changed = copy.deepcopy(self.reference["specification"])
        changed["revision"] = "changed"
        findings = lab.validate_plan_provenance(
            self.reference["plan"], changed, self.reference["repository"], self.reference["architecture"]
        )
        self.assertIn("PLAN_SPECIFICATION_BINDING_INVALID", self.finding_codes(findings))

    def test_reference_discovery_is_requirements_guided(self):
        discovery = self.reference["plan"]["discovery"]
        self.assertEqual("requirements_guided", discovery["mode"])
        self.assertTrue(discovery["guided_by_requirement_ids"])

    def test_unbounded_discovery_is_detected(self):
        findings = lab.validate_discovery({"id": "x", "mode": "read_everything", "observations": []}, self.reference["repository"])
        self.assertIn("DISCOVERY_NOT_REQUIREMENTS_GUIDED", self.finding_codes(findings))

    def test_unresolved_discovery_conflict_blocks(self):
        discovery = {"id": "x", "mode": "requirements_guided", "guided_by_requirement_ids": ["R"], "observations": [{"id": "o", "classification": "CONFLICT", "evidence_paths": ["src/underwriting/proposals.py"]}]}
        self.assertIn("REPOSITORY_ARCHITECTURE_CONFLICT_UNRESOLVED", self.finding_codes(lab.validate_discovery(discovery, self.reference["repository"])))

    def test_unrelated_drift_does_not_invalidate_units(self):
        repository = copy.deepcopy(self.reference["repository"])
        repository.update(revision="new", changed_paths_since_plan=["docs/style.md"])
        self.assertEqual("stale_unrelated", lab.assess_plan_staleness(self.reference["plan"], repository)["state"])

    def test_relevant_drift_targets_affected_units(self):
        repository = copy.deepcopy(self.reference["repository"])
        repository.update(revision="new", changed_paths_since_plan=["src/underwriting/proposals.py"])
        result = lab.assess_plan_staleness(self.reference["plan"], repository)
        self.assertEqual("stale_relevant", result["state"])
        self.assertIn("AWU-BR-CONTRACT", result["affected_work_units"])

    def test_all_six_requirements_have_dispositions(self):
        coverage = lab.disposition_metrics(self.reference["plan"], self.reference["specification"])
        self.assertEqual((6, 6), (coverage["requirements_with_disposition"]["numerator"], coverage["requirements_with_disposition"]["denominator"]))

    def test_missing_disposition_is_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["requirement_dispositions"] = plan["requirement_dispositions"][:-1]
        self.assertIn("UNPLANNED_REQUIREMENT", self.finding_codes(lab.validate_requirement_dispositions(plan, self.reference["specification"])))

    def test_already_satisfied_requires_evidence(self):
        plan = copy.deepcopy(self.reference["plan"])
        disposition = next(item for item in plan["requirement_dispositions"] if item["disposition"] == "already_satisfied")
        disposition["evidence_ids"] = []
        self.assertIn("ALREADY_SATISFIED_WITHOUT_EVIDENCE", self.finding_codes(lab.validate_requirement_dispositions(plan, self.reference["specification"])))

    def test_all_requirements_have_complete_trace_chains(self):
        coverage = lab.implementation_traceability(self.reference["plan"], self.reference["specification"])["complete_requirement_chains"]
        self.assertEqual((6, 6), (coverage["numerator"], coverage["denominator"]))

    def test_traceability_uses_semantic_granularity(self):
        trace = lab.implementation_traceability(self.reference["plan"], self.reference["specification"])
        self.assertIn("not_source_lines", trace["trace_granularity"])

    def test_orphan_task_is_detected(self):
        findings = lab.validate_tasks({"tasks": [{"id": "T", "basis": {}}]})
        self.assertIn("ORPHAN_TASK", self.finding_codes(findings))

    def test_new_dependency_requires_architecture_basis(self):
        task = {"id": "T", "introduces_external_dependency": True, "basis": {"requirement_ids": ["R"]}}
        self.assertIn("EXTERNAL_DEPENDENCY_UNAUTHORIZED", self.finding_codes(lab.validate_tasks({"tasks": [task]})))

    def test_work_units_have_accountable_teams_distinct_from_agents(self):
        for unit in self.reference["plan"]["work_units"]:
            self.assertTrue(unit["accountability_team"])
            self.assertEqual("unassigned_until_scheduler", unit["execution_owner"])

    def test_reference_work_units_have_exclusive_write_paths(self):
        units = self.reference["plan"]["work_units"]
        for index, left in enumerate(units):
            for right in units[index + 1:]:
                self.assertFalse(set(left["writable_paths"]) & set(right["writable_paths"]))

    def test_wildcard_write_scope_is_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["work_units"][0]["writable_paths"] = ["**"]
        self.assertIn("WORK_UNIT_WRITE_SCOPE_UNBOUNDED", self.finding_codes(lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])))

    def test_protected_write_is_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["work_units"][0]["writable_paths"] = ["src/underwriting/submission.py"]
        self.assertIn("PROTECTED_PATH_WRITE_ATTEMPT", self.finding_codes(lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])))

    def test_missing_stop_conditions_are_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["work_units"][0]["stop_conditions"] = []
        self.assertIn("WORK_UNIT_STOP_CONDITIONS_INCOMPLETE", self.finding_codes(lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])))

    def test_stop_catalog_routes_all_eight_conditions(self):
        catalog = self.reference["plan"]["stop_condition_catalog"]
        self.assertEqual(8, len(catalog))
        self.assertEqual({"ASK", "PROPOSE", "STOP"}, {item["outcome"] for item in catalog})
        self.assertTrue(all(item["required_artifact"] and item["next_action"] and item["owner"] for item in catalog))

    def test_undefined_stop_action_is_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["work_units"][0]["stop_conditions"].append("unexpected_problem")
        findings = lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])
        self.assertIn("WORK_UNIT_STOP_ACTION_UNDEFINED", self.finding_codes(findings))

    def test_readiness_requires_linked_current_evidence(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["work_units"][0]["readiness_evidence_ids"] = []
        self.assertIn("WORK_UNIT_READINESS_EVIDENCE_MISSING", self.finding_codes(lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])))

    def test_stale_readiness_evidence_blocks(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["readiness_evidence_catalog"][0]["status"] = "stale"
        self.assertIn("WORK_UNIT_READINESS_EVIDENCE_INVALID", self.finding_codes(lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])))

    def test_missing_verification_infrastructure_does_not_hide_dispatch_state(self):
        plan = copy.deepcopy(self.reference["plan"])
        next(item for item in plan["readiness_evidence_catalog"] if item["id"] == "VERIFICATION-INFRA-2219")["status"] = "missing"
        readiness = lab.ready_work_units(plan)
        self.assertEqual(["AWU-BR-CONTRACT"], readiness["ready"])
        self.assertIn("AWU-BR-CONTRACT", readiness["verification_prerequisites_blocked"])

    def test_permission_profiles_are_temporary_requests_not_grants(self):
        for profile in self.reference["plan"]["permission_profiles"]:
            self.assertEqual("planned_not_provisioned", profile["grant_state"])
            self.assertEqual("work_unit_bound_temporary", profile["lifecycle"])
            self.assertFalse(profile["self_provisioning_allowed"])

    def test_self_provisioned_permission_is_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        plan["permission_profiles"][0]["self_provisioning_allowed"] = True
        findings = lab.validate_work_units(plan, self.reference["specification"], self.reference["repository"])
        self.assertIn("EXECUTION_PERMISSION_PROFILE_INVALID", self.finding_codes(findings))

    def test_reference_graph_has_five_waves(self):
        schedule = lab.topological_waves(self.reference["plan"])
        self.assertTrue(schedule["acyclic"])
        self.assertEqual(5, len(schedule["waves"]))

    def test_extraction_and_validation_are_parallel(self):
        waves = lab.topological_waves(self.reference["plan"])["waves"]
        self.assertIn(["AWU-BR-EXTRACTION", "AWU-BR-VALIDATION"], waves)

    def test_cycle_is_detected(self):
        plan = {"work_units": [{"id": "A", "depends_on": ["B"]}, {"id": "B", "depends_on": ["A"]}]}
        self.assertIn("WORK_GRAPH_CYCLE", self.finding_codes(lab.validate_dependency_graph(plan)))

    def test_reference_contract_registry_matches_graph(self):
        self.assertEqual([], lab.validate_contract_dependencies(self.reference["plan"]))

    def test_hidden_contract_dependency_is_detected(self):
        plan = copy.deepcopy(self.reference["plan"])
        next(item for item in plan["work_units"] if item["id"] == "AWU-BR-VALIDATION")["depends_on"] = []
        self.assertIn("UNDECLARED_CONTRACT_DEPENDENCY", self.finding_codes(lab.validate_contract_dependencies(plan)))

    def test_critical_path_uses_coarse_indicators(self):
        result = lab.critical_path(self.reference["plan"])
        self.assertEqual(["AWU-BR-CONTRACT", "AWU-BR-EXTRACTION", "AWU-BR-CONFLICT", "AWU-BR-REVIEW", "AWU-BR-INTEGRATION"], result["path"])
        self.assertIn("not_elapsed_time", result["unit"])

    def test_total_work_and_elapsed_are_separate(self):
        metrics = lab.coordination_metrics(self.reference["plan"])
        self.assertGreater(metrics["total_work_units"], metrics["dependency_aware_elapsed_units"])
        self.assertEqual(5, metrics["wave_count"])

    def test_initial_scheduler_exposes_only_contract_unit(self):
        self.assertEqual(["AWU-BR-CONTRACT"], lab.ready_work_units(self.reference["plan"])["ready"])

    def test_after_contract_two_units_become_ready(self):
        ready = lab.ready_work_units(self.reference["plan"], completed_work_unit_ids=["AWU-BR-CONTRACT"])["ready"]
        self.assertEqual(["AWU-BR-EXTRACTION", "AWU-BR-VALIDATION"], ready)

    def test_execution_context_has_provenance_and_no_credentials(self):
        context = lab.generate_execution_context(self.reference, "AWU-BR-EXTRACTION")
        self.assertTrue(context["plan_digest"].startswith("sha256:"))
        self.assertIn("not grant", context["authority_boundary"])
        self.assertNotIn("credential", context)

    def test_execution_context_preserves_protected_decisions(self):
        context = lab.generate_execution_context(self.reference, "AWU-BR-EXTRACTION")
        self.assertIn("mutation_eligibility", context["protected_decisions"])

    def test_execution_context_contains_routed_stops_and_permission_request(self):
        context = lab.generate_execution_context(self.reference, "AWU-BR-EXTRACTION")
        self.assertEqual(8, len(context["stop_conditions"]))
        self.assertEqual("planned_not_provisioned", context["permission_request"]["grant_state"])
        self.assertEqual("VERIFICATION-INFRA-2219", context["verification_prerequisites"][0]["id"])

    def test_candidate_cannot_generate_execution_context(self):
        with self.assertRaises(ValueError):
            lab.generate_execution_context(self.candidate, "AWU-BR-ALL")

    def test_downstream_impact_is_transitive(self):
        affected = lab.downstream_work_units(self.reference["plan"], "AWU-BR-EXTRACTION")
        self.assertEqual(["AWU-BR-CONFLICT", "AWU-BR-INTEGRATION", "AWU-BR-REVIEW"], affected)

    def test_incomplete_contract_change_is_detected(self):
        self.assertIn("CONTRACT_CHANGE_REQUEST_INCOMPLETE", self.finding_codes(lab.validate_contract_change_request({"id": "C"}, self.reference["plan"])))

    def test_contract_change_requires_full_downstream_impact(self):
        request = {"id": "C", "discovered_by": "AWU-BR-EXTRACTION", "contract": "P", "proposed_change": "x", "reason_requirement_ids": ["REQ-BR-030"], "affected_work_unit_ids": ["AWU-BR-CONFLICT"], "impact": {"tests": "rerun"}}
        self.assertIn("CONTRACT_CHANGE_IMPACT_INCOMPLETE", self.finding_codes(lab.validate_contract_change_request(request, self.reference["plan"])))

    def test_reference_contract_change_has_complete_impact(self):
        request = json.loads((LESSON / "northstar-implementation-plan" / "reference" / "contract-change-request.json").read_text(encoding="utf-8"))
        self.assertEqual([], lab.validate_contract_change_request(request, self.reference["plan"]))

    def test_reference_completion_report_is_clean_and_context_bound(self):
        path = LESSON / "northstar-implementation-plan" / "reference" / "completion-report.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        unit = next(item for item in self.reference["plan"]["work_units"] if item["id"] == report["work_unit_id"])
        context = lab.generate_execution_context(self.reference, report["work_unit_id"])
        self.assertEqual(context["plan_digest"], report["input_context_digest"])
        self.assertEqual([], lab.validate_completion_report(unit, report, actual_changed_paths=report["actual_changed_paths"]))

    def test_reference_plan_separates_readiness_and_deferred_work(self):
        self.assertEqual({"implementation", "merge", "enablement"}, set(self.reference["plan"]["readiness_layers"]))
        self.assertTrue(self.reference["plan"]["future_work"][0]["not_scheduled"])
        self.assertEqual([], lab.validate_plan_assurance(self.reference["plan"]))

    def test_rollout_boundary_forbids_implicit_enablement(self):
        rollout = json.loads((LESSON / "northstar-implementation-plan" / "reference" / "rollout-boundary.json").read_text(encoding="utf-8"))
        self.assertEqual("NOT_AUTHORIZED_FOR_ENABLEMENT", rollout["status"])
        self.assertEqual(2, len(rollout["shadow_requirements"]))
        self.assertIn("do not authorize", rollout["boundary"])

    def test_escalation_artifacts_preserve_proposal_boundary(self):
        artifacts = json.loads((LESSON / "northstar-implementation-plan" / "reference" / "escalation-artifacts.json").read_text(encoding="utf-8"))
        self.assertEqual("ASK", artifacts["clarification_request"]["outcome"])
        self.assertEqual("PROPOSED_NOT_APPROVED", artifacts["architecture_proposal"]["state"])
        self.assertEqual("PROPOSED_NOT_APPROVED", artifacts["dependency_proposal"]["state"])

    def test_completion_detects_path_scope_violation(self):
        unit = self.reference["plan"]["work_units"][0]
        report = {"status": "BLOCKED", "evidence_ids": unit["verification"]["evidence_outputs"]}
        findings = lab.validate_completion_report(unit, report, actual_changed_paths=["policy/authorization.yml"])
        self.assertIn("WORK_UNIT_SCOPE_VIOLATION", self.finding_codes(findings))

    def test_completion_detects_semantic_scope_expansion(self):
        unit = self.reference["plan"]["work_units"][0]
        report = {"status": "BLOCKED", "evidence_ids": unit["verification"]["evidence_outputs"], "semantic_actions": [unit["protected_decisions"][0]]}
        self.assertIn("SEMANTIC_SCOPE_EXPANSION", self.finding_codes(lab.validate_completion_report(unit, report, actual_changed_paths=[])))

    def test_completion_requires_all_evidence(self):
        unit = self.reference["plan"]["work_units"][0]
        self.assertIn("COMPLETION_EVIDENCE_MISSING", self.finding_codes(lab.validate_completion_report(unit, {"status": "COMPLETED", "evidence_ids": []}, actual_changed_paths=[])))

    def test_completed_cannot_hide_unresolved_blockers(self):
        unit = self.reference["plan"]["work_units"][0]
        report = {"status": "COMPLETED", "evidence_ids": unit["verification"]["evidence_outputs"], "unresolved": ["x"]}
        self.assertIn("COMPLETION_WITH_UNRESOLVED_BLOCKERS", self.finding_codes(lab.validate_completion_report(unit, report, actual_changed_paths=[])))

    def test_verification_gate_requires_evidence(self):
        with self.assertRaises(ValueError):
            lab.transition_work_unit_state(lab.WorkUnitState.COMPLETED, lab.WorkUnitState.VERIFIED)

    def test_integration_gate_requires_evidence(self):
        with self.assertRaises(ValueError):
            lab.transition_work_unit_state(lab.WorkUnitState.VERIFIED, lab.WorkUnitState.INTEGRATED)

    def test_happy_lifecycle_reaches_integrated(self):
        state = lab.transition_work_unit_state(lab.WorkUnitState.COMPLETED, lab.WorkUnitState.VERIFIED, verification_passed=True)
        state = lab.transition_work_unit_state(state, lab.WorkUnitState.INTEGRATED, integration_passed=True)
        self.assertEqual(lab.WorkUnitState.INTEGRATED, state)

    def test_labelled_evaluation_is_exact(self):
        result = lab.evaluate_planning_rules()
        self.assertEqual((30, 30, 0, 0), (result["population"], result["true_positive"], result["false_positive"], result["false_negative"]))
        self.assertEqual({"numerator": 30, "denominator": 30}, result["exact_matches"])

    def test_evaluation_claim_is_bounded(self):
        self.assertIn("not_general", lab.evaluate_planning_rules()["claim"])

    def test_notebook_is_valid_json(self):
        notebook = json.loads((LESSON / "implementation_planning.ipynb").read_text(encoding="utf-8"))
        self.assertEqual(4, notebook["nbformat"])

    def test_reference_artifacts_have_no_todos(self):
        for path in (LESSON / "northstar-implementation-plan" / "reference").glob("*.json"):
            self.assertNotIn("TODO", path.read_text(encoding="utf-8"))

    def test_starter_artifacts_have_todos(self):
        starter = LESSON / "northstar-implementation-plan" / "workshop" / "starter"
        self.assertTrue(all("TODO" in path.read_text(encoding="utf-8") for path in starter.glob("*.json")))


if __name__ == "__main__":
    unittest.main()
