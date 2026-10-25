"""Expand-and-contract migration with transactional idempotency."""

from __future__ import annotations

import sqlite3

from .contracts import SummaryProposal


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
                authoritative INTEGER NOT NULL CHECK (authoritative = 0),
                UNIQUE (submission_id, source_revision)
            )
            """
        )

    def migrate(self, proposal: SummaryProposal, source_revision: str) -> bool:
        """Return True for the first write and False for a safe retry."""
        before = self.connection.total_changes
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO summary_proposal
                    (submission_id, source_revision, source, proposal_text, authoritative)
                VALUES (?, ?, ?, ?, 0)
                ON CONFLICT(submission_id, source_revision) DO NOTHING
                """,
                (proposal.submission_id, source_revision, proposal.source, proposal.text),
            )
        return self.connection.total_changes > before

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM summary_proposal").fetchone()[0])

    def authoritative_count(self) -> int:
        return int(
            self.connection.execute(
                "SELECT COUNT(*) FROM summary_proposal WHERE authoritative != 0"
            ).fetchone()[0]
        )
