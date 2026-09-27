from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "beginner" / "09-specification-quality-review-antipatterns"
LAB_PATH = LESSON / "lab.py"
SPEC = importlib.util.spec_from_file_location("course09_lab", LAB_PATH)
assert SPEC and SPEC.loader
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course09SpecificationReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = lab.load_review_bundle()
        self.repaired = lab.load_review_bundle(repaired=True)

    def test_lexical_presence_baseline_looks_complete_but_is_unsafe(self) -> None:
        result = lab.lexical_presence_baseline(self.bundle["package"])
        self.assertEqual((result["numerator"], result["denominator"]), (7, 7))
        self.assertTrue(result["looks_complete"])
        self.assertIn("must never authorize", result["limitations"][1])

    def test_candidate_review_has_typed_findings_without_score(self) -> None:
        report = lab.review_bundle(self.bundle)
        self.assertEqual(report["finding_counts"], {"blocking": 16, "review": 24, "informational": 0})
        self.assertEqual(len(report["findings"]), 40)

    def test_candidate_blocking_codes_cover_authority_autonomy_and_evidence(self) -> None:
        codes = {item["code"] for item in lab.review_bundle(self.bundle)["findings"] if item["severity"] == "blocking"}
        for code in ("UNDEFINED_CONFIDENCE_SEMANTICS", "AUTHORITY_LAUNDERING", "AGENT_TASK_UNDER_CONSTRAINED", "EVIDENCE_STALE", "GENERATED_ARTIFACT_MODIFIED"):
            self.assertIn(code, codes)

    def test_candidate_readiness_stops_affected_work(self) -> None:
        decision = lab.readiness_decision(lab.review_bundle(self.bundle))
        self.assertEqual(decision["decision"], "stop")
        self.assertFalse(decision["ready"])
        self.assertIsNone(decision["score"])
        self.assertTrue(decision["blocking_finding_ids"])

    def test_repaired_package_is_review_clean(self) -> None:
        report = lab.review_bundle(self.repaired)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["finding_counts"], {"blocking": 0, "review": 0, "informational": 0})

    def test_repaired_package_is_ready_only_for_bounded_implementation(self) -> None:
        decision = lab.readiness_decision(lab.review_bundle(self.repaired))
        self.assertEqual(decision["decision"], "ready_for_bounded_implementation")
        self.assertTrue(decision["ready"])
        self.assertIsNone(decision["score"])

    def test_traceability_separates_link_presence_from_validity(self) -> None:
        metrics = lab.review_bundle(self.bundle)["traceability"]
        self.assertEqual((metrics["structural_link_coverage"]["numerator"], metrics["structural_link_coverage"]["denominator"]), (10, 10))
        self.assertEqual((metrics["semantic_link_validity"]["numerator"], metrics["semantic_link_validity"]["denominator"]), (1, 10))

    def test_repaired_traceability_is_structurally_and_semantically_complete(self) -> None:
        metrics = lab.review_bundle(self.repaired)["traceability"]
        self.assertEqual(metrics["structural_link_coverage"]["value"], 1.0)
        self.assertEqual(metrics["semantic_link_validity"]["value"], 1.0)

    def test_vague_requirement_is_detected(self) -> None:
        statement = {"id":"S","text":"The system SHALL be robust.","owner":"Product","defined_terms":[],"measurement":None,"source_refs":[],"technology_names":[]}
        self.assertIn("VAGUE_REQUIREMENT", {item.code for item in lab.review_statement(statement)})

    def test_defined_measured_term_is_not_treated_as_vague(self) -> None:
        statement = {"id":"S","text":"The system SHALL be robust.","owner":"Product","defined_terms":["robust"],"measurement":{"method":"failure suite"},"source_refs":[],"technology_names":[]}
        self.assertNotIn("VAGUE_REQUIREMENT", {item.code for item in lab.review_statement(statement)})

    def test_false_precision_requires_measurement_semantics(self) -> None:
        statement = {"id":"S","text":"P95 SHALL be below 1.7 seconds.","owner":"Product","measurement":None,"decision":{"owner":"Product"},"source_refs":[],"technology_names":[]}
        self.assertIn("FALSE_PRECISION", {item.code for item in lab.review_statement(statement)})

    def test_consequential_number_without_owner_is_blocking(self) -> None:
        statement = {"id":"S","text":"Auto-apply above 90%.","owner":"Risk","measurement":{"method":"x"},"decision":{},"source_refs":[],"technology_names":[],"controls_authoritative_action":True,"confidence_contract":{"population":"p","calibration":"c","metric_definition":"m","owner":"o","decision_id":"d"}}
        finding = next(item for item in lab.review_statement(statement) if item.code == "DECISION_AUTHORITY_MISSING")
        self.assertEqual(finding.severity, lab.Severity.BLOCKING)

    def test_confidence_theater_is_detected(self) -> None:
        statement = self.bundle["package"]["statements"][2]
        self.assertIn("UNDEFINED_CONFIDENCE_SEMANTICS", {item.code for item in lab.review_statement(statement)})

    def test_unjustified_technology_is_implementation_leakage(self) -> None:
        statement = self.bundle["package"]["statements"][0]
        self.assertIn("IMPLEMENTATION_LEAKAGE", {item.code for item in lab.review_statement(statement)})

    def test_inherited_technology_constraint_is_preserved(self) -> None:
        statement = self.repaired["package"]["statements"][3]
        self.assertNotIn("IMPLEMENTATION_LEAKAGE", {item.code for item in lab.review_statement(statement)})

    def test_informal_cache_choice_is_accidental_architecture(self) -> None:
        statement = self.bundle["package"]["statements"][3]
        self.assertIn("ACCIDENTAL_ARCHITECTURE", {item.code for item in lab.review_statement(statement)})

    def test_single_accuracy_metric_requires_components_and_slices(self) -> None:
        codes = {item.code for item in lab.review_statement(self.bundle["package"]["statements"][1])}
        self.assertIn("AGGREGATE_ACCURACY_UNDEFINED", codes)
        self.assertIn("CRITICAL_EVALUATION_SLICES_MISSING", codes)

    def test_blanket_policy_compliance_is_not_effective_context(self) -> None:
        statement = self.bundle["package"]["statements"][7]
        self.assertIn("POLICY_APPLICABILITY_UNRESOLVED", {item.code for item in lab.review_statement(statement)})

    def test_hearsay_does_not_grant_authority(self) -> None:
        statement = self.bundle["package"]["statements"][9]
        self.assertIn("AUTHORITY_LAUNDERING", {item.code for item in lab.review_statement(statement)})

    def test_project_cannot_launder_policy_exception(self) -> None:
        statement = self.bundle["package"]["statements"][9]
        self.assertIn("EXCEPTION_LAUNDERING", {item.code for item in lab.review_statement(statement)})

    def test_unbounded_population_is_detected(self) -> None:
        statement = self.bundle["package"]["statements"][4]
        self.assertIn("POPULATION_UNBOUNDED", {item.code for item in lab.review_statement(statement)})

    def test_undefined_test_request_is_not_an_evidence_contract(self) -> None:
        statement = self.bundle["package"]["statements"][8]
        self.assertIn("EVIDENCE_CONTRACT_UNDEFINED", {item.code for item in lab.review_statement(statement)})

    def test_happy_path_only_is_blocking_for_authoritative_side_effects(self) -> None:
        findings = lab.review_package_structure(self.bundle["package"])
        finding = next(item for item in findings if item.code == "SCENARIO_COVERAGE_INCOMPLETE")
        self.assertEqual(finding.severity, lab.Severity.BLOCKING)
        self.assertIn("failure", finding.message)

    def test_missing_policy_sources_block_review(self) -> None:
        codes = {item.code for item in lab.review_package_structure(self.bundle["package"])}
        self.assertIn("REQUIRED_POLICY_SOURCES_MISSING", codes)
        self.assertIn("POLICY_PROVENANCE_INCOMPLETE", codes)

    def test_temporary_exception_needs_expiry_authority_and_scope(self) -> None:
        codes = {item.code for item in lab.review_package_structure(self.bundle["package"])}
        self.assertTrue({"EXCEPTION_EXPIRY_MISSING", "EXCEPTION_APPROVER_UNAUTHORIZED", "EXCEPTION_SCOPE_INCOMPLETE"} <= codes)

    def test_giant_specification_is_detected(self) -> None:
        self.assertIn("GIANT_SPECIFICATION", {item.code for item in lab.review_package_structure(self.bundle["package"])})

    def test_over_fragmentation_is_detected_without_forcing_one_file_per_concept(self) -> None:
        package = copy.deepcopy(self.repaired["package"])
        package["artifacts"] = [{"path":f"REQ-{i}.md","lines":8,"concerns":["requirement"]} for i in range(51)]
        package["average_requirements_per_artifact"] = 1
        self.assertIn("OVER_FRAGMENTED_SPECIFICATION", {item.code for item in lab.review_package_structure(package)})

    def test_possible_duplicates_are_not_automatically_merged(self) -> None:
        finding = next(item for item in lab.review_package_structure(self.bundle["package"]) if item.code == "POSSIBLE_REQUIREMENT_DUPLICATION")
        self.assertIn("automatic merging would be unsafe", finding.message)

    def test_tests_and_code_are_not_the_sole_specification(self) -> None:
        codes = {item.code for item in lab.review_package_structure(self.bundle["package"])}
        self.assertIn("TESTS_AS_SPECIFICATION", codes)
        self.assertIn("CODE_AS_SPECIFICATION", codes)

    def test_requirement_ownership_is_reviewed_as_a_set(self) -> None:
        findings = [item for item in lab.review_package_structure(self.bundle["package"]) if item.code == "REQUIREMENT_OWNERSHIP_INCOMPLETE"]
        self.assertEqual(len(findings), 1)
        self.assertIn("REQ-2290-001", findings[0].evidence)

    def test_under_constrained_agent_task_is_blocked(self) -> None:
        codes = {item.code for item in lab.review_autonomy(self.bundle["autonomy"])}
        self.assertIn("AGENT_TASK_UNDER_CONSTRAINED", codes)
        self.assertIn("AGENT_STOP_CONDITIONS_MISSING", codes)
        self.assertIn("DEPLOYMENT_AUTHORITY_DELEGATED", codes)

    def test_over_constrained_agent_task_is_reviewed(self) -> None:
        contract = copy.deepcopy(self.repaired["autonomy"])
        contract["exact_line_edits"] = [42]
        self.assertIn("AGENT_TASK_OVER_CONSTRAINED", {item.code for item in lab.review_autonomy(contract)})

    def test_bounded_autonomy_contract_is_clean(self) -> None:
        self.assertEqual(lab.review_autonomy(self.repaired["autonomy"]), ())

    def test_evidence_pass_label_requires_context(self) -> None:
        codes = {item.code for item in lab.review_evidence(self.bundle["evidence"])}
        self.assertIn("EVIDENCE_CONTEXT_INCOMPLETE", codes)
        self.assertIn("EVIDENCE_STALE", codes)

    def test_generated_context_edit_is_blocking(self) -> None:
        finding = next(item for item in lab.review_context(self.bundle["context"]) if item.code == "GENERATED_ARTIFACT_MODIFIED")
        self.assertEqual(finding.severity, lab.Severity.BLOCKING)

    def test_context_provenance_overload_and_starvation_are_separate(self) -> None:
        codes = {item.code for item in lab.review_context(self.bundle["context"])}
        self.assertTrue({"CONTEXT_PROVENANCE_MISSING", "CONTEXT_OVERLOAD", "CONTEXT_REQUIRED_SOURCE_MISSING"} <= codes)

    def evaluation_case(self, identifier: str) -> dict:
        cases = lab.load_json(lab.EVALUATION_PATH)["cases"]
        return next(item["input"] for item in cases if item["id"] == identifier)

    def test_authority_conflict_is_not_resolved_by_specificity_recency_or_proximity(self) -> None:
        codes = {item.code for item in lab.review_normative_context(self.evaluation_case("EV-12-authority-resolution-heuristics"))}
        self.assertTrue({"NORMATIVE_CONFLICT", "SPECIFICITY_MISTAKEN_FOR_AUTHORITY", "RECENCY_MISTAKEN_FOR_AUTHORITY", "PROXIMITY_MISTAKEN_FOR_AUTHORITY"} <= codes)

    def test_agent_instructions_cannot_become_shadow_governance(self) -> None:
        codes = {item.code for item in lab.review_normative_context(self.evaluation_case("EV-13-shadow-governance"))}
        self.assertEqual(codes, {"AGENT_INSTRUCTION_EXCEEDS_AUTHORITY"})

    def test_self_confirming_agent_loop_preserves_authority_and_independence_findings(self) -> None:
        codes = {item.code for item in lab.review_normative_context(self.evaluation_case("EV-14-self-confirming-loop"))}
        self.assertEqual(codes, {"DERIVED_REQUIREMENT_UNAPPROVED", "SELF_CONFIRMING_SPECIFICATION_LOOP", "EVIDENCE_INDEPENDENCE_WEAK"})

    def test_uncertainty_and_open_questions_are_scoped(self) -> None:
        codes = {item.code for item in lab.review_normative_context(self.evaluation_case("EV-15-uncertainty-scope"))}
        self.assertEqual(codes, {"UNCERTAINTY_LAUNDERED", "OPEN_QUESTION_CONSEQUENCE_UNDEFINED", "OPEN_QUESTION_OVER_BLOCKS"})

    def test_requirement_granularity_and_behavioral_organization(self) -> None:
        codes = {item.code for item in lab.review_requirement_model(self.evaluation_case("EV-16-requirement-granularity"))}
        self.assertEqual(codes, {"REQUIREMENT_EXPLOSION", "COMPOUND_REQUIREMENT", "REQUIREMENTS_ORGANIZED_BY_IMPLEMENTATION"})

    def test_api_database_and_prompt_do_not_replace_behavior(self) -> None:
        codes = {item.code for item in lab.review_requirement_model(self.evaluation_case("EV-17-implementation-restatements"))}
        self.assertEqual(codes, {"API_RESTATEMENT_AS_REQUIREMENT", "DATABASE_RESTATEMENT_AS_REQUIREMENT", "PROMPT_RESTATEMENT_AS_REQUIREMENT"})

    def test_prompt_only_control_and_magic_human_review_are_blocked(self) -> None:
        findings = lab.review_requirement_model(self.evaluation_case("EV-18-control-and-human-review"))
        blocking = {item.code for item in findings if item.severity == lab.Severity.BLOCKING}
        self.assertEqual(blocking, {"CONTROL_UNDERENFORCED", "ENFORCEMENT_MAPPING_MISSING", "HUMAN_REVIEW_CONTROL_INCOMPLETE"})

    def test_approval_is_bound_to_exact_content_and_single_use(self) -> None:
        codes = {item.code for item in lab.review_execution_safety(self.evaluation_case("EV-19-approval-integrity"))}
        self.assertEqual(codes, {"APPROVAL_NOT_CONTENT_BOUND", "APPROVAL_REUSE_PERMITTED"})

    def test_unknown_side_effect_outcome_requires_idempotent_bounded_retry(self) -> None:
        codes = {item.code for item in lab.review_execution_safety(self.evaluation_case("EV-20-side-effect-retry"))}
        self.assertEqual(codes, {"SIDE_EFFECT_IDEMPOTENCY_UNDEFINED", "UNKNOWN_OUTCOME_COLLAPSED", "RETRY_BUDGET_UNDEFINED", "RETRY_BUDGET_PROVENANCE_MISSING"})

    def test_nfrs_preserve_safety_workload_and_measurement_boundaries(self) -> None:
        codes = {item.code for item in lab.review_execution_safety(self.evaluation_case("EV-21-optimization-and-nfr"))}
        self.assertEqual(codes, {"COST_OPTIMIZATION_PRECEDES_CORRECTNESS", "SAFETY_INVARIANT_TRADED_FOR_PERFORMANCE", "NFR_WORKLOAD_UNDEFINED", "NFR_MEASUREMENT_BOUNDARY_UNDEFINED"})

    def test_degradation_cannot_inflate_success_or_increase_autonomy(self) -> None:
        codes = {item.code for item in lab.review_execution_safety(self.evaluation_case("EV-22-semantic-availability-degradation"))}
        self.assertEqual(codes, {"SEMANTIC_GOOD_EVENT_UNDEFINED", "DEGRADED_SUCCESS_UNDEFINED", "DEGRADATION_WEAKENS_CONTROL"})

    def test_evaluation_population_and_dashboard_states_are_not_laundered(self) -> None:
        population_codes = {item.code for item in lab.review_evaluation_and_gate(self.evaluation_case("EV-23-evaluation-claim-boundary"))}
        dashboard_codes = {item.code for item in lab.review_evaluation_and_gate(self.evaluation_case("EV-24-dashboard-state-laundering"))}
        self.assertIn("EVALUATION_DEPLOYMENT_POPULATION_MISMATCH", population_codes)
        self.assertEqual(dashboard_codes, {"UNRESOLVED_GATE_REPORTED_READY", "MISSING_EVIDENCE_INTERPRETED_AS_PASS", "UNKNOWN_MISCLASSIFIED_NOT_APPLICABLE"})

    def test_lifecycle_history_is_retained_but_not_presented_as_current(self) -> None:
        codes = {item.code for item in lab.review_lifecycle(self.evaluation_case("EV-25-lifecycle-history"))}
        self.assertEqual(codes, {"REQUIREMENT_STATUS_IGNORED", "SUPERSEDED_HISTORY_DELETED", "HISTORICAL_ARTIFACT_PRESENTED_AS_CURRENT"})

    def test_adr_conflict_and_reconsideration_remain_distinct(self) -> None:
        codes = {item.code for item in lab.review_lifecycle(self.evaluation_case("EV-26-design-conflict-and-adr-freshness"))}
        self.assertEqual(codes, {"DESIGN_CONTRADICTS_REQUIREMENT", "ADR_RECONSIDERATION_UNDEFINED"})

    def test_repository_reconciliation_localizes_trust_boundary_violation(self) -> None:
        codes = {item.code for item in lab.review_brownfield_delivery(self.evaluation_case("EV-28-repository-reconciliation"))}
        self.assertEqual(codes, {"REPOSITORY_DISCOVERY_INCOMPLETE", "IMPLEMENTATION_VIOLATES_TRUST_BOUNDARY", "REPOSITORY_PATTERN_WORSHIP"})

    def test_desired_state_does_not_replace_transition_and_rollback(self) -> None:
        codes = {item.code for item in lab.review_brownfield_delivery(self.evaluation_case("EV-29-migration-gap"))}
        self.assertEqual(codes, {"MIGRATION_BEHAVIOR_UNDEFINED", "BIG_BANG_ROLLOUT_ASSUMPTION", "ROLLBACK_SEMANTICS_UNDEFINED"})

    def test_flags_kill_switches_and_fallback_require_operational_evidence(self) -> None:
        rollout = {item.code for item in lab.review_brownfield_delivery(self.evaluation_case("EV-31-rollout-controls"))}
        fallback = {item.code for item in lab.review_brownfield_delivery(self.evaluation_case("EV-32-fallback-and-sensitive-telemetry"))}
        self.assertIn("KILL_SWITCH_UNVERIFIED", rollout)
        self.assertTrue({"FALLBACK_CAPACITY_UNVERIFIED", "FALLBACK_WORK_NOT_PRESERVED", "SENSITIVE_TELEMETRY_EXPOSURE"} <= fallback)

    def test_observability_ids_and_metrics_retain_outcome_context(self) -> None:
        codes = {item.code for item in lab.review_brownfield_delivery(self.evaluation_case("EV-33-correlation-and-outcome-metrics"))}
        self.assertTrue({"CORRELATION_IDENTITY_UNDEFINED", "CORRELATION_SCOPE_INVALID", "COST_OUTCOME_DENOMINATOR_MISSING", "LATENCY_OUTCOME_CONTEXT_MISSING"} <= codes)

    def test_readiness_is_bounded_by_capability(self) -> None:
        result = lab.agent_readiness_by_capability(lab.load_json(lab.CAPABILITY_READINESS_PATH))
        self.assertEqual(result["counts"], {"blocked": 1, "ready_for_bounded_implementation": 4})
        automatic = next(item for item in result["capabilities"] if item["capability"] == "automatic_mutation")
        self.assertEqual(automatic["decision"], "blocked")
        self.assertIn("authorization_contract_unresolved", automatic["blockers"])
        self.assertTrue(all(item["claim"] == "implementation_readiness_only_not_production_release" for item in result["capabilities"]))

    def test_missing_trace_target_is_reported(self) -> None:
        trace = copy.deepcopy(self.repaired["traceability"])
        trace["links"].append({"requirement_id":"REQ-MISSING","evidence_id":"E-MISSING"})
        _, findings = lab.traceability_metrics(self.repaired["package"], trace, self.repaired["evidence"])
        self.assertIn("TRACE_LINK_TARGET_MISSING", {item.code for item in findings})

    def test_labelled_evaluation_reports_denominators_and_limit(self) -> None:
        result = lab.evaluate_review_rules()
        self.assertEqual(result["population"], 35)
        self.assertEqual(result["true_positive"], 78)
        self.assertEqual(result["exact_case_matches"], {"numerator": 35, "denominator": 35})
        self.assertEqual((result["false_positive"], result["false_negative"]), (0, 0))
        self.assertIn("not_general", result["claim"])

    def test_bundle_digest_is_stable_and_content_sensitive(self) -> None:
        first = lab.stable_bundle_digest(self.bundle)
        second = lab.stable_bundle_digest(copy.deepcopy(self.bundle))
        changed = copy.deepcopy(self.bundle)
        changed["package"]["revision"] = "changed"
        self.assertEqual(first, second)
        self.assertNotEqual(first, lab.stable_bundle_digest(changed))

    def test_reference_review_report_matches_executable_summary(self) -> None:
        expected = lab.load_json(lab.REFERENCE_ROOT / "review-report.json")
        actual = lab.review_bundle(self.bundle)
        self.assertEqual(actual["finding_counts"], expected["finding_counts"])
        blocking_codes = {item["code"] for item in actual["findings"] if item["severity"] == "blocking"}
        self.assertEqual(blocking_codes, set(expected["required_blocking_codes"]))

    def test_reference_package_contains_no_todos(self) -> None:
        files = [path for path in lab.REFERENCE_ROOT.rglob("*") if path.is_file()]
        self.assertTrue(files)
        self.assertTrue(all("TODO" not in path.read_text(encoding="utf-8") for path in files))

    def test_starter_package_remains_editable(self) -> None:
        starter = lab.SCENARIO_ROOT / "workshop" / "starter"
        self.assertTrue(any("TODO" in path.read_text(encoding="utf-8") for path in starter.rglob("*") if path.is_file()))

    def test_demo_preserves_claim_boundaries(self) -> None:
        report = lab.run_demo()
        self.assertEqual(report["fixture_status"], "synthetic_specification_review_training_fixture")
        self.assertEqual(report["candidate_readiness"]["decision"], "stop")
        self.assertEqual(report["repaired_readiness"]["decision"], "ready_for_bounded_implementation")
        self.assertIsNone(report["candidate_readiness"]["score"])


if __name__ == "__main__":
    unittest.main()
