"""Revision-2 tolerant consumer with executable review-policy enforcement."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


AUTHORIZED_REVIEW_ROLE = "AUTHORIZED_DOCUMENT_REVIEWER"


def accepts(contract_revision: int) -> bool:
    return contract_revision in {1, 2}


def _digest(proposal: dict[str, object]) -> str:
    payload = json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_v2(proposal: dict[str, object]) -> bool:
    required = {
        "proposal_id",
        "document_id",
        "tenant_id",
        "candidate_requirement_ids",
        "ambiguity_status",
        "model_confidence",
        "review_required",
        "evidence_refs",
        "model_provenance",
    }
    if set(proposal) != required:
        return False
    expected_review = proposal["ambiguity_status"] in {"AMBIGUOUS", "UNSUPPORTED"}
    return (
        bool(proposal["evidence_refs"])
        and bool(proposal["model_provenance"])
        and proposal["review_required"] is expected_review
    )


class ReviewEngine:
    """Idempotent routing boundary; it never mutates underwriting state."""

    def __init__(self) -> None:
        self._submissions: dict[str, tuple[str, dict[str, object]]] = {}
        self._consumed_approval_receipts: set[str] = set()

    def process(
        self,
        proposal: dict[str, object],
        *,
        contract_revision: int,
        submission_id: str,
        authorized_tenant: str,
        evidence_tenants: dict[str, str],
        approval_receipt: dict[str, object] | None,
        now: datetime,
        review_available: bool = True,
    ) -> dict[str, object]:
        if not accepts(contract_revision):
            raise ValueError("unsupported contract revision")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("current time must be timezone-aware")
        if contract_revision == 2 and not validate_v2(proposal):
            raise ValueError("revision two proposal violates the behavioral contract")

        proposal_tenant = proposal.get("tenant_id", authorized_tenant)
        if proposal_tenant != authorized_tenant:
            raise PermissionError("proposal tenant does not match authenticated tenant")
        for evidence_ref in proposal.get("evidence_refs", []):
            if evidence_tenants.get(str(evidence_ref)) != authorized_tenant:
                raise PermissionError("evidence is missing or belongs to another tenant")

        proposal_digest = _digest(proposal)
        existing = self._submissions.get(submission_id)
        if existing is not None:
            if existing[0] != proposal_digest:
                raise ValueError("submission id was reused for a different proposal")
            return {**existing[1], "duplicate": True, "side_effect_count": 0}

        review_required = bool(proposal["review_required"])
        if review_required:
            if not review_available:
                raise RuntimeError("required review service is unavailable")
            if not approval_receipt:
                raise PermissionError("a trusted approval receipt is required")
            receipt_id = str(approval_receipt.get("receipt_id", ""))
            reviewer_id = str(approval_receipt.get("reviewer_id", ""))
            roles = set(approval_receipt.get("reviewer_roles", []))
            expires_at = approval_receipt.get("expires_at")
            if not receipt_id or not reviewer_id:
                raise PermissionError("approval and reviewer identity are required")
            if AUTHORIZED_REVIEW_ROLE not in roles:
                raise PermissionError("authorized reviewer role is required")
            if approval_receipt.get("tenant_id") != authorized_tenant:
                raise PermissionError("approval tenant does not match authenticated tenant")
            if approval_receipt.get("proposal_digest") != proposal_digest:
                raise PermissionError("approval is not bound to this proposal")
            if not isinstance(expires_at, datetime) or expires_at.tzinfo is None:
                raise PermissionError("a timezone-aware approval expiry is required")
            if expires_at <= now.astimezone(timezone.utc):
                raise PermissionError("review approval is stale")
            if receipt_id in self._consumed_approval_receipts:
                raise PermissionError("review approval receipt was already consumed")
            self._consumed_approval_receipts.add(receipt_id)

        result: dict[str, object] = {
            "status": "ROUTED_TO_REVIEW" if review_required else "PROPOSAL_ACCEPTED",
            "review_required": review_required,
            "tenant_id": authorized_tenant,
            "authoritative_mutation_count": 0,
            "side_effect_count": 1,
            "duplicate": False,
        }
        self._submissions[submission_id] = (proposal_digest, result)
        return dict(result)
