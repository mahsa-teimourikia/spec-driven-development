"""Trusted evidence resolution, release policy, deployment, and recovery."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from .builder import file_digest, verify_statement
from .models import Decision, Evidence, ReleaseError, ReleaseManifest


RELEASE_STATES = frozenset({
    "CANDIDATE", "BLOCKED", "ELIGIBLE_FOR_RELEASE_REVIEW", "AUTHORIZED", "DISPATCHED",
    "VERIFYING", "ACTIVE", "HALTED", "FAILED", "UNKNOWN_OUTCOME", "RECOVERY_INCOMPLETE",
    "RECOVERY_IN_PROGRESS", "RECOVERED",
})


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ReleaseControlPlane:
    """Application-owned trust boundary; candidate metadata never grants release authority."""

    def __init__(self, db_path: Path, root: Path) -> None:
        self.db_path = db_path
        self.root = root
        self.policy = self._load("policies/release-policy.json")
        self.trust = self._load("policies/trust-policy.json")
        self.sessions = self._load("registry/principals.json")["sessions"]
        self._initialize()

    def _load(self, relative: str):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

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
                CREATE TABLE IF NOT EXISTS artifacts (
                    release_id TEXT PRIMARY KEY, artifact_digest TEXT NOT NULL, source_commit TEXT NOT NULL,
                    provenance_json TEXT NOT NULL, signature TEXT NOT NULL, registered_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY, release_id TEXT NOT NULL, kind TEXT NOT NULL,
                    subject_digest TEXT NOT NULL, producer TEXT NOT NULL, result TEXT NOT NULL,
                    evidence_json TEXT NOT NULL, evidence_digest TEXT NOT NULL, registered_at TEXT NOT NULL,
                    UNIQUE(release_id, kind)
                );
                CREATE TABLE IF NOT EXISTS releases (
                    release_id TEXT PRIMARY KEY, manifest_json TEXT NOT NULL, manifest_digest TEXT NOT NULL,
                    state TEXT NOT NULL, findings_json TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    receipt_id TEXT PRIMARY KEY, release_id TEXT NOT NULL, manifest_digest TEXT NOT NULL,
                    environment TEXT NOT NULL, principal TEXT NOT NULL, role TEXT NOT NULL,
                    issued_at TEXT NOT NULL, expires_at TEXT NOT NULL, state TEXT NOT NULL,
                    UNIQUE(release_id, role)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY, release_id TEXT NOT NULL UNIQUE, manifest_digest TEXT NOT NULL,
                    state TEXT NOT NULL, result_json TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operation_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL,
                    state TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS environments (
                    environment TEXT PRIMARY KEY, release_id TEXT, manifest_json TEXT,
                    feature_enabled INTEGER NOT NULL, manual_review_required INTEGER NOT NULL,
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reconciliation (
                    incident_id TEXT PRIMARY KEY, failed_release TEXT NOT NULL, target_release TEXT NOT NULL,
                    state TEXT NOT NULL, record_json TEXT NOT NULL, updated_at TEXT NOT NULL
                );
            """)
            connection.execute(
                "INSERT OR IGNORE INTO environments VALUES ('production', NULL, NULL, 0, 1, 1)"
            )

    def authenticate(self, session_id: str) -> str:
        principal = self.sessions.get(session_id)
        if not principal:
            raise ReleaseError("UNAUTHENTICATED_PRINCIPAL", session_id)
        return principal

    def register_artifact(
        self, release_id: str, artifact_path: Path, source_commit: str,
        statement: dict, signature: str, now: str,
    ) -> str:
        build = statement.get("build", {})
        builder_id = build.get("builder_id")
        builder = self.trust["builders"].get(builder_id)
        if not builder or not verify_statement(statement, signature, builder["verification_key"]):
            raise ReleaseError("PROVENANCE_IDENTITY_UNTRUSTED", str(builder_id))
        if build.get("workflow_revision") != builder["workflow_revision"]:
            raise ReleaseError("PROVENANCE_WORKFLOW_UNAPPROVED", str(build.get("workflow_revision")))
        if build.get("source_branch") not in builder["source_branches"]:
            raise ReleaseError("PROVENANCE_SOURCE_UNAPPROVED", str(build.get("source_branch")))
        digest = file_digest(artifact_path)
        if statement.get("subject", {}).get("digest") != digest:
            raise ReleaseError("ARTIFACT_MISMATCH", digest)
        if build.get("source_commit") != source_commit or not build.get("dependencies_locked"):
            raise ReleaseError("PROVENANCE_BUILD_INVALID", source_commit)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?)",
                (release_id, digest, source_commit, json.dumps(statement, sort_keys=True), signature, now),
            )
        return digest

    @staticmethod
    def evidence_signature(evidence: Evidence, key: str) -> str:
        material = json.dumps(asdict(evidence), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "hmac-sha256:" + hmac.new(key.encode("utf-8"), material, hashlib.sha256).hexdigest()

    def register_evidence(self, release_id: str, evidence: Evidence, signature: str, now: str) -> None:
        trusted = self.trust["evidence_producers"].get(evidence.kind, {})
        verification_key = trusted.get(evidence.producer)
        if not verification_key:
            raise ReleaseError("EVIDENCE_PRODUCER_UNTRUSTED", f"{evidence.kind}:{evidence.producer}")
        if not hmac.compare_digest(self.evidence_signature(evidence, verification_key), signature):
            raise ReleaseError("EVIDENCE_AUTHENTICITY_UNVERIFIED", evidence.evidence_id)
        with self._connect() as connection:
            release = connection.execute(
                "SELECT manifest_digest FROM releases WHERE release_id = ?", (release_id,)
            ).fetchone()
            if release and release["manifest_digest"] != evidence.subject_digest:
                raise ReleaseError("EVIDENCE_SUBJECT_MISMATCH", evidence.evidence_id)
            connection.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    evidence.evidence_id, release_id, evidence.kind, evidence.subject_digest,
                    evidence.producer, evidence.result, json.dumps(asdict(evidence), sort_keys=True),
                    evidence.digest, now,
                ),
            )

    def submit_candidate(self, manifest: ReleaseManifest, now: str) -> Decision:
        if manifest.risk_tier not in self.policy["required_evidence"]:
            raise ReleaseError("RISK_TIER_UNRESOLVED", manifest.risk_tier)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO releases VALUES (?, ?, ?, 'CANDIDATE', '[]', ?)",
                (manifest.release_id, json.dumps(asdict(manifest), sort_keys=True), manifest.digest, now),
            )
        return Decision("CANDIDATE", (), manifest.release_id, manifest.digest)

    def _evidence_findings(self, connection: sqlite3.Connection, manifest: ReleaseManifest) -> list[str]:
        findings: list[str] = []
        artifact = connection.execute(
            "SELECT * FROM artifacts WHERE release_id = ?", (manifest.release_id,)
        ).fetchone()
        if not artifact:
            findings.append("BUILD_PROVENANCE_MISSING")
        elif artifact["artifact_digest"] != manifest.artifact_digest:
            findings.append("ARTIFACT_MISMATCH")
        elif artifact["source_commit"] != manifest.source_commit:
            findings.append("SOURCE_REVISION_MISMATCH")
        if manifest.tool_policy_revision not in self.policy["approved_tool_policy_revisions"]:
            findings.append("TOOL_POLICY_UNAPPROVED")
        rows = {
            row["kind"]: row for row in connection.execute(
                "SELECT * FROM evidence WHERE release_id = ?", (manifest.release_id,)
            )
        }
        for kind in self.policy["required_evidence"][manifest.risk_tier]:
            row = rows.get(kind)
            if not row:
                findings.append(f"MISSING_EVIDENCE:{kind}")
                continue
            evidence = Evidence(**json.loads(row["evidence_json"]))
            if evidence.subject_digest != manifest.digest:
                findings.append(f"STALE_EVIDENCE:{kind}")
                continue
            required_dependencies = self.policy["evidence_dependencies"].get(kind, [])
            if any(evidence.dependencies.get(key) != manifest.dependencies[key] for key in required_dependencies):
                findings.append(f"STALE_EVIDENCE:{kind}")
            elif evidence.result != "PASS":
                findings.append(f"EVIDENCE_FAILED:{kind}")
        return sorted(set(findings))

    def evaluate(self, manifest: ReleaseManifest, artifact_path: Path, now: str) -> Decision:
        with self._connect() as connection:
            release = connection.execute(
                "SELECT * FROM releases WHERE release_id = ?", (manifest.release_id,)
            ).fetchone()
            if not release or release["manifest_digest"] != manifest.digest:
                raise ReleaseError("RELEASE_MANIFEST_UNTRUSTED", manifest.release_id)
            findings = self._evidence_findings(connection, manifest)
            if file_digest(artifact_path) != manifest.artifact_digest:
                findings.append("ARTIFACT_MISMATCH")
            findings = sorted(set(findings))
            state = "BLOCKED" if findings else "ELIGIBLE_FOR_RELEASE_REVIEW"
            connection.execute(
                "UPDATE releases SET state = ?, findings_json = ?, updated_at = ? WHERE release_id = ?",
                (state, json.dumps(findings), now, manifest.release_id),
            )
        return Decision(state, tuple(findings), manifest.release_id, manifest.digest)

    def approve(
        self, release_id: str, manifest_digest: str, environment: str, session_id: str,
        role: str, now: str, expires_at: str,
    ) -> str:
        principal = self.authenticate(session_id)
        if self.trust["authority"].get(principal) != role or role not in self.policy["required_approval_roles"]:
            raise ReleaseError("APPROVER_NOT_AUTHORIZED", principal)
        if not _time(now) < _time(expires_at):
            raise ReleaseError("APPROVAL_EXPIRY_INVALID", expires_at)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            release = connection.execute("SELECT * FROM releases WHERE release_id = ?", (release_id,)).fetchone()
            if not release or release["state"] != "ELIGIBLE_FOR_RELEASE_REVIEW":
                raise ReleaseError("RELEASE_NOT_ELIGIBLE", release_id)
            if release["manifest_digest"] != manifest_digest:
                raise ReleaseError("APPROVAL_SUBJECT_MISMATCH", release_id)
            existing = connection.execute(
                "SELECT principal FROM approvals WHERE release_id = ? AND state = 'APPROVED'", (release_id,)
            ).fetchall()
            if principal in {row["principal"] for row in existing}:
                raise ReleaseError("SEPARATION_OF_DUTIES_VIOLATION", principal)
            receipt_id = f"REL-APR-{release_id}-{role}"
            connection.execute(
                "INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED')",
                (receipt_id, release_id, manifest_digest, environment, principal, role, now, expires_at),
            )
            connection.commit()
        return receipt_id

    def _operation_event(
        self, connection: sqlite3.Connection, operation_id: str, state: str, payload: dict, now: str,
    ) -> None:
        if state not in RELEASE_STATES:
            raise ReleaseError("RELEASE_STATE_INVALID", state)
        connection.execute(
            "INSERT INTO operation_events (operation_id,state,payload_json,created_at) VALUES (?,?,?,?)",
            (operation_id, state, json.dumps(payload, sort_keys=True), now),
        )

    def deploy(
        self, manifest: ReleaseManifest, receipt_ids: Iterable[str], operation_id: str, now: str,
        *, timeout_after_effect: bool = False,
    ) -> Decision:
        receipt_ids = tuple(sorted(set(receipt_ids)))
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                release = connection.execute("SELECT * FROM releases WHERE release_id = ?", (manifest.release_id,)).fetchone()
                if not release or release["state"] != "ELIGIBLE_FOR_RELEASE_REVIEW":
                    raise ReleaseError("RELEASE_NOT_ELIGIBLE", manifest.release_id)
                receipts = [connection.execute("SELECT * FROM approvals WHERE receipt_id = ?", (item,)).fetchone() for item in receipt_ids]
                if any(item is None for item in receipts):
                    raise ReleaseError("APPROVAL_UNTRUSTED", manifest.release_id)
                roles, principals = set(), set()
                for receipt in receipts:
                    if receipt["release_id"] != manifest.release_id or receipt["manifest_digest"] != manifest.digest or receipt["environment"] != manifest.environment:
                        raise ReleaseError("APPROVAL_SUBJECT_MISMATCH", receipt["receipt_id"])
                    if receipt["state"] == "CONSUMED":
                        raise ReleaseError("APPROVAL_ALREADY_CONSUMED", receipt["receipt_id"])
                    if receipt["state"] != "APPROVED" or _time(receipt["expires_at"]) <= _time(now):
                        raise ReleaseError("APPROVAL_EXPIRED_OR_REVOKED", receipt["receipt_id"])
                    roles.add(receipt["role"])
                    principals.add(receipt["principal"])
                required = set(self.policy["required_approval_roles"])
                if roles != required or len(principals) != len(required):
                    raise ReleaseError("REQUIRED_APPROVAL_MISSING", manifest.release_id)
                for receipt_id in receipt_ids:
                    updated = connection.execute(
                        "UPDATE approvals SET state = 'CONSUMED' WHERE receipt_id = ? AND state = 'APPROVED'", (receipt_id,)
                    )
                    if updated.rowcount != 1:
                        raise ReleaseError("APPROVAL_ALREADY_CONSUMED", receipt_id)
                connection.execute(
                    "INSERT INTO operations VALUES (?, ?, ?, 'AUTHORIZED', '{}', ?)",
                    (operation_id, manifest.release_id, manifest.digest, now),
                )
                self._operation_event(connection, operation_id, "AUTHORIZED", {"receipts": receipt_ids}, now)
                connection.execute("UPDATE operations SET state='DISPATCHED', updated_at=? WHERE operation_id=?", (now, operation_id))
                self._operation_event(connection, operation_id, "DISPATCHED", {"environment": manifest.environment}, now)
                current = connection.execute("SELECT version FROM environments WHERE environment = ?", (manifest.environment,)).fetchone()
                connection.execute(
                    "UPDATE environments SET release_id=?, manifest_json=?, feature_enabled=1, manual_review_required=1, version=? WHERE environment=?",
                    (manifest.release_id, json.dumps(asdict(manifest), sort_keys=True), current["version"] + 1, manifest.environment),
                )
                if timeout_after_effect:
                    state, result = "UNKNOWN_OUTCOME", {"reconciliation_required": True}
                else:
                    state, result = "VERIFYING", {"deployment_observed": True}
                connection.execute(
                    "UPDATE operations SET state=?, result_json=?, updated_at=? WHERE operation_id=?",
                    (state, json.dumps(result, sort_keys=True), now, operation_id),
                )
                self._operation_event(connection, operation_id, state, result, now)
                connection.execute("UPDATE releases SET state=?, updated_at=? WHERE release_id=?", (state, now, manifest.release_id))
                connection.commit()
            return Decision(state, (), manifest.release_id, manifest.digest, operation_id)
        except sqlite3.IntegrityError as exc:
            raise ReleaseError("DEPLOYMENT_REPLAYED", manifest.release_id) from exc

    def reconcile_unknown(self, operation_id: str, now: str) -> Decision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute("SELECT * FROM operations WHERE operation_id = ?", (operation_id,)).fetchone()
            if not operation or operation["state"] != "UNKNOWN_OUTCOME":
                raise ReleaseError("RECONCILIATION_NOT_REQUIRED", operation_id)
            release = connection.execute("SELECT * FROM releases WHERE release_id = ?", (operation["release_id"],)).fetchone()
            environment = connection.execute("SELECT * FROM environments WHERE release_id = ?", (operation["release_id"],)).fetchone()
            if not environment or release["manifest_digest"] != operation["manifest_digest"]:
                raise ReleaseError("DEPLOYMENT_STATE_UNRESOLVED", operation_id)
            connection.execute("UPDATE operations SET state='VERIFYING', result_json='{}', updated_at=? WHERE operation_id=?", (now, operation_id))
            connection.execute("UPDATE releases SET state='VERIFYING', updated_at=? WHERE release_id=?", (now, operation["release_id"]))
            self._operation_event(connection, operation_id, "VERIFYING", {"effect_reconciled": True}, now)
            connection.commit()
        return Decision("VERIFYING", (), operation["release_id"], operation["manifest_digest"], operation_id)

    def verify_runtime(self, operation_id: str, observations: list[dict], now: str) -> Decision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute("SELECT * FROM operations WHERE operation_id = ?", (operation_id,)).fetchone()
            if not operation or operation["state"] != "VERIFYING":
                raise ReleaseError("RUNTIME_VERIFICATION_NOT_READY", operation_id)
            failures = []
            if not observations:
                failures.append("RUNTIME_EVIDENCE_MISSING")
            for observation in observations:
                if observation.get("tenant_authorized") is not True:
                    failures.append("TENANT_ISOLATION_VIOLATION")
                if observation.get("ambiguous") and not observation.get("human_review_required"):
                    failures.append("HUMAN_REVIEW_BYPASS")
                if observation.get("protected_mutation"):
                    failures.append("UNAUTHORIZED_PROTECTED_MUTATION")
            state = "HALTED" if failures else "ACTIVE"
            result = {"observations": len(observations), "findings": sorted(set(failures))}
            connection.execute(
                "UPDATE operations SET state=?, result_json=?, updated_at=? WHERE operation_id=?",
                (state, json.dumps(result, sort_keys=True), now, operation_id),
            )
            connection.execute("UPDATE releases SET state=?, findings_json=?, updated_at=? WHERE release_id=?", (state, json.dumps(result["findings"]), now, operation["release_id"]))
            if failures:
                connection.execute(
                    "UPDATE environments SET feature_enabled=0, manual_review_required=1, version=version+1 WHERE release_id=?",
                    (operation["release_id"],),
                )
            self._operation_event(connection, operation_id, state, result, now)
            connection.commit()
        return Decision(state, tuple(result["findings"]), operation["release_id"], operation["manifest_digest"], operation_id)

    def recover(
        self, incident_id: str, failed_release: str, target: ReleaseManifest,
        restored_components: dict[str, str], reconciled: Iterable[str], unresolved: Iterable[str], now: str,
    ) -> Decision:
        with self._connect() as connection:
            target_record = connection.execute(
                "SELECT manifest_digest, state FROM releases WHERE release_id = ?", (target.release_id,)
            ).fetchone()
        if (
            not target_record
            or target_record["manifest_digest"] != target.digest
            or target_record["state"] not in {"ELIGIBLE_FOR_RELEASE_REVIEW", "ACTIVE", "HALTED"}
        ):
            raise ReleaseError("RECOVERY_TARGET_UNTRUSTED", target.release_id)
        required = target.dependencies
        mismatches = sorted(key for key, value in required.items() if restored_components.get(key) != value)
        unresolved = sorted(set(unresolved))
        required_reconciliation = set(self.policy["required_reconciliation"])
        missing_reconciliation = sorted(required_reconciliation - set(reconciled))
        if mismatches:
            state, reasons = "RECOVERY_INCOMPLETE", tuple(f"COMPONENT_NOT_RESTORED:{item}" for item in mismatches)
        elif unresolved or missing_reconciliation:
            state = "RECOVERY_IN_PROGRESS"
            reasons = tuple([*(f"UNRESOLVED:{item}" for item in unresolved), *(f"RECONCILIATION_MISSING:{item}" for item in missing_reconciliation)])
        else:
            state, reasons = "RECOVERED", ()
        record = {
            "failed_release": failed_release, "target_release": target.release_id,
            "restored_components": restored_components, "reconciled": sorted(set(reconciled)),
            "unresolved": unresolved, "reasons": reasons,
        }
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO reconciliation VALUES (?, ?, ?, ?, ?, ?)",
                (incident_id, failed_release, target.release_id, state, json.dumps(record, sort_keys=True), now),
            )
            if state == "RECOVERED":
                current = connection.execute("SELECT version FROM environments WHERE environment=?", (target.environment,)).fetchone()
                connection.execute(
                    "UPDATE environments SET release_id=?, manifest_json=?, feature_enabled=1, manual_review_required=1, version=? WHERE environment=?",
                    (target.release_id, json.dumps(asdict(target), sort_keys=True), current["version"] + 1, target.environment),
                )
        return Decision(state, reasons, target.release_id, target.digest)

    def release_state(self, release_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM releases WHERE release_id=?", (release_id,)).fetchone()
        return dict(row) if row else {}

    def operation_events(self, operation_id: str) -> list[dict]:
        with self._connect() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM operation_events WHERE operation_id=? ORDER BY sequence", (operation_id,))]

    def operation_count(self, release_id: str) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM operations WHERE release_id=?", (release_id,)).fetchone()[0]

    def environment_state(self, environment: str = "production") -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM environments WHERE environment=?", (environment,)).fetchone()
        result = dict(row)
        result["feature_enabled"] = bool(result["feature_enabled"])
        result["manual_review_required"] = bool(result["manual_review_required"])
        result["manifest"] = json.loads(result.pop("manifest_json")) if result["manifest_json"] else None
        return result
