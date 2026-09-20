from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB_PATH = ROOT / "curriculum" / "beginner" / "03-the-specification-hierarchy" / "lab.py"
SPEC = importlib.util.spec_from_file_location("course_03_lab", LAB_PATH)
assert SPEC and SPEC.loader
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)


class ScenarioMixin:
    def setUp(self):
        self.change, self.requirements, self.exceptions = LAB.load_scenario()

    def requirement(self, requirement_id):
        return next(item for item in self.requirements if item.id == requirement_id)


class ApplicabilityTests(ScenarioMixin, unittest.TestCase):
    def test_payment_control_is_not_applicable_without_card_data(self):
        decision = LAB.evaluate_applicability(self.requirement("PCI-002"), self.change)
        self.assertIs(decision.result, LAB.Applicability.NOT_APPLICABLE)
        self.assertIn("SCOPE_MISMATCH_DATA_KIND", decision.reason_codes)

    def test_missing_classification_is_uncertain_not_not_applicable(self):
        change = replace(
            self.change,
            facts=tuple(
                fact for fact in self.change.facts if fact.field != "data_classification"
            ),
        )
        decision = LAB.evaluate_applicability(self.requirement("PRIV-018"), change)
        self.assertIs(decision.result, LAB.Applicability.UNCERTAIN)
        self.assertIn("SCOPE_UNKNOWN_DATA_CLASSIFICATION", decision.reason_codes)

    def test_superseded_project_record_is_retained_but_not_inherited(self):
        decision = LAB.evaluate_applicability(self.requirement("ARCH-004"), self.change)
        self.assertIs(decision.result, LAB.Applicability.NOT_APPLICABLE)
        self.assertEqual(decision.reason_codes, ("STATUS_SUPERSEDED",))

    def test_stale_active_source_requires_clarification(self):
        stale = replace(self.requirement("ARCH-004"), status=LAB.ArtifactStatus.ACTIVE)
        decision = LAB.evaluate_applicability(stale, self.change)
        self.assertIs(decision.result, LAB.Applicability.UNCERTAIN)
        self.assertEqual(decision.reason_codes, ("SOURCE_REVIEW_OVERDUE",))

    def test_ended_effective_period_is_not_applicable_not_stale(self):
        ended = replace(
            self.requirement("PRIV-018"),
            effective_until=date(2026, 9, 19),
            review_due=None,
        )
        decision = LAB.evaluate_applicability(ended, self.change)
        self.assertIs(decision.result, LAB.Applicability.NOT_APPLICABLE)
        self.assertEqual(
            decision.reason_codes, ("REQUIREMENT_EFFECTIVE_PERIOD_ENDED",)
        )

    def test_scope_rules_are_all_and_allowed_values_are_any(self):
        confidential = replace(
            self.change,
            facts=tuple(
                replace(fact, values=("confidential",))
                if fact.field == "data_classification"
                else fact
                for fact in self.change.facts
            ),
        )
        decision = LAB.evaluate_applicability(self.requirement("PRIV-018"), confidential)
        self.assertIs(decision.result, LAB.Applicability.APPLICABLE)

    def test_false_conjunct_with_an_unknown_is_not_applicable(self):
        development_facts = tuple(
            replace(fact, values=("development",))
            if fact.field == "environment"
            else fact
            for fact in self.change.facts
            if fact.field != "data_classification"
        )
        development = replace(self.change, facts=development_facts)
        decision = LAB.evaluate_applicability(self.requirement("PRIV-018"), development)
        self.assertIs(decision.result, LAB.Applicability.NOT_APPLICABLE)
        self.assertIn("SCOPE_MISMATCH_ENVIRONMENT", decision.reason_codes)
        self.assertIn("SCOPE_UNKNOWN_DATA_CLASSIFICATION", decision.reason_codes)

    def test_applicability_preserves_evidence_ids(self):
        decision = LAB.evaluate_applicability(self.requirement("PRIV-018"), self.change)
        self.assertIs(decision.result, LAB.Applicability.APPLICABLE)
        self.assertEqual(
            set(decision.evidence_ids),
            {
                "DATA-CLASS-019",
                "DATA-RESIDENCY-ASSESSMENT-004",
                "DEPLOYMENT-ARCH-002",
            },
        )


