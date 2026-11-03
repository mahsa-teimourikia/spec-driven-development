"""Independent, durable AI-governance decisions over trusted registry facts."""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import ApprovalReceipt, Evidence, GovernanceDecision, GovernanceError
from .registry import digest, load_json, parse_time, verify_evidence, verify_payload


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
        self.deployments = self._indexed("registry/deployments.json", "id")
        self.principals = self._indexed("registry/principals.json", "id")
        self.sessions = load_json(root / "registry/sessions.json")
        self.assessments = {
            "AI-UC-2500": load_json(root / "assessments/AI-UC-2500/impact-assessment.json")
        }
        self.assessment_approvals = self._indexed("registry/assessment-approvals.json", "id")
        self.keys = dict(verification_keys)
        self._lock = threading.Lock()
        self.db = sqlite3.connect(database, check_same_thread=False, isolation_level=None)
        self._create_schema()
        self._initialize_lifecycle()

    def _create_schema(self) -> None:
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS governance_state ("
            "use_case_id TEXT PRIMARY KEY, lifecycle TEXT NOT NULL, state_version INTEGER NOT NULL, "
            "updated_at TEXT NOT NULL, reason_code TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS evidence_records ("
            "evidence_id TEXT PRIMARY KEY, use_case_id TEXT NOT NULL, claim_id TEXT NOT NULL, "
            "kind TEXT NOT NULL, payload_json TEXT NOT NULL, signature TEXT NOT NULL, "
            "registered_at TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS evidence_revocations ("
            "revocation_id TEXT PRIMARY KEY, evidence_id TEXT UNIQUE NOT NULL, "
            "principal_id TEXT NOT NULL, revoked_at TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS approvals ("
            "receipt_id TEXT PRIMARY KEY, use_case_id TEXT, subject_digest TEXT, "
            "evidence_set_digest TEXT, policy_version TEXT, action TEXT, principal_id TEXT, "
            "issued_at TEXT, expires_at TEXT, consumed_by TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS operations (operation_id TEXT PRIMARY KEY, "
            "receipt_id TEXT UNIQUE, use_case_id TEXT, subject_digest TEXT, state TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS audit_events (event_id TEXT PRIMARY KEY, "
            "use_case_id TEXT, event_type TEXT, subject_digest TEXT, occurred_at TEXT, details_json TEXT)"
        )

    def _initialize_lifecycle(self) -> None:
        for use_case in self.use_cases.values():
            self.db.execute(
                "INSERT OR IGNORE INTO governance_state VALUES (?, ?, 1, ?, 'REGISTRY_INITIALIZATION')",
                (use_case["id"], use_case["lifecycle"],
                 use_case.get("lifecycle_updated_at", "2026-10-01T00:00:00Z")),
            )

    def _indexed(self, relative: str, key: str) -> dict[str, dict[str, Any]]:
        return {item[key]: item for item in load_json(self.root / relative)}

    def authenticate(self, session_id: str) -> dict[str, Any]:
        principal_id = self.sessions.get(session_id)
        principal = self.principals.get(principal_id or "")
        if not principal or principal.get("status") != "ACTIVE":
            raise GovernanceError("UNAUTHENTICATED_PRINCIPAL")
        return principal

    def lifecycle(self, use_case_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT lifecycle, state_version, updated_at, reason_code FROM governance_state "
            "WHERE use_case_id = ?", (use_case_id,),
        ).fetchone()
        if not row:
            raise GovernanceError("USE_CASE_UNKNOWN")
        return dict(zip(("lifecycle", "state_version", "updated_at", "reason_code"), row))

    def subject(self, use_case_id: str) -> dict[str, Any]:
        registered = self.use_cases.get(use_case_id)
        if not registered:
            raise GovernanceError("USE_CASE_UNKNOWN")
        use_case = copy.deepcopy(registered)
        state = self.lifecycle(use_case_id)
        use_case["lifecycle"] = state["lifecycle"]
        use_case["lifecycle_state_version"] = state["state_version"]
        model = self.models.get(use_case["model_id"])
        agent = self.agents.get(use_case["agent_id"])
        assessment = self.assessments.get(use_case_id)
        if not model or not agent or not assessment:
            raise GovernanceError("REGISTRY_RELATIONSHIP_UNRESOLVED")
        resolved_tools = [self.tools.get(tool_id) for tool_id in agent["tool_ids"]]
        deployments = sorted(
            (item for item in self.deployments.values() if item["use_case_id"] == use_case_id),
            key=lambda item: item["id"],
        )
        return {
            "use_case": use_case, "model": model, "agent": agent,
            "tools": resolved_tools, "deployments": deployments,
            "assessment": assessment, "policy_version": self.policy["version"],
        }

    def subject_digest(self, use_case_id: str) -> str:
        return digest(self.subject(use_case_id))

    def _producer_for(self, evidence: Evidence) -> tuple[dict[str, Any], str]:
        producer = self.trust["evidence_producers"].get(evidence.producer)
        if (not producer or evidence.kind not in producer["kinds"]
                or evidence.claim_id not in producer["claims"]):
            raise GovernanceError("EVIDENCE_PRODUCER_UNTRUSTED")
        key = self.keys.get(producer["key_id"])
        if not key:
            raise GovernanceError("EVIDENCE_AUTHENTICITY_UNVERIFIED")
        return producer, key

    def register_evidence(
        self, use_case_id: str, evidence: Evidence, signature: str, now: str
    ) -> None:
        _, key = self._producer_for(evidence)
        if not verify_evidence(evidence, signature, key):
            raise GovernanceError("EVIDENCE_AUTHENTICITY_UNVERIFIED")
        claim = self.policy["claim_catalog"].get(evidence.claim_id)
        if not claim or claim["kind"] != evidence.kind:
            raise GovernanceError("EVIDENCE_CLAIM_UNKNOWN")
        if evidence.subject_digest != self.subject_digest(use_case_id):
            raise GovernanceError("EVIDENCE_SUBJECT_MISMATCH")
        try:
            issued_at = parse_time(evidence.issued_at)
            expires_at = parse_time(evidence.expires_at)
            evaluated_at = parse_time(now)
        except (TypeError, ValueError) as exc:
            raise GovernanceError("EVIDENCE_INTERVAL_INVALID") from exc
        if issued_at > evaluated_at:
            raise GovernanceError("EVIDENCE_FROM_FUTURE")
        if expires_at <= issued_at:
            raise GovernanceError("EVIDENCE_INTERVAL_INVALID")
        payload_json = json.dumps(evidence.payload(), sort_keys=True, separators=(",", ":"))
        row = self.db.execute(
            "SELECT payload_json, signature FROM evidence_records WHERE evidence_id = ?",
            (evidence.evidence_id,),
        ).fetchone()
        if row:
            if row != (payload_json, signature):
                raise GovernanceError("EVIDENCE_ID_COLLISION")
            return
        self.db.execute(
            "INSERT INTO evidence_records VALUES (?, ?, ?, ?, ?, ?, ?)",
            (evidence.evidence_id, use_case_id, evidence.claim_id, evidence.kind,
             payload_json, signature, now),
        )

    def evidence_history(self, use_case_id: str) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT e.payload_json, e.signature, e.registered_at, r.revoked_at, r.principal_id "
            "FROM evidence_records e LEFT JOIN evidence_revocations r ON r.evidence_id = e.evidence_id "
            "WHERE e.use_case_id = ? ORDER BY e.registered_at, e.evidence_id", (use_case_id,),
        ).fetchall()
        return [{"evidence": json.loads(payload), "signature": signature,
                 "registered_at": registered, "revoked_at": revoked, "revoked_by": revoker}
                for payload, signature, registered, revoked, revoker in rows]

    def revoke_evidence(self, evidence_id: str, session_id: str, now: str) -> None:
        principal = self.authenticate(session_id)
        if "ai_governance_authority" not in principal["roles"]:
            raise GovernanceError("EVIDENCE_REVOCATION_NOT_AUTHORIZED")
        exists = self.db.execute(
            "SELECT 1 FROM evidence_records WHERE evidence_id = ?", (evidence_id,)
        ).fetchone()
        if not exists:
            raise GovernanceError("EVIDENCE_UNKNOWN_OR_REVOKED")
        try:
            self.db.execute(
                "INSERT INTO evidence_revocations VALUES (?, ?, ?, ?)",
                (f"REV-{uuid.uuid4().hex}", evidence_id, principal["id"], now),
            )
        except sqlite3.IntegrityError as exc:
            raise GovernanceError("EVIDENCE_UNKNOWN_OR_REVOKED") from exc

    def _risk_tier(self, use_case_id: str) -> tuple[str, list[str]]:
        subject = self.subject(use_case_id)
        total = sum(int(value) for value in subject["assessment"].get("dimensions", {}).values())
        thresholds = self.policy["risk_thresholds"]
        scored = "LOW" if total <= thresholds["low_max"] else "MODERATE"
        if total >= thresholds["consequential_min"]:
            scored = "CONSEQUENTIAL"
        floors: list[str] = []
        tools = [tool for tool in subject["tools"] if tool]
        if any(tool["effect"] == "AUTHORITATIVE_MUTATION" for tool in tools):
            floors.append("AUTHORITATIVE_MUTATION")
        if subject["agent"]["autonomy_level"] in {"A3", "A4"}:
            floors.append("HIGH_AUTONOMY")
        if floors:
            scored = "CONSEQUENTIAL"
        return scored, floors

    def _assessment_findings(self, use_case_id: str, tier: str, now: str) -> list[str]:
        assessment = self.assessments[use_case_id]
        approval = next((item for item in self.assessment_approvals.values()
                         if item["use_case_id"] == use_case_id), None)
        if assessment.get("status") != "APPROVED" or not approval:
            return ["ASSESSMENT_AUTHORITY_UNVERIFIED"]
        payload = approval.get("payload", {})
        principal = self.principals.get(payload.get("principal_id", ""), {})
        authority = self.trust["risk_assessment_authorities"].get(
            payload.get("principal_id", ""), {}
        )
        key = self.keys.get(authority.get("key_id", ""))
        try:
            interval_valid = (parse_time(payload["issued_at"]) <= parse_time(now)
                              < parse_time(payload["expires_at"]))
        except (KeyError, TypeError, ValueError):
            interval_valid = False
        valid = all((key, principal.get("status") == "ACTIVE",
                     "risk_owner" in principal.get("roles", []),
                     assessment.get("owner_principal_id") == principal.get("id"),
                     payload.get("assessment_digest") == digest(assessment),
                     payload.get("use_case_revision") == self.use_cases[use_case_id]["version"],
                     payload.get("methodology") == assessment.get("methodology"),
                     payload.get("approved_tier") == assessment.get("approved_tier") == tier,
                     payload.get("methodology") in authority.get("methodologies", []),
                     interval_valid,
                     verify_payload(payload, approval.get("signature", ""), key or "")))
        return [] if valid else ["ASSESSMENT_AUTHORITY_UNVERIFIED"]

    def _evidence_for_claim(self, use_case_id: str, claim_id: str) -> list[tuple[Evidence, str]]:
        rows = self.db.execute(
            "SELECT e.payload_json, e.signature FROM evidence_records e "
            "LEFT JOIN evidence_revocations r ON r.evidence_id = e.evidence_id "
            "WHERE e.use_case_id = ? AND e.claim_id = ? AND r.evidence_id IS NULL "
            "ORDER BY e.registered_at DESC, e.evidence_id DESC",
            (use_case_id, claim_id),
        ).fetchall()
        return [(Evidence(**json.loads(payload)), signature) for payload, signature in rows]

    def _validate_claim(
        self, use_case_id: str, claim_id: str, now: str, dependencies: dict[str, str]
    ) -> tuple[Evidence | None, list[str], list[str]]:
        candidates = self._evidence_for_claim(use_case_id, claim_id)
        if not candidates:
            return None, [], [f"EVIDENCE_MISSING:{claim_id}"]
        current_digest = self.subject_digest(use_case_id)
        candidate_findings: list[tuple[list[str], list[str]]] = []
        for evidence, signature in candidates:
            blocking: list[str] = []
            missing: list[str] = []
            try:
                _, key = self._producer_for(evidence)
            except GovernanceError:
                key = ""
            if not key or not verify_evidence(evidence, signature, key):
                blocking.append(f"EVIDENCE_AUTHENTICITY_INVALID:{claim_id}")
            if evidence.subject_digest != current_digest:
                missing.append(f"EVIDENCE_STALE_SUBJECT:{claim_id}")
            if evidence.status != "PASS":
                blocking.append(f"EVIDENCE_FAILED:{claim_id}")
            if parse_time(evidence.expires_at) <= parse_time(evidence.issued_at):
                missing.append(f"EVIDENCE_INTERVAL_INVALID:{claim_id}")
            elif parse_time(evidence.issued_at) > parse_time(now):
                missing.append(f"EVIDENCE_NOT_YET_VALID:{claim_id}")
            elif parse_time(evidence.expires_at) <= parse_time(now):
                missing.append(f"EVIDENCE_EXPIRED:{claim_id}")
            for name, expected in dependencies.items():
                if evidence.dependencies.get(name) != expected:
                    missing.append(f"EVIDENCE_STALE_DEPENDENCY:{claim_id}:{name}")
            if not blocking and not missing:
                return evidence, [], []
            candidate_findings.append((blocking, missing))
        return None, *candidate_findings[0]

    def evaluate(self, use_case_id: str, now: str) -> GovernanceDecision:
        subject = self.subject(use_case_id)
        use_case, model, agent = subject["use_case"], subject["model"], subject["agent"]
        risk_tier, floors = self._risk_tier(use_case_id)
        blocking: list[str] = []
        missing: list[str] = self._assessment_findings(use_case_id, risk_tier, now)
        statuses = self.policy["approved_lifecycle_statuses"]
        if use_case["lifecycle"] not in statuses["use_case"]:
            blocking.append("USE_CASE_NOT_APPROVED")
        if model["status"] not in statuses["model"]:
            blocking.append("MODEL_NOT_APPROVED")
        if agent["status"] not in statuses["agent"]:
            blocking.append("AGENT_NOT_APPROVED")
        if use_case_id not in agent.get("permitted_use_case_ids", []):
            blocking.append("AGENT_NOT_PERMITTED")
        if use_case["intended_task"] not in model["permitted_tasks"]:
            blocking.append("MODEL_TASK_NOT_PERMITTED")
        if use_case["risk_tier"] != risk_tier:
            blocking.append("RISK_TIER_MISMATCH")
        for tool in subject["tools"]:
            if tool is None:
                blocking.append("TOOL_UNKNOWN")
            elif tool.get("status") not in statuses["tool"]:
                blocking.append("TOOL_NOT_APPROVED")
            elif use_case_id not in tool.get("permitted_use_case_ids", []):
                blocking.append("TOOL_NOT_PERMITTED")
        if any(tool and tool["effect"] == "AUTHORITATIVE_MUTATION"
               for tool in subject["tools"]) and not use_case["authority"]["may_update_underwriting_state"]:
            blocking.append("UNAUTHORIZED_AUTONOMY")
        if risk_tier == "CONSEQUENTIAL" and use_case["human_oversight"] != "VERIFIED":
            blocking.append("HUMAN_OVERSIGHT_UNVERIFIED")
        if use_case["data_residency"] == "UNKNOWN":
            missing.append("DATA_RESIDENCY_UNKNOWN")

        required = tuple(self.policy["required_claims"][risk_tier])
        dependencies = {"model_revision": model["revision"],
                        "agent_revision": agent["revision"],
                        "policy_version": self.policy["version"]}
        selected: list[dict[str, str]] = []
        for claim_id in required:
            evidence, claim_blocking, claim_missing = self._validate_claim(
                use_case_id, claim_id, now, dependencies
            )
            blocking.extend(claim_blocking)
            missing.extend(claim_missing)
            if evidence:
                selected.append({"claim_id": claim_id, "evidence_id": evidence.evidence_id,
                                 "payload_digest": digest(evidence.payload())})
        evidence_set_digest = digest(selected) if len(selected) == len(required) else ""
        current_digest = self.subject_digest(use_case_id)
        if blocking:
            state, findings = "BLOCKED", tuple(sorted(set(blocking + missing)))
        elif missing:
            state, findings = "INSUFFICIENT_EVIDENCE", tuple(sorted(set(missing)))
        else:
            state, findings = "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL", tuple(
                f"POLICY_FLOOR:{floor}" for floor in floors
            )
        return GovernanceDecision(
            use_case_id=use_case_id, decision=state, subject_digest=current_digest,
            authority=self.policy["version"], risk_tier=risk_tier, findings=findings,
            required_evidence=required, evidence_set_digest=evidence_set_digest,
        )

    def approve(self, use_case_id: str, subject_digest: str, session_id: str,
                action: str, issued_at: str, expires_at: str) -> ApprovalReceipt:
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
            receipt_id=f"GOV-APR-{uuid.uuid4().hex[:12]}", use_case_id=use_case_id,
            subject_digest=subject_digest, evidence_set_digest=decision.evidence_set_digest,
            policy_version=self.policy["version"], action=action,
            principal_id=principal["id"], issued_at=issued_at, expires_at=expires_at,
        )
        self.db.execute("INSERT INTO approvals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                        tuple(asdict(receipt).values()))
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
                    "SELECT use_case_id, subject_digest, evidence_set_digest, policy_version, "
                    "principal_id, expires_at, consumed_by FROM approvals WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if not row:
                    raise GovernanceError("APPROVAL_UNKNOWN")
                (use_case_id, approved_digest, approved_evidence, policy_version,
                 principal_id, expires_at, consumed_by) = row
                decision = self.evaluate(use_case_id, now)
                if consumed_by:
                    raise GovernanceError("APPROVAL_ALREADY_CONSUMED")
                if parse_time(expires_at) <= parse_time(now):
                    raise GovernanceError("APPROVAL_EXPIRED")
                if policy_version != self.policy["version"]:
                    raise GovernanceError("APPROVAL_POLICY_STALE")
                if approved_digest != decision.subject_digest:
                    raise GovernanceError("APPROVAL_SUBJECT_STALE")
                if approved_evidence != decision.evidence_set_digest:
                    raise GovernanceError("APPROVAL_EVIDENCE_SET_STALE")
                principal = self.principals.get(principal_id)
                if not principal or principal.get("status") != "ACTIVE" or \
                        "ai_governance_authority" not in principal["roles"]:
                    raise GovernanceError("APPROVAL_AUTHORITY_REVOKED")
                if decision.decision != "ELIGIBLE_FOR_ACCOUNTABLE_APPROVAL":
                    raise GovernanceError("POINT_OF_USE_REVALIDATION_FAILED")
                updated = self.db.execute(
                    "UPDATE approvals SET consumed_by = ? WHERE receipt_id = ? AND consumed_by IS NULL",
                    (operation_id, receipt_id),
                ).rowcount
                if updated != 1:
                    raise GovernanceError("APPROVAL_ALREADY_CONSUMED")
                self.db.execute("INSERT INTO operations VALUES (?, ?, ?, ?, 'ALLOWED')",
                                (operation_id, receipt_id, use_case_id, decision.subject_digest))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        return GovernanceDecision(
            use_case_id=decision.use_case_id, decision="ALLOWED",
            subject_digest=decision.subject_digest, authority=decision.authority,
            risk_tier=decision.risk_tier, findings=("APPROVAL_CONSUMED",),
            required_evidence=decision.required_evidence,
            evidence_set_digest=decision.evidence_set_digest,
        )

    def change_impact(self, use_case_id: str, changes: dict[str, str]) -> dict[str, Any]:
        obligations: set[str] = set()
        for component in changes:
            obligations.update(self.policy["reassessment_triggers"].get(component, []))
        return {"use_case_id": use_case_id,
                "state": "REASSESSMENT_REQUIRED" if obligations else "NO_GOVERNANCE_IMPACT_IDENTIFIED",
                "changed_components": sorted(changes),
                "required_reassessment": sorted(obligations),
                "authority": self.policy["version"]}

    def _validate_runtime_observation(
        self, use_case_id: str, observation: Evidence, signature: str, now: str
    ) -> None:
        try:
            _, key = self._producer_for(observation)
        except GovernanceError as exc:
            raise GovernanceError("RUNTIME_VIOLATION_AUTHENTICITY_UNVERIFIED") from exc
        if not verify_evidence(observation, signature, key):
            raise GovernanceError("RUNTIME_VIOLATION_AUTHENTICITY_UNVERIFIED")
        if observation.subject_digest != self.subject_digest(use_case_id):
            raise GovernanceError("RUNTIME_VIOLATION_SUBJECT_MISMATCH")
        invariant = self.policy["protected_invariants"].get(
            observation.details.get("protected_invariant", "")
        )
        if (not invariant or use_case_id not in invariant["use_case_ids"]
                or invariant.get("action") != "SUSPEND"):
            raise GovernanceError("RUNTIME_INVARIANT_UNKNOWN")
        deployment = self.deployments.get(observation.details.get("deployment_id", ""))
        subject = self.subject(use_case_id)
        if not deployment or any((deployment.get("use_case_id") != use_case_id,
                                  deployment.get("status") != "ACTIVE",
                                  deployment.get("model_revision") != subject["model"]["revision"],
                                  deployment.get("agent_revision") != subject["agent"]["revision"],
                                  deployment.get("environment") != observation.details.get("environment"))):
            raise GovernanceError("RUNTIME_DEPLOYMENT_MISMATCH")
        window = observation.details.get("observation_window", {})
        population, violations = (observation.details.get("population"),
                                  observation.details.get("violations"))
        event_ids = observation.details.get("event_ids", [])
        try:
            interval_valid = (parse_time(window["start"]) < parse_time(window["end"])
                              <= parse_time(observation.issued_at) <= parse_time(now)
                              < parse_time(observation.expires_at))
        except (KeyError, TypeError, ValueError):
            interval_valid = False
        counts_valid = (isinstance(population, int) and not isinstance(population, bool)
                        and isinstance(violations, int) and not isinstance(violations, bool)
                        and population >= invariant["minimum_population"]
                        and 1 <= violations <= population
                        and isinstance(event_ids, list) and len(set(event_ids)) >= violations)
        if observation.status != "FAIL" or not interval_valid or not counts_valid:
            raise GovernanceError("RUNTIME_OBSERVATION_INVALID")

    def suspend_on_violation(
        self, use_case_id: str, observation: Evidence, signature: str, now: str
    ) -> GovernanceDecision:
        self._validate_runtime_observation(use_case_id, observation, signature, now)
        self.register_evidence(use_case_id, observation, signature, now)
        invariant = observation.details["protected_invariant"]
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute(
                    "UPDATE governance_state SET lifecycle = 'SUSPENDED', "
                    "state_version = state_version + 1, updated_at = ?, reason_code = ? "
                    "WHERE use_case_id = ?", (now, f"PROTECTED_INVARIANT:{invariant}", use_case_id),
                )
                suspended_digest = self.subject_digest(use_case_id)
                self.db.execute(
                    "INSERT INTO audit_events VALUES (?, ?, 'SUSPENSION', ?, ?, ?)",
                    (f"AUD-{uuid.uuid4().hex}", use_case_id, suspended_digest, now,
                     json.dumps({"invariant": invariant, "evidence_id": observation.evidence_id})),
                )
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        tier, _ = self._risk_tier(use_case_id)
        return GovernanceDecision(
            use_case_id=use_case_id, decision="SUSPENDED", subject_digest=suspended_digest,
            authority=self.policy["version"], risk_tier=tier,
            findings=(f"PROTECTED_INVARIANT_VIOLATION:{invariant}",),
            required_evidence=tuple(self.policy["required_claims"][tier]),
        )

    def reinstate_after_review(
        self, use_case_id: str, evidence: Evidence, signature: str, session_id: str, now: str
    ) -> GovernanceDecision:
        principal = self.authenticate(session_id)
        if "ai_governance_authority" not in principal["roles"]:
            raise GovernanceError("REINSTATEMENT_NOT_AUTHORIZED")
        if self.lifecycle(use_case_id)["lifecycle"] != "SUSPENDED":
            raise GovernanceError("REINSTATEMENT_STATE_INVALID")
        if evidence.kind != "reinstatement" or evidence.status != "PASS" or not all((
                evidence.details.get("protected_invariant"), evidence.details.get("deployment_id"),
                evidence.details.get("remediation_id"), evidence.details.get("verification_summary"))):
            raise GovernanceError("REINSTATEMENT_EVIDENCE_INVALID")
        invariant = self.policy["protected_invariants"].get(
            evidence.details["protected_invariant"], {}
        )
        deployment = self.deployments.get(evidence.details["deployment_id"], {})
        if (use_case_id not in invariant.get("use_case_ids", [])
                or deployment.get("use_case_id") != use_case_id
                or deployment.get("status") != "ACTIVE"):
            raise GovernanceError("REINSTATEMENT_EVIDENCE_INVALID")
        self.register_evidence(use_case_id, evidence, signature, now)
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute(
                    "UPDATE governance_state SET lifecycle = 'REASSESSMENT_REQUIRED', "
                    "state_version = state_version + 1, updated_at = ?, reason_code = 'HUMAN_REVIEW_COMPLETE' "
                    "WHERE use_case_id = ?", (now, use_case_id),
                )
                updated_digest = self.subject_digest(use_case_id)
                self.db.execute(
                    "INSERT INTO audit_events VALUES (?, ?, 'REINSTATEMENT_REVIEW', ?, ?, ?)",
                    (f"AUD-{uuid.uuid4().hex}", use_case_id, updated_digest, now,
                     json.dumps({"principal_id": principal["id"], "evidence_id": evidence.evidence_id})),
                )
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
        tier, _ = self._risk_tier(use_case_id)
        return GovernanceDecision(
            use_case_id=use_case_id, decision="REASSESSMENT_REQUIRED",
            subject_digest=updated_digest, authority=self.policy["version"], risk_tier=tier,
            findings=("ACCOUNTABLE_REINSTATEMENT_REQUIRES_NEW_APPROVAL",),
            required_evidence=tuple(self.policy["required_claims"][tier]),
        )

    def close(self) -> None:
        self.db.close()
