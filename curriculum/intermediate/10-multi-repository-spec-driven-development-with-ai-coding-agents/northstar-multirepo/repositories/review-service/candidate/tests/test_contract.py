import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from review import accepts, validate_v2


class ConsumerV2Tests(unittest.TestCase):
    def test_old_and_new_contracts_are_accepted(self):
        self.assertTrue(accepts(1))
        self.assertTrue(accepts(2))

    def test_v2_requires_provenance(self):
        self.assertFalse(validate_v2({"evidence_refs": []}))


if __name__ == "__main__":
    unittest.main()
