"""Tests for Course 04 requirement ownership and propagation."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "beginner" / "04-company-project-feature-requirements"
LAB_PATH = LESSON / "lab.py"
SPEC = importlib.util.spec_from_file_location("course04_lab", LAB_PATH)
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course04ResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = lab.load_scenario()
        cls.requirements = {item.id: item for item in cls.scenario["requirements"]}

    def test_reference_scenario_is_ready(self) -> None:
        report = lab.resolve_project()
        self.assertEqual(report.gate, lab.Gate.READY)
        self.assertEqual(report.findings, ())
        self.assertEqual({item.id for item in report.applicable}, {"AI-007", "AI-030", "AI-041", "SEC-100", "UW-041"})

    def test_manifest_cannot_select_missing_authority_artifacts(self) -> None:
        manifest = replace(
            self.scenario["manifest"],
            policy_sources=self.scenario["manifest"].policy_sources + ("enterprise/missing",),
            specialization_ids=("ARCH-404",),
            exception_ids=("EXC-404",),
        )
        findings = lab.validate_manifest(
            manifest,
            self.scenario["requirements"],
            self.scenario["specializations"],
            self.scenario["exceptions"],
        )
        self.assertEqual(
            {item.code for item in findings},
            {"POLICY_SOURCE_EMPTY", "SPECIALIZATION_SELECTION_MISSING", "EXCEPTION_SELECTION_MISSING"},
        )

    def test_irrelevant_payment_control_is_not_applicable(self) -> None:
        report = lab.resolve_project()
        decision = next(item for item in report.decisions if item.requirement_id == "SEC-220")
        self.assertEqual(decision.result, lab.Applicability.NOT_APPLICABLE)
        self.assertIn("SCOPE_MISMATCH_DATA_KIND", decision.reason_codes)

    def test_weakening_specialization_is_rejected(self) -> None:
        unsafe = lab.load_specialization(lab.SCENARIO_ROOT / "project" / "architecture" / "ARCH-032-weakening.json")
        findings = lab.validate_specialization(unsafe, self.requirements[unsafe.parent_requirement_id])
        codes = {item.code for item in findings}
        self.assertIn("SPECIALIZATION_FIELD_NOT_DELEGATED", codes)
        self.assertIn("SPECIALIZATION_WEAKENS_PARENT", codes)

    def test_stale_parent_revision_requires_review(self) -> None:
        specialization = self.scenario["specializations"][0]
        stale = replace(specialization, parent_revision="obsolete-revision")
        findings = lab.validate_specialization(stale, self.requirements["AI-030"])
        self.assertIn("SPECIALIZATION_PARENT_STALE", {item.code for item in findings})

    def test_agent_cannot_write_policy_or_exception_sources(self) -> None:
        boundary = self.scenario["boundary"]
        findings = lab.validate_write_paths(
            ("catalog/enterprise/ai-governance/AI-030.json", "exceptions/EXC-014.json"),
            boundary,
        )
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(item.code == "SCOPE_EXPANSION_REQUIRED" for item in findings))

    def test_agent_instruction_cannot_weaken_policy(self) -> None:
        findings = lab.validate_agent_instruction(
            "AGENT-UNSAFE",
            {"human_review": "optional"},
            lab.resolve_project().applicable,
        )
        self.assertEqual([item.code for item in findings], ["AGENT_INSTRUCTION_EXCEEDS_AUTHORITY"])

    def test_selected_exception_is_versioned_scoped_and_independently_approved(self) -> None:
        report = lab.resolve_project()
        self.assertEqual([item.id for item in report.exceptions], ["EXC-014"])
        exception = report.exceptions[0]
        self.assertNotEqual(exception.requester, exception.approver)
        self.assertEqual(exception.requirement_revision, self.requirements["AI-007"].source.revision)
        self.assertEqual(exception.modification.field, "model_gateway")
        self.assertTrue(exception.conditions)

    def test_self_approved_and_expired_exception_stops(self) -> None:
        exception = self.scenario["exceptions"][0]
        invalid = replace(exception, approver=exception.requester, expires_on=date(2026, 1, 1))
        findings = lab.validate_exception(
            invalid,
            self.requirements,
            "underwriter-assistant",
            date(2026, 9, 20),
        )
        codes = {item.code for item in findings}
        self.assertIn("EXCEPTION_SELF_APPROVED", codes)
        self.assertIn("EXCEPTION_APPROVER_UNAUTHORIZED", codes)
        self.assertIn("EXCEPTION_EXPIRED", codes)

    def test_central_change_reaches_direct_and_transitive_consumers(self) -> None:
        old = self.requirements["AI-030"]
        new = lab.load_requirement(lab.SCENARIO_ROOT / "updates" / "AI-030-v4.json")
        specialization = self.scenario["specializations"][0]
        graph = self.scenario["graph"]
        artifact_types = {"ARCH-031": "project", "REQ-REN-004": "feature", "ReviewServiceAdapter": "implementation", "TEST-REVIEW-004": "evidence"}
        impact = lab.analyze_impact(old, new, graph, artifact_types, specialization)
        impacted_ids = {item.artifact_id for item in impact.impacted}
        self.assertTrue({"ARCH-031", "REQ-REN-004", "ReviewServiceAdapter", "TEST-REVIEW-004"}.issubset(impacted_ids))
        self.assertTrue(impact.migration_required)

    def test_copied_policy_drift_is_visible(self) -> None:
        finding = lab.copied_policy_drift(
            lab.SCENARIO_ROOT / "project" / "copied-policy" / "AI-030.json",
            self.requirements["AI-030"],
        )
        self.assertIsNotNone(finding)
        self.assertEqual(finding.code, "POLICY_SOURCE_STALE")

    def test_context_and_metrics_preserve_denominators(self) -> None:
        report = lab.resolve_project()
        metrics = lab.evaluation_metrics(report, self.scenario["manifest"], self.scenario["graph"])
        self.assertEqual(metrics["ownership_completeness"], {"covered": 5, "total": 5, "percent": 100.0})
        self.assertEqual(metrics["machine_enforcement_coverage"], {"covered": 5, "total": 5, "percent": 100.0})
        self.assertEqual(metrics["valid_exception_coverage"], {"covered": 1, "total": 1, "percent": 100.0})
        context = lab.compose_agent_context(report)
        self.assertIn("enterprise-policy:ai-governance/AI-030.json@3.0-training#ai030v3-training", context)
        self.assertIn("exception = EXC-014", context)
        self.assertIn("modify:model_gateway=legacy_enterprise_gateway_proxy", context)

    def test_exception_changes_effective_context_digest(self) -> None:
        report = lab.resolve_project()
        without_exception = lab._context_material(
            report.applicable,
            report.specializations,
            (),
        )
        with_exception = lab._context_material(
            report.applicable,
            report.specializations,
            report.exceptions,
        )
        self.assertNotEqual(without_exception, with_exception)

    def test_release_context_preserves_exception_evidence_and_limitations(self) -> None:
        snapshot = lab.release_context(lab.resolve_project())
        self.assertEqual(snapshot["exceptions"][0]["id"], "EXC-014")
        self.assertEqual(snapshot["exceptions"][0]["scope"]["feature_ids"], ["REQ-REN-001"])
        ai_gateway = next(
            item for item in snapshot["governing_requirements"] if item["id"] == "AI-007"
        )
        self.assertEqual(ai_gateway["disposition"], "excepted")
        self.assertIn("GATEWAY-TELEMETRY-007", snapshot["evidence"])
        self.assertTrue(snapshot["limitations"])

    def test_runtime_evidence_distinguishes_implementation_from_effectiveness(self) -> None:
        evidence = json.loads(
            (
                lab.SCENARIO_ROOT
                / "reference"
                / "runtime-evidence.json"
            ).read_text(encoding="utf-8")
        )
        effective = lab.runtime_control_effectiveness(evidence)
        self.assertEqual(effective["status"], "effective_in_observed_window")
        self.assertEqual(
            effective["review_receipt_coverage"],
            {"covered": 4211, "total": 4211, "percent": 100.0},
        )
        gap = lab.runtime_control_effectiveness(
            {**evidence, "review_receipts": 4200, "authorized_review_receipts": 4199}
        )
        self.assertEqual(gap["status"], "control_gap_detected")
        no_observations = lab.runtime_control_effectiveness(
            {
                **evidence,
                "consequential_recommendations": 0,
                "review_receipts": 0,
                "authorized_review_receipts": 0,
            }
        )
        self.assertEqual(no_observations["status"], "insufficient_observations")

    def test_agent_signals_are_counts_not_a_composite_score(self) -> None:
        metrics = lab.agent_behavior_metrics(
            (
                {"type": "clarification_request"},
                {"type": "scope_expansion_request"},
                {"type": "scope_expansion_request"},
                {"type": "new_signal"},
            )
        )
        self.assertEqual(metrics["event_total"], 4)
        self.assertEqual(metrics["by_type"]["scope_expansion_request"], 2)
        self.assertEqual(metrics["unknown_event_types"], 1)
        self.assertNotIn("score", metrics)

    def test_metric_helpers_do_not_hide_misses(self) -> None:
        impact = lab.impact_recall(["ARCH-031"], ["ARCH-031", "REQ-REN-004"])
        self.assertEqual(impact["recall_percent"], 50.0)
        self.assertEqual(impact["missed_ids"], ("REQ-REN-004",))
        location = lab.location_accuracy({"AI-030": "enterprise"}, {"AI-030": "enterprise", "UW-041": "domain"})
        self.assertEqual(location, {"correct": 1, "total": 2, "percent": 50.0})


if __name__ == "__main__":
    unittest.main()
