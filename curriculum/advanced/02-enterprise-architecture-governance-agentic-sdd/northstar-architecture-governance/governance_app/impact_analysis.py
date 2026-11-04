"""Targeted invalidation for architecture-policy and ADR changes."""

from __future__ import annotations

from typing import Any


def impact_for(change_id: str, graph: dict[str, Any]) -> dict[str, Any]:
    impacts = [item for item in graph["changes"] if item["change_id"] == change_id]
    if not impacts:
        return {
            "change_id": change_id,
            "repositories": [],
            "contracts": [],
            "evaluations": [],
            "controls": [],
            "decision": "NO_REGISTERED_IMPACT",
        }
    record = impacts[0]
    return {
        "change_id": change_id,
        "repositories": sorted(record["repositories"]),
        "contracts": sorted(record["contracts"]),
        "evaluations": sorted(record["evaluations"]),
        "controls": sorted(record["controls"]),
        "decision": "TARGETED_REASSESSMENT_REQUIRED",
    }
