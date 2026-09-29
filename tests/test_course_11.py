"""Regression tests for Course 11's deterministic coordination control plane."""

from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "01-multi-agent-coding-workflows-coordination"
MODULE_SPEC = importlib.util.spec_from_file_location("course11_lab", LESSON / "lab.py")
assert MODULE_SPEC and MODULE_SPEC.loader
lab = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = lab
MODULE_SPEC.loader.exec_module(lab)


class Course11CoordinationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = lab.load_bundle()
        self.candidate = lab.load_bundle(candidate=True)

    @staticmethod
    def codes(findings):
        return {item.code if hasattr(item, "code") else item["code"] for item in findings}

    def test_fixture_is_explicitly_fictional(self):
        self.assertIn("fictional", lab.run_demo()["fixture_status"])

    def test_reference_is_coordination_ready(self):
        report = lab.review_workflow(self.reference)
        self.assertEqual({}, report["counts"])
        self.assertEqual("COORDINATION_READY", lab.coordination_decision(report)["state"])

    def test_readiness_does_not_claim_external_authority(self):
        decision = lab.coordination_decision(lab.review_workflow(self.reference))
        self.assertIn("does not provision identities", decision["boundary"])

    def test_candidate_is_blocked_with_stable_counts(self):
        report = lab.review_workflow(self.candidate)
        self.assertEqual({"review": 11, "blocking": 50}, report["counts"])
        self.assertEqual("COORDINATION_BLOCKED", lab.coordination_decision(report)["state"])

    def test_multi_agent_use_requires_a_written_justification(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        workflow["multi_agent_decision"]["why_multiple_agents"] = []
        self.assertIn("MULTI_AGENT_JUSTIFICATION_MISSING", self.codes(lab.validate_strategy(workflow)))

    def test_budget_is_not_agent_count_alone(self):
        budgets = self.reference["workflow"]["budgets"]
        self.assertTrue({"max_parallel", "max_handoffs", "max_replans", "max_units_waiting_for_review"} <= set(budgets))
        self.assertIn("not recommended defaults", self.reference["workflow"]["budget_provenance"]["claim"])

    def test_dependency_graph_has_five_waves(self):
        schedule = lab.topological_waves(self.reference["workflow"])
        self.assertTrue(schedule["acyclic"])
        self.assertEqual(5, len(schedule["waves"]))

    def test_only_extraction_and_validation_share_a_wave(self):
        waves = lab.topological_waves(self.reference["workflow"])["waves"]
        self.assertEqual(["AWU-BR-EXTRACTION", "AWU-BR-VALIDATION"], waves[1])

    def test_initial_pull_exposes_only_contract_work(self):
        states = {item["id"]: "PROPOSED" for item in self.reference["workflow"]["work_units"]}
        self.assertEqual(["AWU-BR-CONTRACT"], lab.ready_work_units(self.reference["workflow"], states))

    def test_pull_scheduler_respects_review_capacity(self):
        workflow = self.reference["workflow"]
        states = {item["id"]: "PROPOSED" for item in workflow["work_units"]}
        states["AWU-BR-CONTRACT"] = "VERIFIED"
        result = lab.pull_dispatch(
            workflow,
            states,
            active_count=0,
            review_queue_depths={"ENGINEERING_REVIEW": 0, "SECURITY_REVIEW": 0, "DOMAIN_REVIEW": 1},
            review_capacities={"ENGINEERING_REVIEW": 2, "SECURITY_REVIEW": 1, "DOMAIN_REVIEW": 1},
        )
        self.assertIn("AWU-BR-EXTRACTION", result["dispatchable"])
        self.assertIn("AWU-BR-VALIDATION", result["waiting_for_review_capacity"])

    def test_pull_scheduler_respects_parallelism_budget(self):
        workflow = self.reference["workflow"]
        states = {item["id"]: "PROPOSED" for item in workflow["work_units"]}
        states["AWU-BR-CONTRACT"] = "VERIFIED"
        result = lab.pull_dispatch(
            workflow,
            states,
            active_count=workflow["budgets"]["max_parallel"],
            review_queue_depths={},
            review_capacities={"Security": 2, "Domain": 2},
        )
        self.assertEqual([], result["dispatchable"])

    def test_assignments_use_verified_workload_identities(self):
        registry = {item["id"]: item for item in self.reference["workflow"]["identity_registry"]}
        for assignment in self.reference["workflow"]["assignments"]:
            self.assertEqual("workload_identity", registry[assignment["agent_identity"]]["kind"])
            self.assertTrue(registry[assignment["agent_identity"]]["expires_at"])

    def test_role_label_is_not_an_identity(self):
        self.assertIn(
            "AGENT_IDENTITY_UNVERIFIED",
            self.codes(lab.validate_assignments(self.candidate["workflow"])),
        )

    def test_permissions_are_temporary_and_not_self_provisioned(self):
        for assignment in self.reference["workflow"]["assignments"]:
            self.assertEqual("assignment_bound_temporary", assignment["permissions"]["lifecycle"])
            self.assertFalse(assignment["permissions"]["self_provisioned"])
            self.assertTrue(assignment["permissions"]["expires_at"])

    def test_each_assignment_has_an_expiring_lease(self):
        for assignment in self.reference["workflow"]["assignments"]:
            lease = assignment["lease"]
            self.assertTrue(lease["id"] and lease["expires_at"] and lease["heartbeat_policy"] and lease["state"])

    def test_future_work_has_no_assignment_permission_lease_or_lock(self):
        workflow = self.reference["workflow"]
        assigned = {item["work_unit_id"] for item in workflow["assignments"]}
        locked = {item["work_unit_id"] for item in workflow["locks"]}
        for unit in workflow["work_units"]:
            if unit["state"] in {"PLANNED", "READY"}:
                self.assertEqual("unassigned", unit["execution_owner"])
                self.assertNotIn(unit["id"], assigned)
                self.assertNotIn(unit["id"], locked)

    def test_premature_assignment_is_rejected(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        workflow["assignments"].append({
            "id": "ASSIGN-CONFLICT-EARLY", "work_unit_id": "AWU-BR-CONFLICT",
            "agent_identity": "agent-conflict-01", "state": "ASSIGNED",
            "permissions": {
                "write_paths": ["src/underwriting/conflicts.py", "tests/underwriting/test_conflicts.py"],
                "lifecycle": "assignment_bound_temporary", "expires_at": "2026-10-01T17:00:00Z",
                "self_provisioned": False,
            },
            "lease": {
                "id": "LEASE-CONFLICT-EARLY", "state": "ACTIVE", "expires_at": "2026-10-01T17:00:00Z",
                "heartbeat_policy": "every_5_minutes", "recovery_policy": "inspect_before_reassign",
            },
        })
        self.assertIn("PREMATURE_RESOURCE_RESERVATION", self.codes(lab.validate_assignments(workflow)))

    def test_pull_dispatch_binds_resources_only_for_ready_work(self):
        workflow = self.reference["workflow"]
        states = {item["id"]: item["state"] for item in workflow["work_units"]}
        assignment = {
            "id": "ASSIGN-CONFLICT-020", "work_unit_id": "AWU-BR-CONFLICT",
            "agent_identity": "agent-conflict-01",
            "permissions": {
                "write_paths": ["src/underwriting/conflicts.py", "tests/underwriting/test_conflicts.py"],
                "lifecycle": "assignment_bound_temporary", "expires_at": "2026-10-01T17:00:00Z",
                "self_provisioned": False,
            },
            "lease": {
                "id": "LEASE-CONFLICT-020", "expires_at": "2026-10-01T17:00:00Z",
                "heartbeat_policy": "every_5_minutes", "recovery_policy": "inspect_before_reassign",
            },
        }
        lock = {
            "id": "LOCK-CONFLICT", "work_unit_id": "AWU-BR-CONFLICT",
            "assignment_id": "ASSIGN-CONFLICT-020", "lease_id": "LEASE-CONFLICT-020",
            "paths": ["src/underwriting/conflicts.py", "tests/underwriting/test_conflicts.py"],
        }
        result = lab.bind_dispatch_resources(
            workflow, states, work_unit_id="AWU-BR-CONFLICT", assignment=assignment, lock=lock
        )
        self.assertEqual("ASSIGNED", result["outcome"])
        unit = next(item for item in result["workflow"]["work_units"] if item["id"] == "AWU-BR-CONFLICT")
        self.assertEqual(("ASSIGNED", "agent-conflict-01"), (unit["state"], unit["execution_owner"]))
        self.assertEqual("RESERVED", result["workflow"]["locks"][-1]["state"])

    def test_lease_cannot_outlive_workload_identity(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        workflow["assignments"][0]["lease"]["expires_at"] = "2026-10-01T19:00:00Z"
        self.assertIn("LEASE_OUTLIVES_IDENTITY", self.codes(lab.validate_assignments(workflow)))

    def test_permission_cannot_outlive_lease(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        workflow["assignments"][0]["permissions"]["expires_at"] = "2026-10-01T17:30:00Z"
        self.assertIn("PERMISSION_OUTLIVES_ASSIGNMENT", self.codes(lab.validate_assignments(workflow)))

    def test_duplicate_assignment_delivery_is_idempotent(self):
        assignment = self.reference["workflow"]["assignments"][0]
        first = lab.process_assignment_delivery({"assignments": {}}, assignment)
        second = lab.process_assignment_delivery(first["state"], assignment)
        self.assertTrue(first["started"])
        self.assertFalse(second["started"])
        self.assertEqual("duplicate_delivery_reconciled", second["outcome"])

    def test_expired_lease_requires_inspection_before_reassignment(self):
        assignment = copy.deepcopy(self.reference["workflow"]["assignments"][0])
        assignment["state"] = "IN_PROGRESS"
        assignment["lease"]["state"] = "ACTIVE"
        result = lab.recover_expired_lease(assignment, now="2030-01-01T00:00:00Z")
        self.assertEqual("RECOVERY_REQUIRED", result["next_state"])
        self.assertTrue(result["may_reassign"])

    def test_released_completed_lease_does_not_reenter_recovery(self):
        assignment = self.reference["workflow"]["assignments"][0]
        result = lab.recover_expired_lease(assignment, now="2030-01-01T00:00:00Z")
        self.assertFalse(result["expired"])
        self.assertEqual("COMPLETED", result["next_state"])

    def test_each_work_unit_has_its_own_branch(self):
        branches = [item["branch"] for item in self.reference["workflow"]["work_units"]]
        self.assertEqual(len(branches), len(set(branches)))

    def test_parallel_writers_have_exclusive_paths(self):
        units = {item["id"]: item for item in self.reference["workflow"]["work_units"]}
        left = units["AWU-BR-EXTRACTION"]
        right = units["AWU-BR-VALIDATION"]
        self.assertFalse(set(left["writable_paths"]) & set(right["writable_paths"]))

    def test_same_path_in_different_waves_is_sequential_ownership(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        contract = next(item for item in workflow["work_units"] if item["id"] == "AWU-BR-CONTRACT")
        conflict = next(item for item in workflow["work_units"] if item["id"] == "AWU-BR-CONFLICT")
        conflict["writable_paths"] = contract["writable_paths"]
        findings = lab.validate_branches_locks_and_context(workflow)
        self.assertNotIn("PARALLEL_WRITE_COLLISION", self.codes(findings))

    def test_same_path_in_same_wave_is_parallel_collision(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        extraction = next(item for item in workflow["work_units"] if item["id"] == "AWU-BR-EXTRACTION")
        validation = next(item for item in workflow["work_units"] if item["id"] == "AWU-BR-VALIDATION")
        validation["writable_paths"] = extraction["writable_paths"]
        findings = lab.validate_branches_locks_and_context(workflow)
        self.assertIn("PARALLEL_WRITE_COLLISION", self.codes(findings))

    def test_locks_bind_owner_subject_and_lease(self):
        for lock in self.reference["workflow"]["locks"]:
            self.assertTrue(lock["work_unit_id"] and lock["paths"] and lock["lease_id"])

    def test_released_lease_cannot_hold_active_lock(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        workflow["locks"][0]["state"] = "ACTIVE"
        self.assertIn(
            "WRITE_LOCK_LIFECYCLE_INVALID",
            self.codes(lab.validate_branches_locks_and_context(workflow)),
        )

    def test_shared_context_is_revision_pinned(self):
        workflow = self.reference["workflow"]
        self.assertTrue(workflow["specification_digest"].startswith("sha256:"))
        self.assertTrue(workflow["plan_digest"].startswith("sha256:"))
        self.assertTrue(workflow["repository_revision"])

    def test_delegated_authority_cannot_exceed_parent(self):
        findings = lab.validate_delegation_and_independence(self.candidate["workflow"])
        self.assertIn("DELEGATION_AUTHORITY_AMPLIFIED", self.codes(findings))

    def test_read_only_delegation_cannot_write(self):
        findings = lab.validate_delegation_and_independence(self.candidate["workflow"])
        self.assertIn("READ_ONLY_DELEGATE_CAN_WRITE", self.codes(findings))

    def test_executor_does_not_verify_its_own_work(self):
        workflow = self.reference["workflow"]
        implementers = {item["agent_identity"] for item in workflow["assignments"]}
        self.assertTrue(workflow["verification"]["independent"])
        self.assertNotIn(workflow["verification"]["verifier_identity"], implementers)

    def test_coordination_events_are_typed_and_attributed(self):
        for event in self.reference["event_log"]["events"]:
            self.assertTrue(event["id"] and event["type"] and event["producer_identity"])
            self.assertTrue(event["repository_revision"] and event["timestamp"])

    def test_verified_event_references_verification_evidence(self):
        governed_events = [
            item for item in self.reference["event_log"]["events"]
            if item.get("type") == "WORK_UNIT_VERIFIED"
        ]
        self.assertTrue(governed_events)
        self.assertTrue(all(item.get("transition_artifact_id") for item in governed_events))

    def test_event_label_does_not_substitute_for_transition_artifact(self):
        log = copy.deepcopy(self.reference["event_log"])
        event = next(item for item in log["events"] if item["type"] == "WORK_UNIT_VERIFIED")
        event["transition_artifact_id"] = "agent-says-passed"
        self.assertIn(
            "COORDINATION_TRANSITION_ARTIFACT_INVALID",
            self.codes(lab.validate_events(self.reference["workflow"], log)),
        )

    def test_verification_transition_evidence_is_revision_bound(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        artifact = next(item for item in workflow["transition_artifacts"] if item["id"] == "VERIFY-CONTRACT-81AB21")
        artifact["subject_revision"] = "stale-revision"
        self.assertIn(
            "COORDINATION_TRANSITION_ARTIFACT_INVALID",
            self.codes(lab.validate_events(workflow, self.reference["event_log"])),
        )

    def test_handoff_contains_outputs_evidence_and_unresolved_items(self):
        handoff = self.reference["handoff"]
        self.assertTrue(handoff["outputs"] and handoff["evidence_ids"])
        self.assertIn("unresolved", handoff)

    def test_handoff_evidence_is_explicitly_verified(self):
        artifacts = {item["id"]: item for item in self.reference["workflow"]["transition_artifacts"]}
        evidence_id = self.reference["handoff"]["evidence_ids"][0]
        verification = next(item for item in artifacts.values() if evidence_id in item.get("supports_evidence_ids", []))
        self.assertEqual("component_evidence_bundle", artifacts[evidence_id]["kind"])
        self.assertEqual(("verification_evidence", "passed"), (verification["kind"], verification["state"]))

    def test_handoff_rejects_unverified_component_evidence(self):
        workflow = copy.deepcopy(self.reference["workflow"])
        verification = next(
            item for item in workflow["transition_artifacts"]
            if item["id"] == "VERIFY-CONTRACT-81AB21"
        )
        verification["supports_evidence_ids"] = []
        self.assertIn(
            "HANDOFF_EVIDENCE_UNVERIFIED",
            self.codes(lab.validate_handoff(workflow, self.reference["handoff"])),
        )

    def test_contract_registry_names_consumers(self):
        contracts = {item["id"]: item for item in self.reference["workflow"]["contract_registry"]}
        self.assertEqual(
            {"AWU-BR-EXTRACTION", "AWU-BR-VALIDATION", "AWU-BR-CONFLICT", "AWU-BR-REVIEW", "AWU-BR-INTEGRATION"},
            set(contracts["ProposedUpdate"]["consumers"]),
        )
        self.assertEqual([], lab.validate_contract_registry(self.reference["workflow"]))

    def test_integration_inputs_are_explicit_beyond_ordering_edge(self):
        integration = next(item for item in self.reference["workflow"]["work_units"] if item["id"] == "AWU-BR-INTEGRATION")
        self.assertEqual(["AWU-BR-REVIEW"], integration["depends_on"])
        self.assertEqual(
            {item["id"] for item in self.reference["workflow"]["component_registry"]},
            set(integration["integration_inputs"]),
        )

    def test_stale_handoff_contract_is_detected(self):
        handoff = copy.deepcopy(self.reference["handoff"])
        handoff["outputs"]["ProposedUpdate"]["revision"] = "stale"
        findings = lab.validate_handoff(self.reference["workflow"], handoff)
        self.assertIn("HANDOFF_CONTRACT_REVISION_STALE", self.codes(findings))

    def test_integration_authority_excludes_product_policy_and_release(self):
        authority = self.reference["workflow"]["integration_authority"]
        self.assertEqual({"test_fixture_structure", "diagnostic_sequence"}, set(authority["may_decide"]))
        self.assertTrue({"change_shared_contract", "weaken_acceptance_criteria", "approve_architecture_change"} <= set(authority["may_not_decide"]))

    def test_component_change_invalidates_integration_evidence(self):
        integration = self.reference["integration"]
        component = next(iter(integration["components"]))
        result = lab.invalidate_integration_evidence(integration, component, "sha256:new")
        self.assertEqual("REVALIDATION_REQUIRED", result["state"])
        self.assertTrue(result["stale_evidence_ids"])

    def test_recovery_persists_results_not_private_reasoning(self):
        recovery = self.reference["recovery"]
        self.assertIsNone(recovery["private_reasoning"])
        self.assertTrue(recovery["completed"] and recovery["remaining"])

    def test_blind_resume_is_detected(self):
        recovery = copy.deepcopy(self.reference["recovery"])
        recovery["inspection"]["partial_work_treated_as_trusted"] = True
        findings = lab.validate_recovery(self.reference["workflow"], recovery)
        self.assertIn("RECOVERY_BLIND_RESUME", self.codes(findings))

    def test_review_package_limits_changed_paths(self):
        findings = lab.validate_review_package(self.reference["workflow"], self.reference["review_package"])
        self.assertEqual([], findings)

    def test_policy_denial_is_not_retryable(self):
        result = lab.classify_execution_failure("policy_denied", 1, self.reference["policy"])
        self.assertEqual("STOP_AND_ROUTE", result["action"])

    def test_stale_context_refreshes_before_retry(self):
        result = lab.classify_execution_failure("context_stale", 1, self.reference["policy"])
        self.assertEqual("REFRESH_REPLAN", result["action"])

    def test_transient_failure_has_a_bounded_retry(self):
        result = lab.classify_execution_failure("transient_infrastructure_failure", 1, self.reference["policy"])
        self.assertEqual("BOUNDED_RETRY", result["action"])

    def test_retry_budget_exhaustion_escalates(self):
        limit = self.reference["policy"]["retry_policy"]["attempt_limit"]
        result = lab.classify_execution_failure("transient_infrastructure_failure", limit, self.reference["policy"])
        self.assertEqual("ESCALATE", result["action"])

    def test_repair_oscillation_is_systemic(self):
        history = [
            {"failure_class": "test_failure", "semantic_change": "A_TO_B"},
            {"failure_class": "test_failure", "semantic_change": "B_TO_A"},
            {"failure_class": "test_failure", "semantic_change": "A_TO_B"},
        ]
        result = lab.analyze_execution_history(history, self.reference["policy"])
        self.assertTrue(result["repair_oscillation"])
        self.assertEqual("SYSTEMIC_PROBLEM_SUSPECTED", result["action"])

    def test_contract_change_identifies_active_and_completed_consumers(self):
        states = {item["id"]: "PROPOSED" for item in self.reference["workflow"]["work_units"]}
        states.update({"AWU-BR-CONTRACT": "VERIFIED", "AWU-BR-EXTRACTION": "IN_PROGRESS", "AWU-BR-VALIDATION": "COMPLETED"})
        result = lab.contract_change_blast_radius(
            self.reference["workflow"], "ProposedUpdate", states, {"AWU-BR-VALIDATION": ["EVID-VALIDATION-01"]}
        )
        self.assertEqual(["AWU-BR-EXTRACTION"], result["active"])
        self.assertIn("AWU-BR-VALIDATION", result["completed"])
        self.assertEqual(["EVID-VALIDATION-01"], result["evidence_invalidated"])

    def test_unsafe_parallelism_is_not_declared_best(self):
        models = {item["name"]: item for item in lab.compare_execution_models()["models"]}
        self.assertLess(models["unsafe_parallel"]["lead_time_units"], models["governed_multi_agent"]["lead_time_units"])
        self.assertGreater(models["unsafe_parallel"]["rework_units"], models["governed_multi_agent"]["rework_units"])

    def test_evaluation_is_exact_on_declared_fixture(self):
        evaluation = lab.evaluate_coordination_rules()
        self.assertEqual((36, 38, 0, 0), (
            evaluation["population"], evaluation["true_positive"],
            evaluation["false_positive"], evaluation["false_negative"],
        ))
        self.assertEqual({"numerator": 36, "denominator": 36}, evaluation["exact_matches"])

    def test_evaluation_discloses_non_general_boundary(self):
        self.assertIn("not_general", lab.evaluate_coordination_rules()["claim"])

    def test_policy_has_ten_named_orchestration_invariants(self):
        invariants = self.reference["policy"]["invariants"]
        self.assertEqual(10, len(invariants))
        self.assertEqual({f"ORCH-INV-{index:03d}" for index in range(1, 11)}, {item["id"] for item in invariants})


if __name__ == "__main__":
    unittest.main()
