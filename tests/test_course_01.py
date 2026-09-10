from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAB_PATH = ROOT / "curriculum" / "beginner" / "01-why-agentic-coding-changes-pdlc" / "lab.py"
SPEC = importlib.util.spec_from_file_location("course_01_lab", LAB_PATH)
assert SPEC and SPEC.loader
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)


class ContextCompositionTests(unittest.TestCase):
    def test_enterprise_context_preserves_all_requirements(self):
        context = LAB.compose_context(LAB.enterprise_requirements())
        self.assertEqual(len(context.requirement_ids), 14)
        self.assertEqual(context.conflicts, ())

    def test_higher_authority_control_wins_and_conflict_is_visible(self):
        context = LAB.compose_context(
            LAB.inject_feature_policy_override(LAB.enterprise_requirements())
        )
        self.assertEqual(len(context.conflicts), 1)
        conflict = context.conflicts[0]
        self.assertEqual(conflict.winning_requirement_id, "C-02")
        self.assertEqual(conflict.rejected_requirement_id, "F-99")

    def test_compatible_repetition_preserves_provenance(self):
        requirements = LAB.enterprise_requirements() + (
            LAB.Requirement(
                "F-77",
                LAB.Layer.FEATURE,
                "telemetry",
                "opentelemetry",
                "Use inherited telemetry for this feature.",
            ),
        )
        context = LAB.compose_context(requirements)
        telemetry = next(item for item in context.controls if item.control == "telemetry")
        self.assertEqual(telemetry.source_ids, ("P-01", "F-77"))


class ProposalGateTests(unittest.TestCase):
    def setUp(self):
        self.context = LAB.compose_context(LAB.enterprise_requirements())
        self.boundary = LAB.default_boundary()

    def test_prompt_only_proposal_stops(self):
        report = LAB.evaluate_proposal(
            self.context, LAB.prompt_only_proposal(), self.boundary
        )
        self.assertIs(report.decision, LAB.GateDecision.STOP)
        self.assertTrue(report.autonomy_overreach)
        self.assertTrue(report.boundary_violations)
        self.assertLess(report.requirement_coverage, 1)

    def test_controlled_proposal_needs_human_approval(self):
        report = LAB.evaluate_proposal(
            self.context, LAB.controlled_proposal(self.context), self.boundary
        )
        self.assertIs(report.decision, LAB.GateDecision.REVIEW)
        self.assertIn("approval:missing", report.trace)

    def test_controlled_proposal_passes_after_approval(self):
        report = LAB.evaluate_proposal(
            self.context,
            LAB.controlled_proposal(self.context),
            self.boundary,
            human_approval_granted=True,
        )
        self.assertIs(report.decision, LAB.GateDecision.PASS)
        self.assertEqual(report.requirement_coverage, 1)
        self.assertEqual(report.evidence_coverage, 1)
        self.assertEqual(report.task_traceability, 1)

    def test_context_conflict_stops_an_otherwise_good_proposal(self):
        conflicting = LAB.compose_context(
            LAB.inject_feature_policy_override(LAB.enterprise_requirements())
        )
        report = LAB.evaluate_proposal(
            conflicting,
            LAB.controlled_proposal(conflicting),
            self.boundary,
            human_approval_granted=True,
        )
        self.assertIs(report.decision, LAB.GateDecision.STOP)

    def test_file_budget_is_enforced(self):
        proposal = LAB.controlled_proposal(self.context)
        strict = LAB.ExecutionBoundary(
            allowed_repositories=self.boundary.allowed_repositories,
            allowed_permissions=self.boundary.allowed_permissions,
            max_files_changed=5,
            human_approval_required=False,
        )
        report = LAB.evaluate_proposal(self.context, proposal, strict)
        self.assertIs(report.decision, LAB.GateDecision.STOP)
        self.assertIn("change budget exceeded", report.boundary_violations[0])


class ProportionalWorkflowTests(unittest.TestCase):
    def test_low_risk_reversible_change_routes_directly(self):
        result = LAB.recommend_workflow(LAB.ChangeProfile("copy edit", 0, 0, 1))
        self.assertIs(result.workflow, LAB.Workflow.DIRECT_CHANGE)

    def test_regulated_change_routes_to_specialist_review(self):
        result = LAB.recommend_workflow(
            LAB.ChangeProfile("policy Q&A", 4, 5, 4, True, True, True)
        )
        self.assertIs(result.workflow, LAB.Workflow.FULL_SDD_WITH_SPECIALIST_REVIEW)

    def test_invalid_risk_score_is_rejected(self):
        with self.assertRaises(ValueError):
            LAB.ChangeProfile("invalid", 0, 6, 0)


if __name__ == "__main__":
    unittest.main()
