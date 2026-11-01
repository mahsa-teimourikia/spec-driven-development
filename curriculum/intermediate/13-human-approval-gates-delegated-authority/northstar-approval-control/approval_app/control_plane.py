"""SQLite-backed approval, delegation, emergency, and audit enforcement."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, replace
from pathlib import Path
from typing import Iterable, Iterator

from .models import ActionSubject, AuthorityGrant, ControlError, Decision, DelegationGrant, RISK_ORDER


class ApprovalControlPlane:
    """Trusted application boundary; callers provide references, never authority facts."""

    def __init__(self, db_path: Path, fixture_root: Path) -> None:
        self.db_path = db_path
        self.fixture_root = fixture_root
        self.policy = self._load("policies/approval-policy.json")
        self.emergency_policy = self._load("policies/emergency-policy.json")
        self.sessions = self._load("registry/principals.json")["sessions"]
        self.grants = {
            item["grant_id"]: AuthorityGrant(
                item["grant_id"], item["principal"], item["role"], frozenset(item["actions"]),
                frozenset(item["resources"]), frozenset(item["environments"]), item["max_risk"],
                item["starts_at"], item["expires_at"], item["delegable"], item.get("state", "ACTIVE"),
            ) for item in self._load("registry/authority-grants.json")["grants"]
        }
        self.delegations: dict[str, DelegationGrant] = {}
        self.incidents = {item["incident_id"]: item for item in self._load("registry/incidents.json")["incidents"]}
        self._initialize()

    def _load(self, relative: str):
        return json.loads((self.fixture_root / relative).read_text(encoding="utf-8"))

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=10000")
        try:
            yield connection
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY, requester TEXT NOT NULL, implementation_author TEXT NOT NULL,
                    subject_json TEXT NOT NULL, subject_digest TEXT NOT NULL, state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY, request_id TEXT NOT NULL, principal TEXT NOT NULL,
                    role TEXT NOT NULL, subject_digest TEXT NOT NULL, policy_revision TEXT NOT NULL,
                    authority_source TEXT NOT NULL, issued_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                    usage TEXT NOT NULL, state TEXT NOT NULL,
                    UNIQUE(request_id, role)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    execution_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                    subject_digest TEXT NOT NULL, effect TEXT NOT NULL, executed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL, subject_id TEXT NOT NULL, principal TEXT NOT NULL,
                    reason_code TEXT NOT NULL, payload_json TEXT NOT NULL,
                    previous_digest TEXT NOT NULL, event_digest TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)

    def authenticate(self, session_id: str) -> str:
        principal = self.sessions.get(session_id)
        if not principal:
            raise ControlError("UNAUTHENTICATED_PRINCIPAL", session_id)
        return principal

    def required_roles(self, subject: ActionSubject) -> tuple[str, ...]:
        if subject.action in self.emergency_policy["permitted_actions"]:
            if subject.policy_revision != self.emergency_policy["revision"]:
                raise ControlError("POLICY_REVISION_MISMATCH", subject.policy_revision)
            incident = self.incidents.get(subject.incident_id or "")
            if not incident or incident["state"] != "ACTIVE" or incident["severity"] not in self.emergency_policy["severities"]:
                raise ControlError("EMERGENCY_AUTHORIZATION_DENIED", subject.incident_id or "missing incident")
            if subject.resource not in incident["resources"]:
                raise ControlError("EMERGENCY_SCOPE_VIOLATION", subject.resource)
            return (self.emergency_policy["required_role"],)
        if subject.policy_revision != self.policy["revision"]:
            raise ControlError("POLICY_REVISION_MISMATCH", subject.policy_revision)
        key = f"{subject.action}|{subject.environment}|{subject.risk_tier}"
        roles = self.policy["required_roles"].get(key)
        if not roles:
            raise ControlError("APPROVAL_POLICY_UNRESOLVED", key)
        return tuple(roles)

    def create_request(self, request_id: str, requester_session: str, implementation_author: str, subject: ActionSubject, now: str) -> Decision:
        requester = self.authenticate(requester_session)
        self.required_roles(subject)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO requests VALUES (?, ?, ?, ?, ?, 'REQUESTED', ?)",
                (request_id, requester, implementation_author, json.dumps(asdict(subject), sort_keys=True), subject.digest, now),
            )
            self._append_audit(connection, "REQUEST_CREATED", request_id, requester, "REQUESTED", {"subject_digest": subject.digest}, now)
            connection.commit()
        return Decision("REQUESTED", "REQUESTED", request_id)

    def _direct_grant(self, principal: str, role: str, subject: ActionSubject, now: str) -> AuthorityGrant | None:
        for grant in self.grants.values():
            if (
                grant.principal == principal and grant.role == role and grant.state == "ACTIVE"
                and grant.starts_at <= now < grant.expires_at
                and subject.action in grant.actions and subject.resource in grant.resources
                and subject.environment in grant.environments
                and RISK_ORDER[subject.risk_tier] <= RISK_ORDER[grant.max_risk]
            ):
                return grant
        return None

    def _delegated_grant(self, principal: str, role: str, subject: ActionSubject, now: str) -> DelegationGrant | None:
        for delegation in self.delegations.values():
            parent = self.grants.get(delegation.parent_grant_id)
            if not parent or parent.state != "ACTIVE":
                continue
            if (
                delegation.delegate == principal and delegation.role == role and delegation.state == "ACTIVE"
                and delegation.starts_at <= now < delegation.expires_at
                and subject.action in delegation.actions and subject.resource in delegation.resources
                and subject.environment in delegation.environments
                and RISK_ORDER[subject.risk_tier] <= RISK_ORDER[delegation.max_risk]
            ):
                return delegation
        return None

    def issue_delegation(self, delegation: DelegationGrant, authenticated_session: str, now: str) -> DelegationGrant:
        principal = self.authenticate(authenticated_session)
        parent = self.grants.get(delegation.parent_grant_id)
        if not parent or parent.principal != principal or delegation.delegator != principal or parent.state != "ACTIVE":
            raise ControlError("DELEGATION_CHAIN_INVALID", delegation.parent_grant_id)
        contained = (
            parent.delegable and delegation.actions <= parent.actions and delegation.resources <= parent.resources
            and delegation.environments <= parent.environments
            and RISK_ORDER[delegation.max_risk] <= RISK_ORDER[parent.max_risk]
            and parent.starts_at <= delegation.starts_at <= now < delegation.expires_at <= parent.expires_at
            and not delegation.may_redelegate
        )
        if not contained:
            raise ControlError("DELEGATION_SCOPE_EXPANSION", delegation.delegation_id)
        self.delegations[delegation.delegation_id] = delegation
        self.audit("DELEGATION_ISSUED", delegation.delegation_id, principal, "AUTHORIZED", asdict(delegation), now)
        return delegation

    def decide(self, request_id: str, approver_session: str, role: str, outcome: str, now: str, expires_at: str) -> Decision:
        principal = self.authenticate(approver_session)
        with self._connect() as connection:
            request = connection.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
        if not request:
            raise ControlError("REQUEST_NOT_FOUND", request_id)
        subject = ActionSubject(**json.loads(request["subject_json"]))
        if role not in self.required_roles(subject):
            self.audit("DECISION_DENIED", request_id, principal, "APPROVER_NOT_AUTHORIZED", {"role": role}, now)
            raise ControlError("APPROVER_NOT_AUTHORIZED", role)
        if principal in {request["requester"], request["implementation_author"]}:
            self.audit("DECISION_DENIED", request_id, principal, "SEPARATION_OF_DUTIES_VIOLATION", {}, now)
            raise ControlError("SEPARATION_OF_DUTIES_VIOLATION", principal)
        direct = self._direct_grant(principal, role, subject, now)
        delegated = self._delegated_grant(principal, role, subject, now)
        if not direct and not delegated:
            self.audit("DECISION_DENIED", request_id, principal, "AUTHORITY_SCOPE_DENIED", {"role": role}, now)
            raise ControlError("AUTHORITY_SCOPE_DENIED", principal)
        if outcome != "APPROVED":
            with self._connect() as connection:
                connection.execute("UPDATE requests SET state = 'REJECTED' WHERE request_id = ?", (request_id,))
            self.audit("REQUEST_REJECTED", request_id, principal, "REJECTED", {}, now)
            return Decision("REJECTED", "REJECTED", request_id)
        receipt_id = f"APR-{request_id}-{role}"
        source = direct.grant_id if direct else delegated.delegation_id
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'single_use', 'APPROVED')",
                (receipt_id, request_id, principal, role, subject.digest, subject.policy_revision, source, now, expires_at),
            )
            connection.execute("UPDATE requests SET state = 'APPROVED' WHERE request_id = ?", (request_id,))
            self._append_audit(connection, "APPROVAL_ISSUED", receipt_id, principal, "APPROVED", {"request_id": request_id, "role": role, "subject_digest": subject.digest}, now)
            connection.commit()
        return Decision("APPROVED", "APPROVED", request_id, (receipt_id,))

    def revoke_receipt(self, receipt_id: str, now: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            updated = connection.execute("UPDATE receipts SET state = 'REVOKED' WHERE receipt_id = ? AND state = 'APPROVED'", (receipt_id,))
            if updated.rowcount != 1:
                connection.rollback()
                raise ControlError("APPROVAL_UNAVAILABLE", receipt_id)
            self._append_audit(connection, "APPROVAL_REVOKED", receipt_id, "approval-service", "REVOKED", {}, now)
            connection.commit()

    def revoke_grant(self, grant_id: str) -> None:
        grant = self.grants[grant_id]
        self.grants[grant_id] = replace(grant, state="REVOKED")

    def execute(self, request_id: str, receipt_ids: Iterable[str], expected_subject: ActionSubject, execution_id: str, now: str) -> Decision:
        receipt_ids = tuple(sorted(set(receipt_ids)))
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                request = connection.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
                if not request:
                    raise ControlError("REQUEST_NOT_FOUND", request_id)
                actual_subject = ActionSubject(**json.loads(request["subject_json"]))
                if actual_subject.digest != expected_subject.digest:
                    raise ControlError("APPROVAL_SUBJECT_MISMATCH", expected_subject.digest)
                roles_required = set(self.required_roles(actual_subject))
                receipts = [connection.execute("SELECT * FROM receipts WHERE receipt_id = ?", (item,)).fetchone() for item in receipt_ids]
                if any(item is None for item in receipts):
                    raise ControlError("UNTRUSTED_RECEIPT", request_id)
                roles, principals = set(), set()
                for receipt in receipts:
                    if receipt["request_id"] != request_id or receipt["subject_digest"] != actual_subject.digest:
                        raise ControlError("APPROVAL_SUBJECT_MISMATCH", receipt["receipt_id"])
                    current_revision = (
                        self.emergency_policy["revision"]
                        if actual_subject.action in self.emergency_policy["permitted_actions"]
                        else self.policy["revision"]
                    )
                    if receipt["policy_revision"] != current_revision:
                        raise ControlError("POLICY_REVISION_MISMATCH", receipt["policy_revision"])
                    if receipt["state"] == "REVOKED":
                        raise ControlError("APPROVAL_REVOKED", receipt["receipt_id"])
                    if receipt["state"] == "CONSUMED":
                        raise ControlError("APPROVAL_ALREADY_CONSUMED", receipt["receipt_id"])
                    if receipt["state"] != "APPROVED":
                        raise ControlError("APPROVAL_UNAVAILABLE", receipt["receipt_id"])
                    if receipt["expires_at"] <= now:
                        raise ControlError("APPROVAL_EXPIRED", receipt["receipt_id"])
                    role, principal = receipt["role"], receipt["principal"]
                    if not self._direct_grant(principal, role, actual_subject, now) and not self._delegated_grant(principal, role, actual_subject, now):
                        raise ControlError("DELEGATED_AUTHORITY_REVOKED", principal)
                    roles.add(role)
                    principals.add(principal)
                if not roles_required <= roles:
                    raise ControlError("REQUIRED_APPROVAL_MISSING", ",".join(sorted(roles_required - roles)))
                if self.policy["distinct_principals"] and len(principals) != len(roles_required):
                    raise ControlError("SEPARATION_OF_DUTIES_VIOLATION", "dual control")
                for receipt_id in receipt_ids:
                    updated = connection.execute("UPDATE receipts SET state = 'CONSUMED' WHERE receipt_id = ? AND state = 'APPROVED'", (receipt_id,))
                    if updated.rowcount != 1:
                        raise ControlError("APPROVAL_ALREADY_CONSUMED", receipt_id)
                connection.execute("INSERT INTO operations VALUES (?, ?, ?, ?, ?)", (execution_id, request_id, actual_subject.digest, actual_subject.action, now))
                self._append_audit(connection, "PROTECTED_ACTION_EXECUTED", execution_id, "protected-executor", "AUTHORIZED", {"request_id": request_id, "receipts": receipt_ids}, now)
                connection.commit()
            return Decision("EXECUTED", "AUTHORIZED", request_id, receipt_ids, execution_id)
        except ControlError as exc:
            self.audit("EXECUTION_DENIED", request_id, "protected-executor", exc.code, {"execution_id": execution_id}, now)
            raise
        except sqlite3.IntegrityError:
            self.audit("EXECUTION_DENIED", request_id, "protected-executor", "APPROVAL_ALREADY_CONSUMED", {"execution_id": execution_id}, now)
            raise ControlError("APPROVAL_ALREADY_CONSUMED", request_id)

    def _append_audit(self, connection: sqlite3.Connection, event_type: str, subject_id: str, principal: str, reason_code: str, payload: dict, now: str) -> None:
        last = connection.execute("SELECT event_digest FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
        previous = last[0] if last else "GENESIS"
        event_id = f"AUD-{connection.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0] + 1:04d}"
        payload_json = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        material = "|".join((event_id, event_type, subject_id, principal, reason_code, payload_json, previous, now))
        digest = "sha256:" + hashlib.sha256(material.encode()).hexdigest()
        connection.execute("INSERT INTO audit_events (event_id,event_type,subject_id,principal,reason_code,payload_json,previous_digest,event_digest,created_at) VALUES (?,?,?,?,?,?,?,?,?)", (event_id, event_type, subject_id, principal, reason_code, payload_json, previous, digest, now))

    def audit(self, event_type: str, subject_id: str, principal: str, reason_code: str, payload: dict, now: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._append_audit(connection, event_type, subject_id, principal, reason_code, payload, now)
            connection.commit()

    def verify_audit_chain(self) -> bool:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM audit_events ORDER BY sequence").fetchall()
        previous = "GENESIS"
        for row in rows:
            material = "|".join((row["event_id"], row["event_type"], row["subject_id"], row["principal"], row["reason_code"], row["payload_json"], previous, row["created_at"]))
            expected = "sha256:" + hashlib.sha256(material.encode()).hexdigest()
            if row["previous_digest"] != previous or row["event_digest"] != expected:
                return False
            previous = row["event_digest"]
        return True

    def audit_events(self) -> list[dict]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM audit_events ORDER BY sequence")]

    def operation_count(self, request_id: str) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM operations WHERE request_id = ?", (request_id,)).fetchone()[0]
