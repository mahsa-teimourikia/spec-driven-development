"""Independent review using registry-backed approval facts and single-use state."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ApprovalReceipt, PipelineResult, TrustedApprovalRecord, ValidationReport

AUTHORIZED_REVIEWERS = {"northstar/underwriter-reviewer-204"}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class TrustedReceiptRegistry:
    """Trusted boundary; callers receive handles, never self-asserted approval facts."""

    def __init__(self, records: tuple[TrustedApprovalRecord, ...] = ()) -> None:
        self._records = {record.receipt_id: record for record in records}

    def lookup(self, receipt_id: str) -> TrustedApprovalRecord | None:
        return self._records.get(receipt_id)


class ReceiptStore:
    """Process-local teaching store; restart behavior is intentionally limited."""

    def __init__(self) -> None:
        self._used: set[str] = set()

    def consume(self, receipt_id: str) -> bool:
        if receipt_id in self._used:
            return False
        self._used.add(receipt_id)
        return True


class SqliteReceiptStore:
    """Durable training example with atomic uniqueness across store restarts."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS consumed_receipts "
                "(receipt_id TEXT PRIMARY KEY, consumed_at TEXT NOT NULL)"
            )
            connection.commit()
        finally:
            connection.close()

    def consume(self, receipt_id: str) -> bool:
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "INSERT INTO consumed_receipts(receipt_id, consumed_at) VALUES (?, ?)",
                (receipt_id, utc_now()),
            )
            connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            connection.close()


def review_for_integration(
    report: ValidationReport,
    receipt: ApprovalReceipt | None,
    *,
    registry: TrustedReceiptRegistry,
    evaluation_time: str,
    store: ReceiptStore | SqliteReceiptStore,
) -> PipelineResult:
    if report.status != "PASS":
        return PipelineResult("BLOCKED", tuple(item.code for item in report.findings), report.proposal_digest, report.evidence_ids)
    if receipt is None:
        return PipelineResult("READY_FOR_HUMAN_REVIEW", ("HUMAN_REVIEW_REQUIRED",), report.proposal_digest, report.evidence_ids)

    record = registry.lookup(receipt.receipt_id)
    if record is None:
        return PipelineResult("BLOCKED", ("REVIEW_RECEIPT_NOT_FOUND",), report.proposal_digest, report.evidence_ids)

    reasons: list[str] = []
    if not record.authenticated:
        reasons.append("REVIEW_IDENTITY_UNVERIFIED")
    if not record.principal_authorized or record.principal not in AUTHORIZED_REVIEWERS:
        reasons.append("REVIEW_PRINCIPAL_UNAUTHORIZED")
    if record.revoked:
        reasons.append("REVIEW_RECEIPT_REVOKED")
    if record.proposal_digest != report.proposal_digest:
        reasons.append("REVIEW_SUBJECT_MISMATCH")
    if record.decision != "APPROVE_FOR_INTEGRATION_REVIEW":
        reasons.append("REVIEW_DECISION_INVALID")
    if _time(record.issued_at) > _time(evaluation_time) or _time(record.expires_at) <= _time(record.issued_at):
        reasons.append("REVIEW_TIME_INVALID")
    elif _time(record.expires_at) <= _time(evaluation_time):
        reasons.append("REVIEW_RECEIPT_EXPIRED")
    if reasons:
        return PipelineResult("BLOCKED", tuple(reasons), report.proposal_digest, report.evidence_ids)
    if not store.consume(record.receipt_id):
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
