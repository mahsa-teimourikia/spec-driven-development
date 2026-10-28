"""Revision-2 tolerant review consumer."""


def accepts(contract_revision: int) -> bool:
    return contract_revision in {1, 2}


def validate_v2(proposal: dict[str, object]) -> bool:
    return bool(proposal.get("evidence_refs")) and bool(proposal.get("model_provenance"))
