"""Scenario-local smoke tests; repository tests provide the independent gate."""

import importlib.util
import sys
import unittest
from pathlib import Path


SCENARIO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("course17_scenario_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class VerticalSliceSmokeTests(unittest.TestCase):
    def test_reference_stops_at_integration_review(self):
        result, _ = lab.run_pipeline()
        self.assertEqual(result.state, "READY_FOR_INTEGRATION_REVIEW")
        self.assertFalse(result.release_authorized)

    def test_unauthorized_side_effect_is_blocked(self):
        result, trace = lab.run_pipeline(mode="unauthorized_mutation")
        self.assertEqual(result.state, "BLOCKED")
        self.assertIn("UNAUTHORIZED_SIDE_EFFECT", trace["validation_findings"])

    def test_adversarial_document_attempt_never_reaches_effect_gateway(self):
        result, trace = lab.run_pipeline(mode="prompt_injection")
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(trace["attempted_actions"], ["send_broker_email"])
        self.assertEqual(trace["effect_invocations"], [])

    def test_empty_evidence_abstains(self):
        from app.generator import DeterministicRiskGenerator
        proposal = DeterministicRiskGenerator().generate(lab.reference_context()[0], {})
        self.assertEqual(proposal.generation_outcome, "INSUFFICIENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
