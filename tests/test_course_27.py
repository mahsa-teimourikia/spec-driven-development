"""Focused invariants for Course 27 testing and quality."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "curriculum/advanced/03-testing-quality-agentic-sdd/northstar-quality-control"
sys.path.insert(0, str(SCENARIO))

from quality_app.control_plane import QualityControlPlane  # noqa: E402
from quality_app.models import QualityError  # noqa: E402
from quality_app.registry import digest_payload, sign_payload  # noqa: E402
from quality_app.simulation import (  # noqa: E402
    FUTURE,
    GOLDEN,
    NOW,
    demonstrate_subject_tamper,
    evidence_for,
    passing_cases,
    run_evaluation,
    run_golden,
    run_reference,
    run_scenario,
    subject_for,
)


class Course27Tests(unittest.TestCase):
    def setUp(self):
        self.plane = QualityControlPlane(SCENARIO)
        self.subject = subject_for(self.plane)

    def evaluate(self, record=None):
        return self.plane.evaluate(
            self.subject,
            [record or evidence_for(self.plane, self.subject)],
            NOW,
        )

    def resign(self, record):
        record["signature"] = sign_payload(record["payload"], self.plane.evidence_key)
        return record

    def assert_error(self, code, operation):
        with self.assertRaises(QualityError) as caught:
            operation()
        self.assertEqual(code, caught.exception.code)

    def test_active_policy_is_external(self):
        self.assertEqual(self.plane.policy_version, "QUALITY-POLICY@1")

    def test_passing_portfolio_is_accepted(self):
        self.assertEqual(self.evaluate().decision, "QUALITY_EVIDENCE_ACCEPTED")

    def test_quality_acceptance_does_not_authorize_release(self):
        self.assertFalse(self.evaluate().release_authorized)

    def test_observation_signature_is_required(self):
        forged = replace(self.subject, signature="hmac-sha256:forged")
        self.assert_error("SUBJECT_AUTHENTICITY_UNVERIFIED", lambda: self.plane.evaluate(forged, [], NOW))

    def test_observation_producer_is_required(self):
        forged = replace(self.subject, producer="candidate-agent")
        forged = replace(forged, signature=sign_payload(forged.payload(), self.plane.observation_key))
        self.assert_error("SUBJECT_PRODUCER_UNTRUSTED", lambda: self.plane.evaluate(forged, [], NOW))

    def test_stale_quality_policy_is_rejected(self):
        stale = replace(self.subject, policy_version="QUALITY-POLICY@0")
        stale = replace(stale, signature=sign_payload(stale.payload(), self.plane.observation_key))
        self.assert_error("QUALITY_POLICY_STALE", lambda: self.plane.evaluate(stale, [], NOW))

    def test_candidate_tests_are_diagnostic_only(self):
        report = self.evaluate(evidence_for(self.plane, self.subject, producer="candidate-agent"))
        self.assertEqual(report.decision, "INSUFFICIENT_EVIDENCE")
        self.assertIn("CANDIDATE_EVIDENCE_NOT_ATTESTATION", [item.code for item in report.findings])

    def test_forged_independent_evidence_is_rejected(self):
        record = evidence_for(self.plane, self.subject)
        record["signature"] = "hmac-sha256:forged"
        self.assertIn("EVIDENCE_AUTHENTICITY_UNVERIFIED", [item.code for item in self.evaluate(record).findings])

    def test_missing_evidence_id_is_rejected(self):
        record = evidence_for(self.plane, self.subject)
        record["payload"].pop("evidence_id")
        self.resign(record)
        self.assertIn("EVIDENCE_ID_MISSING", [item.code for item in self.evaluate(record).findings])

    def test_evidence_id_collision_blocks(self):
        first = evidence_for(self.plane, self.subject)
        second = evidence_for(self.plane, self.subject)
        second["payload"]["cases"][0]["runs"] = ["PASS", "PASS"]
        self.resign(second)
        report = self.plane.evaluate(self.subject, [first, second], NOW)
        self.assertIn("EVIDENCE_ID_COLLISION", [item.code for item in report.findings])

    def test_malformed_signed_evidence_is_insufficient(self):
        record = evidence_for(self.plane, self.subject)
        record["payload"]["cases"] = "not-a-list"
        self.resign(record)
        self.assertIn("EVIDENCE_SCHEMA_INVALID", [item.code for item in self.evaluate(record).findings])

    def test_evidence_binds_exact_subject(self):
        record = evidence_for(self.plane, self.subject, subject_digest="sha256:wrong")
        self.assertIn("EVIDENCE_SUBJECT_MISMATCH", [item.code for item in self.evaluate(record).findings])

    def test_evidence_binds_suite_revision(self):
        record = evidence_for(self.plane, self.subject, suite_revision="NORTHSTAR-QUALITY-SUITE@0")
        self.assertIn("EVIDENCE_SUITE_STALE", [item.code for item in self.evaluate(record).findings])

    def test_evidence_binds_policy_revision(self):
        record = evidence_for(self.plane, self.subject)
        record["payload"]["policy_version"] = "QUALITY-POLICY@0"
        self.resign(record)
        self.assertIn("EVIDENCE_POLICY_STALE", [item.code for item in self.evaluate(record).findings])

    def test_expired_evidence_is_rejected(self):
        record = evidence_for(self.plane, self.subject, expires_at="2026-11-08T17:30:00Z")
        self.assertIn("EVIDENCE_EXPIRED", [item.code for item in self.evaluate(record).findings])

    def test_failed_independent_test_blocks(self):
        self.assertEqual(run_scenario(SCENARIO, "failed-test")["decision"], "BLOCKED")

    def test_missing_negative_test_is_insufficient(self):
        self.assertEqual(run_scenario(SCENARIO, "missing-negative")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_surviving_critical_mutant_blocks(self):
        result = run_scenario(SCENARIO, "surviving-mutant")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("CRITICAL_MUTANT_SURVIVED", result["finding_codes"])

    def test_missing_mutation_is_insufficient(self):
        mutations = [
            {"mutation_id": item, "outcome": "KILLED"}
            for item in self.plane.policy["required_mutations"][1:]
        ]
        report = self.evaluate(evidence_for(self.plane, self.subject, mutations=mutations))
        self.assertIn("REQUIRED_MUTATION_NOT_EXECUTED", [item.code for item in report.findings])

    def test_unregistered_mutation_does_not_change_denominator(self):
        record = evidence_for(self.plane, self.subject)
        record["payload"]["mutations"].append({"mutation_id": "EASY_EXTRA", "outcome": "KILLED"})
        self.resign(record)
        report = self.evaluate(record)
        self.assertEqual(report.metrics["mutation"]["required"], 4)
        self.assertIn("UNREGISTERED_MUTATION", [item.code for item in report.findings])

    def test_unsafe_fault_experiment_blocks(self):
        result = run_scenario(SCENARIO, "unsafe-failure")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("FAILURE_EXPERIMENT_UNSAFE", result["finding_codes"])

    def test_missing_fault_experiment_is_insufficient(self):
        self.assertEqual(run_scenario(SCENARIO, "missing-failure")["decision"], "INSUFFICIENT_EVIDENCE")

    def test_flaky_test_cannot_satisfy_obligation(self):
        result = run_scenario(SCENARIO, "flaky")
        self.assertEqual(result["decision"], "REVIEW_REQUIRED")
        self.assertIn("FLAKY_TEST_NOT_EVIDENCE", result["finding_codes"])

    def test_repeated_consistent_passes_are_not_flaky(self):
        cases = passing_cases()
        cases[0] = {**cases[0], "runs": ["PASS", "PASS"]}
        report = self.evaluate(evidence_for(self.plane, self.subject, cases=cases))
        self.assertEqual(report.decision, "QUALITY_EVIDENCE_ACCEPTED")

    def test_conflicting_mutation_outcomes_block(self):
        record = evidence_for(self.plane, self.subject)
        record["payload"]["mutations"].append(
            {"mutation_id": "REMOVE_AUTHORIZATION", "outcome": "SURVIVED"}
        )
        self.resign(record)
        report = self.evaluate(record)
        self.assertIn("MUTATION_OUTCOME_CONFLICT", [item.code for item in report.findings])

    def test_unknown_oracle_is_insufficient(self):
        cases = passing_cases()
        cases[0] = {**cases[0], "oracle_source": "candidate"}
        report = self.evaluate(evidence_for(self.plane, self.subject, cases=cases))
        self.assertIn("ORACLE_INDEPENDENCE_UNPROVEN", [item.code for item in report.findings])

    def test_unknown_requirement_reference_blocks(self):
        self.assertEqual(run_scenario(SCENARIO, "unknown-requirement")["decision"], "BLOCKED")

    def test_no_evidence_is_insufficient(self):
        report = self.plane.evaluate(self.subject, [], NOW)
        self.assertEqual(report.decision, "INSUFFICIENT_EVIDENCE")

    def test_requirement_coverage_is_complete(self):
        coverage = self.evaluate().coverage
        self.assertEqual(coverage["covered_obligations"], coverage["required_obligations"])
        self.assertEqual(coverage["value"], 1.0)

    def test_mutation_metric_has_explicit_denominator(self):
        metric = self.evaluate().metrics["mutation"]
        self.assertEqual(metric, {"killed": 4, "required": 4, "value": 1.0, "excluded_from_denominator": 0})

    def test_fault_metric_has_explicit_population(self):
        metric = self.evaluate().metrics["fault_experiments"]
        self.assertEqual(metric, {"safe": 3, "required": 3})

    def test_report_declares_limitations(self):
        report = self.evaluate()
        self.assertTrue(any("does not authorize release" in item for item in report.limitations))
        self.assertGreaterEqual(len(report.limitations), 3)

    def test_report_is_bound_to_specification_revision(self):
        self.assertEqual(self.evaluate().specification_revision, "CLASSIFICATION-SPEC@7")

    def test_report_id_is_deterministic_for_same_evidence(self):
        record = evidence_for(self.plane, self.subject)
        self.assertEqual(self.evaluate(record).report_id, self.evaluate(record).report_id)

    def test_subject_tamper_is_rejected(self):
        self.assertEqual(demonstrate_subject_tamper(SCENARIO), "SUBJECT_AUTHENTICITY_UNVERIFIED")

    def test_all_golden_scenarios_match(self):
        results = run_golden(SCENARIO)
        self.assertEqual(len(results), 12)
        self.assertTrue(all(item["passed"] for item in results))

    def test_evaluation_has_exact_populations(self):
        evaluation = run_evaluation(SCENARIO)
        metric = evaluation["metrics"]["exact_decision_accuracy"]
        self.assertEqual(metric, {"numerator": 24, "denominator": 24, "value": 1.0})

    def test_evaluation_reports_unsafe_recall(self):
        metric = run_evaluation(SCENARIO)["metrics"]["unsafe_case_recall"]
        self.assertEqual(metric, {"numerator": 8, "denominator": 8, "value": 1.0})

    def test_reference_run_is_reproducible(self):
        result = run_reference(SCENARIO)
        self.assertTrue(result["golden_passed"])
        self.assertEqual(result["course"], 27)

    def test_policy_and_contract_are_machine_readable(self):
        self.assertEqual(json.loads((SCENARIO / "quality-policy.json").read_text())["policy_version"], "QUALITY-POLICY@1")
        self.assertEqual(json.loads((SCENARIO / "contracts/quality-report.schema.json").read_text())["type"], "object")

    def test_every_required_kind_is_traced(self):
        expected = {
            (item["id"], kind)
            for item in self.plane.policy["requirements"]
            for kind in item["required_kinds"]
        }
        observed = {
            (requirement_id, case["kind"])
            for case in passing_cases()
            for requirement_id in case["requirement_ids"]
        }
        self.assertEqual(expected, observed)

    def test_golden_registry_is_stable(self):
        self.assertEqual(
            set(GOLDEN),
            {
                "passing", "candidate-only", "forged", "wrong-subject", "stale-suite",
                "failed-test", "missing-negative", "surviving-mutant", "flaky",
                "unsafe-failure", "missing-failure", "unknown-requirement",
            },
        )

    def test_subject_digest_changes_with_spec_revision(self):
        changed = replace(self.subject, specification_revision="CLASSIFICATION-SPEC@8")
        self.assertNotEqual(digest_payload(self.subject.payload()), digest_payload(changed.payload()))


if __name__ == "__main__":
    unittest.main()
