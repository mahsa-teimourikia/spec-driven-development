"""Northstar protected underwriting state boundary."""

from __future__ import annotations


def persist_classification(
    state: dict,
    proposal,
    review_result: dict,
    *,
    caller: str,
    mutant: str | None = None,
) -> dict:
    if caller == "ai-service" and mutant != "ALLOW_AI_STATE_MUTATION":
        return {"status": "DENIED", "state": dict(state)}
    if review_result.get("status") not in {"APPLIED", "REPLAYED"}:
        return {"status": "DENIED", "state": dict(state)}
    updated = dict(state)
    updated[proposal.document_id] = proposal.document_type
    return {"status": "PERSISTED", "state": updated}


def route_during_review_outage(*, mutant: str | None = None) -> str:
    if mutant == "TREAT_REVIEW_OUTAGE_AS_SUCCESS":
        return "AUTONOMOUS_APPROVAL"
    return "REVIEW_UNAVAILABLE_SAFE_HOLD"
