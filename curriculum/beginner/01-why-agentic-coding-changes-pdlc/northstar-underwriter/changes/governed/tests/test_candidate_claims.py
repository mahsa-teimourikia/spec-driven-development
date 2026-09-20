"""Candidate-owned smoke tests; independent fixture tests remain authoritative."""

from __future__ import annotations

import unittest

from northstar_underwriter.policy_qa import ask_policy_question


class Gateway:
    def generate(self, question, passages, *, route, region, prompt_version):
        del question, passages, route, region, prompt_version
        return "The deductible is $1,000."


class CandidateClaimTests(unittest.TestCase):
    def test_supported_question_returns_the_stable_contract(self):
        result = ask_policy_question(
            "What is the deductible?",
            [{"id": "p1", "text": "The deductible is $1,000."}],
            Gateway(),
        )
        self.assertEqual(set(result), {"answer", "citations", "status"})
        self.assertEqual(result["status"], "answered")


if __name__ == "__main__":
    unittest.main()
