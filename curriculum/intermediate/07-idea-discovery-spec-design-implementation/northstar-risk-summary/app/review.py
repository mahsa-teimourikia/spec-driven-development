"""Independent review boundary for exact, validated proposals."""

from __future__ import annotations

from datetime import datetime, timezone

from .contracts import ApprovalReceipt, PipelineResult, ValidationReport

AUTHORIZED_REVIEWERS = {"northstar/underwriter-reviewer-204"}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ReceiptStore:
    """Process-local teaching store; production requires durable atomic storage."""

    def __init__(self) -> None:
        self._used: set[str] = set()

    def consume(self, receipt_id: str) -> bool:
        if receipt_id in self._used:
            return False
        self._used.add(receipt_id)
        return True


def review_for_integration(
    report: ValidationReport,
    receipt: ApprovalReceipt | None,
    *,
    evaluation_time: str,
    store: ReceiptStore,
) -> PipelineResult:
    if report.status != "PASS":
        return PipelineResult("BLOCKED", tuple(item.code for item in report.findings), report.proposal_digest, report.evidence_ids)
    if receipt is None:
        return PipelineResult("READY_FOR_HUMAN_REVIEW", ("HUMAN_REVIEW_REQUIRED",), report.proposal_digest, report.evidence_ids)
    reasons: list[str] = []
    if not receipt.identity_verified or not receipt.attestation_verified:
        reasons.append("REVIEW_IDENTITY_UNVERIFIED")
    if receipt.principal not in AUTHORIZED_REVIEWERS:
        reasons.append("REVIEW_PRINCIPAL_UNAUTHORIZED")
    if receipt.proposal_digest != report.proposal_digest:
        reasons.append("REVIEW_SUBJECT_MISMATCH")
    if receipt.decision != "APPROVE_FOR_INTEGRATION_REVIEW":
        reasons.append("REVIEW_DECISION_INVALID")
    if _time(receipt.issued_at) > _time(evaluation_time) or _time(receipt.expires_at) <= _time(receipt.issued_at):
        reasons.append("REVIEW_TIME_INVALID")
    elif _time(receipt.expires_at) <= _time(evaluation_time):
        reasons.append("REVIEW_RECEIPT_EXPIRED")
    if reasons:
        return PipelineResult("BLOCKED", tuple(reasons), report.proposal_digest, report.evidence_ids)
    if not store.consume(receipt.receipt_id):
        return PipelineResult("BLOCKED", ("REVIEW_RECEIPT_REPLAYED",), report.proposal_digest, report.evidence_ids)
    return PipelineResult(
        "READY_FOR_INTEGRATION_REVIEW",
        (),
        report.proposal_digest,
        report.evidence_ids,
        release_authorized=False,
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
