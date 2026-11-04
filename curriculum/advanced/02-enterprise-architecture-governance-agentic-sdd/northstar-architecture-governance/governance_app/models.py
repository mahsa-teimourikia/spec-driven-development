"""Stable records used by the Course 26 architecture control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class ArchitectureError(ValueError):
    """A fail-closed architecture-governance error with a stable code."""

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class ServiceEdge:
    source: str
    target: str
    mode: str = "sync"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    code: str
    resource: str
    disposition: str
    message: str
    evidence: tuple[str, ...] = ()
    exception_id: str | None = None

    def payload(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


@dataclass(frozen=True)
class Observation:
    observation_id: str
    repository: str
    base_commit: str
    head_commit: str
    environment: str
    policy_version: str
    changed_files: tuple[str, ...]
    imports: tuple[dict[str, Any], ...]
    urls: tuple[dict[str, Any], ...]
    technologies: tuple[dict[str, Any], ...]
    service_edges: tuple[ServiceEdge, ...]
    file_digests: dict[str, str]
    adr_proposal: dict[str, Any] | None
    architecture_context: dict[str, Any] | None
    policy_shadow_paths: tuple[str, ...]
    runtime_egress_evidence: bool
    runtime_evidence_id: str | None
    producer: str
    issued_at: str
    signature: str = field(default="", compare=False)

    def payload(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("signature", None)
        result["changed_files"] = list(self.changed_files)
        result["imports"] = list(self.imports)
        result["urls"] = list(self.urls)
        result["technologies"] = list(self.technologies)
        result["service_edges"] = [asdict(edge) for edge in self.service_edges]
        result["policy_shadow_paths"] = list(self.policy_shadow_paths)
        return result


@dataclass(frozen=True)
class ConformanceReport:
    report_id: str
    repository: str
    base_commit: str
    head_commit: str
    environment: str
    policy_version: str
    decision: str
    findings: tuple[Finding, ...]
    changed_files: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    generated_at: str
    observation_signature_verified: bool

    def payload(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "repository": self.repository,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "environment": self.environment,
            "policy_version": self.policy_version,
            "decision": self.decision,
            "findings": [item.payload() for item in self.findings],
            "changed_files": list(self.changed_files),
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "generated_at": self.generated_at,
            "observation_signature_verified": self.observation_signature_verified,
        }
