"""Typed records crossing the Course 25 governance boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class GovernanceError(RuntimeError):
    """Stable, observable denial from the trusted control plane."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    kind: str
    subject_digest: str
    producer: str
    status: str
    issued_at: str
    expires_at: str
    dependencies: dict[str, str]
    details: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovalReceipt:
    receipt_id: str
    use_case_id: str
    subject_digest: str
    policy_version: str
    action: str
    principal_id: str
    issued_at: str
    expires_at: str


@dataclass(frozen=True)
class GovernanceDecision:
    use_case_id: str
    decision: str
    subject_digest: str
    authority: str
    risk_tier: str
    findings: tuple[str, ...]
    required_evidence: tuple[str, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "use_case_id": self.use_case_id,
            "decision": self.decision,
            "subject_digest": self.subject_digest,
            "authority": self.authority,
            "risk_tier": self.risk_tier,
            "findings": list(self.findings),
            "required_evidence": list(self.required_evidence),
        }
