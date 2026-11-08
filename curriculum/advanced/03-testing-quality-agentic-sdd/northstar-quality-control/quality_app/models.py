"""Typed records for specification-traceable quality evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class QualityError(ValueError):
    """Fail-closed error with a stable reason code."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class SubjectObservation:
    change_id: str
    repository: str
    revision: str
    specification_revision: str
    implementation_digest: str
    policy_version: str
    producer: str
    issued_at: str
    signature: str = field(default="", compare=False)

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("signature", None)
        return value


@dataclass(frozen=True)
class QualityFinding:
    code: str
    requirement_id: str
    resource: str
    disposition: str
    message: str
    evidence: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = list(self.evidence)
        return value


@dataclass(frozen=True)
class QualityReport:
    report_id: str
    change_id: str
    revision: str
    specification_revision: str
    policy_version: str
    decision: str
    findings: tuple[QualityFinding, ...]
    evidence_ids: tuple[str, ...]
    coverage: dict[str, Any]
    metrics: dict[str, Any]
    limitations: tuple[str, ...]
    generated_at: str
    release_authorized: bool = False

    def payload(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "change_id": self.change_id,
            "revision": self.revision,
            "specification_revision": self.specification_revision,
            "policy_version": self.policy_version,
            "decision": self.decision,
            "findings": [item.payload() for item in self.findings],
            "evidence_ids": list(self.evidence_ids),
            "coverage": self.coverage,
            "metrics": self.metrics,
            "limitations": list(self.limitations),
            "generated_at": self.generated_at,
            "release_authorized": self.release_authorized,
        }

