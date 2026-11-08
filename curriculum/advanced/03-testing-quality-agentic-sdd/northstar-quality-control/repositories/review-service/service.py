"""Northstar Review Service fixture with transactional idempotency."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


def _digest(value: dict) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def requires_review(proposal, *, mutant: str | None = None) -> bool:
    if proposal.ambiguous and mutant != "IGNORE_AMBIGUITY":
        return True
    if not proposal.evidence_refs:
        return True
    return proposal.confidence < 0.95


def can_read(*, actor_tenant: str, resource_tenant: str, mutant: str | None = None) -> bool:
    return mutant == "REMOVE_TENANT_FILTER" or actor_tenant == resource_tenant


@dataclass(frozen=True)
class Approval:
    approval_id: str
    tenant_id: str
    actor_role: str
    proposal_digest: str
    expires_at: str
    revoked: bool = False


class ReviewStore:
    """SQLite models the trusted atomic boundary used by duplicate requests."""

    def __init__(self, path: Path, *, mutant: str | None = None) -> None:
        self.path = path
        self.mutant = mutant
        self._sequence = 0
        self._sequence_lock = threading.Lock()
        connection = self._connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS operations ("
                "operation_id TEXT PRIMARY KEY, payload_digest TEXT NOT NULL, "
                "tenant_id TEXT NOT NULL, effect_id TEXT NOT NULL)"
            )
        finally:
            connection.close()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def apply(
        self,
        *,
        operation_id: str,
        tenant_id: str,
        actor_tenant: str,
        payload: dict,
        approval: Approval,
        now: str,
    ) -> dict:
        if not can_read(
            actor_tenant=actor_tenant,
            resource_tenant=tenant_id,
            mutant=self.mutant,
        ):
            return {"status": "DENIED", "effect_id": None}
        moment = datetime.fromisoformat(now.replace("Z", "+00:00")).astimezone(timezone.utc)
        expiry = datetime.fromisoformat(approval.expires_at.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
        expected_digest = _digest(payload)
        if approval.revoked:
            return {"status": "APPROVAL_REVOKED", "effect_id": None}
        if moment >= expiry and self.mutant != "ACCEPT_EXPIRED_APPROVAL":
            return {"status": "APPROVAL_EXPIRED", "effect_id": None}
        if approval.actor_role != "authorized-underwriter":
            return {"status": "UNAUTHORIZED", "effect_id": None}
        if approval.tenant_id != tenant_id or approval.proposal_digest != expected_digest:
            return {"status": "APPROVAL_MISMATCH", "effect_id": None}

        storage_id = operation_id
        if self.mutant == "DROP_IDEMPOTENCY_KEY":
            with self._sequence_lock:
                self._sequence += 1
                storage_id = f"{operation_id}-mutant-{self._sequence}"

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT payload_digest, effect_id FROM operations WHERE operation_id = ?",
                (storage_id,),
            ).fetchone()
            if existing:
                connection.commit()
                if existing[0] == expected_digest:
                    return {"status": "REPLAYED", "effect_id": existing[1]}
                return {"status": "IDEMPOTENCY_CONFLICT", "effect_id": None}
            effect_id = "EFFECT-" + hashlib.sha256(storage_id.encode("utf-8")).hexdigest()[:12]
            connection.execute(
                "INSERT INTO operations VALUES (?, ?, ?, ?)",
                (storage_id, expected_digest, tenant_id, effect_id),
            )
            connection.commit()
            return {"status": "APPLIED", "effect_id": effect_id}
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def effect_count(self) -> int:
        connection = self._connect()
        try:
            return int(connection.execute("SELECT COUNT(*) FROM operations").fetchone()[0])
        finally:
            connection.close()


def payload_digest(payload: dict) -> str:
    return _digest(payload)
