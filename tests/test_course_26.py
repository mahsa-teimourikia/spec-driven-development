"""Focused verification for Course 26 architecture governance."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/advanced/02-enterprise-architecture-governance-agentic-sdd"
SCENARIO = LESSON / "northstar-architecture-governance"
for module_name in list(sys.modules):
    if module_name == "governance_app" or module_name.startswith("governance_app."):
        del sys.modules[module_name]
sys.path.insert(0, str(SCENARIO))

from governance_app.architecture_graph import find_cycles  # noqa: E402
from governance_app.control_plane import ArchitectureControlPlane  # noqa: E402
from governance_app.exceptions import exception_subject_digest, validate_exception  # noqa: E402
from governance_app.models import ArchitectureError, Finding, ServiceEdge  # noqa: E402
from governance_app.registry import current_head, sign_payload  # noqa: E402
from governance_app.simulation import (  # noqa: E402
    FUTURE,
    NOW,
    demonstrate_stale_report,
    exception_for,
    initialize_repository,
    mutate_and_commit,
    run_adversarial_evaluations,
    run_golden_scenarios,
    run_reference,
)


class Course26Tests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="course26-test-")
        self.repo = Path(self.directory.name) / "ai-service"
        self.base, self.head = initialize_repository(SCENARIO, self.repo)
        self.plane = ArchitectureControlPlane(SCENARIO)

    def tearDown(self):
        self.directory.cleanup()

    def observation(self, mutation="clean", environment="development"):
        head = self.head if mutation == "clean" else mutate_and_commit(self.repo, mutation)
        return self.plane.observe(self.repo, self.base, head, environment, NOW)

    def report(self, mutation="clean", environment="development", exceptions=()):
        observation = self.observation(mutation, environment)
        return self.plane.evaluate(observation, NOW, exceptions)

    def assert_error(self, code, operation):
        with self.assertRaises(ArchitectureError) as caught:
            operation()
        self.assertEqual(code, caught.exception.code)

    def test_active_policy_is_external_authority(self):
        self.assertEqual(self.plane.policy_version, "EA-POLICY@7")

    def test_clean_change_is_conformant(self):
        self.assertEqual(self.report().decision, "CONFORMANT")

    def test_observation_binds_real_git_commits(self):
        observation = self.observation()
        self.assertEqual(observation.base_commit, self.base)
        self.assertEqual(observation.head_commit, current_head(self.repo))

    def test_changed_files_are_derived_from_git(self):
        observation = self.observation()
        self.assertEqual(observation.changed_files, ("docs/change-note.md",))

    def test_source_imports_are_derived_from_ast(self):
        observation = self.observation()
        modules = {item["module"] for item in observation.imports}
        self.assertIn("northstar_ai_gateway", modules)

    def test_service_edges_are_derived_from_repository(self):
        observation = self.observation()
        self.assertEqual(len(observation.service_edges), 3)

    def test_observation_signature_is_verified(self):
        self.assertTrue(self.report().observation_signature_verified)

    def test_forged_observation_is_rejected(self):
        observation = replace(self.observation(), signature="hmac-sha256:forged")
        self.assert_error(
            "OBSERVATION_AUTHENTICITY_UNVERIFIED",
            lambda: self.plane.evaluate(observation, NOW),
        )

    def test_untrusted_observation_producer_is_rejected(self):
        observation = self.observation()
        forged = replace(observation, producer="candidate-agent")
        forged = replace(forged, signature=sign_payload(forged.payload(), self.plane.observation_key))
        self.assert_error("OBSERVATION_PRODUCER_UNTRUSTED", lambda: self.plane.evaluate(forged, NOW))

    def test_candidate_cannot_select_old_policy(self):
        observation = self.observation()
        stale = replace(observation, policy_version="EA-POLICY@6")
        stale = replace(stale, signature=sign_payload(stale.payload(), self.plane.observation_key))
        self.assert_error("POLICY_REVISION_STALE", lambda: self.plane.evaluate(stale, NOW))

    def test_wrong_head_is_rejected_before_scan(self):
        self.assert_error(
            "HEAD_BINDING_MISMATCH",
            lambda: self.plane.observe(self.repo, self.base, "0" * 40, "development", NOW),
        )

    def test_direct_provider_dependency_blocks(self):
        report = self.report("direct_provider")
        self.assertEqual(report.decision, "BLOCKED")
        self.assertIn("DIRECT_MODEL_PROVIDER_DEPENDENCY", [item.code for item in report.findings])

    def test_direct_provider_endpoint_blocks(self):
        report = self.report("endpoint_bypass")
        self.assertIn("DIRECT_MODEL_PROVIDER_ENDPOINT", [item.code for item in report.findings])

    def test_generic_http_without_runtime_evidence_is_insufficient(self):
        report = self.report("generic_http")
        self.assertEqual(report.decision, "INSUFFICIENT_EVIDENCE")
        self.assertIn("RUNTIME_EGRESS_EVIDENCE_MISSING", [item.code for item in report.findings])

    def test_candidate_egress_self_report_is_not_trusted(self):
        report = self.report("generic_http")
        self.assertIn("config/egress-evidence.json", report.changed_files)
        self.assertEqual(report.decision, "INSUFFICIENT_EVIDENCE")

    def runtime_evidence(self, head, **overrides):
        payload = {
            "evidence_id": "NET-EGRESS-2602",
            "producer": self.plane.runtime_evidence_producer,
            "head_commit": head,
            "environment": "development",
            "allowed_destinations": ["enterprise-ai-gateway.internal"],
            "issued_at": "2026-11-03T17:00:00Z",
            "expires_at": FUTURE,
            **overrides,
        }
        return {"payload": payload, "signature": sign_payload(payload, self.plane.runtime_evidence_key)}

    def test_trusted_runtime_egress_resolves_generic_http_uncertainty(self):
        head = mutate_and_commit(self.repo, "generic_http")
        evidence = self.runtime_evidence(head)
        observation = self.plane.observe(
            self.repo, self.base, head, "development", NOW, runtime_evidence=evidence
        )
        report = self.plane.evaluate(observation, NOW)
        self.assertEqual(report.decision, "CONFORMANT")
        self.assertIn("NET-EGRESS-2602", report.evidence_ids)

    def test_forged_runtime_egress_is_rejected(self):
        head = mutate_and_commit(self.repo, "generic_http")
        evidence = self.runtime_evidence(head)
        evidence["signature"] = "hmac-sha256:forged"
        self.assert_error(
            "RUNTIME_EGRESS_EVIDENCE_UNVERIFIED",
            lambda: self.plane.observe(
                self.repo, self.base, head, "development", NOW, runtime_evidence=evidence
            ),
        )

    def test_wrong_head_runtime_egress_is_rejected(self):
        head = mutate_and_commit(self.repo, "generic_http")
        evidence = self.runtime_evidence("0" * 40)
        self.assert_error(
            "RUNTIME_EGRESS_SUBJECT_MISMATCH",
            lambda: self.plane.observe(
                self.repo, self.base, head, "development", NOW, runtime_evidence=evidence
            ),
        )

    def test_domain_to_infrastructure_dependency_blocks(self):
        report = self.report("layer_violation")
        self.assertIn("LAYER_DEPENDENCY_VIOLATION", [item.code for item in report.findings])

    def test_private_database_access_blocks(self):
        report = self.report("private_database")
        self.assertIn("PRIVATE_DATASTORE_ACCESS", [item.code for item in report.findings])

    def test_unapproved_database_requires_architecture_decision(self):
        report = self.report("unapproved_vector")
        self.assertEqual(report.decision, "REVIEW_REQUIRED")
        self.assertIn("ARCHITECTURE_DECISION_REQUIRED", [item.code for item in report.findings])

    def test_dependency_cycle_is_deterministic(self):
        cycles = find_cycles(
            (
                ServiceEdge("b", "c", "async"),
                ServiceEdge("c", "a", "async"),
                ServiceEdge("a", "b", "async"),
            )
        )
        self.assertEqual(cycles, (("a", "b", "c", "a"),))

    def test_new_service_cycle_blocks(self):
        report = self.report("cycle")
        self.assertIn("SERVICE_DEPENDENCY_CYCLE", [item.code for item in report.findings])

    def test_candidate_policy_shadow_blocks(self):
        report = self.report("policy_shadow")
        self.assertIn("POLICY_SHADOWING_ATTEMPT", [item.code for item in report.findings])

    def test_conflicting_adr_requires_review(self):
        report = self.report("conflicting_adr")
        self.assertEqual(report.decision, "REVIEW_REQUIRED")

    def test_superseded_adr_requires_reassessment(self):
        report = self.report("superseded_adr")
        self.assertEqual(report.decision, "REASSESSMENT_REQUIRED")

    def test_valid_exception_is_exact_scope(self):
        observation = self.observation("direct_provider")
        record = exception_for(self.plane, observation)
        report = self.plane.evaluate(observation, NOW, [record])
        self.assertEqual(report.decision, "CONFORMANT_WITH_EXCEPTION")
        self.assertEqual(report.findings[0].exception_id, "ARCH-EX-2601")

    def test_exception_subject_binds_resource_content(self):
        observation = self.observation("direct_provider")
        finding = self.plane.evaluate(observation, NOW).findings[0]
        digest = exception_subject_digest(observation, finding)
        self.assertTrue(digest.startswith("sha256:"))

    def test_expired_exception_does_not_waive(self):
        observation = self.observation("direct_provider")
        record = exception_for(self.plane, observation, expires_at="2026-11-02T00:00:00Z")
        report = self.plane.evaluate(observation, NOW, [record])
        self.assertEqual(report.decision, "BLOCKED")
        self.assertIn("EXCEPTION_EXPIRED", [item.code for item in report.findings])

    def test_wrong_environment_exception_does_not_waive(self):
        observation = self.observation("direct_provider")
        record = exception_for(self.plane, observation, environment="production")
        report = self.plane.evaluate(observation, NOW, [record])
        self.assertIn("EXCEPTION_ENVIRONMENT_MISMATCH", [item.code for item in report.findings])

    def test_wrong_subject_exception_does_not_waive(self):
        observation = self.observation("direct_provider")
        record = exception_for(self.plane, observation, subject_digest="sha256:wrong")
        report = self.plane.evaluate(observation, NOW, [record])
        self.assertIn("EXCEPTION_SUBJECT_MISMATCH", [item.code for item in report.findings])

    def test_revoked_exception_does_not_waive(self):
        observation = self.observation("direct_provider")
        record = exception_for(self.plane, observation, status="REVOKED")
        report = self.plane.evaluate(observation, NOW, [record])
        self.assertIn("EXCEPTION_NOT_APPROVED", [item.code for item in report.findings])

    def test_forged_exception_does_not_waive(self):
        observation = self.observation("direct_provider")
        record = exception_for(self.plane, observation)
        record["signature"] = "hmac-sha256:forged"
        report = self.plane.evaluate(observation, NOW, [record])
        self.assertIn("EXCEPTION_AUTHENTICITY_UNVERIFIED", [item.code for item in report.findings])

    def test_missing_compensating_control_evidence_is_rejected(self):
        observation = self.observation("direct_provider")
        preliminary = self.plane.evaluate(observation, NOW)
        finding = next(item for item in preliminary.findings if item.disposition == "BLOCK")
        record = exception_for(self.plane, observation)
        record["payload"]["compensating_controls"] = []
        record["signature"] = sign_payload(record["payload"], self.plane.exception_keys["architecture-board-v1"])
        valid, code = validate_exception(record, finding, observation, NOW, self.plane.exception_keys)
        self.assertFalse(valid)
        self.assertEqual(code, "COMPENSATING_CONTROL_EVIDENCE_MISSING")

    def test_exception_cannot_be_used_before_issue_time(self):
        observation = self.observation("direct_provider")
        preliminary = self.plane.evaluate(observation, NOW)
        finding = next(item for item in preliminary.findings if item.disposition == "BLOCK")
        record = exception_for(self.plane, observation)
        record["payload"]["issued_at"] = "2026-11-04T00:00:00Z"
        record["signature"] = sign_payload(record["payload"], self.plane.exception_keys["architecture-board-v1"])
        valid, code = validate_exception(record, finding, observation, NOW, self.plane.exception_keys)
        self.assertFalse(valid)
        self.assertEqual(code, "EXCEPTION_NOT_YET_VALID")

    def test_report_contains_actionable_evidence(self):
        report = self.report("direct_provider")
        finding = next(item for item in report.findings if item.code == "DIRECT_MODEL_PROVIDER_DEPENDENCY")
        self.assertEqual(finding.rule_id, "EA-001")
        self.assertTrue(finding.resource.endswith("provider.py"))
        self.assertTrue(finding.evidence)

    def test_report_declares_limitations(self):
        report = self.report()
        self.assertGreaterEqual(len(report.limitations), 3)
        self.assertTrue(any("not deployment authorization" in item for item in report.limitations))

    def test_report_is_bound_to_policy_and_head(self):
        report = self.report()
        self.assertEqual(report.policy_version, "EA-POLICY@7")
        self.assertEqual(report.head_commit, current_head(self.repo))

    def test_stale_report_is_rejected_after_new_commit(self):
        self.assertEqual(demonstrate_stale_report(SCENARIO), "REPORT_STALE_FOR_HEAD")

    def test_retrieval_change_has_targeted_impact(self):
        impact = self.plane.impact("ADR-028-RETRIEVAL-PLATFORM")
        self.assertEqual(impact["decision"], "TARGETED_REASSESSMENT_REQUIRED")
        self.assertIn("ai-service", impact["repositories"])
        self.assertIn("retrieval-quality-suite", impact["evaluations"])

    def test_unknown_change_does_not_invalidate_everything(self):
        impact = self.plane.impact("UNKNOWN")
        self.assertEqual(impact["decision"], "NO_REGISTERED_IMPACT")
        self.assertEqual(impact["repositories"], [])

    def test_scenario_files_are_machine_readable(self):
        files = sorted((SCENARIO / "scenarios").glob("*.json"))
        self.assertEqual(len(files), 13)
        self.assertTrue(all(json.loads(path.read_text())["expected_decision"] for path in files))

    def test_golden_scenarios_match_expected_decisions(self):
        results = run_golden_scenarios(SCENARIO)
        self.assertEqual(len(results), 13)
        self.assertTrue(all(item["passed"] for item in results))

    def test_adversarial_evaluations_are_exact(self):
        result = run_adversarial_evaluations(SCENARIO)
        self.assertEqual(result["metrics"]["counts"]["total"], 16)
        self.assertEqual(result["metrics"]["exact_decision_accuracy"], 1.0)
        self.assertEqual(result["metrics"]["exception_validation_accuracy"], 1.0)

    def test_reference_run_exposes_metrics_and_impact(self):
        result = run_reference(SCENARIO)
        self.assertTrue(result["golden_passed"])
        self.assertEqual(result["stale_report_result"], "REPORT_STALE_FOR_HEAD")
        self.assertEqual(result["retrieval_change_impact"]["decision"], "TARGETED_REASSESSMENT_REQUIRED")

    def test_conformance_report_is_not_execution_authority(self):
        report = self.report()
        payload = report.payload()
        self.assertNotIn("deploy", payload)
        self.assertNotIn("authorization", payload)


if __name__ == "__main__":
    unittest.main()
