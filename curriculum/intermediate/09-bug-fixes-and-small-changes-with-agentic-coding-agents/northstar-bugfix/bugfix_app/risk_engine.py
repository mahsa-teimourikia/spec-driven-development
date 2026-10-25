"""The observed boundary defect and the minimal sufficient correction."""

from __future__ import annotations


def validate_score(score: int) -> None:
    if type(score) is not int or not 0 <= score <= 100:
        raise ValueError("score must be an integer from 0 through 100")


def classify_risk_buggy(score: int) -> str:
    """Observed BUG-2415 behavior: the exact boundary is wrong."""
    validate_score(score)
    if score > 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def classify_risk_fixed(score: int) -> str:
    """Approved REQ-RISK-010@3 behavior."""
    validate_score(score)
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"
