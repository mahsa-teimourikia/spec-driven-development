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

from review_app.control_plane import REVIEWER_GRANTS  # noqa: E402
from review_app.git_harness import TrustedGitHarness  # noqa: E402
from review_app.review_engine import ReviewerGrant, ReviewEngine  # noqa: E402
from review_app.simulation import (  # noqa: E402
    NOW, approval, ci_evidence, conformance_checks, evaluate, evaluation_checks,
    git_backed_experiments, make_subject, reference_assessment, reference_candidate,
    strategy_comparison,
)


class Course22Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate, cls.subject, cls.decision = reference_assessment(SCENARIO)
        cls.approval = approval(cls.subject, cls.candidate, "implementation")
        cls.evidence = ci_evidence(cls.subject, cls.candidate)
        cls.experiments = git_backed_experiments(SCENARIO)

    def codes(self, decision):
        return {finding.code for finding in decision.findings}

    def test_reference_uses_full_git_shas_and_ancestry(self):
        self.assertEqual((len(self.candidate.base_commit), len(self.candidate.head_commit)), (40, 40))
        self.assertTrue(self.candidate.base_is_ancestor)

    def test_diff_is_derived_from_real_git(self):
        self.assertEqual(set(self.candidate.changed_paths), {"src/classifier.py", "tests/test_classifier.py"})

    def test_reference_stops_at_merge_review_eligibility(self):
        self.assertEqual(self.decision.state, "ELIGIBLE_FOR_MERGE_REVIEW")
        self.assertFalse(self.decision.merge_authorized or self.decision.deployment_authorized or self.decision.release_authorized)

    def test_protected_acceptance_runner_executes_exact_head(self):
        self.assertEqual(self.evidence.result, "PASS")
        self.assertEqual(self.evidence.execution_id, f"RUN-{self.subject.head_commit[:12]}")
        self.assertTrue(self.evidence.protected_test_digest.startswith("sha256:"))

    def test_reference_contributor_test_is_not_placeholder(self):
        self.assertNotIn("assert True", self.candidate.blobs["tests/test_classifier.py"])
        self.assertIn("confidence=0.98", self.candidate.blobs["tests/test_classifier.py"])

    def test_bad_implementation_with_placeholder_test_fails_protected_ci(self):
        candidate = TrustedGitHarness().create_candidate("ai-service", {
            "src/classifier.py": "def route(ambiguous: bool, confidence: float = 0.0) -> str:\n    return 'straight_through'\n",
            "tests/test_classifier.py": "def test_nothing():\n    assert True\n",
        })
        subject = make_subject(SCENARIO, candidate)
        evidence = ci_evidence(subject, candidate)
        decision = evaluate(subject, candidate, [approval(subject, candidate, "implementation")], [evidence])
        self.assertEqual(evidence.result, "FAIL")
        self.assertIn("EVIDENCE_RESULT_INVALID", self.codes(decision))

    def test_candidate_cannot_register_forged_approval(self):
        forged = replace(self.approval, approval_id="APR-FORGED")
        decision = evaluate(self.subject, self.candidate, [forged], [self.evidence])
        self.assertIn("APPROVAL_RECORD_UNVERIFIED", self.codes(decision))

    def test_candidate_cannot_register_forged_evidence(self):
        forged = replace(self.evidence, evidence_id="EVID-FORGED", result_digest=ReviewEngine.digest("PASS"))
        decision = evaluate(self.subject, self.candidate, [self.approval], [forged])
        self.assertIn("EVIDENCE_RECORD_UNVERIFIED", self.codes(decision))

    def test_future_approval_is_rejected(self):
        future = replace(self.approval, issued_at=NOW + timedelta(minutes=1))
        decision = evaluate(self.subject, self.candidate, [future], [self.evidence], approval_registry={future.approval_id: future})
        self.assertIn("APPROVAL_NOT_YET_VALID", self.codes(decision))

    def test_expired_approval_is_rejected(self):
        expired = replace(self.approval, expires_at=NOW - timedelta(seconds=1))
        decision = evaluate(self.subject, self.candidate, [expired], [self.evidence], approval_registry={expired.approval_id: expired})
        self.assertIn("STALE_REVIEW_APPROVAL", self.codes(decision))

    def test_resource_scoped_grant_is_required(self):
        wrong_grant = ReviewerGrant(self.approval.reviewer, self.approval.role, "repository:other", self.approval.decision)
        decision = evaluate(self.subject, self.candidate, [self.approval], [self.evidence], grants=(wrong_grant,))
        self.assertIn("REVIEWER_AUTHORITY_UNVERIFIED", self.codes(decision))

    def test_authoritative_spec_digest_is_resolved_independently(self):
        forged = replace(self.subject, specification_digest=ReviewEngine.digest("candidate-selected"))
        decision = evaluate(forged, self.candidate, [], [])
        self.assertIn("AUTHORITATIVE_REVISION_MISMATCH", self.codes(decision))

    def test_candidate_cannot_widen_work_unit(self):
        widened = replace(self.subject, allowed_paths=("src", "tests", "infra"))
        decision = evaluate(widened, self.candidate, [self.approval], [self.evidence])
        self.assertIn("AWU_SCOPE_ESCALATION_REQUESTED", self.codes(decision))

    def test_new_file_under_protected_directory_requires_owner(self):
        self.assertTrue(self.experiments["unauthorized_spec_change"])
        self.assertTrue(self.experiments["contract_owner_missing"])

    def test_rename_checks_source_and_destination(self):
        candidate = TrustedGitHarness().create_candidate(
            "ai-service", {},
            baseline_files={"specifications/approved.json": "{}\n", "src/classifier.py": "def route(ambiguous, confidence=0): return 'review' if ambiguous else 'straight_through'\n"},
            renames={"specifications/approved.json": "src/approved.json"},
        )
        subject = make_subject(SCENARIO, candidate, allowed_paths=("specifications",), work_unit="WU-SPEC")
        decision = evaluate(subject, candidate, [], [ci_evidence(subject, candidate)])
        self.assertEqual(set(candidate.changed_paths), {"specifications/approved.json", "src/approved.json"})
        self.assertIn("AWU_SCOPE_VIOLATION", self.codes(decision))
        self.assertIn("UNAUTHORIZED_SPEC_CHANGE", self.codes(decision))

    def test_deleted_protected_path_still_requires_owner(self):
        candidate = TrustedGitHarness().create_candidate(
            "ai-service", {"tests/protected/test_acceptance.py": None},
            baseline_files={"tests/protected/test_acceptance.py": "assert True\n", "src/classifier.py": "def route(ambiguous, confidence=0): return 'review' if ambiguous else 'straight_through'\n"},
        )
        subject = make_subject(SCENARIO, candidate, allowed_paths=("tests/protected",), work_unit="WU-ORACLE")
        decision = evaluate(subject, candidate, [], [ci_evidence(subject, candidate)])
        self.assertIn("TEST_ORACLE_CHANGED", self.codes(decision))

    def test_longest_prefix_selects_acceptance_owner(self):
        candidate = TrustedGitHarness().create_candidate("ai-service", {"tests/protected/new.py": "assert True\n"})
        subject = make_subject(SCENARIO, candidate, allowed_paths=("tests/protected",), work_unit="WU-ORACLE")
        protected = approval(subject, candidate, "acceptance_oracle")
        decision = evaluate(subject, candidate, [protected], [ci_evidence(subject, candidate)])
        self.assertEqual(decision.required_scopes, ("acceptance_oracle",))

    def test_untrusted_producer_is_rejected_even_if_registered(self):
        record = replace(self.evidence, producer="agent-reported-ci")
        decision = evaluate(self.subject, self.candidate, [self.approval], [record], evidence_registry={record.evidence_id: record})
        self.assertIn("UNTRUSTED_EVIDENCE_PRODUCER", self.codes(decision))

    def test_review_failures_cover_core_experiments(self):
        self.assertTrue(all(self.experiments.values()))
        self.assertEqual(len(self.experiments), 10)

    def test_stale_approval_experiment(self):
        self.assertTrue(self.experiments["stale_approval"])

    def test_acceptance_oracle_change_experiment(self):
        self.assertTrue(self.experiments["test_oracle_changed"])

    def test_merge_group_conflict_experiment(self):
        self.assertTrue(self.experiments["merge_group_conflict"])

    def test_evidence_subject_mismatch_experiment(self):
        self.assertTrue(self.experiments["evidence_subject_mismatch"])

    def test_self_approval_experiment(self):
        self.assertTrue(self.experiments["self_approval_denied"])

    def test_conformance_population_is_twelve(self):
        checks = conformance_checks(SCENARIO)
        self.assertEqual((len(checks), all(checks.values())), (12, True))

    def test_evaluation_population_is_twenty_eight(self):
        checks = evaluation_checks(SCENARIO)
        self.assertEqual((len(checks), all(checks.values())), (28, True))

    def test_strategy_comparison_is_event_based_and_synthetic(self):
        comparison = strategy_comparison()
        self.assertTrue(all(item["model"] == "deterministic event simulation" for item in comparison.values()))
        self.assertTrue(all(item["source"] == "synthetic teaching workload" for item in comparison.values()))
        self.assertTrue(all(item["events"] for item in comparison.values()))

    def test_strategy_lead_time_is_computed_from_events(self):
        for item in strategy_comparison().values():
            self.assertEqual(item["lead_time_hours"], max(event["completed"] for event in item["events"]))

    def test_parallel_latency_is_not_total_review_effort(self):
        parallel = strategy_comparison()["parallel_repositories"]
        self.assertNotEqual(parallel["lead_time_hours"], parallel["review_effort_hours"])

    def test_lab_report_is_complete(self):
        report = lab.build_report()
        self.assertEqual(report["course_validation"]["status"], "PASS")
        self.assertEqual((report["conformance"]["passed"], report["evaluation"]["passed"], report["git_experiments"]["passed"]), (12, 28, 10))

    def test_stored_evidence_matches_deterministic_subject(self):
        stored = json.loads((SCENARIO / "evidence/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["candidate_assessment"]["head_commit"], self.subject.head_commit)

    def test_reference_handoff_preserves_non_authorities(self):
        reference = json.loads((SCENARIO / "reference/review-package.json").read_text(encoding="utf-8"))
        self.assertEqual(reference["state"], "ELIGIBLE_FOR_MERGE_REVIEW")
        self.assertFalse(any(reference["non_authorities"].values()))

    def test_starter_retains_six_learner_decisions(self):
        source = (SCENARIO / "workshop/starter/review-package.json").read_text(encoding="utf-8")
        self.assertEqual(source.count("TODO:"), 6)

    def test_scenario_labels_are_not_evaluator_inputs(self):
        source = (SCENARIO / "review_app/simulation.py").read_text(encoding="utf-8")
        self.assertNotIn("scenarios/", source)
        self.assertNotIn("expected_finding", source)

    def test_notebook_imports_reusable_module(self):
        notebook = json.loads((SCENARIO / "pr_review_strategies.ipynb").read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook["cells"])
        self.assertIn("from review_app.simulation import", source)
        self.assertIn("run_reference(ROOT)", source)

    def test_merge_group_uses_real_git(self):
        self.assertTrue(TrustedGitHarness().merge_group_conflicts())


if __name__ == "__main__":
    unittest.main()
