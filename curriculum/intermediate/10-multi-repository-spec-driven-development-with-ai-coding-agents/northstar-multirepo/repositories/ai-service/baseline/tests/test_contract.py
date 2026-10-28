import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classifier import propose


class ProducerV1Tests(unittest.TestCase):
    def test_proposal_is_non_authoritative(self):
        self.assertNotIn("underwriting_state", propose("DOC-1", 0.90))


if __name__ == "__main__":
    unittest.main()
