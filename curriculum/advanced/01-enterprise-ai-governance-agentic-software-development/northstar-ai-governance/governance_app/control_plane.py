"""Independent AI-governance decisions over trusted registry facts."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import ApprovalReceipt, Evidence, GovernanceDecision, GovernanceError
from .registry import digest, load_json, parse_time, verify_evidence


class GovernanceControlPlane:
    """Resolve facts, select controls, verify evidence, and consume authority."""

    def __init__(self, root: Path, database: Path, verification_keys: dict[str, str]) -> None:
        self.root = root
        self.policy = load_json(root / "policies/ai-governance-policy.json")
        self.trust = load_json(root / "policies/trust-policy.json")
        self.use_cases = self._indexed("registry/use-cases.json", "id")
        self.models = self._indexed("registry/models.json", "id")
        self.agents = self._indexed("registry/agents.json", "id")
        self.tools = self._indexed("registry/tools.json", "id")
        self.principals = self._indexed("registry/principals.json", "id")
        self.sessions = load_json(root / "registry/sessions.json")
        self.assessments = {
            "AI-UC-2500": load_json(root / "assessments/AI-UC-2500/impact-assessment.json")
        }
        self.keys = dict(verification_keys)
        self.evidence: dict[str, dict[str, tuple[Evidence, str]]] = {}
        self._lock = threading.Lock()
        self.db = sqlite3.connect(database, check_same_thread=False, isolation_level=None)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS approvals ("
            "receipt_id TEXT PRIMARY KEY, use_case_id TEXT, subject_digest TEXT, "
            "policy_version TEXT, action TEXT, principal_id TEXT, issued_at TEXT, "
            "expires_at TEXT, consumed_by TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS operations (operation_id TEXT PRIMARY KEY, "
            "receipt_id TEXT UNIQUE, use_case_id TEXT, subject_digest TEXT, state TEXT)"
        )

    def _indexed(self, relative: str, key: str) -> dict[str, dict[str, Any]]:
        return {item[key]: item for item in load_json(self.root / relative)}

    def authenticate(self, session_id: str) -> dict[str, Any]:
        principal_id = self.sessions.get(session_id)
        principal = self.principals.get(principal_id or "")
        if not principal or principal.get("status") != "ACTIVE":
            raise GovernanceError("UNAUTHENTICATED_PRINCIPAL")
        return principal

    def subject(self, use_case_id: str) -> dict[str, Any]:
        use_case = self.use_cases.get(use_case_id)
        if not use_case:
            raise GovernanceError("USE_CASE_UNKNOWN")
        model = self.models.get(use_case["model_id"])
        agent = self.agents.get(use_case["agent_id"])
        assessment = self.assessments.get(use_case_id)
        if not model or not agent or not assessment:
            raise GovernanceError("REGISTRY_RELATIONSHIP_UNRESOLVED")
        resolved_tools = [self.tools.get(tool_id) for tool_id in agent["tool_ids"]]
        return {
            "use_case": use_case,
            "model": model,
            "agent": agent,
            "tools": resolved_tools,
            "assessment": assessment,
            "policy_version": self.policy["version"],
        }

    def subject_digest(self, use_case_id: str) -> str:
        return digest(self.subject(use_case_id))

    def register_evidence(
        self, use_case_id: str, evidence: Evidence, signature: str, now: str
    ) -> None:
        producer = self.trust["evidence_producers"].get(evidence.producer)
        if not producer or evidence.kind not in producer["kinds"]:
            raise GovernanceError("EVIDENCE_PRODUCER_UNTRUSTED")
        key = self.keys.get(producer["key_id"])
        if not key or not verify_evidence(evidence, signature, key):
            raise GovernanceError("EVIDENCE_AUTHENTICITY_UNVERIFIED")
        if evidence.subject_digest != self.subject_digest(use_case_id):
            raise GovernanceError("EVIDENCE_SUBJECT_MISMATCH")
        if parse_time(evidence.issued_at) > parse_time(now):
            raise GovernanceError("EVIDENCE_FROM_FUTURE")
        self.evidence.setdefault(use_case_id, {})[evidence.kind] = (evidence, signature)

    def _risk_tier(self, use_case_id: str) -> tuple[str, list[str]]:
        subject = self.subject(use_case_id)
        assessment = subject["assessment"]
        total = sum(int(value) for value in assessment["dimensions"].values())
        thresholds = self.policy["risk_thresholds"]
        scored = "LOW" if total <= thresholds["low_max"] else "MODERATE"
        if total >= thresholds["consequential_min"]:
            scored = "CONSEQUENTIAL"
        floors: list[str] = []
        agent = subject["agent"]
        tools = [tool for tool in subject["tools"] if tool]
        if any(tool["effect"] == "AUTHORITATIVE_MUTATION" for tool in tools):
            floors.append("AUTHORITATIVE_MUTATION")
        if agent["autonomy_level"] in {"A3", "A4"}:
            floors.append("HIGH_AUTONOMY")
        if floors:
            scored = "CONSEQUENTIAL"
        return scored, floors

    def evaluate(self, use_case_id: str, now: str) -> GovernanceDecision:
        subject = self.subject(use_case_id)
        use_case, model, agent = subject["use_case"], subject["model"], subject["agent"]
        risk_tier, floors = self._risk_tier(use_case_id)
        blocking: list[str] = []
        missing: list[str] = []
        if use_case["lifecycle"] not in {"APPROVED_FOR_BOUNDED_USE", "ACTIVE"}:
            blocking.append("USE_CASE_NOT_APPROVED")
        if model["status"] != "APPROVED":
            blocking.append("MODEL_NOT_APPROVED")
        if use_case["intended_task"] not in model["permitted_tasks"]:
            blocking.append("MODEL_TASK_NOT_PERMITTED")
        if use_case["risk_tier"] != risk_tier:
            blocking.append("RISK_TIER_MISMATCH")
        if any(tool is None for tool in subject["tools"]):
            blocking.append("TOOL_UNKNOWN")
        if any(
            tool and tool["effect"] == "AUTHORITATIVE_MUTATION"
            for tool in subject["tools"]
        ) and not use_case["authority"]["may_update_underwriting_state"]:
            blocking.append("UNAUTHORIZED_AUTONOMY")
        if risk_tier == "CONSEQUENTIAL" and use_case["human_oversight"] != "VERIFIED":
            blocking.append("HUMAN_OVERSIGHT_UNVERIFIED")
        if use_case["data_residency"] == "UNKNOWN":
            missing.append("DATA_RESIDENCY_UNKNOWN")

        required = tuple(self.policy["required_evidence"][risk_tier])
        current_digest = self.subject_digest(use_case_id)
        dependencies = {
            "model_revision": model["revision"],
            "agent_revision": agent["revision"],
            "policy_version": self.policy["version"],
        }
        records = self.evidence.get(use_case_id, {})
        for kind in required:
            record = records.get(kind)
            if not record:
                missing.append(f"EVIDENCE_MISSING:{kind}")
                continue
            evidence, signature = record
            producer = self.trust["evidence_producers"].get(evidence.producer, {})
            key = self.keys.get(producer.get("key_id", ""))
            if not key or not verify_evidence(evidence, signature, key):
                blocking.append(f"EVIDENCE_AUTHENTICITY_INVALID:{kind}")
            if evidence.subject_digest != current_digest:
                missing.append(f"EVIDENCE_STALE_SUBJECT:{kind}")
            if evidence.status != "PASS":
                blocking.append(f"EVIDENCE_FAILED:{kind}")
            if parse_time(evidence.expires_at) <= parse_time(now):
                missing.append(f"EVIDENCE_EXPIRED:{kind}")
            for name, expected in dependencies.items():
                if evidence.dependencies.get(name) != expected:
                    missing.append(f"EVIDENCE_STALE_DEPENDENCY:{kind}:{name}")

        if blocking:
            state, findings = "BLOCKED", tuple(sorted(set(blocking + missing)))
        elif missing:
            state, findings = "INSUFFICIENT_EVIDENCE", tuple(sorted(set(missing)))
        else:
            state = "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL"
            findings = tuple(f"POLICY_FLOOR:{floor}" for floor in floors)
        return GovernanceDecision(
            use_case_id, state, current_digest, self.policy["version"], risk_tier,
            findings, required,
        )

    def approve(
        self, use_case_id: str, subject_digest: str, session_id: str,
        action: str, issued_at: str, expires_at: str,
    ) -> ApprovalReceipt:
        decision = self.evaluate(use_case_id, issued_at)
        if decision.decision != "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL":
            raise GovernanceError("GOVERNANCE_NOT_APPROVABLE")
        if subject_digest != decision.subject_digest:
            raise GovernanceError("APPROVAL_SUBJECT_MISMATCH")
        principal = self.authenticate(session_id)
        if "ai_governance_authority" not in principal["roles"]:
            raise GovernanceError("APPROVER_NOT_AUTHORIZED")
        if action != "operate_bounded_use_case":
            raise GovernanceError("APPROVAL_ACTION_OUT_OF_SCOPE")
        if parse_time(expires_at) <= parse_time(issued_at):
            raise GovernanceError("APPROVAL_EXPIRY_INVALID")
        receipt = ApprovalReceipt(
            f"GOV-APR-{uuid.uuid4().hex[:12]}", use_case_id, subject_digest,
            self.policy["version"], action, principal["id"], issued_at, expires_at,
        )
        self.db.execute(
            "INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            tuple(asdict(receipt).values()),
        )
        return receipt

    def authorize_operation(
        self, receipt_id: str, operation_id: str, session_id: str, now: str
    ) -> GovernanceDecision:
        actor = self.authenticate(session_id)
        if "protected_executor" not in actor["roles"]:
            raise GovernanceError("EXECUTOR_NOT_AUTHORIZED")
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                row = self.db.execute(
                    "SELECT * FROM approvals WHERE receipt_id = ?", (receipt_id,)
                ).fetchone()
                if not row:
                    raise GovernanceError("APPROVAL_UNKNOWN")
                (_, use_case_id, approved_digest, policy_version, action,
                 principal_id, issued_at, expires_at, consumed_by) = row
                decision = self.evaluate(use_case_id, now)
                if consumed_by:
                    raise GovernanceError("APPROVAL_ALREADY_CONSUMED")
                if parse_time(expires_at) <= parse_time(now):
                    raise GovernanceError("APPROVAL_EXPIRED")
                if policy_version != self.policy["version"]:
                    raise GovernanceError("APPROVAL_POLICY_STALE")
                if approved_digest != decision.subject_digest:
                    raise GovernanceError("APPROVAL_SUBJECT_STALE")
                principal = self.principals.get(principal_id)
                if not principal or principal.get("status") != "ACTIVE" or "ai_governance_authority" not in principal["roles"]:
                    raise GovernanceError("APPROVAL_AUTHORITY_REVOKED")
                if decision.decision != "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL":
                    raise GovernanceError("POINT_OF_USE_REVALIDATION_FAILED")
                updated = self.db.execute(
                    "UPDATE approvals SET consumed_by = ? WHERE receipt_id = ? AND consumed_by IS NULL",
                    (operation_id, receipt_id),
                ).rowcount
                if updated != 1:
                    raise GovernanceError("APPROVAL_ALREADY_CONSUMED")
                self.db.execute(
                    "INSERT INTO operations VALUES (?, ?, ?, ?, 'ALLOWED')",
                    (operation_id, receipt_id, use_case_id, decision.subject_digest),
                )
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return GovernanceDecision(
            decision.use_case_id, "ALLOWED", decision.subject_digest,
            decision.authority, decision.risk_tier, ("APPROVAL_CONSUMED",),
            decision.required_evidence,
        )

    def change_impact(self, use_case_id: str, changes: dict[str, str]) -> dict[str, Any]:
        obligations: set[str] = set()
        mapping = self.policy["reassessment_triggers"]
        for component in changes:
            obligations.update(mapping.get(component, []))
        return {
            "use_case_id": use_case_id,
            "state": "REASSESSMENT_REQUIRED" if obligations else "NO_GOVERNANCE_IMPACT_IDENTIFIED",
            "changed_components": sorted(changes),
            "required_reassessment": sorted(obligations),
            "authority": self.policy["version"],
        }

    def suspend_on_violation(
        self, use_case_id: str, observation: Evidence, signature: str, now: str
    ) -> GovernanceDecision:
        producer = self.trust["evidence_producers"].get(observation.producer)
        key = self.keys.get(producer.get("key_id", "")) if producer else None
        if (
            not producer
            or observation.kind not in producer["kinds"]
            or not key
            or not verify_evidence(observation, signature, key)
        ):
            raise GovernanceError("RUNTIME_VIOLATION_AUTHENTICITY_UNVERIFIED")
        if observation.subject_digest != self.subject_digest(use_case_id):
            raise GovernanceError("RUNTIME_VIOLATION_SUBJECT_MISMATCH")
        if parse_time(observation.expires_at) <= parse_time(now):
            raise GovernanceError("RUNTIME_VIOLATION_STALE")
        if observation.status != "FAIL" or not observation.details.get("protected_invariant"):
            raise GovernanceError("RUNTIME_VIOLATION_NOT_ACTIONABLE")
        self.use_cases[use_case_id]["lifecycle"] = "SUSPENDED"
        return GovernanceDecision(
            use_case_id, "SUSPENDED", self.subject_digest(use_case_id),
            self.policy["version"], self._risk_tier(use_case_id)[0],
            (f"PROTECTED_INVARIANT_VIOLATION:{observation.details['protected_invariant']}",),
            tuple(self.policy["required_evidence"][self._risk_tier(use_case_id)[0]]),
        )

    def close(self) -> None:
        self.db.close()