class ResolutionTests(ScenarioMixin, unittest.TestCase):
    def test_reference_scenario_is_ready(self):
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, self.exceptions
        )
        self.assertIs(report.gate, LAB.Gate.READY)
        self.assertEqual(len(report.effective_controls), 9)
        self.assertEqual(report.conflicts, ())

    def test_different_retention_resources_do_not_conflict(self):
        requirements = tuple(
            item for item in self.requirements if item.id != "PRIV-031"
        )
        report = LAB.resolve_effective_specification(self.change, requirements)
        self.assertIs(report.gate, LAB.Gate.READY)
        retention_resources = {
            item.resource
            for item in report.effective_controls
            if item.control == "retention_days"
        }
        self.assertEqual(
            retention_resources,
            {"intermediate_model_interaction", "final_approved_broker_communication"},
        )

    def test_without_exception_same_resource_retention_conflict_blocks(self):
        report = LAB.resolve_effective_specification(self.change, self.requirements)
        self.assertIs(report.gate, LAB.Gate.STOP)
        self.assertEqual(len(report.conflicts), 1)
        self.assertEqual(
            set(report.conflicts[0].requirement_ids), {"PRIV-031", "RET-017"}
        )
        self.assertEqual(
            report.conflicts[0].resource, "final_approved_broker_communication"
        )

    def test_scoped_exception_preserves_policy_and_conditions(self):
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, self.exceptions
        )
        retention = next(
            item
            for item in report.effective_controls
            if item.control == "retention_days"
            and item.resource == "final_approved_broker_communication"
        )
        self.assertEqual(retention.expected, "2555")
        self.assertEqual(set(retention.requirement_ids), {"PRIV-031", "RET-017"})
        self.assertEqual(
            set(retention.base_expectations), {"PRIV-031=30", "RET-017=2555"}
        )
        self.assertEqual(retention.exception_ids, ("EXC-009",))
        self.assertEqual(
            retention.related_unaffected_obligation_ids, ("PRIV-030",)
        )
        self.assertEqual(len(retention.conditions), 4)

    def test_related_unaffected_obligations_are_optional_traceability(self):
        exception = replace(
            self.exceptions[0], related_unaffected_obligation_ids=()
        )
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, (exception,)
        )
        self.assertIs(report.gate, LAB.Gate.READY)
        retention = next(
            item
            for item in report.effective_controls
            if item.control == "retention_days"
            and item.resource == "final_approved_broker_communication"
        )
        self.assertEqual(retention.related_unaffected_obligation_ids, ())

    def test_expired_exception_cannot_resolve_conflict(self):
        expired = replace(self.exceptions[0], expires_on=date(2026, 9, 19))
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, (expired,)
        )
        self.assertIs(report.gate, LAB.Gate.STOP)
        self.assertIn("EXCEPTION_EXPIRED", {item.code for item in report.findings})
        self.assertEqual(len(report.conflicts), 1)

    def test_exception_outside_change_scope_does_not_apply(self):
        other_change = replace(self.exceptions[0], change_ids=("AI-OTHER",))
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, (other_change,)
        )
        self.assertIs(report.gate, LAB.Gate.STOP)
        self.assertEqual(
            report.exception_decisions[0].disposition,
            LAB.ExceptionDisposition.NOT_APPLICABLE,
        )

    def test_exception_cannot_modify_a_different_resource(self):
        wrong_resource = replace(
            self.exceptions[0], resources=("intermediate_model_interaction",)
        )
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, (wrong_resource,)
        )
        self.assertIs(report.gate, LAB.Gate.STOP)
        self.assertIn(
            "EXCEPTION_RESOURCE_MISMATCH", {item.code for item in report.findings}
        )

    def test_informal_specific_ticket_does_not_override_platform_authority(self):
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, self.exceptions
        )
        resolution = next(
            item for item in report.precedence if item.control == "outbound_email_provider"
        )
        self.assertEqual(resolution.selected_requirement_ids, ("MSG-004",))
        self.assertEqual(resolution.rejected_requirement_ids, ("TICKET-MSG-001",))
        self.assertEqual(
            resolution.reason_code,
            "HIGHER_AUTHORITY_WINS_NOT_GREATER_SPECIFICITY",
        )

    def test_competing_authority_domains_stop_instead_of_using_global_rank(self):
        ticket = self.requirement("TICKET-MSG-001")
        conflicting_domain = replace(ticket, authority_domain="product_delivery")
        requirements = tuple(
            conflicting_domain if item.id == ticket.id else item
            for item in self.requirements
        )
        report = LAB.resolve_effective_specification(
            self.change, requirements, self.exceptions
        )
        self.assertIs(report.gate, LAB.Gate.STOP)
        self.assertIn(
            "REQ_AUTHORITY_DOMAIN_COLLISION",
            {item.code for item in report.findings},
        )

    def test_incomplete_provenance_stops_resolution(self):
        privacy = self.requirement("PRIV-018")
        broken = replace(
            privacy,
            source=replace(privacy.source, revision=""),
        )
        requirements = tuple(
            broken if item.id == privacy.id else item for item in self.requirements
        )
        report = LAB.resolve_effective_specification(
            self.change, requirements, self.exceptions
        )
        self.assertIs(report.gate, LAB.Gate.STOP)
        self.assertIn(
            "REQ_PROVENANCE_INCOMPLETE", {item.code for item in report.findings}
        )


