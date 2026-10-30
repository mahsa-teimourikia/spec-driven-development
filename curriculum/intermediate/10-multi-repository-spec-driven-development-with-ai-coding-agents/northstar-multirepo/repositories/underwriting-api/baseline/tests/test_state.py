import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from state import apply_review_decision


class StateTests(unittest.TestCase):
    def test_stale_or_unauthorized_transition_is_blocked(self):
        self.assertEqual(apply_review_decision(authorized=False, current=True), "BLOCKED")
        self.assertEqual(apply_review_decision(authorized=True, current=False), "BLOCKED")


if __name__ == "__main__":
    unittest.main()
