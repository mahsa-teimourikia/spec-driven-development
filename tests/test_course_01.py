from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAB_PATH = ROOT / "curriculum" / "beginner" / "01-why-agentic-coding-changes-pdlc" / "lab.py"
SPEC = importlib.util.spec_from_file_location("course_01_lab", LAB_PATH)
assert SPEC and SPEC.loader
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)

REPO_LAB_PATH = (
    ROOT
    / "curriculum"
    / "beginner"
    / "01-why-agentic-coding-changes-pdlc"
    / "repo_lab.py"
)
REPO_SPEC = importlib.util.spec_from_file_location("course_01_repo_lab", REPO_LAB_PATH)
assert REPO_SPEC and REPO_SPEC.loader
REPO_LAB = importlib.util.module_from_spec(REPO_SPEC)
sys.modules[REPO_SPEC.name] = REPO_LAB
REPO_SPEC.loader.exec_module(REPO_LAB)


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


class RepositoryLabTests(unittest.TestCase):
    def test_default_context_distinguishes_applicable_policy(self):
        assembly = REPO_LAB.assemble_context(
            REPO_LAB.load_requirements(), REPO_LAB.load_change_context()
        )
        outcomes = {item.requirement_id: item.outcome for item in assembly.decisions}
        self.assertEqual(len(assembly.applicable_ids), 17)
        self.assertIs(outcomes["C-90"], REPO_LAB.Applicability.NOT_APPLICABLE)
        self.assertEqual(assembly.uncertain, ())

    def test_missing_applicability_signal_stops_resolution(self):
        context = REPO_LAB.load_change_context()
        del context["data_classification"]
        assembly = REPO_LAB.assemble_context(REPO_LAB.load_requirements(), context)
        uncertain_ids = {item.requirement_id for item in assembly.uncertain}
        self.assertEqual(uncertain_ids, {"C-02", "C-05"})

    def test_missing_provenance_is_uncertain(self):
        requirement = REPO_LAB.load_requirements()[0]
        incomplete = REPO_LAB.Requirement(
            requirement_id=requirement.requirement_id,
            layer=requirement.layer,
            control=requirement.control,
            expected_value=requirement.expected_value,
            statement=requirement.statement,
            owner="",
            status=requirement.status,
            effective_from=requirement.effective_from,
            mandatory=requirement.mandatory,
            scope=requirement.scope,
            applies_when=requirement.applies_when,
            exceptions=requirement.exceptions,
            source=REPO_LAB.Source(),
        )
        decision = REPO_LAB.decide_applicability(
            incomplete, REPO_LAB.load_change_context()
        )
        self.assertIs(decision.outcome, REPO_LAB.Applicability.UNCERTAIN)
        self.assertIn("missing provenance", decision.reasons[0])

    def test_feature_override_preserves_company_policy_and_records_conflict(self):
        requirements = REPO_LAB.load_requirements() + (
            REPO_LAB.load_experiment_requirement("F-99-public-model-override.json"),
        )
        assembly = REPO_LAB.assemble_context(requirements, REPO_LAB.load_change_context())
        self.assertEqual(len(assembly.conflicts), 1)
        self.assertEqual(assembly.conflicts[0]["winner"], "C-02")
        self.assertEqual(assembly.conflicts[0]["rejected"], "F-99")

    def test_real_candidates_produce_stop_review_and_pass_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            unsafe = REPO_LAB.run_candidate("unsafe", output)
            governed = REPO_LAB.run_candidate("governed", output)
            approved = REPO_LAB.run_candidate(
                "governed", output, approve=True, label="governed-approved"
            )
            self.assertEqual(unsafe["gate"], "STOP")
            self.assertEqual(governed["gate"], "REVIEW")
            self.assertEqual(approved["gate"], "PASS")
            self.assertTrue((output / "unsafe" / "policy-check.json").exists())
            self.assertTrue((output / "governed-approved" / "traceability.json").exists())
            self.assertTrue(unsafe["unverified_risks"])


if __name__ == "__main__":
    unittest.main()
