"""Validate ADR lifecycle, typed decisions, and authority independently of author claims."""

from __future__ import annotations

from typing import Any

from .models import Finding, Observation


PROPOSAL_FIELDS = {
    "id",
    "decision_type",
    "capability",
    "selected_dependency",
    "boundary",
    "status",
    "scope",
}
SCOPE_LEVEL = {"implementation": 1, "solution": 2, "enterprise": 3}


def _matches_module(module: str, names: tuple[str, ...]) -> bool:
    return module in names or module.startswith(tuple(name + "." for name in names))


def evaluate_adrs(
    observation: Observation,
    registry: dict[str, Any],
    standards: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    proposal = observation.adr_proposal
    if proposal is not None:
        missing = sorted(PROPOSAL_FIELDS - set(proposal))
        if missing:
            findings.append(
                Finding(
                    rule_id="ADR-GOV-001",
                    code="ADR_DECISION_UNTYPED",
                    resource="architecture/adr-proposal.json",
                    disposition="EVIDENCE",
                    message="The ADR proposal lacks typed decision fields needed for independent evaluation.",
                    evidence=tuple(missing),
                )
            )
        else:
            dependency = str(proposal["selected_dependency"])
            prohibited = tuple(standards["prohibited_provider_modules"])
            conflicts = sorted(set(proposal.get("conflicts_with", [])))
            if _matches_module(dependency, prohibited):
                evidence = (dependency, *conflicts)
                findings.append(
                    Finding(
                        rule_id="ADR-GOV-001",
                        code="ADR_CONFLICTS_WITH_ENTERPRISE_STANDARD",
                        resource="architecture/adr-proposal.json",
                        disposition="REVIEW",
                        message="The selected dependency conflicts with the enterprise gateway boundary.",
                        evidence=evidence,
                    )
                )
            if proposal["status"] != "PROPOSED":
                findings.append(
                    Finding(
                        rule_id="ADR-GOV-004",
                        code="ADR_STATUS_NOT_PROPOSAL",
                        resource="architecture/adr-proposal.json",
                        disposition="REVIEW",
                        message="A repository-local proposal cannot self-assert an accepted decision.",
                        evidence=(str(proposal["status"]),),
                    )
                )
            if proposal["scope"] not in {"implementation", "solution"}:
                findings.append(
                    Finding(
                        rule_id="ADR-GOV-005",
                        code="ADR_SCOPE_EXCEEDS_LOCAL_AUTHORITY",
                        resource="architecture/adr-proposal.json",
                        disposition="REVIEW",
                        message="A local proposal cannot claim enterprise decision authority.",
                        evidence=(str(proposal["scope"]),),
                    )
                )

    statuses = {item["id"]: item for item in registry["records"]}
    context = observation.architecture_context or {}
    required_scope = str(context.get("required_scope", "implementation"))
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
        elif record["status"] != "ACCEPTED":
            findings.append(
                Finding(
                    rule_id="ADR-GOV-002",
                    code="ADR_NOT_ACCEPTED",
                    resource="architecture/context.json",
                    disposition="REVIEW",
                    message=f"ADR {adr_id} is not an accepted architecture decision.",
                    evidence=(adr_id, str(record["status"])),
                )
            )
        elif SCOPE_LEVEL.get(str(record.get("scope")), 0) < SCOPE_LEVEL.get(required_scope, 1):
            findings.append(
                Finding(
                    rule_id="ADR-GOV-002",
                    code="ADR_SCOPE_INSUFFICIENT",
                    resource="architecture/context.json",
                    disposition="EVIDENCE",
                    message=f"ADR {adr_id} does not have the required decision scope.",
                    evidence=(adr_id, required_scope, str(record.get("scope"))),
                )
            )
    return findings
