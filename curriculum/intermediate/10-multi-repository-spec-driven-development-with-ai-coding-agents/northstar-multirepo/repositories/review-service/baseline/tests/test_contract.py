import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from review import accepts, consume


class ConsumerV1Tests(unittest.TestCase):
    def test_only_revision_one_is_accepted(self):
        self.assertTrue(accepts(1))
        self.assertFalse(accepts(2))

    def test_revision_one_proposal_is_consumed(self):
        proposal = {
            "proposal_id": "proposal:DOC-1",
            "document_id": "DOC-1",
            "candidate_requirement_ids": ["REQ-45"],
            "review_required": False,
        }
        self.assertEqual(consume(proposal, 1), "ACCEPTED")
        self.assertEqual(consume(proposal, 2), "REJECTED")


if __name__ == "__main__":
    unittest.main()
