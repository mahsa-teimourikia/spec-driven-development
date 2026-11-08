"""Requirement-weighted mutations executed against the real service fixtures."""

from __future__ import annotations

from typing import Any

from .behavior_harness import execute_protected_checks, metamorphic_population, property_population
from .repository_harness import RevisionFixture


MUTATION_TO_CHECK = {
    "IGNORE_AMBIGUITY": "ambiguous_requires_review",
    "REMOVE_TENANT_FILTER": "cross_tenant_denied",
    "DROP_IDEMPOTENCY_KEY": "duplicate_effect_is_single",
    "ACCEPT_EXPIRED_APPROVAL": "expired_approval_rejected",
    "DROP_EVIDENCE_REFERENCES": "evidence_provenance_preserved",
    "ALLOW_AI_STATE_MUTATION": "ai_cannot_mutate_state",
    "TREAT_REVIEW_OUTAGE_AS_SUCCESS": "review_outage_holds_safely",
}


def execute_mutations(fixture: RevisionFixture) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    for mutation_id, expected_check in MUTATION_TO_CHECK.items():
        behavior = execute_protected_checks(fixture, mutant=mutation_id)
        detected = not behavior["checks"][expected_check]
        if mutation_id == "IGNORE_AMBIGUITY":
            detected = detected and not property_population(fixture, mutant=mutation_id)["passed"]
            detected = detected and not metamorphic_population(fixture, mutant=mutation_id)["passed"]
        outcomes.append(
            {
                "mutation_id": mutation_id,
                "requirement_id": _requirement_for(mutation_id),
                "detected_by": expected_check,
                "outcome": "KILLED" if detected else "SURVIVED",
            }
        )
    return outcomes


def _requirement_for(mutation_id: str) -> str:
    if mutation_id == "IGNORE_AMBIGUITY":
        return "QI-001"
    if mutation_id == "REMOVE_TENANT_FILTER":
        return "QI-002"
    if mutation_id in {"ALLOW_AI_STATE_MUTATION", "ACCEPT_EXPIRED_APPROVAL"}:
        return "QI-003"
    if mutation_id == "DROP_IDEMPOTENCY_KEY":
        return "QI-004"
    if mutation_id == "DROP_EVIDENCE_REFERENCES":
        return "QI-005"
    return "QI-001"
