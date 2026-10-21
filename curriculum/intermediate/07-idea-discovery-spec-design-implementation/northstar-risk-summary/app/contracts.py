"""Typed contracts at the model/application trust boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceDocument:
    document_id: str
    submission_id: str
    revision: int
    content: str
    risk_terms: tuple[str, ...]
    authorized: bool = True


@dataclass(frozen=True)
class ExecutionContext:
    context_id: str
    submission_id: str
    specification_revision: int
    architecture_revision: str
    repository_base: str
    document_revisions: tuple[tuple[str, int], ...]
    permissions: tuple[str, ...]
    digest: str


@dataclass(frozen=True)
class RiskClaim:
    claim_id: str
    risk_code: str
    text: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ModelProposal:
    proposal_id: str
    submission_id: str
    context_digest: str
    specification_revision: int
    architecture_revision: str
    claims: tuple[RiskClaim, ...]
    attempted_actions: tuple[str, ...] = ()

    def payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    subject: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    status: str
    proposal_digest: str
    findings: tuple[ValidationFinding, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalReceipt:
    receipt_id: str
    proposal_digest: str
    principal: str
    decision: str
    issued_at: str
    expires_at: str
    identity_verified: bool
    attestation_verified: bool


@dataclass(frozen=True)
class PipelineResult:
    state: str
    reason_codes: tuple[str, ...]
    proposal_digest: str | None
    evidence_ids: tuple[str, ...]
    release_authorized: bool = False
