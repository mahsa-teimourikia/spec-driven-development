"""Revision-1 review consumer."""


def accepts(contract_revision: int) -> bool:
    return contract_revision == 1


def consume(proposal: dict[str, object], contract_revision: int) -> str:
    required = {"proposal_id", "document_id", "candidate_requirement_ids", "review_required"}
    return "ACCEPTED" if accepts(contract_revision) and required <= proposal.keys() else "REJECTED"
