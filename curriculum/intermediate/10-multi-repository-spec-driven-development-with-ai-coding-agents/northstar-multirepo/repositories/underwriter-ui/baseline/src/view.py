"""Render proposal state without representing it as an approved decision."""


def label(proposal: dict[str, object]) -> str:
    return "Review required" if proposal.get("review_required") else "Proposal pending authorization"
