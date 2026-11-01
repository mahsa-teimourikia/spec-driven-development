"""Durable approval, delegation, protected-action, and audit enforcement."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator

from .models import ActionSubject, AuthorityGrant, ControlError, Decision, DelegationGrant, RISK_ORDER


OPERATION_STATES = frozenset({"AUTHORIZED", "DISPATCHED", "SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME"})
_CHECKPOINT_LOCK_GUARD = threading.Lock()
_CHECKPOINT_LOCKS: dict[str, threading.Lock] = {}


def _checkpoint_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _CHECKPOINT_LOCK_GUARD:
        return _CHECKPOINT_LOCKS.setdefault(key, threading.Lock())


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ControlError("TIME_FORMAT_INVALID", value) from exc


class ApprovalControlPlane:
    """Trusted application boundary; callers provide references, never authority facts."""

    def __init__(self, db_path: Path, fixture_root: Path) -> None:
        self.db_path = db_path
        self.checkpoint_path = db_path.with_suffix(db_path.suffix + ".audit-checkpoint.json")
        self.fixture_root = fixture_root
        self.policy = self._load("policies/approval-policy.json")
        self.emergency_policy = self._load("policies/emergency-policy.json")
        self.sessions = self._load("registry/principals.json")["sessions"]
        registry = self._load("registry/authority-grants.json")
        self.authority_registry_revision = registry["revision"]
        self.grants = {item["grant_id"]: self._authority_from_payload(item) for item in registry["grants"]}
        self.delegations: dict[str, DelegationGrant] = {}
        self.incidents = {item["incident_id"]: item for item in self._load("registry/incidents.json")["incidents"]}
        self._initialize()
        self._load_persisted_authority()

    def _load(self, relative: str):
        return json.loads((self.fixture_root / relative).read_text(encoding="utf-8"))

    @staticmethod
    def _authority_from_payload(item: dict) -> AuthorityGrant:
        return AuthorityGrant(
            item["grant_id"], item["principal"], item["role"], frozenset(item["actions"]),
            frozenset(item["resources"]), frozenset(item["environments"]), item["max_risk"],
            item["starts_at"], item["expires_at"], item["delegable"], item.get("state", "ACTIVE"),
        )

    @staticmethod
    def _delegation_from_payload(item: dict) -> DelegationGrant:
        return DelegationGrant(
            item["delegation_id"], item["parent_grant_id"], item["delegator"], item["delegate"],
            item["role"], frozenset(item["actions"]), frozenset(item["resources"]),
            frozenset(item["environments"]), item["max_risk"], item["starts_at"], item["expires_at"],
            item["may_redelegate"], item.get("state", "ACTIVE"),
        )

    @staticmethod
    def _jsonable(value) -> dict:
        payload = asdict(value)
        for key, item in tuple(payload.items()):
            if isinstance(item, (set, frozenset)):
                payload[key] = sorted(item)
        return payload

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
                    authority_source TEXT NOT NULL, authority_registry_revision TEXT NOT NULL,
                    authority_snapshot_digest TEXT NOT NULL, issued_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                    usage TEXT NOT NULL, state TEXT NOT NULL,
                    UNIQUE(request_id, role)
                );
                CREATE TABLE IF NOT EXISTS delegations (
                    delegation_id TEXT PRIMARY KEY, delegation_json TEXT NOT NULL,
                    state TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS grant_overrides (
                    grant_id TEXT PRIMARY KEY, grant_json TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS authority_snapshots (
                    snapshot_digest TEXT PRIMARY KEY, registry_revision TEXT NOT NULL,
                    authority_source TEXT NOT NULL, snapshot_json TEXT NOT NULL, captured_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS protected_resources (
                    resource TEXT PRIMARY KEY, state_json TEXT NOT NULL, version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operations (
                    execution_id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
                    subject_digest TEXT NOT NULL, effect TEXT NOT NULL, state TEXT NOT NULL,
                    result_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operation_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, execution_id TEXT NOT NULL,
                    state TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL, subject_id TEXT NOT NULL, principal TEXT NOT NULL,
                    reason_code TEXT NOT NULL, payload_json TEXT NOT NULL,
                    previous_digest TEXT NOT NULL, event_digest TEXT NOT NULL, created_at TEXT NOT NULL
                );
            """)
            resources = {
                "underwriting-assistant-production": {
                    "ai_classification_enabled": True,
                    "manual_review_required": False,
                    "deployed_artifact_digest": "sha256:baseline-underwriting-v1",
                },
                "underwriting-platform": {"last_exception_digest": None},
            }
            for resource, state in resources.items():
                connection.execute(
                    "INSERT OR IGNORE INTO protected_resources VALUES (?, ?, 1)",
                    (resource, json.dumps(state, sort_keys=True)),
                )

    def _load_persisted_authority(self) -> None:
        with self._connect() as connection:
            for row in connection.execute("SELECT grant_json FROM grant_overrides"):
                grant = self._authority_from_payload(json.loads(row["grant_json"]))
                self.grants[grant.grant_id] = grant
            for row in connection.execute("SELECT delegation_json FROM delegations WHERE state = 'ACTIVE'"):
                delegation = self._delegation_from_payload(json.loads(row["delegation_json"]))
                self.delegations[delegation.delegation_id] = delegation

    def authenticate(self, session_id: str) -> str:
        principal = self.sessions.get(session_id)
        if not principal:
            raise ControlError("UNAUTHENTICATED_PRINCIPAL", session_id)
        return principal

    def _current_policy_revision(self, subject: ActionSubject) -> str:
        return self.emergency_policy["revision"] if subject.action in self.emergency_policy["permitted_actions"] else self.policy["revision"]

    def required_roles(self, subject: ActionSubject) -> tuple[str, ...]:
        if subject.policy_revision != self._current_policy_revision(subject):
            raise ControlError("POLICY_REVISION_MISMATCH", subject.policy_revision)
        if subject.action in self.emergency_policy["permitted_actions"]:
            incident = self.incidents.get(subject.incident_id or "")
            if not incident or incident["state"] != "ACTIVE" or incident["severity"] not in self.emergency_policy["severities"]:
                raise ControlError("EMERGENCY_AUTHORIZATION_DENIED", subject.incident_id or "missing incident")
            if subject.resource not in incident["resources"]:
                raise ControlError("EMERGENCY_SCOPE_VIOLATION", subject.resource)
            return (self.emergency_policy["required_role"],)
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
        self._sync_audit_checkpoint()
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

    def _delegation_is_contained(self, delegation: DelegationGrant, parent: AuthorityGrant, now: str | None = None) -> bool:
        contained = (
            parent.state == "ACTIVE" and parent.delegable
            and delegation.role == parent.role
            and delegation.actions <= parent.actions
            and delegation.resources <= parent.resources
            and delegation.environments <= parent.environments
            and RISK_ORDER[delegation.max_risk] <= RISK_ORDER[parent.max_risk]
            and parent.starts_at <= delegation.starts_at < delegation.expires_at <= parent.expires_at
            and not delegation.may_redelegate and delegation.state == "ACTIVE"
        )
        if now is not None:
            contained = contained and parent.starts_at <= now < parent.expires_at and delegation.starts_at <= now < delegation.expires_at
        return contained

    def _delegated_grant(self, principal: str, role: str, subject: ActionSubject, now: str) -> DelegationGrant | None:
        for delegation in self.delegations.values():
            parent = self.grants.get(delegation.parent_grant_id)
            if not parent or not self._delegation_is_contained(delegation, parent, now):
                continue
            if (
                delegation.delegate == principal and delegation.role == role
                and subject.action in delegation.actions and subject.resource in delegation.resources
                and subject.environment in delegation.environments
                and RISK_ORDER[subject.risk_tier] <= RISK_ORDER[delegation.max_risk]
            ):
                return delegation
        return None

    def issue_delegation(self, delegation: DelegationGrant, authenticated_session: str, now: str) -> DelegationGrant:
        principal = self.authenticate(authenticated_session)
        parent = self.grants.get(delegation.parent_grant_id)
        if not parent or parent.principal != principal or delegation.delegator != principal:
            raise ControlError("DELEGATION_CHAIN_INVALID", delegation.parent_grant_id)
        if not self._delegation_is_contained(delegation, parent, now):
            raise ControlError("DELEGATION_SCOPE_EXPANSION", delegation.delegation_id)
        payload = self._jsonable(delegation)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO delegations VALUES (?, ?, 'ACTIVE', ?)",
                (delegation.delegation_id, json.dumps(payload, sort_keys=True), now),
            )
            self._append_audit(connection, "DELEGATION_ISSUED", delegation.delegation_id, principal, "AUTHORIZED", payload, now)
            connection.commit()
        self.delegations[delegation.delegation_id] = delegation
        self._sync_audit_checkpoint()
        return delegation

    def _persist_grant(self, grant: AuthorityGrant, now: str, event_type: str) -> None:
        payload = self._jsonable(grant)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO grant_overrides VALUES (?, ?, ?) ON CONFLICT(grant_id) DO UPDATE SET grant_json=excluded.grant_json, updated_at=excluded.updated_at",
                (grant.grant_id, json.dumps(payload, sort_keys=True), now),
            )
            self._append_audit(connection, event_type, grant.grant_id, "authority-registry", grant.state, payload, now)
            connection.commit()
        self.grants[grant.grant_id] = grant
        self._sync_audit_checkpoint()

    def narrow_grant(
        self, grant_id: str, now: str, *, actions: frozenset[str] | None = None,
        resources: frozenset[str] | None = None, environments: frozenset[str] | None = None,
        max_risk: str | None = None, expires_at: str | None = None,
    ) -> AuthorityGrant:
        current = self.grants[grant_id]
        updated = replace(
            current,
            actions=current.actions if actions is None else actions,
            resources=current.resources if resources is None else resources,
            environments=current.environments if environments is None else environments,
            max_risk=current.max_risk if max_risk is None else max_risk,
            expires_at=current.expires_at if expires_at is None else expires_at,
        )
        if not (
            updated.actions <= current.actions and updated.resources <= current.resources
            and updated.environments <= current.environments
            and RISK_ORDER[updated.max_risk] <= RISK_ORDER[current.max_risk]
            and updated.expires_at <= current.expires_at and updated.state == "ACTIVE"
        ):
            raise ControlError("GRANT_SCOPE_EXPANSION", grant_id)
        self._persist_grant(updated, now, "AUTHORITY_GRANT_NARROWED")
        return updated

    def revoke_grant(self, grant_id: str, now: str) -> None:
        self._persist_grant(replace(self.grants[grant_id], state="REVOKED"), now, "AUTHORITY_GRANT_REVOKED")

    def _authority_snapshot(self, direct: AuthorityGrant | None, delegated: DelegationGrant | None) -> tuple[str, str, dict]:
        if direct:
            payload = {"kind": "direct", "grant": self._jsonable(direct)}
            source = direct.grant_id
        else:
            assert delegated is not None
            payload = {"kind": "delegated", "delegation": self._jsonable(delegated), "parent": self._jsonable(self.grants[delegated.parent_grant_id])}
            source = delegated.delegation_id
        material = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return source, "sha256:" + hashlib.sha256(material.encode()).hexdigest(), payload

    def _validate_receipt_lifetime(self, subject: ActionSubject, now: str, expires_at: str, direct: AuthorityGrant | None, delegated: DelegationGrant | None) -> None:
        issued, expiry = _parse_time(now), _parse_time(expires_at)
        maximum_minutes = self.emergency_policy["max_duration_minutes"] if subject.action in self.emergency_policy["permitted_actions"] else self.policy["max_approval_lifetime_minutes"]
        authority_expiry = _parse_time(direct.expires_at if direct else delegated.expires_at)
        if not issued < expiry <= authority_expiry or expiry > issued + timedelta(minutes=maximum_minutes):
            raise ControlError("RECEIPT_LIFETIME_EXCEEDED", expires_at)

    def decide(self, request_id: str, approver_session: str, role: str, outcome: str, now: str, expires_at: str) -> Decision:
        principal = self.authenticate(approver_session)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
            if not request:
                raise ControlError("REQUEST_NOT_FOUND", request_id)
            if request["state"] in {"REJECTED", "COMPLETED"}:
                raise ControlError("INVALID_REQUEST_TRANSITION", request["state"])
            subject = ActionSubject(**json.loads(request["subject_json"]))
            required = set(self.required_roles(subject))
            if role not in required:
                raise ControlError("APPROVER_NOT_AUTHORIZED", role)
            if principal in {request["requester"], request["implementation_author"]}:
                raise ControlError("SEPARATION_OF_DUTIES_VIOLATION", principal)
            direct = self._direct_grant(principal, role, subject, now)
            delegated = self._delegated_grant(principal, role, subject, now)
            if not direct and not delegated:
                raise ControlError("AUTHORITY_SCOPE_DENIED", principal)
            if outcome == "REJECTED":
                connection.execute("UPDATE requests SET state = 'REJECTED' WHERE request_id = ?", (request_id,))
                connection.execute("UPDATE receipts SET state = 'REVOKED' WHERE request_id = ? AND state = 'APPROVED'", (request_id,))
                self._append_audit(connection, "REQUEST_REJECTED", request_id, principal, "REJECTED_AND_RECEIPTS_REVOKED", {}, now)
                connection.commit()
                decision = Decision("REJECTED", "REJECTED_AND_RECEIPTS_REVOKED", request_id)
            elif outcome == "APPROVED":
                existing_principals = {row["principal"] for row in connection.execute("SELECT principal FROM receipts WHERE request_id = ? AND state = 'APPROVED'", (request_id,))}
                if self.policy["distinct_principals"] and principal in existing_principals:
                    raise ControlError("SEPARATION_OF_DUTIES_VIOLATION", "dual control")
                self._validate_receipt_lifetime(subject, now, expires_at, direct, delegated)
                source, snapshot_digest, snapshot = self._authority_snapshot(direct, delegated)
                connection.execute(
                    "INSERT OR IGNORE INTO authority_snapshots VALUES (?, ?, ?, ?, ?)",
                    (snapshot_digest, self.authority_registry_revision, source, json.dumps(snapshot, sort_keys=True, separators=(",", ":")), now),
                )
                receipt_id = f"APR-{request_id}-{role}"
                connection.execute(
                    "INSERT INTO receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'single_use', 'APPROVED')",
                    (receipt_id, request_id, principal, role, subject.digest, subject.policy_revision, source, self.authority_registry_revision, snapshot_digest, now, expires_at),
                )
                active = list(connection.execute("SELECT role, principal FROM receipts WHERE request_id = ? AND state = 'APPROVED'", (request_id,)))
                roles, principals = {row["role"] for row in active}, {row["principal"] for row in active}
                request_state = "APPROVED" if required <= roles and (not self.policy["distinct_principals"] or len(principals) == len(required)) else "PARTIALLY_APPROVED"
                connection.execute("UPDATE requests SET state = ? WHERE request_id = ?", (request_state, request_id))
                self._append_audit(
                    connection, "APPROVAL_ISSUED", receipt_id, principal, "APPROVED",
                    {"request_id": request_id, "role": role, "subject_digest": subject.digest, "authority_source": source, "authority_registry_revision": self.authority_registry_revision, "authority_snapshot_digest": snapshot_digest, "request_state": request_state}, now,
                )
                connection.commit()
                decision = Decision("APPROVED", request_state, request_id, (receipt_id,))
            else:
                raise ControlError("DECISION_OUTCOME_INVALID", outcome)
        self._sync_audit_checkpoint()
        return decision

    def revoke_receipt(self, receipt_id: str, now: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            receipt = connection.execute("SELECT request_id FROM receipts WHERE receipt_id = ? AND state = 'APPROVED'", (receipt_id,)).fetchone()
            if not receipt:
                raise ControlError("APPROVAL_UNAVAILABLE", receipt_id)
            connection.execute("UPDATE receipts SET state = 'REVOKED' WHERE receipt_id = ?", (receipt_id,))
            connection.execute("UPDATE requests SET state = 'PARTIALLY_APPROVED' WHERE request_id = ? AND state = 'APPROVED'", (receipt["request_id"],))
            self._append_audit(connection, "APPROVAL_REVOKED", receipt_id, "approval-service", "REVOKED", {}, now)
            connection.commit()
        self._sync_audit_checkpoint()

    def _append_operation_event(self, connection: sqlite3.Connection, execution_id: str, state: str, payload: dict, now: str) -> None:
        if state not in OPERATION_STATES:
            raise ControlError("OPERATION_STATE_INVALID", state)
        connection.execute(
            "INSERT INTO operation_events (execution_id,state,payload_json,created_at) VALUES (?,?,?,?)",
            (execution_id, state, json.dumps(payload, sort_keys=True, separators=(",", ":")), now),
        )

    def _apply_protected_action(self, connection: sqlite3.Connection, subject: ActionSubject) -> dict:
        row = connection.execute("SELECT * FROM protected_resources WHERE resource = ?", (subject.resource,)).fetchone()
        if not row:
            raise ControlError("PROTECTED_RESOURCE_NOT_FOUND", subject.resource)
        state = json.loads(row["state_json"])
        if subject.action == "deploy":
            state["deployed_artifact_digest"] = subject.artifact_digest
            success = state["deployed_artifact_digest"] == subject.artifact_digest
        elif subject.action in {"disable_ai_classification", "restore_manual_review"}:
            state["ai_classification_enabled"] = False
            state["manual_review_required"] = True
            success = not state["ai_classification_enabled"] and state["manual_review_required"]
        elif subject.action == "approve_low_risk_exception":
            state["last_exception_digest"] = subject.artifact_digest
            success = state["last_exception_digest"] == subject.artifact_digest
        else:
            raise ControlError("PROTECTED_ACTION_UNSUPPORTED", subject.action)
        if not success:
            raise ControlError("ACTION_EFFECT_NOT_VERIFIED", subject.resource)
        version = row["version"] + 1
        connection.execute(
            "UPDATE protected_resources SET state_json = ?, version = ? WHERE resource = ? AND version = ?",
            (json.dumps(state, sort_keys=True), version, subject.resource, row["version"]),
        )
        return {"resource": subject.resource, "version": version, "state": state, "success_condition_verified": True}

    def execute(self, request_id: str, receipt_ids: Iterable[str], expected_subject: ActionSubject, execution_id: str, now: str) -> Decision:
        receipt_ids = tuple(sorted(set(receipt_ids)))
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                request = connection.execute("SELECT * FROM requests WHERE request_id = ?", (request_id,)).fetchone()
                if not request:
                    raise ControlError("REQUEST_NOT_FOUND", request_id)
                if request["state"] == "REJECTED":
                    raise ControlError("REQUEST_NOT_AUTHORIZED", request["state"])
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
                    if receipt["policy_revision"] != self._current_policy_revision(actual_subject):
                        raise ControlError("POLICY_REVISION_MISMATCH", receipt["policy_revision"])
                    if receipt["state"] == "REVOKED":
                        raise ControlError("APPROVAL_REVOKED", receipt["receipt_id"])
                    if receipt["state"] == "CONSUMED":
                        raise ControlError("APPROVAL_ALREADY_CONSUMED", receipt["receipt_id"])
                    if receipt["state"] != "APPROVED":
                        raise ControlError("APPROVAL_UNAVAILABLE", receipt["receipt_id"])
                    if receipt["expires_at"] <= now:
                        raise ControlError("APPROVAL_EXPIRED", receipt["receipt_id"])
                    snapshot = connection.execute("SELECT * FROM authority_snapshots WHERE snapshot_digest = ?", (receipt["authority_snapshot_digest"],)).fetchone()
                    if not snapshot or snapshot["authority_source"] != receipt["authority_source"] or snapshot["registry_revision"] != receipt["authority_registry_revision"]:
                        raise ControlError("APPROVAL_PROVENANCE_UNVERIFIED", receipt["receipt_id"])
                    role, principal = receipt["role"], receipt["principal"]
                    direct = self._direct_grant(principal, role, actual_subject, now)
                    delegated = self._delegated_grant(principal, role, actual_subject, now)
                    current_source = direct.grant_id if direct else delegated.delegation_id if delegated else None
                    if current_source != receipt["authority_source"]:
                        raise ControlError("DELEGATED_AUTHORITY_REVOKED", principal)
                    roles.add(role)
                    principals.add(principal)
                if not roles_required <= roles:
                    raise ControlError("REQUIRED_APPROVAL_MISSING", ",".join(sorted(roles_required - roles)))
                if self.policy["distinct_principals"] and len(principals) != len(roles_required):
                    raise ControlError("SEPARATION_OF_DUTIES_VIOLATION", "dual control")
                if request["state"] not in {"APPROVED", "COMPLETED"}:
                    raise ControlError("REQUEST_NOT_AUTHORIZED", request["state"])
                for receipt_id in receipt_ids:
                    updated = connection.execute("UPDATE receipts SET state = 'CONSUMED' WHERE receipt_id = ? AND state = 'APPROVED'", (receipt_id,))
                    if updated.rowcount != 1:
                        raise ControlError("APPROVAL_ALREADY_CONSUMED", receipt_id)

                connection.execute("INSERT INTO operations VALUES (?, ?, ?, ?, 'AUTHORIZED', '{}', ?, ?)", (execution_id, request_id, actual_subject.digest, actual_subject.action, now, now))
                self._append_operation_event(connection, execution_id, "AUTHORIZED", {"receipts": receipt_ids}, now)
                self._append_audit(connection, "OPERATION_AUTHORIZED", execution_id, "protected-executor", "RECEIPTS_CONSUMED", {"request_id": request_id}, now)
                connection.execute("UPDATE operations SET state = 'DISPATCHED', updated_at = ? WHERE execution_id = ?", (now, execution_id))
                self._append_operation_event(connection, execution_id, "DISPATCHED", {"action": actual_subject.action}, now)
                result = self._apply_protected_action(connection, actual_subject)
                connection.execute("UPDATE operations SET state = 'SUCCEEDED', result_json = ?, updated_at = ? WHERE execution_id = ?", (json.dumps(result, sort_keys=True), now, execution_id))
                self._append_operation_event(connection, execution_id, "SUCCEEDED", result, now)
                connection.execute("UPDATE requests SET state = 'COMPLETED' WHERE request_id = ?", (request_id,))
                self._append_audit(connection, "PROTECTED_ACTION_SUCCEEDED", execution_id, "protected-executor", "ACTION_EFFECT_VERIFIED", result, now)
                connection.commit()
            self._sync_audit_checkpoint()
            return Decision("SUCCEEDED", "ACTION_EFFECT_VERIFIED", request_id, receipt_ids, execution_id)
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
        connection.execute(
            "INSERT INTO audit_events (event_id,event_type,subject_id,principal,reason_code,payload_json,previous_digest,event_digest,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (event_id, event_type, subject_id, principal, reason_code, payload_json, previous, digest, now),
        )

    def _sync_audit_checkpoint(self) -> None:
        with _checkpoint_lock(self.checkpoint_path):
            with self._connect() as connection:
                row = connection.execute("SELECT sequence, event_digest FROM audit_events ORDER BY sequence DESC LIMIT 1").fetchone()
            if not row:
                return
            current = {"sequence": row["sequence"], "event_digest": row["event_digest"]}
            current["checkpoint_digest"] = "sha256:" + hashlib.sha256(f"{current['sequence']}|{current['event_digest']}".encode()).hexdigest()
            if self.checkpoint_path.exists():
                retained = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
                if retained.get("sequence", 0) > current["sequence"]:
                    return
            temporary = self.checkpoint_path.with_suffix(self.checkpoint_path.suffix + ".tmp")
            temporary.write_text(json.dumps(current, sort_keys=True), encoding="utf-8")
            temporary.replace(self.checkpoint_path)

    def audit(self, event_type: str, subject_id: str, principal: str, reason_code: str, payload: dict, now: str) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._append_audit(connection, event_type, subject_id, principal, reason_code, payload, now)
            connection.commit()
        self._sync_audit_checkpoint()

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
        if not rows or not self.checkpoint_path.exists():
            return False
        checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))
        checkpoint_digest = "sha256:" + hashlib.sha256(f"{checkpoint.get('sequence')}|{checkpoint.get('event_digest')}".encode()).hexdigest()
        return checkpoint.get("checkpoint_digest") == checkpoint_digest and checkpoint.get("sequence") == rows[-1]["sequence"] and checkpoint.get("event_digest") == rows[-1]["event_digest"]

    def audit_events(self) -> list[dict]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM audit_events ORDER BY sequence")]

    def operation_count(self, request_id: str) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM operations WHERE request_id = ? AND state = 'SUCCEEDED'", (request_id,)).fetchone()[0]

    def operation(self, execution_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM operations WHERE execution_id = ?", (execution_id,)).fetchone()
            return dict(row) if row else {}

    def operation_events(self, execution_id: str) -> list[dict]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM operation_events WHERE execution_id = ? ORDER BY sequence", (execution_id,))]

    def resource_state(self, resource: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT state_json, version FROM protected_resources WHERE resource = ?", (resource,)).fetchone()
        if not row:
            raise ControlError("PROTECTED_RESOURCE_NOT_FOUND", resource)
        return {"resource": resource, "version": row["version"], "state": json.loads(row["state_json"])}

    def request_state(self, request_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute("SELECT state FROM requests WHERE request_id = ?", (request_id,)).fetchone()
            return row["state"] if row else "NOT_FOUND"

    def receipt(self, receipt_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
            if not row:
                return {}
            result = dict(row)
            snapshot = connection.execute(
                "SELECT snapshot_json FROM authority_snapshots WHERE snapshot_digest = ?",
                (row["authority_snapshot_digest"],),
            ).fetchone()
        result["authority_snapshot"] = json.loads(snapshot["snapshot_json"]) if snapshot else None
        return result
