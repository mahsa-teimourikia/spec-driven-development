import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classifier import propose


class ProducerV2Tests(unittest.TestCase):
    def test_proposal_preserves_evidence_and_model_provenance(self):
        proposal = propose("DOC-1", 0.90, ["evidence:DOC-1"])
        self.assertEqual(proposal["evidence_refs"], ["evidence:DOC-1"])
        self.assertTrue(proposal["review_required"])
        self.assertNotIn("underwriting_state", proposal)

    def test_missing_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            propose("DOC-1", 0.90, [])


if __name__ == "__main__":
    unittest.main()
