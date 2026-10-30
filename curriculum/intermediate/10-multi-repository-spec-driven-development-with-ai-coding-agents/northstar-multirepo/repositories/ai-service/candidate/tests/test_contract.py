import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classifier import propose


class ProducerV2Tests(unittest.TestCase):
    def test_proposal_preserves_evidence_and_model_provenance(self):
        proposal = propose(
            "DOC-1",
            ["REQ-45"],
            ["evidence:DOC-1"],
            "SUPPORTED",
            tenant_id="TENANT-A",
            model_confidence=0.90,
        )
        self.assertEqual(proposal["evidence_refs"], ["evidence:DOC-1"])
        self.assertFalse(proposal["review_required"])
        self.assertEqual(proposal["tenant_id"], "TENANT-A")
        self.assertNotIn("underwriting_state", proposal)

    def test_missing_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            propose(
                "DOC-1",
                ["REQ-45"],
                [],
                "SUPPORTED",
                tenant_id="TENANT-A",
                model_confidence=0.90,
            )

    def test_high_confidence_ambiguity_still_requires_review(self):
        proposal = propose(
            "DOC-2",
            ["REQ-46"],
            ["evidence:DOC-2"],
            "AMBIGUOUS",
            tenant_id="TENANT-A",
            model_confidence=0.99,
        )
        self.assertTrue(proposal["review_required"])


if __name__ == "__main__":
    unittest.main()
