from __future__ import annotations

import unittest

from northstar_underwriter.auth import require_underwriter
from northstar_underwriter.models import PolicyPassage
from northstar_underwriter.retrieval import passages_for_tenant


class ExistingBoundaryTests(unittest.TestCase):
    def test_corporate_claims_must_include_underwriter_role_and_tenant(self):
        self.assertEqual(
            require_underwriter({"role": "underwriter", "tenant_id": "north-17"}),
            "north-17",
        )
        with self.assertRaises(PermissionError):
            require_underwriter({"role": "viewer", "tenant_id": "north-17"})

    def test_retrieval_filters_passages_by_tenant(self):
        passages = (
            PolicyPassage("p-1", "north-17", "Northstar policy text"),
            PolicyPassage("p-2", "south-03", "Another tenant's policy text"),
        )
        visible = passages_for_tenant(passages, "north-17")
        self.assertEqual([item.passage_id for item in visible], ["p-1"])


if __name__ == "__main__":
    unittest.main()
