"""Revision-2 non-authoritative classification producer with provenance."""


def propose(document_id: str, confidence: float, evidence_refs: list[str]) -> dict[str, object]:
    if not evidence_refs:
        raise ValueError("at least one evidence reference is required")
    return {
        "proposal_id": f"proposal:{document_id}",
        "document_id": document_id,
        "candidate_requirement_ids": ["REQ-45"],
        "review_required": confidence < 0.95,
        "evidence_refs": evidence_refs,
        "model_provenance": {"model_id": "northstar-classifier", "model_revision": "2026-02"},
    }
