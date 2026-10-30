import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from view import label


class ViewTests(unittest.TestCase):
    def test_proposal_is_not_labeled_approved(self):
        self.assertNotEqual(label({"review_required": False}), "Approved")


if __name__ == "__main__":
    unittest.main()
