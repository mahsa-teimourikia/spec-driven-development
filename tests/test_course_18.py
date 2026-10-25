"""Focused verification for Course 18 brownfield development."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "08-brownfield-development-with-agentic-coding-agents"
SCENARIO = LESSON / "northstar-underwriter-modernization"
sys.path.insert(0, str(SCENARIO))

from brownfield_app.contracts import BehaviorRecord, ExecutionContext, Submission  # noqa: E402
from brownfield_app.discovery import required_regression_tests, validate_behavior_records  # noqa: E402
from brownfield_app.governance import (  # noqa: E402
    EXPECTED_REPOSITORY_REVISION,
    EXPECTED_SPECIFICATION_REVISION,
    PROTECTED_TESTS,
    check_v1_semantics,
    evaluate_case,
    select_summary_provider,
)
from brownfield_app.legacy import AISummaryProvider, classify_risk, legacy_v1_response  # noqa: E402
from brownfield_app.migration import ProposalStore  # noqa: E402


class Course18Tests(unittest.TestCase):
    def test_characterization_boundaries(self) -> None:
        self.assertEqual([classify_risk(v) for v in (49, 50, 79, 80)], ["LOW", "MEDIUM", "MEDIUM", "HIGH"])

    def test_high_risk_requires_review(self) -> None:
        response = legacy_v1_response(Submission("SUB-1", 80, ("DOC-1",)))
        self.assertEqual(response["risk_category"], "HIGH")
        self.assertIs(response["review_required"], True)

    def test_semantic_break_is_detected(self) -> None:
        submission = Submission("SUB-1", 90, ("DOC-1",))
        candidate = {"submission_id": "SUB-1", "risk_category": "HIGH", "review_required": False}
        decision = check_v1_semantics(submission, candidate)
        self.assertEqual(decision.state, "BLOCKED")

    def test_ai_proposal_never_authoritative(self) -> None:
        proposal = AISummaryProvider().generate(Submission("SUB-1", 55, ("DOC-1",)))
        self.assertFalse(proposal.authoritative)

    def test_feature_flag_is_not_authorization(self) -> None:
        context = ExecutionContext(
            EXPECTED_REPOSITORY_REVISION,
            EXPECTED_SPECIFICATION_REVISION,
            "observer",
            frozenset({"SUB-1"}),
            frozenset({"ai_risk_summary"}),
            frozenset(),
        )
        provider, decision = select_summary_provider(context, authorized=True)
        self.assertIsNone(provider)
        self.assertEqual(decision.state, "BLOCKED")

    def test_transactional_retry(self) -> None:
        store = ProposalStore()
        proposal = AISummaryProvider().generate(Submission("SUB-1", 55, ("DOC-1",)))
        self.assertTrue(store.migrate(proposal, "legacy@1"))
        self.assertFalse(store.migrate(proposal, "legacy@1"))
        self.assertEqual(store.count(), 1)
        self.assertEqual(store.authoritative_count(), 0)

    def test_unknown_behavior_blocks_retirement(self) -> None:
        result = validate_behavior_records([BehaviorRecord("BEH-1", "UNKNOWN", None, ("TRACE-1",))])
        self.assertEqual(result.state, "BLOCKED")
        self.assertIn("UNKNOWN_BEHAVIOR", {item.code for item in result.findings})

    def test_selective_regression_keeps_protected_invariants(self) -> None:
        selected = required_regression_tests(
            impacted_consumers={"SubmissionAPIv1"},
            mapped_tests={"CHANGED_COMPONENT": {"test_provider"}, "SubmissionAPIv1": {"test_v1"}},
            protected_tests=PROTECTED_TESTS,
        )
        self.assertTrue(PROTECTED_TESTS.issubset(selected))

    def test_shadow_divergence_routes_to_review(self) -> None:
        decision = evaluate_case({
            "repository_revision": EXPECTED_REPOSITORY_REVISION,
            "specification_revision": EXPECTED_SPECIFICATION_REVISION,
            "shadow_divergence": True,
        })
        self.assertEqual(decision.state, "REVIEW_REQUIRED")

    def test_stale_repository_blocks(self) -> None:
        decision = evaluate_case({"repository_revision": "old", "specification_revision": EXPECTED_SPECIFICATION_REVISION})
        self.assertEqual(decision.state, "BLOCKED")

    def test_reference_package_cannot_authorize_release(self) -> None:
        package = json.loads((SCENARIO / "reference" / "modernization-package.json").read_text())
        self.assertFalse(package["merge_authorized"])
        self.assertFalse(package["deployment_authorized"])
        self.assertFalse(package["legacy_retirement_authorized"])

    def test_delta_has_no_retirements(self) -> None:
        delta = json.loads((SCENARIO / "specs" / "AI-2410" / "semantic-delta.yaml").read_text())
        self.assertEqual(delta["retired"], [])
        self.assertIn("REQ-RISK-010", {item["requirement_id"] for item in delta["preserved"]})

    def test_impact_graph_keeps_investigation_blocker(self) -> None:
        impact = json.loads((SCENARIO / "specs" / "AI-2410" / "impact-analysis.json").read_text())
        portal = next(item for item in impact["consumers"] if item["id"] == "LegacyPortal")
        self.assertEqual(portal["impact"], "INVESTIGATE")
        self.assertTrue(portal["block_retirement"])

    def test_starter_has_five_decisions(self) -> None:
        starter = (SCENARIO / "workshop" / "starter" / "modernization-package.json").read_text()
        self.assertEqual(starter.count("TODO-"), 5)

    def test_lab_report(self) -> None:
        result = subprocess.run([sys.executable, str(SCENARIO / "lab.py")], cwd=ROOT, text=True, capture_output=True, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["conformance"]["passed"], 12)
        self.assertEqual(report["evaluation"]["passed"], 24)
        self.assertEqual(report["experiments"]["passed"], 10)
        self.assertEqual(report["reference"]["state"], "READY_FOR_INTEGRATION_REVIEW")


if __name__ == "__main__":
    unittest.main()
