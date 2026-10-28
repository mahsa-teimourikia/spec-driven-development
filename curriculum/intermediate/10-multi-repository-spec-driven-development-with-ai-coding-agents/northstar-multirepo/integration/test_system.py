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


if __name__ == "__main__":
    unittest.main()
