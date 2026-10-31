"""Focused verification for Course 22 pull-request review strategy."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum/intermediate/12-pull-request-review-strategies-agentic-sdd"
SCENARIO = LESSON / "northstar-pr-review"
sys.path.insert(0, str(SCENARIO))
SPEC = importlib.util.spec_from_file_location("course22_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)

from review_app.git_harness import TrustedGitHarness  # noqa: E402
from review_app.review_engine import ReviewEngine  # noqa: E402
from review_app.simulation import (  # noqa: E402
    NOW,
    TRUSTED_REVIEWERS,
    TRUSTED_PR_AUTHORS,
    approval,
    ci_evidence,
    conformance_checks,
    evaluation_checks,
    evaluate,
    git_backed_experiments,
    make_subject,
    reference_assessment,
    reference_candidate,
    strategy_comparison,
)


class Course22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate, cls.subject, cls.decision = reference_assessment(SCENARIO)
        cls.experiments = git_backed_experiments(SCENARIO)

    def test_reference_uses_full_git_shas(self):
        self.assertEqual(len(self.candidate.base_commit), 40)
        self.assertEqual(len(self.candidate.head_commit), 40)

    def test_reference_base_is_ancestor(self):
        self.assertTrue(self.candidate.base_is_ancestor)

    def test_diff_is_derived_from_real_git(self):
        self.assertEqual(
            set(self.candidate.changed_paths),
            {"src/classifier.py", "tests/test_classifier.py"},
        )

    def test_reference_stops_at_merge_review_eligibility(self):
        self.assertEqual(self.decision.state, "ELIGIBLE_FOR_MERGE_REVIEW")
        self.assertFalse(self.decision.merge_authorized)
        self.assertFalse(self.decision.deployment_authorized)
        self.assertFalse(self.decision.release_authorized)

    def test_review_requires_implementation_scope(self):
        self.assertEqual(self.decision.required_scopes, ("implementation",))

    def test_review_records_exact_evidence(self):
        self.assertEqual(self.decision.evidence_ids, ("EVID-PR-001",))

    def test_unauthorized_specification_change_is_blocked(self):
        self.assertTrue(self.experiments["unauthorized_spec_change"])

    def test_shared_contract_requires_owner(self):
        self.assertTrue(self.experiments["contract_owner_missing"])

    def test_approval_for_earlier_commit_is_stale(self):
        self.assertTrue(self.experiments["stale_approval"])

    def test_protected_acceptance_oracle_cannot_be_weakened(self):
        self.assertTrue(self.experiments["test_oracle_changed"])

    def test_two_green_branches_can_conflict_when_combined(self):
        self.assertTrue(self.experiments["merge_group_conflict"])

    def test_actual_diff_enforces_work_unit_scope(self):
        self.assertTrue(self.experiments["awu_scope_violation"])

    def test_evidence_for_wrong_commit_is_rejected(self):
        self.assertTrue(self.experiments["evidence_subject_mismatch"])

    def test_required_review_cannot_be_omitted(self):
        self.assertTrue(self.experiments["required_review_missing"])

    def test_author_cannot_approve_own_pr(self):
        self.assertTrue(self.experiments["self_approval_denied"])

    def test_review_success_is_not_deployment_approval(self):
        self.assertTrue(self.experiments["deployment_authority_separate"])

    def test_expired_approval_is_rejected(self):
        record = replace(
            approval(self.subject, "implementation", "reviewer-engineering", "engineering_reviewer"),
            expires_at=NOW - timedelta(seconds=1),
        )
        decision = evaluate(self.subject, self.candidate, [record], [ci_evidence(self.subject)])
        self.assertIn("STALE_REVIEW_APPROVAL", {finding.code for finding in decision.findings})

    def test_untrusted_ci_producer_is_rejected(self):
        decision = evaluate(
            self.subject,
            self.candidate,
            [approval(self.subject, "implementation", "reviewer-engineering", "engineering_reviewer")],
            [ci_evidence(self.subject, producer="agent-reported-ci")],
        )
        self.assertIn("UNTRUSTED_EVIDENCE_PRODUCER", {finding.code for finding in decision.findings})

    def test_declared_head_must_match_trusted_git(self):
        mismatched = replace(self.subject, head_commit=self.subject.base_commit)
        decision = evaluate(mismatched, self.candidate, [], [])
        self.assertIn("PR_SUBJECT_MISMATCH", {finding.code for finding in decision.findings})

    def test_approval_role_comes_from_trusted_registry(self):
        forged = approval(self.subject, "implementation", "unknown-reviewer", "engineering_reviewer")
        decision = evaluate(
            self.subject,
            self.candidate,
            [forged],
            [ci_evidence(self.subject)],
        )
        self.assertIn("REVIEWER_AUTHORITY_UNVERIFIED", {finding.code for finding in decision.findings})

    def test_pr_author_is_resolved_from_trusted_application_state(self):
        forged_subject = replace(self.subject, author="reviewer-engineering")
        decision = evaluate(forged_subject, self.candidate, [], [])
        self.assertIn("UNAUTHENTICATED_PR_AUTHOR", {finding.code for finding in decision.findings})

    def test_unregistered_approval_record_is_rejected(self):
        record = approval(self.subject, "implementation", "reviewer-engineering", "engineering_reviewer")
        evidence = ci_evidence(self.subject)
        engine = ReviewEngine(
            TRUSTED_REVIEWERS,
            TRUSTED_PR_AUTHORS,
            {},
            {evidence.evidence_id: evidence},
        )
        decision = engine.evaluate(self.subject, self.candidate, [record], [evidence], now=NOW)
        self.assertIn("APPROVAL_RECORD_UNVERIFIED", {finding.code for finding in decision.findings})

    def test_unregistered_evidence_record_is_rejected(self):
        record = approval(self.subject, "implementation", "reviewer-engineering", "engineering_reviewer")
        evidence = ci_evidence(self.subject)
        engine = ReviewEngine(
            TRUSTED_REVIEWERS,
            TRUSTED_PR_AUTHORS,
            {record.approval_id: record},
            {},
        )
        decision = engine.evaluate(self.subject, self.candidate, [record], [evidence], now=NOW)
        self.assertIn("EVIDENCE_RECORD_UNVERIFIED", {finding.code for finding in decision.findings})

    def test_conformance_population_is_twelve(self):
        checks = conformance_checks(SCENARIO)
        self.assertEqual(len(checks), 12)
        self.assertTrue(all(checks.values()))

    def test_evaluation_population_is_twenty_eight(self):
        checks = evaluation_checks(SCENARIO)
        self.assertEqual(len(checks), 28)
        self.assertTrue(all(checks.values()))

    def test_strategy_values_are_explicitly_synthetic(self):
        comparison = strategy_comparison()
        self.assertTrue(all(item["source"] == "synthetic teaching workload" for item in comparison.values()))

    def test_parallel_latency_is_not_total_review_effort(self):
        parallel = strategy_comparison()["parallel_repositories"]
        self.assertNotEqual(parallel["lead_time_hours"], parallel["review_effort_hours"])

    def test_lab_report_is_complete(self):
        report = lab.build_report()
        self.assertEqual(report["course_validation"]["status"], "PASS")
        self.assertEqual((report["conformance"]["passed"], report["conformance"]["total"]), (12, 12))
        self.assertEqual((report["evaluation"]["passed"], report["evaluation"]["total"]), (28, 28))
        self.assertEqual((report["git_experiments"]["passed"], report["git_experiments"]["total"]), (10, 10))

    def test_stored_evidence_matches_deterministic_subject(self):
        stored = json.loads((SCENARIO / "evidence/manifest.json").read_text(encoding="utf-8"))
        assessment = stored["candidate_assessment"]
        self.assertEqual(assessment["head_commit"], self.subject.head_commit)
        self.assertEqual(assessment["specification_digest"], self.subject.specification_digest)
        self.assertEqual(assessment["contract_digest"], self.subject.contract_digest)

    def test_reference_handoff_preserves_non_authorities(self):
        reference = json.loads((SCENARIO / "reference/review-package.json").read_text(encoding="utf-8"))
        self.assertEqual(reference["state"], "ELIGIBLE_FOR_MERGE_REVIEW")
        self.assertFalse(any(reference["non_authorities"].values()))

    def test_starter_retains_six_learner_decisions(self):
        source = (SCENARIO / "workshop/starter/review-package.json").read_text(encoding="utf-8")
        self.assertEqual(source.count("TODO:"), 6)

    def test_scenario_expected_labels_are_not_evaluator_inputs(self):
        simulation = (SCENARIO / "review_app/simulation.py").read_text(encoding="utf-8")
        self.assertNotIn("scenarios/", simulation)
        self.assertNotIn("expected_finding", simulation)

    def test_notebook_imports_reusable_module(self):
        notebook = json.loads((SCENARIO / "pr_review_strategies.ipynb").read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
        self.assertIn("from review_app.simulation import", source)
        self.assertIn("run_reference(ROOT)", source)

    def test_git_harness_detects_combined_state_not_scenario_name(self):
        self.assertTrue(TrustedGitHarness().merge_group_conflicts())


if __name__ == "__main__":
    unittest.main()
