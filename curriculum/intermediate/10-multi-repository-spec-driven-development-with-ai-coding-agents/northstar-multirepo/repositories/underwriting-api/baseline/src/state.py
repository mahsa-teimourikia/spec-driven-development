"""Protected owner of authoritative underwriting requirement state."""


def apply_review_decision(*, authorized: bool, current: bool) -> str:
    if not authorized or not current:
        return "BLOCKED"
    return "APPLIED"
