import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from review import accepts


class ConsumerV1Tests(unittest.TestCase):
    def test_only_revision_one_is_accepted(self):
        self.assertTrue(accepts(1))
        self.assertFalse(accepts(2))


if __name__ == "__main__":
    unittest.main()
