import sys
import unittest
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from review import AUTHORIZED_REVIEW_ROLE, ReviewEngine, accepts, validate_v2


class ConsumerV2Tests(unittest.TestCase):
    def proposal(self, **updates):
        value = {
            "proposal_id": "proposal:TENANT-A:DOC-1",
            "document_id": "DOC-1",
            "tenant_id": "TENANT-A",
            "candidate_requirement_ids": ["REQ-45"],
            "ambiguity_status": "AMBIGUOUS",
            "model_confidence": 0.99,
            "review_required": True,
            "evidence_refs": ["evidence:DOC-1"],
            "model_provenance": {"model_id": "model", "model_revision": "1"},
        }
        value.update(updates)
        return value

    def process(self, proposal=None, **updates):
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        proposal = proposal or self.proposal()
        proposal_digest = hashlib.sha256(
            json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        arguments = {
            "contract_revision": 2,
            "submission_id": "submission-1",
            "authorized_tenant": "TENANT-A",
            "evidence_tenants": {"evidence:DOC-1": "TENANT-A"},
            "approval_receipt": {
                "receipt_id": "approval-1",
                "tenant_id": "TENANT-A",
                "reviewer_id": "reviewer-17",
                "reviewer_roles": [AUTHORIZED_REVIEW_ROLE],
                "proposal_digest": proposal_digest,
                "expires_at": now + timedelta(minutes=5),
            },
            "now": now,
        }
        arguments.update(updates)
        return ReviewEngine().process(proposal, **arguments)

    def test_old_and_new_contracts_are_accepted(self):
        self.assertTrue(accepts(1))
        self.assertTrue(accepts(2))

    def test_v2_requires_provenance(self):
        self.assertFalse(validate_v2({"evidence_refs": []}))

    def test_high_confidence_ambiguity_is_routed_for_review(self):
        result = self.process()
        self.assertTrue(result["review_required"])
        self.assertEqual(result["authoritative_mutation_count"], 0)

    def test_unauthorized_reviewer_is_rejected(self):
        proposal = self.proposal()
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        with self.assertRaises(PermissionError):
            self.process(
                proposal,
                approval_receipt={
                    "receipt_id": "approval-1",
                    "tenant_id": "TENANT-A",
                    "reviewer_id": "reviewer-17",
                    "reviewer_roles": [],
                    "proposal_digest": hashlib.sha256(
                        json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest(),
                    "expires_at": now + timedelta(minutes=5),
                },
            )

    def test_cross_tenant_proposal_is_rejected(self):
        with self.assertRaises(PermissionError):
            self.process(self.proposal(tenant_id="TENANT-B"))

    def test_stale_approval_is_rejected(self):
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        proposal = self.proposal()
        with self.assertRaises(PermissionError):
            self.process(
                proposal,
                now=now,
                approval_receipt={
                    "receipt_id": "approval-1",
                    "tenant_id": "TENANT-A",
                    "reviewer_id": "reviewer-17",
                    "reviewer_roles": [AUTHORIZED_REVIEW_ROLE],
                    "proposal_digest": hashlib.sha256(
                        json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest(),
                    "expires_at": now - timedelta(seconds=1),
                },
            )

    def test_duplicate_submission_has_no_second_effect(self):
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        engine = ReviewEngine()
        proposal = self.proposal()
        arguments = {
            "contract_revision": 2,
            "submission_id": "submission-1",
            "authorized_tenant": "TENANT-A",
            "evidence_tenants": {"evidence:DOC-1": "TENANT-A"},
            "approval_receipt": {
                "receipt_id": "approval-1",
                "tenant_id": "TENANT-A",
                "reviewer_id": "reviewer-17",
                "reviewer_roles": [AUTHORIZED_REVIEW_ROLE],
                "proposal_digest": hashlib.sha256(
                    json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                "expires_at": now + timedelta(minutes=5),
            },
            "now": now,
        }
        self.assertEqual(engine.process(proposal, **arguments)["side_effect_count"], 1)
        self.assertEqual(engine.process(proposal, **arguments)["side_effect_count"], 0)

    def test_approval_receipt_is_bound_and_single_use(self):
        proposal = self.proposal()
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        digest = hashlib.sha256(
            json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        receipt = {
            "receipt_id": "approval-1",
            "tenant_id": "TENANT-A",
            "reviewer_id": "reviewer-17",
            "reviewer_roles": [AUTHORIZED_REVIEW_ROLE],
            "proposal_digest": digest,
            "expires_at": now + timedelta(minutes=5),
        }
        engine = ReviewEngine()
        common = {
            "contract_revision": 2,
            "authorized_tenant": "TENANT-A",
            "evidence_tenants": {"evidence:DOC-1": "TENANT-A"},
            "approval_receipt": receipt,
            "now": now,
        }
        engine.process(proposal, submission_id="submission-1", **common)
        with self.assertRaises(PermissionError):
            engine.process(proposal, submission_id="submission-2", **common)


if __name__ == "__main__":
    unittest.main()
