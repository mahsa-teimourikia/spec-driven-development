"""Northstar AI Service fixture executed from an isolated Git revision."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Proposal:
    document_id: str
    tenant_id: str
    document_type: str
    confidence: float
    ambiguous: bool
    evidence_refs: tuple[str, ...]
    model_revision: str


def propose(document: dict, *, mutant: str | None = None) -> Proposal:
    """Create a non-authoritative proposal from a deterministic prediction artifact."""

    evidence_refs = tuple(document.get("evidence_refs", ()))
    if mutant == "DROP_EVIDENCE_REFERENCES":
        evidence_refs = ()
    return Proposal(
        document_id=str(document["document_id"]),
        tenant_id=str(document["tenant_id"]),
        document_type=str(document["prediction"]),
        confidence=float(document["confidence"]),
        ambiguous=bool(document.get("ambiguous", False)),
        evidence_refs=evidence_refs,
        model_revision=str(document.get("model_revision", "classifier-v2")),
    )


def evidence_is_supported(proposal: Proposal, authorized_refs: set[str]) -> bool:
    """A populated citation is insufficient unless every reference is authorized and known."""

    return bool(proposal.evidence_refs) and set(proposal.evidence_refs).issubset(authorized_refs)
