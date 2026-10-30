"""Small standalone smoke test for the exact-revision Course 20 integration fixture."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCENARIO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCENARIO))
from lab import assess_candidate, build_candidate  # noqa: E402


class SystemIntegrationSmokeTests(unittest.TestCase):
    def test_reference_revision_set_passes_all_declared_scenarios(self):
        decision, context = assess_candidate(build_candidate())
        self.assertEqual(decision.state, "READY_FOR_INTEGRATION_REVIEW")
        self.assertTrue(all(context.scenario_results.values()))

    def test_cross_tenant_failure_blocks_even_when_local_ci_is_green(self):
        candidate = build_candidate(["cross_tenant_leak"])
        decision, _ = assess_candidate(candidate)
        self.assertTrue(all(candidate["local_ci"].values()))
        self.assertEqual(decision.state, "BLOCKED")

    def test_review_authority_and_high_confidence_ambiguity_are_executed(self):
        _, context = assess_candidate(build_candidate())
        self.assertTrue(context.scenario_results["ambiguous_mapping"])
        self.assertTrue(context.scenario_results["unauthorized_reviewer"])
        self.assertTrue(context.scenario_results["stale_approval"])

    def test_requirement_evidence_is_bound_to_executed_scenarios(self):
        _, context = assess_candidate(build_candidate())
        self.assertEqual(
            set(context.requirement_evidence),
            {"REQ-DOC-2500-01", "REQ-DOC-2500-02", "REQ-DOC-2500-03", "REQ-DOC-2500-04"},
        )
        self.assertTrue(all(item["passed"] for item in context.requirement_evidence.values()))


if __name__ == "__main__":
    unittest.main()