class ContextAndMetricTests(ScenarioMixin, unittest.TestCase):
    def test_agent_context_keeps_ids_sources_and_exception_conditions(self):
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, self.exceptions
        )
        context = LAB.compose_agent_context(report, self.requirements)
        self.assertIn("[PRIV-018 | mandatory | enterprise-policy:", context)
        self.assertIn("exception = EXC-009", context)
        self.assertIn("base_obligations = PRIV-031=30; RET-017=2555", context)
        self.assertIn("related_unaffected_obligation = PRIV-030", context)
        self.assertIn("applicability_evidence = DATA-CLASS-019", context)
        self.assertIn("not authenticated in this lab", context)
        self.assertIn("delete intermediate model interactions after 30 days", context)
        self.assertNotIn("PCI-002", context)
        self.assertNotIn("ARCH-004", context)

    def test_agent_context_is_not_produced_for_blocked_resolution(self):
        report = LAB.resolve_effective_specification(self.change, self.requirements)
        with self.assertRaises(ValueError):
            LAB.compose_agent_context(report, self.requirements)

    def test_naive_baseline_includes_irrelevant_and_superseded_statements(self):
        baseline = LAB.naive_concatenation(self.requirements)
        self.assertEqual(len(baseline), 14)
        self.assertTrue(any("Payment-card" in item for item in baseline))
        self.assertTrue(any("us-east-1" in item for item in baseline))

    def test_metrics_publish_explicit_applicability_denominators(self):
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, self.exceptions
        )
        metrics = LAB.resolution_metrics(report, self.requirements)
        self.assertEqual(metrics["candidate_requirements"], 14)
        self.assertEqual(
            metrics["applicability"],
            {"applicable": 12, "not_applicable": 2, "uncertain": 0},
        )
        self.assertEqual(
            metrics["provenance_completeness"],
            {"covered": 14, "total": 14, "percent": 100.0},
        )

    def test_context_selection_recall_exposes_missed_applicable_policy(self):
        report = LAB.resolve_effective_specification(
            self.change, self.requirements, self.exceptions
        )
        gold = {
            item.requirement_id
            for item in report.decisions
            if item.result is LAB.Applicability.APPLICABLE
        }
        selected = {item.id for item in self.requirements if item.id != "AI-012"}
        metrics = LAB.context_selection_metrics(gold, selected)
        self.assertEqual(metrics["true_positive"], 11)
        self.assertEqual(metrics["selected_total"], 13)
        self.assertEqual(metrics["gold_applicable_total"], 12)
        self.assertEqual(metrics["recall_percent"], 91.7)
        self.assertEqual(metrics["missed_applicable_ids"], ("AI-012",))

    def test_context_selection_metrics_do_not_invent_empty_denominators(self):
        metrics = LAB.context_selection_metrics((), ())
        self.assertIsNone(metrics["precision_percent"])
        self.assertIsNone(metrics["recall_percent"])


if __name__ == "__main__":
    unittest.main()
