"""Candidate-owned tests that deliberately validate only the unsafe design's claims."""

from __future__ import annotations

import unittest

from northstar_underwriter.policy_qa import ask_policy_question


class UnusedGateway:
    pass


class CandidateClaimTests(unittest.TestCase):
    def test_returns_an_answer_for_any_non_empty_question(self):
        result = ask_policy_question("Does this cover lunar travel?", [], UnusedGateway())
        self.assertEqual(result["status"], "answered")
        self.assertIn("answer_text", result)

    def test_exposes_provider_debug_fields(self):
        result = ask_policy_question("What is covered?", [], UnusedGateway())
        self.assertEqual(result["provider_route"], "public_model_api")
        self.assertEqual(result["provider_region"], "us-east-1")


if __name__ == "__main__":
    unittest.main()
