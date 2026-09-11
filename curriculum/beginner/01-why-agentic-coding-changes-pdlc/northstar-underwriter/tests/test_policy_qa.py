from __future__ import annotations

import unittest

from northstar_underwriter.policy_qa import ask_policy_question


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate(self, question, passages, *, route, region, prompt_version):
        self.calls.append(
            {
                "question": question,
                "route": route,
                "region": region,
                "prompt_version": prompt_version,
            }
        )
        return "The collision deductible is $1,000."


class PolicyQuestionTests(unittest.TestCase):
    def setUp(self):
        self.gateway = RecordingGateway()
        self.passages = [
            {"id": "policy-17#p4", "text": "Collision coverage has a $1,000 deductible."},
            {"id": "policy-17#p8", "text": "Roadside assistance is optional."},
        ]

    def test_supported_answer_has_citation_and_stable_contract(self):
        result = ask_policy_question("What is the collision deductible?", self.passages, self.gateway)
        self.assertEqual(set(result), {"answer", "citations", "status"})
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["citations"], ["policy-17#p4"])

    def test_model_access_uses_approved_canadian_gateway_route(self):
        ask_policy_question("What is the collision deductible?", self.passages, self.gateway)
        self.assertEqual(len(self.gateway.calls), 1)
        self.assertEqual(self.gateway.calls[0]["route"], "approved_ai_gateway")
        self.assertEqual(self.gateway.calls[0]["region"], "ca-central-1")
        self.assertEqual(self.gateway.calls[0]["prompt_version"], "policy-qa-v1")

    def test_unsupported_question_does_not_call_model(self):
        result = ask_policy_question("Does this cover lunar travel?", self.passages, self.gateway)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["citations"], [])
        self.assertEqual(self.gateway.calls, [])

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            ask_policy_question("   ", self.passages, self.gateway)


if __name__ == "__main__":
    unittest.main()
