"""Deterministic teaching classifier: proposals never mutate underwriting state."""


def classify(document: str) -> dict:
    normalized = document.lower()
    injection = any(token in normalized for token in ("ignore policy", "invoke tool", "approve application"))
    ambiguous = "unclear" in normalized or "ambiguous" in normalized or injection
    category = "UNKNOWN" if ambiguous else "LOSS_NOTICE" if "loss" in normalized else "APPLICATION"
    return {
        "category": category,
        "ambiguous": ambiguous,
        "human_review_required": ambiguous,
        "protected_mutation": False,
    }
