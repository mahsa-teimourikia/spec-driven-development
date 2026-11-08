"""Risk-adaptive verification selection with mandatory protected checks."""

from __future__ import annotations

from typing import Any


STRATEGIES = {
    "documentation": {"documentation"},
    "local_deterministic_bug": {"unit", "negative"},
    "shared_api": {"contract", "integration"},
    "database": {"migration", "rollback", "concurrency", "integrity"},
    "authorization": {"security", "negative", "integration"},
    "ai_model_or_prompt": {"evaluation", "negative", "metamorphic"},
    "cross_repository": {"contract", "integration", "failure"},
    "critical_workflow": {"failure", "recovery", "operational_readiness"},
}

BOUNDARY_MANDATORY = {
    "human_review": {"property", "metamorphic", "negative"},
    "tenant_isolation": {"security", "negative"},
    "state_authority": {"contract", "negative"},
    "idempotency": {"concurrency", "failure", "recovery"},
    "provenance": {"contract", "evaluation", "negative"},
}


def select_tests(change: dict[str, Any]) -> dict[str, Any]:
    category = str(change.get("category", ""))
    selected = set(STRATEGIES.get(category, set()))
    for boundary in change.get("protected_boundaries", []):
        selected.update(BOUNDARY_MANDATORY.get(str(boundary), set()))
    unknown = bool(change.get("unknown_dependencies"))
    return {
        "status": "IMPACT_REVIEW_REQUIRED" if unknown else "READY",
        "selected_kinds": sorted(selected),
        "mandatory_boundaries": sorted(set(change.get("protected_boundaries", []))),
        "unknown_impact_is_no_impact": False,
    }
