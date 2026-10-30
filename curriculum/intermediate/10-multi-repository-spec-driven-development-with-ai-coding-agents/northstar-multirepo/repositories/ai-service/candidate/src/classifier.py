"""Revision-2 non-authoritative classification producer with provenance."""


AMBIGUITY_STATES = {"SUPPORTED", "AMBIGUOUS", "UNSUPPORTED"}


def propose(
    document_id: str,
    candidate_requirement_ids: list[str],
    evidence_refs: list[str],
    ambiguity_status: str,
    *,
    tenant_id: str,
    model_confidence: float,
) -> dict[str, object]:
    """Build a proposal; confidence is observable but never grants review authority."""
    if not document_id or not tenant_id or not candidate_requirement_ids:
        raise ValueError("document, tenant, and candidate requirement identity are required")
    if not evidence_refs:
        raise ValueError("at least one evidence reference is required")
    if ambiguity_status not in AMBIGUITY_STATES:
        raise ValueError("ambiguity status must be a trusted application classification")
    if not 0.0 <= model_confidence <= 1.0:
        raise ValueError("model confidence must be between zero and one")
    return {
        "proposal_id": f"proposal:{tenant_id}:{document_id}",
        "document_id": document_id,
        "tenant_id": tenant_id,
        "candidate_requirement_ids": list(candidate_requirement_ids),
        "ambiguity_status": ambiguity_status,
        "model_confidence": model_confidence,
        "review_required": ambiguity_status in {"AMBIGUOUS", "UNSUPPORTED"},
        "evidence_refs": list(evidence_refs),
        "model_provenance": {
            "model_id": "northstar-classifier",
            "model_revision": "2026-02",
        },
    }
