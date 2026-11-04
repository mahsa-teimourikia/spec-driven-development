"""Validate ADR lifecycle and authority without treating prose as policy override."""

from __future__ import annotations

from typing import Any

from .models import Finding, Observation


def evaluate_adrs(observation: Observation, registry: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    proposal = observation.adr_proposal or {}
    conflicts = set(proposal.get("conflicts_with", []))
    if conflicts:
        findings.append(
            Finding(
                rule_id="ADR-GOV-001",
                code="ADR_CONFLICTS_WITH_ENTERPRISE_STANDARD",
                resource="architecture/adr-proposal.json",
                disposition="REVIEW",
                message="A local ADR cannot silently override an enterprise standard.",
                evidence=tuple(sorted(conflicts)),
            )
        )

    statuses = {item["id"]: item for item in registry["records"]}
    context = observation.architecture_context or {}
    for adr_id in context.get("adr_refs", []):
        record = statuses.get(adr_id)
        if record is None:
            findings.append(
                Finding(
                    rule_id="ADR-GOV-002",
                    code="ADR_REFERENCE_UNKNOWN",
                    resource="architecture/context.json",
                    disposition="EVIDENCE",
                    message=f"Referenced ADR {adr_id} is absent from the authoritative registry.",
                    evidence=(adr_id,),
                )
            )
        elif record["status"] == "SUPERSEDED":
            findings.append(
                Finding(
                    rule_id="ADR-GOV-003",
                    code="ADR_SUPERSEDED",
                    resource="architecture/context.json",
                    disposition="REASSESS",
                    message=f"ADR {adr_id} was superseded by {record['superseded_by']}.",
                    evidence=(adr_id, record["superseded_by"]),
                )
            )
    return findings
