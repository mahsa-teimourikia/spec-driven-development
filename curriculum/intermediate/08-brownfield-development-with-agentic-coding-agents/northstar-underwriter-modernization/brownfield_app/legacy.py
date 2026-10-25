"""Legacy behavior and an additive, non-authoritative proposal path."""

from __future__ import annotations

from .contracts import Submission, SummaryProposal


def classify_risk(score: int) -> str:
    """The approved deterministic baseline from REQ-RISK-010@3."""
    if score >= 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def legacy_v1_response(submission: Submission) -> dict[str, object]:
    """Preserve the semantic v1 contract, including mandatory review for HIGH."""
    category = classify_risk(submission.score)
    return {
        "submission_id": submission.submission_id,
        "risk_category": category,
        "review_required": category == "HIGH",
    }


class LegacySummaryProvider:
    def generate(self, submission: Submission) -> SummaryProposal:
        return SummaryProposal(
            submission_id=submission.submission_id,
            source="legacy",
            text=f"Legacy {classify_risk(submission.score).lower()}-risk summary",
            evidence=submission.evidence,
            authoritative=False,
        )


class AISummaryProvider:
    """Deterministic stand-in for an AI proposer; never an authority boundary."""

    def generate(self, submission: Submission) -> SummaryProposal:
        category = classify_risk(submission.score)
        evidence = ", ".join(submission.evidence) if submission.evidence else "no evidence"
        return SummaryProposal(
            submission_id=submission.submission_id,
            source="ai_proposal",
            text=f"Proposed {category.lower()}-risk summary grounded in {evidence}",
            evidence=submission.evidence,
            authoritative=False,
        )
