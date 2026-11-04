"""Architecture fitness functions over independently derived observations."""

from __future__ import annotations

from typing import Any

from .architecture_graph import layer_findings, service_graph_findings
from .models import Finding, Observation


PROVIDER_MODULES = ("openai", "anthropic", "provider_sdk", "direct_model_client")
HTTP_MODULES = ("httpx", "requests", "urllib3", "aiohttp")


def evaluate_fitness(
    observation: Observation,
    standards: dict[str, Any],
    dependency_rules: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    direct_provider_seen = False
    http_seen = False

    for item in observation.imports:
        module = str(item["module"])
        resource = str(item["file"])
        if module in PROVIDER_MODULES or module.startswith(tuple(name + "." for name in PROVIDER_MODULES)):
            direct_provider_seen = True
            findings.append(
                Finding(
                    rule_id="EA-001",
                    code="DIRECT_MODEL_PROVIDER_DEPENDENCY",
                    resource=resource,
                    disposition="BLOCK",
                    message="Model providers must be reached through the enterprise AI gateway.",
                    evidence=(f"{resource}:{item['line']}", module),
                )
            )
        if module in HTTP_MODULES or module.startswith(tuple(name + "." for name in HTTP_MODULES)):
            http_seen = True

    for item in observation.urls:
        if "model-provider.example" in str(item["url"]):
            direct_provider_seen = True
            findings.append(
                Finding(
                    rule_id="EA-001",
                    code="DIRECT_MODEL_PROVIDER_ENDPOINT",
                    resource=str(item["file"]),
                    disposition="BLOCK",
                    message="A provider endpoint bypasses the approved enterprise AI gateway.",
                    evidence=(f"{item['file']}:{item['line']}", str(item["url"])),
                )
            )

    if http_seen and not direct_provider_seen and not observation.runtime_egress_evidence:
        findings.append(
            Finding(
                rule_id="EA-001",
                code="RUNTIME_EGRESS_EVIDENCE_MISSING",
                resource="runtime-egress",
                disposition="EVIDENCE",
                message="Generic HTTP usage is ambiguous without trusted runtime egress evidence.",
                evidence=("config/egress-evidence.json:missing-or-unverified",),
            )
        )

    for item in observation.imports:
        module = str(item["module"])
        if module == "underwriting_database" or module.startswith("underwriting_database."):
            findings.append(
                Finding(
                    rule_id="EA-004",
                    code="PRIVATE_DATASTORE_ACCESS",
                    resource=str(item["file"]),
                    disposition="BLOCK",
                    message="The AI service must use the governed underwriting data API.",
                    evidence=(f"{item['file']}:{item['line']}", module),
                )
            )

    approved = set(standards["approved_technologies"])
    review_required = set(standards["architecture_review_technologies"])
    for item in observation.technologies:
        name = str(item["name"])
        if name in review_required:
            findings.append(
                Finding(
                    rule_id="EA-003",
                    code="ARCHITECTURE_DECISION_REQUIRED",
                    resource="requirements.txt",
                    disposition="REVIEW",
                    message=f"Technology {name} requires an approved architecture decision.",
                    evidence=(f"requirements.txt:{item['line']}",),
                )
            )
        elif name not in approved:
            findings.append(
                Finding(
                    rule_id="EA-003",
                    code="TECHNOLOGY_NOT_IN_STANDARD",
                    resource="requirements.txt",
                    disposition="REVIEW",
                    message=f"Technology {name} is absent from the enterprise standard.",
                    evidence=(f"requirements.txt:{item['line']}",),
                )
            )

    findings.extend(layer_findings(observation.imports))
    allowed = {
        (item["source"], item["target"], item["mode"])
        for item in dependency_rules["allowed_service_edges"]
    }
    findings.extend(service_graph_findings(observation.service_edges, allowed))
    for path in observation.policy_shadow_paths:
        findings.append(
            Finding(
                rule_id="EA-AUTH-001",
                code="POLICY_SHADOWING_ATTEMPT",
                resource=path,
                disposition="BLOCK",
                message="A candidate repository cannot redefine enterprise architecture authority.",
                evidence=(path,),
            )
        )
    return _deduplicate(findings)


def _deduplicate(findings: list[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str, str], Finding] = {}
    for item in findings:
        unique[(item.rule_id, item.code, item.resource)] = item
    return [unique[key] for key in sorted(unique)]
