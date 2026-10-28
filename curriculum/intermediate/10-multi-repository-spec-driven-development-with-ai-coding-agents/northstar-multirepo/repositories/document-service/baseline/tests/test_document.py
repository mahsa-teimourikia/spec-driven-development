import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from document import extract


class DocumentTests(unittest.TestCase):
    def test_identity_and_evidence_are_preserved(self):
        self.assertEqual(extract("DOC-1", "TENANT-A")["text_ref"], "evidence:DOC-1")


if __name__ == "__main__":
    unittest.main()
