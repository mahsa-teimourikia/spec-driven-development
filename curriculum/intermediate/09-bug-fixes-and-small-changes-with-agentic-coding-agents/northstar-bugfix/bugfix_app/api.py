"""Production-path adapters used to discriminate competing defect causes."""

from __future__ import annotations

from collections.abc import Callable

from .risk_engine import classify_risk_fixed


def identity_normalizer(score: int) -> int:
    return score


def off_by_one_normalizer(score: int) -> int:
    """Synthetic alternative fault used to prove a unit fix may be insufficient."""
    return score - 1


def risk_response(
    submission_id: str,
    raw_score: int,
    *,
    classifier: Callable[[int], str] = classify_risk_fixed,
    normalizer: Callable[[int], int] = identity_normalizer,
) -> dict[str, object]:
    normalized = normalizer(raw_score)
    category = classifier(normalized)
    return {
        "submission_id": submission_id,
        "normalized_score": normalized,
        "risk_category": category,
        "review_required": category == "HIGH",
    }
