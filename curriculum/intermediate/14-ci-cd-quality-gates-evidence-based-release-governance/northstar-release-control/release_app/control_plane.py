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
from .models import (
    Decision,
    Evidence,
    ReconciliationEvidence,
    ReleaseError,
    ReleaseManifest,
    RuntimeObservation,
)


RELEASE_STATES = frozenset({
    "CANDIDATE", "BLOCKED", "ELIGIBLE_FOR_RELEASE_REVIEW", "AUTHORIZED", "DISPATCHED",
    "VERIFYING", "ACTIVE", "HALTED", "FAILED", "UNKNOWN_OUTCOME", "RECOVERY_INCOMPLETE",
    "RECOVERY_IN_PROGRESS", "RECOVERED",
})


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ReleaseControlPlane:
    """Application-owned trust boundary; candidate metadata never grants authority."""

    def __init__(self, db_path: Path, root: Path, keyring: dict[str, str]) -> None:
        self.db_path = db_path
        self.root = root
        self.keyring = dict(keyring)
        self.policy = self._load("policies/release-policy.json")
        self.trust = self._load("policies/trust-policy.json")
        self.sessions = self._load("registry/principals.json")["sessions"]
        self.registry = db_path.parent / "trusted-artifact-registry"
        self.registry.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _load(self, relative: str):
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def _key(self, key_id: str) -> str:
        key = self.keyring.get(key_id)
        if not key:
            raise ReleaseError("TRUST_KEY_UNAVAILABLE", key_id)
        return key

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
                    provenance_json TEXT NOT NULL, signature TEXT NOT NULL, registry_path TEXT NOT NULL,
                    registered_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY, release_id TEXT NOT NULL, kind TEXT NOT NULL,
                    subject_digest TEXT NOT NULL, producer TEXT NOT NULL, result TEXT NOT NULL,
                    evidence_json TEXT NOT NULL, evidence_digest TEXT NOT NULL, signature TEXT NOT NULL,
                    state TEXT NOT NULL, registered_at TEXT NOT NULL, UNIQUE(release_id, kind)
                );
                CREATE TABLE IF NOT EXISTS releases (
                    release_id TEXT PRIMARY KEY, manifest_json TEXT NOT NULL, manifest_digest TEXT NOT NULL,
                    state TEXT NOT NULL, findings_json TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    receipt_id TEXT PRIMARY KEY, release_id TEXT NOT NULL, manifest_digest TEXT NOT NULL,
                    environment TEXT NOT NULL, capability TEXT NOT NULL, principal TEXT NOT NULL,
                    role TEXT NOT NULL, policy_revision TEXT NOT NULL, authority_revision TEXT NOT NULL,
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
                CREATE TABLE IF NOT EXISTS runtime_observations (
                    observation_id TEXT PRIMARY KEY, operation_id TEXT NOT NULL, release_id TEXT NOT NULL,
                    manifest_digest TEXT NOT NULL, source TEXT NOT NULL, record_json TEXT NOT NULL,
                    signature TEXT NOT NULL, registered_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS environments (
                    environment TEXT PRIMARY KEY, release_id TEXT, manifest_json TEXT,
                    feature_enabled INTEGER NOT NULL, manual_review_required INTEGER NOT NULL,
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS recovery_approvals (
                    receipt_id TEXT PRIMARY KEY, incident_id TEXT NOT NULL, failed_release TEXT NOT NULL,
                    target_release TEXT NOT NULL, manifest_digest TEXT NOT NULL, environment TEXT NOT NULL,
                    principal TEXT NOT NULL, role TEXT NOT NULL, policy_revision TEXT NOT NULL,
                    authority_revision TEXT NOT NULL, expires_at TEXT NOT NULL, state TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reconciliation_evidence (
                    evidence_id TEXT PRIMARY KEY, incident_id TEXT NOT NULL, target_release TEXT NOT NULL,
                    check_name TEXT NOT NULL, record_json TEXT NOT NULL, signature TEXT NOT NULL,
                    state TEXT NOT NULL, registered_at TEXT NOT NULL,
                    UNIQUE(incident_id, check_name)
                );
                CREATE TABLE IF NOT EXISTS reconciliation (
                    incident_id TEXT PRIMARY KEY, failed_release TEXT NOT NULL, target_release TEXT NOT NULL,
                    state TEXT NOT NULL, record_json TEXT NOT NULL, updated_at TEXT NOT NULL
                );
            """)
            connection.execute(
                "INSERT OR IGNORE INTO environments VALUES ('production', NULL, NULL, 0, 1, 1)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO environments VALUES ('staging', NULL, NULL, 0, 1, 1)"
            )

    def authenticate(self, session_id: str) -> str:
        principal = self.sessions.get(session_id)
        if not principal:
            raise ReleaseError("UNAUTHENTICATED_PRINCIPAL", session_id)
        return principal

    def _has_authority(self, principal: str, role: str, environment: str, capability: str) -> bool:
        grant = self.trust["authority"].get(principal, {})
        return (
            grant.get("status") == "ACTIVE"
            and role in grant.get("roles", [])
            and environment in grant.get("environments", [])
            and (capability in grant.get("capabilities", []) or "*" in grant.get("capabilities", []))
        )

    def _required_roles(self, manifest: ReleaseManifest) -> tuple[str, ...]:
        environments = self.policy.get("approval_matrix", {})
        tiers = environments.get(manifest.environment)
        capabilities = tiers.get(manifest.risk_tier) if tiers else None
        roles = capabilities.get(manifest.capability) if capabilities else None
        if roles is None and capabilities:
            roles = capabilities.get("*")
        if not roles:
            raise ReleaseError(
                "APPROVAL_POLICY_UNRESOLVED",
                f"{manifest.environment}:{manifest.risk_tier}:{manifest.capability}",
            )
        return tuple(roles)

    def register_artifact(
        self, release_id: str, artifact_path: Path, source_commit: str,
        statement: dict, signature: str, now: str,
    ) -> str:
        build = statement.get("build", {})
        builder_id = build.get("builder_id")
        builder = self.trust["builders"].get(builder_id)
        key = self._key(builder["key_id"]) if builder else ""
        if not builder or not verify_statement(statement, signature, key):
            raise ReleaseError("PROVENANCE_IDENTITY_UNTRUSTED", str(builder_id))
        if build.get("workflow_revision") != builder["workflow_revision"]:
            raise ReleaseError("PROVENANCE_WORKFLOW_UNAPPROVED", str(build.get("workflow_revision")))
        if build.get("source_branch") not in builder["source_branches"]:
            raise ReleaseError("PROVENANCE_SOURCE_UNAPPROVED", str(build.get("source_branch")))
        if build.get("source_repository") not in builder["source_repositories"]:
            raise ReleaseError("PROVENANCE_REPOSITORY_UNAPPROVED", str(build.get("source_repository")))
        digest = file_digest(artifact_path)
        if statement.get("subject", {}).get("digest") != digest:
            raise ReleaseError("ARTIFACT_MISMATCH", digest)
        if build.get("source_commit") != source_commit or not build.get("dependencies_locked"):
            raise ReleaseError("PROVENANCE_BUILD_INVALID", source_commit)
        registry_path = self.registry / f"{digest.removeprefix('sha256:')}.artifact"
        registry_path.write_bytes(artifact_path.read_bytes())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    release_id, digest, source_commit, json.dumps(statement, sort_keys=True), signature,
                    str(registry_path), now,
                ),
            )
        return digest

    def registered_artifact_path(self, release_id: str) -> Path:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT registry_path FROM artifacts WHERE release_id=?", (release_id,)
            ).fetchone()
        if not row:
            raise ReleaseError("BUILD_PROVENANCE_MISSING", release_id)
        return Path(row["registry_path"])

    @staticmethod
    def _signature(value: object, key: str) -> str:
        material = json.dumps(asdict(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "hmac-sha256:" + hmac.new(key.encode("utf-8"), material, hashlib.sha256).hexdigest()

    def evidence_signature(self, evidence: Evidence, key: str) -> str:
        return self._signature(evidence, key)

    def runtime_signature(self, observation: RuntimeObservation, key: str) -> str:
        return self._signature(observation, key)

    def reconciliation_signature(self, evidence: ReconciliationEvidence, key: str) -> str:
        return self._signature(evidence, key)

    def register_evidence(self, release_id: str, evidence: Evidence, signature: str, now: str) -> None:
        trusted = self.trust["evidence_producers"].get(evidence.kind, {})
        key_id = trusted.get(evidence.producer)
        if not key_id:
            raise ReleaseError("EVIDENCE_PRODUCER_UNTRUSTED", f"{evidence.kind}:{evidence.producer}")
        if not hmac.compare_digest(self.evidence_signature(evidence, self._key(key_id)), signature):
            raise ReleaseError("EVIDENCE_AUTHENTICITY_UNVERIFIED", evidence.evidence_id)
        with self._connect() as connection:
            release = connection.execute(
                "SELECT manifest_digest FROM releases WHERE release_id = ?", (release_id,)
            ).fetchone()
            if release and release["manifest_digest"] != evidence.subject_digest:
                raise ReleaseError("EVIDENCE_SUBJECT_MISMATCH", evidence.evidence_id)
            connection.execute(
                "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
                (
                    evidence.evidence_id, release_id, evidence.kind, evidence.subject_digest,
                    evidence.producer, evidence.result, json.dumps(asdict(evidence), sort_keys=True),
                    evidence.digest, signature, now,
                ),
            )

    def revoke_evidence(self, evidence_id: str) -> None:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE evidence SET state='REVOKED' WHERE evidence_id=? AND state='ACTIVE'", (evidence_id,)
            )
        if updated.rowcount != 1:
            raise ReleaseError("EVIDENCE_NOT_ACTIVE", evidence_id)

    def submit_candidate(self, manifest: ReleaseManifest, now: str) -> Decision:
        if manifest.risk_tier not in self.policy["required_evidence"]:
            raise ReleaseError("RISK_TIER_UNRESOLVED", manifest.risk_tier)
        self._required_roles(manifest)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO releases VALUES (?, ?, ?, 'CANDIDATE', '[]', ?)",
                (manifest.release_id, json.dumps(asdict(manifest), sort_keys=True), manifest.digest, now),
            )
        return Decision("CANDIDATE", (), manifest.release_id, manifest.digest)

    def _artifact_findings(self, connection: sqlite3.Connection, manifest: ReleaseManifest) -> list[str]:
        artifact = connection.execute(
            "SELECT * FROM artifacts WHERE release_id = ?", (manifest.release_id,)
        ).fetchone()
        if not artifact:
            return ["BUILD_PROVENANCE_MISSING"]
        findings = []
        if artifact["artifact_digest"] != manifest.artifact_digest:
            findings.append("ARTIFACT_MISMATCH")
        if artifact["source_commit"] != manifest.source_commit:
            findings.append("SOURCE_REVISION_MISMATCH")
        path = Path(artifact["registry_path"])
        if not path.exists() or file_digest(path) != manifest.artifact_digest:
            findings.append("REGISTRY_ARTIFACT_MISMATCH")
        statement = json.loads(artifact["provenance_json"])
        build = statement.get("build", {})
        builder = self.trust["builders"].get(build.get("builder_id"))
        if not builder or not verify_statement(statement, artifact["signature"], self._key(builder["key_id"])):
            findings.append("PROVENANCE_IDENTITY_UNTRUSTED")
        return findings

    def _evidence_findings(self, connection: sqlite3.Connection, manifest: ReleaseManifest) -> list[str]:
        findings = self._artifact_findings(connection, manifest)
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
            if row["state"] != "ACTIVE":
                findings.append(f"REVOKED_EVIDENCE:{kind}")
                continue
            evidence = Evidence(**json.loads(row["evidence_json"]))
            key_id = self.trust["evidence_producers"].get(kind, {}).get(evidence.producer)
            if not key_id or not hmac.compare_digest(
                self.evidence_signature(evidence, self._key(key_id)), row["signature"]
            ):
                findings.append(f"EVIDENCE_AUTHENTICITY_UNVERIFIED:{kind}")
                continue
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
                "UPDATE releases SET state=?, findings_json=?, updated_at=? WHERE release_id=?",
                (state, json.dumps(findings), now, manifest.release_id),
            )
        return Decision(state, tuple(findings), manifest.release_id, manifest.digest)

    def approve(
        self, release_id: str, manifest_digest: str, environment: str, session_id: str,
        role: str, now: str, expires_at: str,
    ) -> str:
        principal = self.authenticate(session_id)
        if not _time(now) < _time(expires_at):
            raise ReleaseError("APPROVAL_EXPIRY_INVALID", expires_at)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            release = connection.execute("SELECT * FROM releases WHERE release_id=?", (release_id,)).fetchone()
            if not release or release["state"] != "ELIGIBLE_FOR_RELEASE_REVIEW":
                raise ReleaseError("RELEASE_NOT_ELIGIBLE", release_id)
            manifest = ReleaseManifest(**json.loads(release["manifest_json"]))
            if release["manifest_digest"] != manifest_digest or environment != manifest.environment:
                raise ReleaseError("APPROVAL_SUBJECT_MISMATCH", release_id)
            if role not in self._required_roles(manifest) or not self._has_authority(
                principal, role, manifest.environment, manifest.capability
            ):
                raise ReleaseError("APPROVER_NOT_AUTHORIZED", principal)
            existing = connection.execute(
                "SELECT principal FROM approvals WHERE release_id=? AND state='APPROVED'", (release_id,)
            ).fetchall()
            if principal in {row["principal"] for row in existing}:
                raise ReleaseError("SEPARATION_OF_DUTIES_VIOLATION", principal)
            receipt_id = f"REL-APR-{release_id}-{role}"
            connection.execute(
                "INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'APPROVED')",
                (
                    receipt_id, release_id, manifest_digest, environment, manifest.capability, principal,
                    role, self.policy["revision"], self.trust["revision"], now, expires_at,
                ),
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
                release = connection.execute(
                    "SELECT * FROM releases WHERE release_id=?", (manifest.release_id,)
                ).fetchone()
                if not release or release["state"] != "ELIGIBLE_FOR_RELEASE_REVIEW":
                    raise ReleaseError("RELEASE_NOT_ELIGIBLE", manifest.release_id)
                stored_manifest = ReleaseManifest(**json.loads(release["manifest_json"]))
                if release["manifest_digest"] != manifest.digest or stored_manifest != manifest:
                    raise ReleaseError("RELEASE_MANIFEST_UNTRUSTED", manifest.release_id)
                current_findings = self._evidence_findings(connection, stored_manifest)
                if current_findings:
                    raise ReleaseError("POINT_OF_USE_REVALIDATION_FAILED", ",".join(current_findings))
                receipts = [
                    connection.execute("SELECT * FROM approvals WHERE receipt_id=?", (item,)).fetchone()
                    for item in receipt_ids
                ]
                if any(item is None for item in receipts):
                    raise ReleaseError("APPROVAL_UNTRUSTED", manifest.release_id)
                roles, principals = set(), set()
                for receipt in receipts:
                    if (
                        receipt["release_id"] != manifest.release_id
                        or receipt["manifest_digest"] != manifest.digest
                        or receipt["environment"] != manifest.environment
                        or receipt["capability"] != manifest.capability
                    ):
                        raise ReleaseError("APPROVAL_SUBJECT_MISMATCH", receipt["receipt_id"])
                    if receipt["policy_revision"] != self.policy["revision"] or receipt["authority_revision"] != self.trust["revision"]:
                        raise ReleaseError("APPROVAL_POLICY_STALE", receipt["receipt_id"])
                    if receipt["state"] == "CONSUMED":
                        raise ReleaseError("APPROVAL_ALREADY_CONSUMED", receipt["receipt_id"])
                    if receipt["state"] != "APPROVED" or _time(receipt["expires_at"]) <= _time(now):
                        raise ReleaseError("APPROVAL_EXPIRED_OR_REVOKED", receipt["receipt_id"])
                    if not self._has_authority(
                        receipt["principal"], receipt["role"], manifest.environment, manifest.capability
                    ):
                        raise ReleaseError("APPROVAL_AUTHORITY_REVOKED", receipt["principal"])
                    roles.add(receipt["role"])
                    principals.add(receipt["principal"])
                required = set(self._required_roles(manifest))
                if roles != required or len(principals) != len(required):
                    raise ReleaseError("REQUIRED_APPROVAL_MISSING", manifest.release_id)
                for receipt_id in receipt_ids:
                    updated = connection.execute(
                        "UPDATE approvals SET state='CONSUMED' WHERE receipt_id=? AND state='APPROVED'",
                        (receipt_id,),
                    )
                    if updated.rowcount != 1:
                        raise ReleaseError("APPROVAL_ALREADY_CONSUMED", receipt_id)
                connection.execute(
                    "INSERT INTO operations VALUES (?, ?, ?, 'AUTHORIZED', '{}', ?)",
                    (operation_id, manifest.release_id, manifest.digest, now),
                )
                self._operation_event(connection, operation_id, "AUTHORIZED", {"receipts": receipt_ids}, now)
                connection.execute(
                    "UPDATE operations SET state='DISPATCHED', updated_at=? WHERE operation_id=?",
                    (now, operation_id),
                )
                self._operation_event(connection, operation_id, "DISPATCHED", {"environment": manifest.environment}, now)
                current = connection.execute(
                    "SELECT version FROM environments WHERE environment=?", (manifest.environment,)
                ).fetchone()
                connection.execute(
                    "UPDATE environments SET release_id=?, manifest_json=?, feature_enabled=1, "
                    "manual_review_required=1, version=? WHERE environment=?",
                    (
                        manifest.release_id, json.dumps(asdict(manifest), sort_keys=True),
                        current["version"] + 1, manifest.environment,
                    ),
                )
                state = "UNKNOWN_OUTCOME" if timeout_after_effect else "VERIFYING"
                result = {"reconciliation_required": True} if timeout_after_effect else {"deployment_observed": True}
                connection.execute(
                    "UPDATE operations SET state=?, result_json=?, updated_at=? WHERE operation_id=?",
                    (state, json.dumps(result, sort_keys=True), now, operation_id),
                )
                self._operation_event(connection, operation_id, state, result, now)
                connection.execute(
                    "UPDATE releases SET state=?, updated_at=? WHERE release_id=?",
                    (state, now, manifest.release_id),
                )
                connection.commit()
            return Decision(state, (), manifest.release_id, manifest.digest, operation_id)
        except sqlite3.IntegrityError as exc:
            raise ReleaseError("DEPLOYMENT_REPLAYED", manifest.release_id) from exc

    def reconcile_unknown(self, operation_id: str, now: str) -> Decision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
            if not operation or operation["state"] != "UNKNOWN_OUTCOME":
                raise ReleaseError("RECONCILIATION_NOT_REQUIRED", operation_id)
            release = connection.execute(
                "SELECT * FROM releases WHERE release_id=?", (operation["release_id"],)
            ).fetchone()
            environment = connection.execute(
                "SELECT * FROM environments WHERE release_id=?", (operation["release_id"],)
            ).fetchone()
            if not environment or release["manifest_digest"] != operation["manifest_digest"]:
                raise ReleaseError("DEPLOYMENT_STATE_UNRESOLVED", operation_id)
            connection.execute(
                "UPDATE operations SET state='VERIFYING', result_json='{}', updated_at=? WHERE operation_id=?",
                (now, operation_id),
            )
            connection.execute(
                "UPDATE releases SET state='VERIFYING', updated_at=? WHERE release_id=?",
                (now, operation["release_id"]),
            )
            self._operation_event(connection, operation_id, "VERIFYING", {"effect_reconciled": True}, now)
            connection.commit()
        return Decision("VERIFYING", (), operation["release_id"], operation["manifest_digest"], operation_id)

    def register_runtime_observation(
        self, observation: RuntimeObservation, signature: str, now: str,
    ) -> None:
        key_id = self.trust["runtime_observation_producers"].get(observation.source)
        if not key_id:
            raise ReleaseError("RUNTIME_OBSERVATION_SOURCE_UNTRUSTED", observation.source)
        if not hmac.compare_digest(self.runtime_signature(observation, self._key(key_id)), signature):
            raise ReleaseError("RUNTIME_OBSERVATION_AUTHENTICITY_UNVERIFIED", observation.observation_id)
        with self._connect() as connection:
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_id=?", (observation.operation_id,)
            ).fetchone()
            release = connection.execute(
                "SELECT manifest_json FROM releases WHERE release_id=?", (observation.release_id,)
            ).fetchone()
            if not operation or not release:
                raise ReleaseError("RUNTIME_OBSERVATION_SUBJECT_UNTRUSTED", observation.observation_id)
            manifest = ReleaseManifest(**json.loads(release["manifest_json"]))
            if (
                operation["release_id"] != observation.release_id
                or operation["manifest_digest"] != observation.manifest_digest
                or manifest.environment != observation.environment
                or not _time(observation.window_start) < _time(observation.window_end) <= _time(now)
            ):
                raise ReleaseError("RUNTIME_OBSERVATION_SUBJECT_UNTRUSTED", observation.observation_id)
            connection.execute(
                "INSERT INTO runtime_observations VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    observation.observation_id, observation.operation_id, observation.release_id,
                    observation.manifest_digest, observation.source,
                    json.dumps(asdict(observation), sort_keys=True), signature, now,
                ),
            )

    def verify_runtime(self, operation_id: str, now: str) -> Decision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            operation = connection.execute(
                "SELECT * FROM operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
            if not operation or operation["state"] != "VERIFYING":
                raise ReleaseError("RUNTIME_VERIFICATION_NOT_READY", operation_id)
            rows = connection.execute(
                "SELECT * FROM runtime_observations WHERE operation_id=? ORDER BY observation_id",
                (operation_id,),
            ).fetchall()
            failures = []
            if len(rows) < self.policy["runtime_observation_minimum"]:
                failures.append("RUNTIME_EVIDENCE_COVERAGE_INSUFFICIENT")
            for row in rows:
                observation = RuntimeObservation(**json.loads(row["record_json"]))
                key_id = self.trust["runtime_observation_producers"].get(observation.source)
                if not key_id or not hmac.compare_digest(
                    self.runtime_signature(observation, self._key(key_id)), row["signature"]
                ):
                    failures.append("RUNTIME_OBSERVATION_AUTHENTICITY_UNVERIFIED")
                    continue
                if observation.manifest_digest != operation["manifest_digest"]:
                    failures.append("RUNTIME_OBSERVATION_SUBJECT_UNTRUSTED")
                if not observation.tenant_authorized:
                    failures.append("TENANT_ISOLATION_VIOLATION")
                if observation.ambiguous and not observation.human_review_required:
                    failures.append("HUMAN_REVIEW_BYPASS")
                if observation.protected_mutation:
                    failures.append("UNAUTHORIZED_PROTECTED_MUTATION")
            state = "HALTED" if failures else "ACTIVE"
            result = {"observations": len(rows), "findings": sorted(set(failures))}
            connection.execute(
                "UPDATE operations SET state=?, result_json=?, updated_at=? WHERE operation_id=?",
                (state, json.dumps(result, sort_keys=True), now, operation_id),
            )
            connection.execute(
                "UPDATE releases SET state=?, findings_json=?, updated_at=? WHERE release_id=?",
                (state, json.dumps(result["findings"]), now, operation["release_id"]),
            )
            if failures:
                connection.execute(
                    "UPDATE environments SET feature_enabled=0, manual_review_required=1, "
                    "version=version+1 WHERE release_id=?",
                    (operation["release_id"],),
                )
            self._operation_event(connection, operation_id, state, result, now)
            connection.commit()
        return Decision(state, tuple(result["findings"]), operation["release_id"], operation["manifest_digest"], operation_id)

    def approve_recovery(
        self, incident_id: str, failed_release: str, target: ReleaseManifest,
        session_id: str, now: str, expires_at: str,
    ) -> str:
        principal = self.authenticate(session_id)
        if not self._has_authority(principal, "recovery_authority", target.environment, target.capability):
            raise ReleaseError("RECOVERY_APPROVER_NOT_AUTHORIZED", principal)
        if not _time(now) < _time(expires_at):
            raise ReleaseError("APPROVAL_EXPIRY_INVALID", expires_at)
        with self._connect() as connection:
            target_record = connection.execute(
                "SELECT manifest_digest,state FROM releases WHERE release_id=?", (target.release_id,)
            ).fetchone()
            if (
                not target_record
                or target_record["manifest_digest"] != target.digest
                or target_record["state"] not in {"ELIGIBLE_FOR_RELEASE_REVIEW", "ACTIVE", "HALTED"}
            ):
                raise ReleaseError("RECOVERY_TARGET_UNTRUSTED", target.release_id)
            receipt_id = f"REC-APR-{incident_id}-{target.release_id}"
            connection.execute(
                "INSERT INTO recovery_approvals VALUES (?, ?, ?, ?, ?, ?, ?, 'recovery_authority', ?, ?, ?, 'APPROVED')",
                (
                    receipt_id, incident_id, failed_release, target.release_id, target.digest,
                    target.environment, principal, self.policy["revision"], self.trust["revision"], expires_at,
                ),
            )
        return receipt_id

    def _validate_recovery_receipt(
        self, receipt: sqlite3.Row | None, target: ReleaseManifest, now: str,
        allowed_states: set[str],
    ) -> None:
        if not receipt:
            raise ReleaseError("RECOVERY_AUTHORIZATION_MISSING", target.release_id)
        if (
            receipt["target_release"] != target.release_id
            or receipt["manifest_digest"] != target.digest
            or receipt["environment"] != target.environment
        ):
            raise ReleaseError("RECOVERY_AUTHORIZATION_SUBJECT_MISMATCH", receipt["receipt_id"])
        if receipt["state"] not in allowed_states or _time(receipt["expires_at"]) <= _time(now):
            raise ReleaseError("RECOVERY_AUTHORIZATION_EXPIRED_OR_CONSUMED", receipt["receipt_id"])
        if receipt["policy_revision"] != self.policy["revision"] or receipt["authority_revision"] != self.trust["revision"]:
            raise ReleaseError("RECOVERY_AUTHORIZATION_STALE", receipt["receipt_id"])
        if not self._has_authority(
            receipt["principal"], receipt["role"], target.environment, target.capability
        ):
            raise ReleaseError("RECOVERY_AUTHORITY_REVOKED", receipt["principal"])

    def execute_recovery_restore(
        self, receipt_id: str, target: ReleaseManifest, now: str,
        *, component_overrides: dict[str, str] | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            receipt = connection.execute(
                "SELECT * FROM recovery_approvals WHERE receipt_id=?", (receipt_id,)
            ).fetchone()
            self._validate_recovery_receipt(receipt, target, now, {"APPROVED"})
            findings = self._evidence_findings(connection, target)
            if findings:
                raise ReleaseError("RECOVERY_TARGET_REVALIDATION_FAILED", ",".join(findings))
            effective = asdict(target)
            effective.update(component_overrides or {})
            current = connection.execute(
                "SELECT version FROM environments WHERE environment=?", (target.environment,)
            ).fetchone()
            connection.execute(
                "UPDATE environments SET release_id=?,manifest_json=?,feature_enabled=0,"
                "manual_review_required=1,version=? WHERE environment=?",
                (
                    target.release_id, json.dumps(effective, sort_keys=True), current["version"] + 1,
                    target.environment,
                ),
            )
            connection.execute(
                "UPDATE recovery_approvals SET state='EXECUTED' WHERE receipt_id=?", (receipt_id,)
            )
            connection.commit()

    def register_reconciliation_evidence(
        self, evidence: ReconciliationEvidence, signature: str, now: str,
    ) -> None:
        key_id = self.trust["reconciliation_evidence_producers"].get(evidence.producer)
        if not key_id:
            raise ReleaseError("RECONCILIATION_EVIDENCE_PRODUCER_UNTRUSTED", evidence.producer)
        if not hmac.compare_digest(self.reconciliation_signature(evidence, self._key(key_id)), signature):
            raise ReleaseError("RECONCILIATION_EVIDENCE_AUTHENTICITY_UNVERIFIED", evidence.evidence_id)
        with self._connect() as connection:
            receipt = connection.execute(
                "SELECT * FROM recovery_approvals WHERE incident_id=?", (evidence.incident_id,)
            ).fetchone()
            if (
                not receipt
                or receipt["target_release"] != evidence.target_release
                or receipt["manifest_digest"] != evidence.manifest_digest
            ):
                raise ReleaseError("RECONCILIATION_EVIDENCE_SUBJECT_UNTRUSTED", evidence.evidence_id)
            connection.execute(
                "INSERT INTO reconciliation_evidence VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)",
                (
                    evidence.evidence_id, evidence.incident_id, evidence.target_release, evidence.check,
                    json.dumps(asdict(evidence), sort_keys=True), signature, now,
                ),
            )

    def recover(self, incident_id: str, target: ReleaseManifest, receipt_id: str, now: str) -> Decision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            receipt = connection.execute(
                "SELECT * FROM recovery_approvals WHERE receipt_id=? AND incident_id=?",
                (receipt_id, incident_id),
            ).fetchone()
            self._validate_recovery_receipt(receipt, target, now, {"EXECUTED"})
            target_record = connection.execute(
                "SELECT manifest_digest,state FROM releases WHERE release_id=?", (target.release_id,)
            ).fetchone()
            if not target_record or target_record["manifest_digest"] != target.digest:
                raise ReleaseError("RECOVERY_TARGET_UNTRUSTED", target.release_id)
            findings = self._evidence_findings(connection, target)
            if findings:
                raise ReleaseError("RECOVERY_TARGET_REVALIDATION_FAILED", ",".join(findings))
            environment = connection.execute(
                "SELECT * FROM environments WHERE environment=?", (target.environment,)
            ).fetchone()
            observed = json.loads(environment["manifest_json"]) if environment["manifest_json"] else {}
            expected = asdict(target)
            mismatches = sorted(key for key, value in expected.items() if observed.get(key) != value)
            rows = connection.execute(
                "SELECT * FROM reconciliation_evidence WHERE incident_id=? AND state='ACTIVE'",
                (incident_id,),
            ).fetchall()
            checks: dict[str, str] = {}
            evidence_findings = []
            for row in rows:
                evidence = ReconciliationEvidence(**json.loads(row["record_json"]))
                key_id = self.trust["reconciliation_evidence_producers"].get(evidence.producer)
                if not key_id or not hmac.compare_digest(
                    self.reconciliation_signature(evidence, self._key(key_id)), row["signature"]
                ):
                    evidence_findings.append(f"RECONCILIATION_EVIDENCE_UNTRUSTED:{evidence.check}")
                else:
                    checks[evidence.check] = evidence.status
            missing = sorted(set(self.policy["required_reconciliation"]) - set(checks))
            open_checks = sorted(name for name, status in checks.items() if status != "PASS")
            if mismatches:
                state = "RECOVERY_INCOMPLETE"
                reasons = tuple(f"COMPONENT_NOT_RESTORED:{item}" for item in mismatches)
            elif evidence_findings or missing or open_checks:
                state = "RECOVERY_IN_PROGRESS"
                reasons = tuple(sorted([
                    *evidence_findings,
                    *(f"RECONCILIATION_MISSING:{item}" for item in missing),
                    *(f"UNRESOLVED:{item}" for item in open_checks),
                ]))
            else:
                state, reasons = "RECOVERED", ()
            record = {
                "failed_release": receipt["failed_release"],
                "target_release": target.release_id,
                "observed_manifest": observed,
                "checks": checks,
                "reasons": reasons,
            }
            connection.execute(
                "INSERT OR REPLACE INTO reconciliation VALUES (?, ?, ?, ?, ?, ?)",
                (
                    incident_id, receipt["failed_release"], target.release_id, state,
                    json.dumps(record, sort_keys=True), now,
                ),
            )
            if state == "RECOVERED":
                connection.execute(
                    "UPDATE environments SET feature_enabled=1,manual_review_required=1,"
                    "version=version+1 WHERE environment=?",
                    (target.environment,),
                )
                connection.execute(
                    "UPDATE recovery_approvals SET state='CONSUMED' WHERE receipt_id=?", (receipt_id,)
                )
                connection.execute(
                    "UPDATE releases SET state='RECOVERED',updated_at=? WHERE release_id=?",
                    (now, target.release_id),
                )
            connection.commit()
        return Decision(state, reasons, target.release_id, target.digest)

    def release_state(self, release_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM releases WHERE release_id=?", (release_id,)).fetchone()
        return dict(row) if row else {}

    def operation_events(self, operation_id: str) -> list[dict]:
        with self._connect() as connection:
            return [
                dict(row) for row in connection.execute(
                    "SELECT * FROM operation_events WHERE operation_id=? ORDER BY sequence", (operation_id,)
                )
            ]

    def operation_count(self, release_id: str) -> int:
        with self._connect() as connection:
            return connection.execute(
                "SELECT COUNT(*) FROM operations WHERE release_id=?", (release_id,)
            ).fetchone()[0]

    def environment_state(self, environment: str = "production") -> dict:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM environments WHERE environment=?", (environment,)
            ).fetchone()
        result = dict(row)
        result["feature_enabled"] = bool(result["feature_enabled"])
        result["manual_review_required"] = bool(result["manual_review_required"])
        result["manifest"] = json.loads(result.pop("manifest_json")) if result["manifest_json"] else None
        return result
