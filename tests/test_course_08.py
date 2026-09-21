from __future__ import annotations

import copy
import csv
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "beginner" / "08-non-functional-requirements-agentic-systems"
LAB_PATH = LESSON / "lab.py"
SPEC = importlib.util.spec_from_file_location("course08_lab", LAB_PATH)
assert SPEC and SPEC.loader
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course08NFRTests(unittest.TestCase):
    def test_reference_contract_is_structurally_clean(self) -> None:
        self.assertEqual(lab.validate_nfr_contract(), ())

    def test_reference_workloads_are_structurally_clean(self) -> None:
        self.assertEqual(lab.validate_workload_profiles(), ())

    def test_reference_measurement_plan_covers_every_nfr(self) -> None:
        self.assertEqual(lab.validate_measurement_plan(), ())

    def test_contract_has_eleven_atomic_quality_requirements(self) -> None:
        requirements = lab.load_contract()["requirements"]
        self.assertEqual(len(requirements), 11)
        self.assertEqual(len({item["characteristic"] for item in requirements}), 11)

    def test_unresolved_targets_do_not_smuggle_values(self) -> None:
        unresolved = [item for item in lab.load_contract()["requirements"] if item["target"]["status"] == "target_unresolved"]
        self.assertEqual({item["id"] for item in unresolved}, {"COST-BR-001", "AIQ-BR-001"})
        self.assertTrue(all(item["target"]["value"] is None for item in unresolved))
        self.assertTrue(all(item["target"]["decision_id"] is None for item in unresolved))

    def test_unresolved_target_with_number_is_rejected(self) -> None:
        contract = copy.deepcopy(lab.load_contract())
        target = next(item["target"] for item in contract["requirements"] if item["id"] == "COST-BR-001")
        target["value"] = 0.01
        codes = {item.code for item in lab.validate_nfr_contract(contract)}
        self.assertIn("NFR_UNRESOLVED_TARGET_HAS_VALUE", codes)

    def test_approved_target_without_owner_decision_is_rejected(self) -> None:
        contract = copy.deepcopy(lab.load_contract())
        target = contract["requirements"][0]["target"]
        target["decision_id"] = "TD-MISSING"
        codes = {item.code for item in lab.validate_nfr_contract(contract)}
        self.assertIn("NFR_TARGET_AUTHORITY_MISSING", codes)

    def test_target_decision_must_match_contract_value(self) -> None:
        decisions = copy.deepcopy(lab.load_target_decisions())
        decisions["decisions"][0]["value"] = 42
        codes = {item.code for item in lab.validate_nfr_contract(decisions=decisions)}
        self.assertIn("NFR_TARGET_DECISION_MISMATCH", codes)

    def test_vague_adjective_is_not_a_complete_nfr(self) -> None:
        contract = copy.deepcopy(lab.load_contract())
        contract["requirements"][0]["statement"] = "fast"
        codes = {item.code for item in lab.validate_nfr_contract(contract)}
        self.assertIn("NFR_VAGUE", codes)

    def test_workload_mix_must_sum_to_one(self) -> None:
        workloads = copy.deepcopy(lab.load_workloads())
        workloads["profiles"][0]["response_mix"]["simple"] = 0.9
        codes = {item.code for item in lab.validate_workload_profiles(workloads)}
        self.assertIn("WORKLOAD_MIX_INVALID", codes)

    def test_w2_and_w3_remain_planning_hypotheses(self) -> None:
        profiles = {item["id"]: item for item in lab.load_workloads()["profiles"]}
        self.assertEqual(profiles["W2"]["status"], "target_unresolved")
        self.assertEqual(profiles["W3"]["status"], "target_unresolved")

    def test_nearest_rank_reports_tail_observation(self) -> None:
        self.assertEqual(lab.nearest_rank([1, 2, 3, 100], 95), 100)

    def test_nearest_rank_rejects_invalid_percentile(self) -> None:
        with self.assertRaises(ValueError):
            lab.nearest_rank([1], 0)

    def test_runtime_latency_has_boundary_percentiles_and_denominator(self) -> None:
        latency = lab.runtime_measurements()["end_to_end_latency_ms"]
        self.assertEqual((latency["p50"], latency["p95"], latency["p99"]), (1850.0, 4800.0, 4800.0))
        self.assertEqual(latency["denominator"], 12)
        self.assertEqual(latency["boundary"], "accepted_request_to_completed_proposal_response")
        self.assertIn("not_statistically_representative", latency["representativeness"])

    def test_semantic_good_events_include_only_approved_degradation(self) -> None:
        metric = lab.runtime_measurements()["semantic_service_success_ratio"]
        self.assertEqual((metric["numerator"], metric["denominator"]), (11, 12))
        self.assertNotIn("error", metric["semantic_success_definition"])
        self.assertTrue(metric["excludes_control_compliance"])

    def test_http_like_error_outcome_reduces_good_event_ratio(self) -> None:
        events = copy.deepcopy(lab.load_runtime_events())
        events[0]["outcome"] = "error"
        metric = lab.runtime_measurements(events)["semantic_service_success_ratio"]
        self.assertEqual((metric["numerator"], metric["denominator"]), (10, 12))

    def test_semantic_success_does_not_hide_control_violation(self) -> None:
        events = copy.deepcopy(lab.load_runtime_events())
        events[0]["authoritative_mutations"] = 2
        result = lab.runtime_measurements(events)
        self.assertEqual(result["semantic_service_success_ratio"]["numerator"], 11)
        self.assertEqual(result["compliant_workflow_success_ratio"]["numerator"], 10)
        self.assertEqual(result["control_violating_semantic_successes"]["value"], 1)
        release = lab.release_assessment(runtime=result)
        self.assertIn("CONTROL_VIOLATING_SEMANTIC_SUCCESS", release["blockers"])

    def test_privacy_gate_retains_numerator_and_denominator(self) -> None:
        gate = {item.requirement_id: item for item in lab.target_gates()}["PRIV-NFR-001"]
        self.assertEqual((gate.numerator, gate.denominator), (0, 12))

    def test_cost_per_compliant_success_exposes_failed_work(self) -> None:
        cost = lab.runtime_measurements()["cost_usd"]
        self.assertGreater(cost["per_successful_compliant_workflow"], cost["per_request"])
        self.assertEqual(cost["successful_compliant_denominator"], 11)
        self.assertEqual(cost["included_components"], ["model_inference", "declared_tool_api_calls"])
        self.assertIn("human_review", cost["excluded_components"])

    def test_runtime_output_is_visibly_synthetic(self) -> None:
        self.assertEqual(lab.runtime_measurements()["evidence_status"], "synthetic_training_fixture_not_production_evidence")

    def test_trace_completeness_requires_correlation_fields(self) -> None:
        event = copy.deepcopy(lab.load_runtime_events()[0])
        event["run_id"] = ""
        codes = {item.code for item in lab.telemetry_event_findings(event)}
        self.assertIn("TELEMETRY_REQUIRED_FIELD_MISSING", codes)

    def test_raw_content_and_secrets_are_rejected_from_telemetry(self) -> None:
        event = copy.deepcopy(lab.load_runtime_events()[0])
        event["raw_broker_content_logged"] = True
        event["secret_logged"] = True
        codes = {item.code for item in lab.telemetry_event_findings(event)}
        self.assertEqual(codes, {"TELEMETRY_RAW_CONTENT_EXPOSED", "TELEMETRY_SECRET_EXPOSED"})

    def test_agent_budget_enforces_only_governed_limits(self) -> None:
        event = copy.deepcopy(lab.load_runtime_events()[0])
        event["tool_calls"] = 700
        event["authoritative_mutations"] = 2
        findings = lab.agent_budget_findings(event)
        self.assertEqual([item.code for item in findings], ["AGENT_BUDGET_EXCEEDED"])
        self.assertIn("authoritative_mutations", findings[0].message)

    def test_unresolved_agent_budgets_block_bounded_production_autonomy(self) -> None:
        findings = lab.validate_agent_budget()
        unresolved = [item.subject_id for item in findings if item.code == "AGENT_BUDGET_TARGET_UNRESOLVED"]
        self.assertEqual(set(unresolved), {"tool_calls", "model_turns", "wall_clock_ms", "input_tokens", "output_tokens", "external_broker_messages"})
        self.assertTrue(all(item.severity == lab.Severity.REVIEW for item in findings))

    def test_governed_agent_budgets_trace_to_owner_decisions(self) -> None:
        findings = lab.validate_agent_budget()
        self.assertNotIn("AGENT_BUDGET_DECISION_MISMATCH", {item.code for item in findings})

    def test_reference_events_conform_to_agent_budget(self) -> None:
        self.assertTrue(all(not lab.agent_budget_findings(event) for event in lab.load_runtime_events()))

    def test_unbounded_retry_baseline_amplifies_outage(self) -> None:
        result = lab.simulate_provider_outage(retry_budget=None, circuit_breaker_threshold=None)
        self.assertEqual(result["provider_attempts"], 600)
        self.assertEqual(result["amplification_factor"], 6.0)

    def test_bounded_retry_opens_circuit_and_preserves_work(self) -> None:
        result = lab.simulate_provider_outage(retry_budget=3, circuit_breaker_threshold=8)
        self.assertEqual(result["provider_attempts"], 8)
        self.assertEqual(result["circuit_state"], "open")
        self.assertEqual(result["manual_routes"], 100)
        self.assertEqual(result["work_items_preserved"], 100)

    def test_invalid_retry_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            lab.simulate_provider_outage(retry_budget=0, circuit_breaker_threshold=8)

    def test_safety_critical_degradation_reduces_autonomy(self) -> None:
        for dependency in ("authorization", "policy_service", "model_provider", "retrieval"):
            self.assertFalse(lab.degradation_decision(dependency)["automatic_mutation"])

    def test_every_degradation_mode_has_exit_criteria(self) -> None:
        for dependency in ("authorization", "model_provider", "policy_service", "retrieval", "analytics_export"):
            recovery = lab.degradation_decision(dependency)["recovery_condition"]
            self.assertTrue(recovery["predicate"])
            self.assertTrue(recovery["anti_flap"])
            self.assertTrue(recovery["preserved_work_re_evaluation"])

    def test_noncritical_analytics_may_buffer(self) -> None:
        result = lab.degradation_decision("analytics_export")
        self.assertEqual(result["mode"], "NORMAL_WITH_BUFFERED_ANALYTICS")
        self.assertTrue(result["preserve_work_item"])
        self.assertIn("all independent authorization", result["continuation_condition"])

    def test_unknown_dependency_fails_closed(self) -> None:
        result = lab.degradation_decision("mystery_service")
        self.assertEqual(result["mode"], "UNAVAILABLE")
        self.assertFalse(result["automatic_mutation"])

    def test_quality_fixture_is_pipeline_exercise_not_model_claim(self) -> None:
        result = lab.quality_measurements()
        self.assertEqual(result["evaluation_mode"], "fixed_prediction_pipeline_exercise")
        self.assertEqual(result["claim"], "pipeline_mechanics_only_not_model_quality")
        self.assertEqual((result["overall"]["numerator"], result["overall"]["denominator"]), (7, 8))

    def test_quality_slices_reveal_unsupported_field_gap(self) -> None:
        slices = lab.quality_measurements()["slices"]
        self.assertEqual((slices["unsupported_field"]["numerator"], slices["unsupported_field"]["denominator"]), (1, 2))

    def test_approved_fixture_targets_pass_but_do_not_authorize_release(self) -> None:
        gates = {item.requirement_id: item for item in lab.target_gates()}
        for requirement_id in ("PERF-BR-001", "REL-BR-001", "RES-BR-001", "AGENT-NFR-001", "OBS-BR-001", "SEC-NFR-001", "SEC-NFR-002", "PRIV-NFR-001"):
            self.assertEqual(gates[requirement_id].decision, lab.GateDecision.PASS)

    def test_unresolved_targets_remain_blocked_even_when_measured(self) -> None:
        gates = {item.requirement_id: item for item in lab.target_gates()}
        self.assertEqual(gates["COST-BR-001"].decision, lab.GateDecision.BLOCKED)
        self.assertIsNotNone(gates["COST-BR-001"].observed)
        self.assertEqual(gates["AIQ-BR-001"].decision, lab.GateDecision.BLOCKED)
        self.assertIsNotNone(gates["AIQ-BR-001"].observed)

    def test_capacity_is_not_inferred_from_static_events(self) -> None:
        gate = {item.requirement_id: item for item in lab.target_gates()}["CAP-BR-001"]
        self.assertEqual(gate.decision, lab.GateDecision.NOT_MEASURED)
        self.assertEqual(gate.reason_codes, ("CAPACITY_LOAD_EVIDENCE_ABSENT",))

    def test_capacity_requires_throughput_and_quality_constraints(self) -> None:
        constraint_ids = next(
            item["measurement"]["required_constraint_results"]
            for item in lab.load_contract()["requirements"]
            if item["id"] == "CAP-BR-001"
        )
        evidence = {"source_status": "representative_load_test", "sustained_requests_per_minute": 120, "constraint_results": {item: "pass" for item in constraint_ids}}
        gate = {item.requirement_id: item for item in lab.target_gates(capacity_evidence=evidence)}["CAP-BR-001"]
        self.assertEqual(gate.decision, lab.GateDecision.PASS)

        evidence["constraint_results"]["PERF-BR-001"] = "fail"
        gate = {item.requirement_id: item for item in lab.target_gates(capacity_evidence=evidence)}["CAP-BR-001"]
        self.assertEqual(gate.decision, lab.GateDecision.FAIL)
        self.assertEqual(gate.reason_codes, ("CAPACITY_QUALITY_CONSTRAINT_FAILED",))

    def test_release_remains_blocked_after_eight_fixture_passes(self) -> None:
        release = lab.release_assessment()
        self.assertEqual(release["decision"], "blocked_for_production")
        self.assertFalse(release["production_ready"])
        self.assertEqual(release["gate_counts"], {"pass": 8, "fail": 0, "blocked": 2, "not_measured": 1})
        self.assertIn("SYNTHETIC_FIXTURE_NOT_PRODUCTION_EVIDENCE", release["blockers"])
        self.assertIn("AGENT_BUDGET_TARGETS_UNRESOLVED", release["blockers"])

    def test_traceability_links_every_nfr_without_claiming_execution(self) -> None:
        with (lab.REFERENCE_ROOT / "traceability.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row["nfr_id"] for row in rows}, {item["id"] for item in lab.load_contract()["requirements"]})
        self.assertTrue(all(row["status"] == "planned" for row in rows))

    def test_starter_preserves_editable_todos(self) -> None:
        starter = lab.SCENARIO_ROOT / "workshop" / "starter"
        self.assertTrue(any("TODO" in path.read_text(encoding="utf-8") for path in starter.glob("*.*") if path.is_file()))

    def test_reference_package_contains_no_unresolved_todo_markers(self) -> None:
        self.assertTrue(all("TODO" not in path.read_text(encoding="utf-8") for path in lab.REFERENCE_ROOT.glob("*.*") if path.is_file()))

    def test_run_demo_preserves_all_claim_boundaries(self) -> None:
        report = lab.run_demo()
        self.assertEqual(report["fixture_status"], "synthetic_training_fixture_not_production_evidence")
        self.assertEqual(report["contract_findings"], [])
        self.assertEqual(report["workload_findings"], [])
        self.assertEqual(report["measurement_plan_findings"], [])
        self.assertFalse(report["release_assessment"]["production_ready"])


if __name__ == "__main__":
    unittest.main()
