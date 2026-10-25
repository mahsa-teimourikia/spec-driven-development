"""Expand-and-contract migration with transactional idempotency."""

from __future__ import annotations

import sqlite3
import hashlib
import json
from dataclasses import asdict

from .contracts import MigrationStatus, SummaryProposal


def canonical_payload_digest(proposal: SummaryProposal) -> str:
    payload = json.dumps(asdict(proposal), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ProposalStore:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            """
            CREATE TABLE summary_proposal (
                submission_id TEXT NOT NULL,
                source_revision TEXT NOT NULL,
                source TEXT NOT NULL,
                proposal_text TEXT NOT NULL,
                payload_digest TEXT NOT NULL,
                authoritative INTEGER NOT NULL CHECK (authoritative = 0),
                UNIQUE (submission_id, source_revision)
            )
            """
        )

    def migrate(self, proposal: SummaryProposal, source_revision: str) -> MigrationStatus:
        """Atomically distinguish an identical retry from a conflicting payload."""
        digest = canonical_payload_digest(proposal)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute(
                """
                SELECT payload_digest
                FROM summary_proposal
                WHERE submission_id = ? AND source_revision = ?
                """,
                (proposal.submission_id, source_revision),
            ).fetchone()
            if existing is not None:
                self.connection.commit()
                return "ALREADY_APPLIED" if existing[0] == digest else "IDEMPOTENCY_CONFLICT"
            self.connection.execute(
                """
                INSERT INTO summary_proposal
                    (submission_id, source_revision, source, proposal_text, payload_digest, authoritative)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (proposal.submission_id, source_revision, proposal.source, proposal.text, digest),
            )
            self.connection.commit()
            return "APPLIED"
        except Exception:
            self.connection.rollback()
            raise

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM summary_proposal").fetchone()[0])

    def authoritative_count(self) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM summary_proposal WHERE authoritative != 0"
            ).fetchone()[0]
        )

    def payload_digest(self, submission_id: str, source_revision: str) -> str | None:
        row = self.connection.execute(
            "SELECT payload_digest FROM summary_proposal WHERE submission_id = ? AND source_revision = ?",
            (submission_id, source_revision),
        ).fetchone()
        return None if row is None else str(row[0])
