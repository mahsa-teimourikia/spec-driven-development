"""Revision-1 non-authoritative classification producer."""


def propose(document_id: str, confidence: float) -> dict[str, object]:
    return {
        "proposal_id": f"proposal:{document_id}",
        "document_id": document_id,
        "candidate_requirement_ids": ["REQ-45"],
        "review_required": confidence < 0.95,
    }
