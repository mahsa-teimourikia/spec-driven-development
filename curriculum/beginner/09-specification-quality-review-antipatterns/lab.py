"""Deterministic Course 09 lab for specification review and anti-patterns.

The rule set is intentionally transparent and bounded. It teaches review
mechanics on labelled fixtures; it is not a general natural-language judge,
an approval authority, or evidence that a specification is complete.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

LESSON_ROOT = Path(__file__).resolve().parent
SCENARIO_ROOT = LESSON_ROOT / "northstar-spec-review"
CANDIDATE_ROOT = SCENARIO_ROOT / "candidate"
REFERENCE_ROOT = SCENARIO_ROOT / "reference"
PACKAGE_PATH = CANDIDATE_ROOT / "review-input.json"
TRACEABILITY_PATH = CANDIDATE_ROOT / "traceability.json"
EVIDENCE_PATH = CANDIDATE_ROOT / "evidence.json"
CONTEXT_PATH = CANDIDATE_ROOT / "context-manifest.json"
AUTONOMY_PATH = CANDIDATE_ROOT / "autonomy-contract.json"
REPAIRED_PACKAGE_PATH = REFERENCE_ROOT / "repaired-review-input.json"
REPAIRED_TRACEABILITY_PATH = REFERENCE_ROOT / "traceability.json"
REPAIRED_EVIDENCE_PATH = REFERENCE_ROOT / "evidence.json"
REPAIRED_CONTEXT_PATH = REFERENCE_ROOT / "context-manifest.json"
REPAIRED_AUTONOMY_PATH = REFERENCE_ROOT / "autonomy-contract.json"
EVALUATION_PATH = SCENARIO_ROOT / "evaluation-cases.json"
CAPABILITY_READINESS_PATH = SCENARIO_ROOT / "capability-readiness.json"
POLICY_EXPECTATION_PATH = SCENARIO_ROOT / "resolved-policy-expectation.json"


class Severity(str, Enum):
    BLOCKING = "blocking"
    REVIEW = "review"
    INFORMATIONAL = "informational"


class Readiness(str, Enum):
    STOP = "stop"
    REVIEW = "review"
    READY_FOR_BOUNDED_IMPLEMENTATION = "ready_for_bounded_implementation"


@dataclass(frozen=True)
class Finding:
    finding_id: str
    severity: Severity
    dimension: str
    code: str
    subject_id: str
    message: str
    evidence: str
    owner: str
    repair: str


@dataclass(frozen=True)
class DraftFinding:
    severity: Severity
    dimension: str
    code: str
    subject_id: str
    message: str
    evidence: str
    owner: str
    repair: str


VAGUE_TERMS = {
    "accurately",
    "appropriate",
    "comprehensive",
    "correctly",
    "intelligently",
    "quickly",
    "robust",
    "scalable",
    "secure",
}

SEVERITY_ORDER = {
    Severity.BLOCKING: 0,
    Severity.REVIEW: 1,
    Severity.INFORMATIONAL: 2,
}

REQUIRED_SCENARIO_CLASSES = {"primary", "negative", "boundary", "failure", "uncertainty"}
FIXTURE_EXPECTED_POLICY_IDS = {"AI-007", "AI-030", "PRIV-018"}
FIXTURE_GIANT_SPEC_CONCERN_TRIGGER = 6
FIXTURE_GIANT_SPEC_LINE_TRIGGER = 1500

FINDING_CLUSTER_RULES = {
    "autonomous_action_governance": {
        "AGENT_STOP_CONDITIONS_MISSING", "AGENT_TASK_UNDER_CONSTRAINED",
        "DEPLOYMENT_AUTHORITY_DELEGATED", "DECISION_AUTHORITY_MISSING",
        "UNDEFINED_CONFIDENCE_SEMANTICS",
    },
    "effective_context_and_policy": {
        "CONTEXT_REQUIRED_SOURCE_MISSING", "GENERATED_ARTIFACT_MODIFIED",
        "CONTEXT_OVERLOAD", "CONTEXT_PROVENANCE_MISSING",
        "POLICY_APPLICABILITY_UNRESOLVED", "REQUIRED_POLICY_SOURCES_MISSING",
        "POLICY_PROVENANCE_INCOMPLETE",
    },
    "exception_and_authority_integrity": {
        "AUTHORITY_LAUNDERING", "EXCEPTION_LAUNDERING",
        "EXCEPTION_APPROVER_UNAUTHORIZED", "EXCEPTION_EXPIRY_MISSING",
        "EXCEPTION_SCOPE_INCOMPLETE",
    },
    "requirement_semantics_and_evaluation": {
        "VAGUE_REQUIREMENT", "AGGREGATE_ACCURACY_UNDEFINED",
        "CRITICAL_EVALUATION_SLICES_MISSING", "FALSE_PRECISION",
        "POPULATION_UNBOUNDED",
    },
    "behavioral_coverage_and_ownership": {
        "SCENARIO_COVERAGE_INCOMPLETE", "EVIDENCE_CONTRACT_UNDEFINED",
        "POSSIBLE_REQUIREMENT_DUPLICATION", "REQUIREMENT_OWNERSHIP_INCOMPLETE",
    },
    "architecture_and_artifact_design": {
        "IMPLEMENTATION_LEAKAGE", "ACCIDENTAL_ARCHITECTURE",
        "GIANT_SPECIFICATION", "SPEC_FRESHNESS_OWNERSHIP_MISSING",
    },
    "source_of_truth_and_evidence_integrity": {
        "EVIDENCE_STALE", "EVIDENCE_CONTEXT_INCOMPLETE", "CODE_AS_SPECIFICATION",
        "TESTS_AS_SPECIFICATION", "TRACE_LINK_SEMANTIC_MISMATCH",
    },
}

FINDING_CLUSTER_TITLES = {
    "autonomous_action_governance": "Automatic action is not safely governed",
    "effective_context_and_policy": "Enterprise context and applicable policy are unresolved",
    "exception_and_authority_integrity": "Authority and exception claims are not valid",
    "requirement_semantics_and_evaluation": "Requirement meaning and evaluation boundaries are incomplete",
    "behavioral_coverage_and_ownership": "Behavioral coverage and ownership are incomplete",
    "architecture_and_artifact_design": "Architecture and specification packaging are poorly separated",
    "source_of_truth_and_evidence_integrity": "Source-of-truth and evidence claims are unreliable",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_review_bundle(*, repaired: bool = False) -> dict[str, Any]:
    policy_expectation = load_json(POLICY_EXPECTATION_PATH)
    if repaired:
        return {
            "package": load_json(REPAIRED_PACKAGE_PATH),
            "traceability": load_json(REPAIRED_TRACEABILITY_PATH),
            "evidence": load_json(REPAIRED_EVIDENCE_PATH),
            "context": load_json(REPAIRED_CONTEXT_PATH),
            "autonomy": load_json(REPAIRED_AUTONOMY_PATH),
            "policy_expectation": policy_expectation,
        }
    return {
        "package": load_json(PACKAGE_PATH),
        "traceability": load_json(TRACEABILITY_PATH),
        "evidence": load_json(EVIDENCE_PATH),
        "context": load_json(CONTEXT_PATH),
        "autonomy": load_json(AUTONOMY_PATH),
        "policy_expectation": policy_expectation,
    }


def _draft(
    severity: Severity,
    dimension: str,
    code: str,
    subject_id: str,
    message: str,
    evidence: str,
    owner: str,
    repair: str,
) -> DraftFinding:
    return DraftFinding(severity, dimension, code, subject_id, message, evidence, owner, repair)


def _finalize(findings: Iterable[DraftFinding]) -> tuple[Finding, ...]:
    ordered = sorted(
        findings,
        key=lambda item: (SEVERITY_ORDER[item.severity], item.subject_id, item.code, item.message),
    )
    return tuple(
        Finding(f"F-{index:03d}", item.severity, item.dimension, item.code, item.subject_id,
                item.message, item.evidence, item.owner, item.repair)
        for index, item in enumerate(ordered, start=1)
    )


def lexical_presence_baseline(package: dict[str, Any]) -> dict[str, Any]:
    """Demonstrate why vocabulary presence is not a quality assessment."""
    text = " ".join(str(item.get("text", "")) for item in package.get("statements", [])).lower()
    concepts = {
        "ai": ("ai", "gpt", "model"),
        "performance": ("quick", "latency", "performance"),
        "security": ("secure", "security"),
        "human_oversight": ("human review", "underwriter review"),
        "policy": ("policy", "policies"),
        "testing": ("test", "tests"),
        "scalability": ("scalable", "capacity"),
    }
    present = {
        concept: any(token in text for token in tokens)
        for concept, tokens in concepts.items()
    }
    return {
        "method": "lexical_presence_only_unsafe_baseline",
        "present": present,
        "numerator": sum(present.values()),
        "denominator": len(present),
        "looks_complete": all(present.values()),
        "limitations": [
            "Presence does not establish semantics, authority, evidence, consistency, or readiness.",
            "This baseline must never authorize implementation.",
        ],
    }


def review_statement(statement: dict[str, Any]) -> tuple[DraftFinding, ...]:
    findings: list[DraftFinding] = []
    identifier = str(statement.get("id", "unknown"))
    text = str(statement.get("text", ""))
    lowered = text.lower()
    defined_terms = {str(term).lower() for term in statement.get("defined_terms", [])}
    measurement = statement.get("measurement")
    decision = statement.get("decision", {})
    source_refs = statement.get("source_refs", [])
    technology_names = statement.get("technology_names", [])
    technology_basis = statement.get("technology_basis")
    quality_contract = statement.get("referenced_quality_contract", {})
    quality_contract_is_bounded = bool(
        isinstance(quality_contract, dict)
        and quality_contract.get("id")
        and quality_contract.get("revision")
        and quality_contract.get("locator")
        and quality_contract.get("measurement")
    )

    vague = sorted(
        term for term in VAGUE_TERMS
        if re.search(rf"\b{re.escape(term)}\b", lowered) and term not in defined_terms
    )
    if vague and not measurement and not quality_contract_is_bounded:
        findings.append(_draft(
            Severity.REVIEW, "clarity", "VAGUE_REQUIREMENT", identifier,
            f"Undefined quality language: {', '.join(vague)}.", text,
            str(statement.get("owner") or "requirement owner"),
            "Define observable semantics, population, measurement, and failure behavior or remove the adjective.",
        ))

    if technology_names and technology_basis not in {"inherited_constraint", "approved_adr", "external_contract"}:
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "IMPLEMENTATION_LEAKAGE", identifier,
            "Technology is prescribed without an inherited constraint, external contract, or approved architecture decision.",
            ", ".join(str(item) for item in technology_names), "Architecture owner",
            "Move the choice to design/ADR work or attach authoritative constraint provenance.",
        ))
    if technology_names and not statement.get("alternatives_considered") and technology_basis == "informal_suggestion":
        findings.append(_draft(
            Severity.REVIEW, "correctness", "ACCIDENTAL_ARCHITECTURE", identifier,
            "An informal suggestion has become a normative architecture choice without evidence or alternatives.",
            text, "Architecture owner",
            "Reclassify as a design candidate and evaluate necessity, staleness, security, cost, and alternatives.",
        ))

    has_number = bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:%|seconds?|ms|milliseconds?)(?=\s|[.,;:]|$)", lowered))
    if has_number and not measurement:
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "FALSE_PRECISION", identifier,
            "A numeric threshold lacks a complete population, boundary, method, unit, or window.",
            text, str(statement.get("owner") or "decision owner"),
            "Define measurement semantics and trace the value to an accountable decision.",
        ))
    if has_number and not decision.get("owner"):
        severity = Severity.BLOCKING if statement.get("controls_authoritative_action") else Severity.REVIEW
        findings.append(_draft(
            severity, "decision_ownership", "DECISION_AUTHORITY_MISSING", identifier,
            "A consequential numeric decision has no accountable owner or decision record.",
            text, "Product or risk owner",
            "Preserve the target as unresolved until an authorized owner records rationale and evidence.",
        ))

    if "confidence" in lowered and has_number:
        required = {"population", "calibration", "metric_definition", "owner", "decision_id"}
        confidence = statement.get("confidence_contract", {})
        missing = sorted(field for field in required if not confidence.get(field))
        if missing:
            findings.append(_draft(
                Severity.BLOCKING, "correctness", "UNDEFINED_CONFIDENCE_SEMANTICS", identifier,
                f"Confidence controls an authoritative action but lacks: {', '.join(missing)}.",
                text, "Underwriting Risk and AI Quality",
                "Replace the floating-point shortcut with a calibrated, population-bound, owner-approved decision rule and trusted authorization.",
            ))

    if statement.get("metric_name") == "accuracy" and not statement.get("component_metrics"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "AGGREGATE_ACCURACY_UNDEFINED", identifier,
            "One accuracy value does not define field mapping, extraction, grounding, conflict detection, or abstention behavior.",
            text, "AI Quality",
            "Decompose the metric and define populations, directions, denominators, and failure costs.",
        ))
    if statement.get("metric_name") == "accuracy" and not statement.get("critical_slices"):
        findings.append(_draft(
            Severity.REVIEW, "completeness", "CRITICAL_EVALUATION_SLICES_MISSING", identifier,
            "Aggregate-only evaluation can hide failure in high-risk cases.",
            text, "AI Quality and domain risk owner",
            "Define critical slices such as conflicts, stale context, unsupported fields, and unauthorized requests.",
        ))

    if "all relevant enterprise policies" in lowered and not source_refs:
        findings.append(_draft(
            Severity.BLOCKING, "traceability", "POLICY_APPLICABILITY_UNRESOLVED", identifier,
            "A blanket policy statement does not identify applicable sources, revisions, or applicability evidence.",
            text, "Policy resolver owner",
            "Resolve the applicable policy manifest before implementation and preserve immutable provenance.",
        ))

    if any(str(source.get("authority", "")) == "hearsay" for source in source_refs):
        findings.append(_draft(
            Severity.BLOCKING, "authority", "AUTHORITY_LAUNDERING", identifier,
            "Informal context has been transformed into a normative decision.",
            json.dumps(source_refs, sort_keys=True), "Named decision owner",
            "Verify the decision through an authoritative source or keep it unresolved.",
        ))

    if statement.get("weakens_requirement_id") and not statement.get("exception_id"):
        findings.append(_draft(
            Severity.BLOCKING, "authority", "EXCEPTION_LAUNDERING", identifier,
            f"The statement weakens {statement['weakens_requirement_id']} without a governed exception.",
            text, "Governing policy owner",
            "Remove the weakening or obtain a scoped, conditional, independently approved, expiring exception.",
        ))

    if statement.get("scope_quantifier") == "all" and not statement.get("eligible_population"):
        findings.append(_draft(
            Severity.REVIEW, "completeness", "POPULATION_UNBOUNDED", identifier,
            "A universal quantifier has no explicit eligible population or exclusions.",
            text, "Product owner",
            "Define supported and unsupported populations plus out-of-population behavior.",
        ))

    if statement.get("evidence_contract") is False:
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "EVIDENCE_CONTRACT_UNDEFINED", identifier,
            "The statement asks for tests without defining the behavior, oracle, population, or evidence boundary.",
            text, "Requirement and evidence owners",
            "Define acceptance semantics and independent evidence without making tests the owner of intent.",
        ))

    return tuple(findings)


def review_package_structure(
    package: dict[str, Any],
    *,
    expected_policy_ids: set[str] | frozenset[str] | None = None,
) -> tuple[DraftFinding, ...]:
    """Review package structure against a resolver-produced expected policy set.

    The default is the Northstar training fixture, not a universal policy list.
    Production callers must provide the output of their applicability resolver.
    """
    findings: list[DraftFinding] = []
    if expected_policy_ids is None:
        expected_policy_ids = FIXTURE_EXPECTED_POLICY_IDS
    source_claims = set(package.get("source_of_truth_claims", []))
    if "tests_define_all_behavior" in source_claims:
        findings.append(_draft(
            Severity.REVIEW, "correctness", "TESTS_AS_SPECIFICATION", "source-of-truth",
            "Tests are treated as the sole owner of expected behavior.", "tests_define_all_behavior",
            "Requirement owner", "Keep tests as evidence linked to durable intent, scope, and negative obligations.",
        ))
    if "current_code_is_required_behavior" in source_claims:
        findings.append(_draft(
            Severity.REVIEW, "correctness", "CODE_AS_SPECIFICATION", "source-of-truth",
            "Observed implementation behavior is treated as required behavior without classification.",
            "current_code_is_required_behavior", "Product and domain owners",
            "Reverse-engineer observed behavior, then distinguish intended and required behavior.",
        ))
    if not package.get("change_owner") or not package.get("freshness_review_triggers"):
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "SPEC_FRESHNESS_OWNERSHIP_MISSING", "specification",
            "The specification has no owner or trigger for review after policy, architecture, or behavior changes.",
            str(package.get("revision", "unknown")), "Specification owner",
            "Name a change owner and review triggers tied to source, contract, implementation, and evidence revisions.",
        ))
    scenario_classes = set(package.get("scenario_classes", []))
    missing_scenarios = sorted(REQUIRED_SCENARIO_CLASSES - scenario_classes)
    if missing_scenarios:
        severity = Severity.BLOCKING if {"failure", "uncertainty"} & set(missing_scenarios) and package.get("authoritative_side_effects") else Severity.REVIEW
        findings.append(_draft(
            severity, "completeness", "SCENARIO_COVERAGE_INCOMPLETE", "scenario-model",
            f"Required scenario classes are absent: {', '.join(missing_scenarios)}.",
            ", ".join(missing_scenarios), "Feature owner",
            "Add owned negative, boundary, failure, and uncertainty behavior, including state preservation and stop/escalation semantics.",
        ))

    policy_ids = {str(item.get("id")) for item in package.get("policy_manifest", [])}
    missing_policies = sorted(set(expected_policy_ids) - policy_ids)
    if missing_policies:
        findings.append(_draft(
            Severity.BLOCKING, "traceability", "REQUIRED_POLICY_SOURCES_MISSING", "policy-manifest",
            f"Required sources are absent from the effective policy manifest: {', '.join(missing_policies)}.",
            ", ".join(missing_policies),
            "Policy resolver owner", "Resolve applicability and add the immutable source revision and evidence.",
        ))
    for source in package.get("policy_manifest", []):
        if not source.get("revision") or not source.get("locator") or not source.get("applicability_evidence"):
            findings.append(_draft(
                Severity.REVIEW, "traceability", "POLICY_PROVENANCE_INCOMPLETE", str(source.get("id", "unknown")),
                "A policy reference lacks revision, locator, or applicability evidence.",
                json.dumps(source, sort_keys=True), "Policy resolver owner",
                "Pin an immutable revision and record why the source applies.",
            ))

    missing_owners = sorted(
        str(statement.get("id"))
        for statement in package.get("statements", [])
        if not statement.get("owner")
    )
    if missing_owners:
        findings.append(_draft(
            Severity.REVIEW, "decision_ownership", "REQUIREMENT_OWNERSHIP_INCOMPLETE", "requirement-set",
            "Requirements lack accountable meaning owners.", ", ".join(missing_owners),
            "Specification owner", "Assign the product, policy, architecture, domain, or evidence owner for each obligation.",
        ))

    for exception in package.get("exceptions", []):
        identifier = str(exception.get("id", "unknown"))
        if not exception.get("expires_on"):
            findings.append(_draft(
                Severity.BLOCKING, "maintainability", "EXCEPTION_EXPIRY_MISSING", identifier,
                "A temporary exception has no expiry.", json.dumps(exception, sort_keys=True),
                "Governing policy owner", "Add expiry, conditions, scope, renewal, and revocation behavior.",
            ))
        if exception.get("approver_authorized") is not True:
            findings.append(_draft(
                Severity.BLOCKING, "authority", "EXCEPTION_APPROVER_UNAUTHORIZED", identifier,
                "The exception approver is not authorized for the governing requirement.",
                json.dumps(exception, sort_keys=True), "Governing policy owner",
                "Route the exception to an independent authorized approver.",
            ))
        if not exception.get("scope") or not exception.get("conditions"):
            findings.append(_draft(
                Severity.BLOCKING, "authority", "EXCEPTION_SCOPE_INCOMPLETE", identifier,
                "The exception lacks bounded scope or enforceable conditions.",
                json.dumps(exception, sort_keys=True), "Governing policy owner",
                "Bind the exception to exact requirement revision, capability, environment, conditions, and expiry.",
            ))

    artifacts = package.get("artifacts", [])
    for artifact in artifacts:
        concerns = artifact.get("concerns", [])
        if (
            len(concerns) >= FIXTURE_GIANT_SPEC_CONCERN_TRIGGER
            or int(artifact.get("lines", 0)) > FIXTURE_GIANT_SPEC_LINE_TRIGGER
        ):
            findings.append(_draft(
                Severity.REVIEW, "maintainability", "GIANT_SPECIFICATION", str(artifact.get("path", "unknown")),
                "One artifact mixes concerns with different owners or lifecycles.",
                ", ".join(str(item) for item in concerns), "Specification owner",
                "Split where authority, lifecycle, or representation differs while preserving navigation.",
            ))
    if len(artifacts) > 50 and package.get("average_requirements_per_artifact", 1) <= 1:
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "OVER_FRAGMENTED_SPECIFICATION", "artifact-set",
            "The package requires excessive file traversal for one feature.", str(len(artifacts)),
            "Specification owner", "Consolidate closely owned, co-evolving requirements into navigable artifacts.",
        ))

    by_concept: dict[str, list[str]] = {}
    for statement in package.get("statements", []):
        concept = statement.get("semantic_concept")
        if concept:
            by_concept.setdefault(str(concept), []).append(str(statement.get("id")))
    for concept, identifiers in sorted(by_concept.items()):
        if len(identifiers) > 1:
            findings.append(_draft(
                Severity.REVIEW, "consistency", "POSSIBLE_REQUIREMENT_DUPLICATION", concept,
                "Multiple statements may express the same obligation; automatic merging would be unsafe.",
                ", ".join(identifiers), "Requirement owners",
                "Compare scope, authority, semantics, and evidence before consolidating or distinguishing them.",
            ))
    return tuple(findings)


def review_autonomy(contract: dict[str, Any]) -> tuple[DraftFinding, ...]:
    findings: list[DraftFinding] = []
    identifier = str(contract.get("id", "autonomy-contract"))
    writable = contract.get("writable_paths", [])
    if "*" in writable or contract.get("change_budget") in (None, "unbounded"):
        findings.append(_draft(
            Severity.BLOCKING, "autonomy", "AGENT_TASK_UNDER_CONSTRAINED", identifier,
            "The agent can change unbounded paths or an unbounded number of files.", json.dumps(writable),
            "Implementation owner", "Declare writable/protected paths, budget, dependencies, evidence, and escalation.",
        ))
    if contract.get("exact_line_edits") or contract.get("implementation_frozen") is True:
        findings.append(_draft(
            Severity.REVIEW, "autonomy", "AGENT_TASK_OVER_CONSTRAINED", identifier,
            "The instruction dictates local implementation mechanics without an authority or compatibility reason.",
            json.dumps(contract.get("exact_line_edits", [])), "Implementation owner",
            "Constrain consequential outcomes while leaving bounded local implementation choices open.",
        ))
    if not contract.get("stop_conditions"):
        findings.append(_draft(
            Severity.BLOCKING, "autonomy", "AGENT_STOP_CONDITIONS_MISSING", identifier,
            "The task has no explicit stop or escalation conditions.", "stop_conditions=[]",
            "Implementation owner", "Stop on policy conflict, scope expansion, missing authority, unsafe evidence, or protected-path need.",
        ))
    if "deploy_production" in contract.get("permissions", []):
        findings.append(_draft(
            Severity.BLOCKING, "authority", "DEPLOYMENT_AUTHORITY_DELEGATED", identifier,
            "The implementation task attempts to grant production deployment authority.", "deploy_production",
            "Release owner", "Remove deployment authority and require the independent release workflow.",
        ))
    return tuple(findings)


def traceability_metrics(
    package: dict[str, Any],
    traceability: dict[str, Any],
    evidence: dict[str, Any],
) -> tuple[dict[str, Any], tuple[DraftFinding, ...]]:
    requirement_ids = {str(item.get("id")) for item in package.get("statements", [])}
    evidence_index = {str(item.get("id")): item for item in evidence.get("records", [])}
    rows = traceability.get("links", [])
    linked_requirements = {
        str(row.get("source_id", row.get("requirement_id")))
        for row in rows
        if row.get("target_id", row.get("evidence_id"))
    }
    semantically_valid: set[str] = set()
    conformance_valid: set[str] = set()
    semantic_mismatches: list[str] = []
    relationship_counts: Counter[str] = Counter()
    findings: list[DraftFinding] = []
    for row in rows:
        requirement_id = str(row.get("source_id", row.get("requirement_id", "unknown")))
        evidence_id = str(row.get("target_id", row.get("evidence_id", "unknown")))
        relationship = str(row.get("relationship", row.get("relationship_claim", "unspecified")))
        target_type = row.get("target_type")
        relationship_counts[relationship] += 1
        record = evidence_index.get(evidence_id)
        if requirement_id not in requirement_ids or record is None:
            findings.append(_draft(
                Severity.REVIEW, "traceability", "TRACE_LINK_TARGET_MISSING", requirement_id,
                "A trace link names a missing requirement or evidence record.", json.dumps(row, sort_keys=True),
                "Evidence owner", "Repair the link to existing, versioned artifacts.",
            ))
            continue
        supported_ids = (
            record.get("reviewed_source_ids", [])
            if relationship == "reviewed_by"
            else record.get("supported_requirement_ids", [])
        )
        if (
            requirement_id not in set(supported_ids)
            or (target_type and target_type != record.get("type"))
        ):
            semantic_mismatches.append(f"{requirement_id}->{evidence_id}")
        else:
            semantically_valid.add(requirement_id)
            if relationship in {"verified_by", "validated_by", "conformance_evidenced_by"}:
                conformance_valid.add(requirement_id)

    if semantic_mismatches:
        findings.append(_draft(
            Severity.REVIEW, "traceability", "TRACE_LINK_SEMANTIC_MISMATCH", "traceability",
            "Structurally present links do not semantically verify their requirements.",
            ", ".join(semantic_mismatches), "Requirement and evidence owners",
            "Inspect each oracle and link only evidence that supports the exact obligation.",
        ))

    structural_numerator = len(requirement_ids & linked_requirements)
    semantic_numerator = len(semantically_valid)
    conformance_numerator = len(conformance_valid)
    denominator = len(requirement_ids)
    metrics = {
        "structural_link_coverage": {
            "numerator": structural_numerator,
            "denominator": denominator,
            "value": structural_numerator / denominator if denominator else None,
        },
        "semantic_link_validity": {
            "numerator": semantic_numerator,
            "denominator": denominator,
            "value": semantic_numerator / denominator if denominator else None,
        },
        "conformance_evidence_coverage": {
            "numerator": conformance_numerator,
            "denominator": denominator,
            "value": conformance_numerator / denominator if denominator else None,
        },
        "relationship_type_counts": dict(sorted(relationship_counts.items())),
        "claim": "link_presence_is_not_link_validity_and_review_is_not_conformance",
        "boundary": (
            "relationship meaning is typed: reviewed_by proves specification-review coverage only; "
            "verified_by requires a supporting oracle; neither link presence nor review alone proves "
            "implementation or production conformance"
        ),
    }
    return metrics, tuple(findings)


def review_evidence(evidence: dict[str, Any]) -> tuple[DraftFinding, ...]:
    findings: list[DraftFinding] = []
    for record in evidence.get("records", []):
        identifier = str(record.get("id", "unknown"))
        missing = [
            field for field in ("producer", "subject_revision", "environment", "population", "numerator", "denominator", "limitations")
            if record.get(field) in (None, "", [])
        ]
        if missing:
            findings.append(_draft(
                Severity.REVIEW, "verifiability", "EVIDENCE_CONTEXT_INCOMPLETE", identifier,
                f"A PASS label lacks: {', '.join(missing)}.", json.dumps(record, sort_keys=True),
                "Evidence producer", "Record population, denominator, revision, environment, producer relationship, and limitations.",
            ))
        if record.get("subject_revision") != record.get("current_subject_revision"):
            findings.append(_draft(
                Severity.BLOCKING, "maintainability", "EVIDENCE_STALE", identifier,
                "Evidence was produced for a different implementation or specification revision.",
                f"observed={record.get('subject_revision')} current={record.get('current_subject_revision')}",
                "Evidence producer", "Re-run the evidence on the exact current subject revision.",
            ))
    return tuple(findings)


def review_context(context: dict[str, Any]) -> tuple[DraftFinding, ...]:
    findings: list[DraftFinding] = []
    identifier = str(context.get("id", "context-manifest"))
    if context.get("generated") and context.get("expected_digest") != context.get("actual_digest"):
        findings.append(_draft(
            Severity.BLOCKING, "maintainability", "GENERATED_ARTIFACT_MODIFIED", identifier,
            "Generated effective context differs from its reproducible source digest.",
            f"expected={context.get('expected_digest')} actual={context.get('actual_digest')}",
            "Context pipeline owner", "Repair source artifacts and regenerate; do not patch derived context manually.",
        ))
    incomplete_sources = [
        source for source in context.get("sources", [])
        if not all(source.get(field) for field in ("id", "revision", "locator", "reason"))
    ]
    if incomplete_sources:
        findings.append(_draft(
            Severity.REVIEW, "traceability", "CONTEXT_PROVENANCE_MISSING", identifier,
            "Compressed context contains instructions without stable source provenance.",
            json.dumps(incomplete_sources, sort_keys=True), "Context pipeline owner",
            "Preserve source ID, revision, locator, and applicability reason through compression.",
        ))
    if int(context.get("candidate_artifact_count", 0)) > int(context.get("reviewed_context_budget", 100)):
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "CONTEXT_OVERLOAD", identifier,
            "The agent context exceeds the reviewed artifact budget and may dilute relevant constraints.",
            f"candidates={context.get('candidate_artifact_count')} budget={context.get('reviewed_context_budget')}",
            "Context pipeline owner", "Select relevant, authoritative, current, minimal-sufficient sources and measure recall.",
        ))
    included = {str(item.get("id")) for item in context.get("sources", []) if item.get("id")}
    missing_sources = sorted(set(context.get("required_source_ids", [])) - included)
    if missing_sources:
        findings.append(_draft(
            Severity.BLOCKING, "completeness", "CONTEXT_REQUIRED_SOURCE_MISSING", identifier,
            f"Required governing sources are absent from implementation context: {', '.join(missing_sources)}.",
            ", ".join(missing_sources),
            "Context pipeline owner", "Improve discovery/selection and stop implementation until the source is included.",
        ))
    return tuple(findings)


def review_normative_context(context: dict[str, Any]) -> tuple[DraftFinding, ...]:
    """Review authority resolution, derived intent, and scoped uncertainty."""
    findings: list[DraftFinding] = []
    authority_rank = {"enterprise": 4, "domain": 3, "project": 2, "feature": 1}
    by_concept: dict[str, list[dict[str, Any]]] = {}
    for requirement in context.get("requirements", []):
        by_concept.setdefault(str(requirement.get("concept", "unknown")), []).append(requirement)
    for concept, requirements in sorted(by_concept.items()):
        if len(requirements) < 2:
            continue
        ordered = sorted(
            requirements,
            key=lambda item: authority_rank.get(str(item.get("authority_level")), 0),
            reverse=True,
        )
        governing = ordered[0]
        conflicting = [
            item for item in ordered[1:]
            if item.get("value") != governing.get("value") and not item.get("authorized_exception")
        ]
        if conflicting:
            findings.append(_draft(
                Severity.BLOCKING, "consistency", "NORMATIVE_CONFLICT", concept,
                "A lower-authority requirement contradicts the governing obligation without an authorized exception.",
                ", ".join(str(item.get("id")) for item in ordered), "Governing requirement owner",
                "Preserve every source and route the conflict; specificity, recency, and proximity do not transfer authority.",
            ))

    heuristic_codes = {
        "specificity": "SPECIFICITY_MISTAKEN_FOR_AUTHORITY",
        "latest": "RECENCY_MISTAKEN_FOR_AUTHORITY",
        "nearest": "PROXIMITY_MISTAKEN_FOR_AUTHORITY",
    }
    for heuristic in context.get("resolution_heuristics", []):
        if heuristic in heuristic_codes:
            findings.append(_draft(
                Severity.REVIEW, "authority", heuristic_codes[heuristic], "resolution-strategy",
                f"The resolver uses {heuristic} as a substitute for authority and applicability.",
                str(heuristic), "Policy resolver owner",
                "Evaluate applicability, authority domain, lifecycle state, and governed exceptions independently.",
            ))

    forbidden_instruction_decisions = {"approve_exception", "skip_control", "authorize_automatic_action", "set_policy"}
    for instruction in context.get("agent_instructions", []):
        attempted = forbidden_instruction_decisions & set(instruction.get("decisions", []))
        if attempted:
            findings.append(_draft(
                Severity.BLOCKING, "authority", "AGENT_INSTRUCTION_EXCEEDS_AUTHORITY",
                str(instruction.get("id", "agent-instruction")),
                "Execution guidance attempts to redefine policy, approval, or product authority.",
                ", ".join(sorted(attempted)), "Instruction and governing policy owners",
                "Keep agent instructions within execution scope and resolve consequential decisions in authoritative artifacts.",
            ))

    for requirement in context.get("derived_requirements", []):
        if requirement.get("status") == "active" and not requirement.get("approved_by"):
            findings.append(_draft(
                Severity.BLOCKING, "authority", "DERIVED_REQUIREMENT_UNAPPROVED",
                str(requirement.get("id", "derived-requirement")),
                "A derived requirement became active without accountable review of the transformation.",
                json.dumps(requirement, sort_keys=True), "Derived requirement owner",
                "Keep the derivation proposed until an authorized owner validates its semantics and scope.",
            ))

    pipeline = context.get("generation_pipeline", {})
    same_producer = {
        pipeline.get("requirement_producer"), pipeline.get("implementation_producer"),
        pipeline.get("test_producer"), pipeline.get("evaluation_producer"),
    }
    same_producer.discard(None)
    if pipeline.get("ambiguity_disposition") == "assumed" and len(same_producer) == 1:
        findings.append(_draft(
            Severity.BLOCKING, "correctness", "SELF_CONFIRMING_SPECIFICATION_LOOP", "generation-pipeline",
            "One producer converts ambiguity into intent, implementation, tests, and a passing evaluation.",
            json.dumps(pipeline, sort_keys=True), "Product and verification owners",
            "Preserve ambiguity, obtain an accountable decision, and verify approved intent with independent evidence.",
        ))
    if pipeline and not pipeline.get("independent_evidence"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "EVIDENCE_INDEPENDENCE_WEAK", "generation-pipeline",
            "Evidence is produced and interpreted inside the same loop that generated intent and implementation.",
            json.dumps(pipeline, sort_keys=True), "Independent evidence owner",
            "Add deterministic external checks or independently owned evidence and disclose residual dependence.",
        ))

    for item in context.get("uncertain_inputs", []):
        if item.get("disposition") == "requirement" and not item.get("confirmed_by"):
            findings.append(_draft(
                Severity.BLOCKING, "correctness", "UNCERTAINTY_LAUNDERED",
                str(item.get("id", "uncertain-input")),
                "An uncertain statement was converted into a normative requirement without confirmation.",
                str(item.get("source_text", "")), str(item.get("owner", "Domain owner")),
                "Record a clarification question and keep the affected capability unresolved until answered.",
            ))
    for question in context.get("open_questions", []):
        identifier = str(question.get("id", "open-question"))
        if not question.get("blocks") and not question.get("does_not_block"):
            findings.append(_draft(
                Severity.REVIEW, "completeness", "OPEN_QUESTION_CONSEQUENCE_UNDEFINED", identifier,
                "An open question does not identify affected and unaffected capabilities.",
                json.dumps(question, sort_keys=True), str(question.get("owner", "Question owner")),
                "Bind the question to the exact capabilities, requirements, and work units it blocks.",
            ))
        if "*" in question.get("blocks", []) and question.get("scope_candidates"):
            findings.append(_draft(
                Severity.REVIEW, "maintainability", "OPEN_QUESTION_OVER_BLOCKS", identifier,
                "A scoped uncertainty blocks the entire change and destroys safe parallelism.",
                json.dumps(question, sort_keys=True), str(question.get("owner", "Question owner")),
                "Block only the capabilities and work units dependent on the unanswered decision.",
            ))
    return tuple(findings)


def review_requirement_model(model: dict[str, Any]) -> tuple[DraftFinding, ...]:
    """Review requirement granularity, behavioral decomposition, and controls."""
    findings: list[DraftFinding] = []
    count = int(model.get("requirement_count", 0))
    obligations = int(model.get("meaningful_obligation_count", count))
    if count > 100 and obligations and count > obligations * 10:
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "REQUIREMENT_EXPLOSION", "requirement-set",
            "Excessive decomposition creates semantic fragmentation and traceability overhead.",
            f"requirements={count} obligations={obligations}", "Specification owner",
            "Consolidate fragments around independently reasoned behavioral obligations.",
        ))
    for requirement in model.get("requirements", []):
        responsibilities = requirement.get("responsibilities", [])
        if len(responsibilities) > 3:
            findings.append(_draft(
                Severity.REVIEW, "maintainability", "COMPOUND_REQUIREMENT",
                str(requirement.get("id", "requirement")),
                "One requirement combines too many behavioral responsibilities for clear ownership and evidence.",
                ", ".join(str(item) for item in responsibilities), "Requirement owner",
                "Split by meaningful behavior, failure semantics, ownership, and independently reviewable evidence.",
            ))
    if model.get("primary_organization") == "implementation_layer":
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "REQUIREMENTS_ORGANIZED_BY_IMPLEMENTATION", "requirement-set",
            "Implementation layers are the primary decomposition instead of end-to-end behavior.",
            str(model.get("sections", [])), "Specification owner",
            "Organize by durable behavior, then map those obligations to architecture components.",
        ))
    representation_codes = {
        "api": "API_RESTATEMENT_AS_REQUIREMENT",
        "database": "DATABASE_RESTATEMENT_AS_REQUIREMENT",
        "prompt": "PROMPT_RESTATEMENT_AS_REQUIREMENT",
    }
    for item in model.get("representation_substitutions", []):
        kind = str(item.get("kind"))
        if kind in representation_codes and not item.get("external_contract"):
            findings.append(_draft(
                Severity.REVIEW, "correctness", representation_codes[kind], str(item.get("id", kind)),
                "An implementation representation is presented as the durable behavioral obligation.",
                str(item.get("text", "")), "Requirement owner",
                "State the observable obligation and trace the API, schema, or prompt as one realization or control.",
            ))
    safety = model.get("safety_control", {})
    if safety.get("prompt_guidance") and not any(
        safety.get(field) for field in ("tool_restriction", "authorization", "runtime_validation")
    ):
        findings.append(_draft(
            Severity.BLOCKING, "correctness", "CONTROL_UNDERENFORCED", "safety-control",
            "A consequential safety requirement relies only on prompt guidance.",
            json.dumps(safety, sort_keys=True), "Security and runtime control owners",
            "Enforce least privilege, authorization, and deterministic runtime validation outside the model.",
        ))
    for enforcement in model.get("enforcement_rules", []):
        if not enforcement.get("requirement_id"):
            findings.append(_draft(
                Severity.REVIEW, "traceability", "ENFORCEMENT_INTENT_MISSING",
                str(enforcement.get("id", "enforcement")),
                "An enforcement rule has no durable requirement explaining its purpose.",
                json.dumps(enforcement, sort_keys=True), "Control and requirement owners",
                "Trace enforcement to an owned obligation and evidence contract.",
            ))
    for obligation in model.get("consequential_obligations", []):
        if not obligation.get("enforcement_locations"):
            findings.append(_draft(
                Severity.BLOCKING, "traceability", "ENFORCEMENT_MAPPING_MISSING",
                str(obligation.get("id", "obligation")),
                "A consequential obligation has no identified preventive or detective enforcement point.",
                json.dumps(obligation, sort_keys=True), "Enforcement owner",
                "Map the obligation to runtime, CI, authorization, human, or operational controls and evidence.",
            ))
    review = model.get("human_review", {})
    if review:
        required = {"reviewer_role", "review_view", "decision", "evidence", "approval_scope", "edit_invalidation"}
        missing = sorted(field for field in required if not review.get(field))
        if missing:
            findings.append(_draft(
                Severity.BLOCKING, "completeness", "HUMAN_REVIEW_CONTROL_INCOMPLETE", "human-review",
                f"Human review lacks: {', '.join(missing)}.", json.dumps(review, sort_keys=True),
                "Domain risk owner", "Define reviewer authority, information, decision, artifact binding, and edit invalidation.",
            ))
    return tuple(findings)


def impact_adjusted_severity(default: Severity, capability: dict[str, Any]) -> Severity:
    """Escalate a defect using consequence and current autonomy, never code alone."""
    if default == Severity.BLOCKING:
        return default
    consequence = str(capability.get("consequence", "moderate"))
    autonomy = str(capability.get("current_autonomy", "proposal"))
    consequential = consequence in {"high", "critical"}
    autonomous = autonomy in {"automatic", "external_side_effect"}
    if consequential and autonomous:
        return Severity.BLOCKING
    return default


def review_execution_safety(contract: dict[str, Any]) -> tuple[DraftFinding, ...]:
    """Review approval, side-effect, retry, NFR, and degradation semantics."""
    findings: list[DraftFinding] = []
    approval = contract.get("approval", {})
    if approval:
        required = {"proposal_digest", "subject_revision", "requirement_context", "reviewer", "decision", "issued_at"}
        missing = sorted(field for field in required if not approval.get(field))
        if missing:
            findings.append(_draft(
                Severity.BLOCKING, "authority", "APPROVAL_NOT_CONTENT_BOUND", "approval",
                f"Approval is not bound to exact content and context: {', '.join(missing)}.",
                json.dumps(approval, sort_keys=True), "Approval-system owner",
                "Bind a trusted receipt to the exact proposal, subject revision, policy context, reviewer, and time.",
            ))
        if approval.get("reusable") or approval.get("proposal_change_invalidates") is False:
            findings.append(_draft(
                Severity.BLOCKING, "authority", "APPROVAL_REUSE_PERMITTED", "approval",
                "Approval may survive proposal mutation or be reused for another action.",
                json.dumps(approval, sort_keys=True), "Approval-system owner",
                "Invalidate changed proposals and atomically consume single-use approval receipts.",
            ))
    side_effect = contract.get("side_effect", {})
    if side_effect:
        if not side_effect.get("logical_operation_id") or not side_effect.get("idempotency_strategy"):
            findings.append(_draft(
                Severity.BLOCKING, "correctness", "SIDE_EFFECT_IDEMPOTENCY_UNDEFINED", "side-effect",
                "A retryable external effect has no stable logical identity or idempotency strategy.",
                json.dumps(side_effect, sort_keys=True), "Integration owner",
                "Define logical operation identity, idempotency behavior, and reconciliation before retry.",
            ))
        if "unknown" not in set(side_effect.get("outcome_states", [])):
            findings.append(_draft(
                Severity.BLOCKING, "correctness", "UNKNOWN_OUTCOME_COLLAPSED", "side-effect",
                "A timeout or lost response is treated as failure instead of an unknown execution outcome.",
                json.dumps(side_effect, sort_keys=True), "Integration owner",
                "Represent UNKNOWN explicitly and reconcile before another attempt.",
            ))
    retry = contract.get("retry", {})
    if retry:
        required = {"attempt_budget", "deadline", "retryable_errors", "backoff", "exhaustion_behavior"}
        missing = sorted(field for field in required if retry.get(field) in (None, "", []))
        if missing:
            severity = impact_adjusted_severity(
                Severity.REVIEW,
                contract.get("capability_context", {}),
            )
            findings.append(_draft(
                severity, "completeness", "RETRY_BUDGET_UNDEFINED", "retry-policy",
                f"Retry behavior lacks: {', '.join(missing)}.", json.dumps(retry, sort_keys=True),
                "Reliability owner", "Define bounded attempts, deadline, retry classes, backoff, and exhaustion behavior.",
            ))
        if retry.get("attempt_budget") is not None and (not retry.get("owner") or not retry.get("rationale")):
            findings.append(_draft(
                Severity.REVIEW, "decision_ownership", "RETRY_BUDGET_PROVENANCE_MISSING", "retry-policy",
                "A precise retry budget has no accountable owner or evidence-backed rationale.",
                json.dumps(retry, sort_keys=True), "Reliability owner",
                "Trace the limit to workload, dependency, cost, latency, and side-effect evidence.",
            ))
    optimization = contract.get("optimization", {})
    if optimization.get("objective") == "minimize_cost" and not optimization.get("feasibility_constraints"):
        findings.append(_draft(
            Severity.REVIEW, "correctness", "COST_OPTIMIZATION_PRECEDES_CORRECTNESS", "optimization",
            "Cost is optimized before quality, safety, latency, and reliability feasibility is established.",
            json.dumps(optimization, sort_keys=True), "Product and service owners",
            "Optimize cost only among designs that satisfy the approved feasible region.",
        ))
    if optimization.get("performance_override_safety"):
        findings.append(_draft(
            Severity.BLOCKING, "authority", "SAFETY_INVARIANT_TRADED_FOR_PERFORMANCE", "optimization",
            "A performance target permits bypassing a non-tradeable safety control.",
            json.dumps(optimization, sort_keys=True), "Security and risk owners",
            "Preserve the invariant and degrade service or reduce autonomy when the control is unavailable.",
        ))
    nfr = contract.get("nfr", {})
    if nfr and not nfr.get("workload"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "NFR_WORKLOAD_UNDEFINED", "nfr",
            "An NFR target has no workload population or operating profile.", json.dumps(nfr, sort_keys=True),
            "Service owner", "Define the request mix, rate, concurrency, data shape, environment, and duration.",
        ))
    if nfr and not nfr.get("measurement_boundary"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "NFR_MEASUREMENT_BOUNDARY_UNDEFINED", "nfr",
            "An NFR target has no start/end boundary or aggregation semantics.", json.dumps(nfr, sort_keys=True),
            "Service owner", "Define the observable boundary, statistic, window, exclusions, and clock source.",
        ))
    availability = contract.get("availability", {})
    if availability.get("success_basis") == "http_status" and not availability.get("semantic_good_event"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "SEMANTIC_GOOD_EVENT_UNDEFINED", "availability",
            "Transport success is treated as useful service without semantic outcome criteria.",
            json.dumps(availability, sort_keys=True), "Service owner",
            "Define successful useful service, valid degradation, and separate transport from semantic outcomes.",
        ))
    degradation = contract.get("degradation", {})
    if degradation.get("manual_fallback_counts_as_success") and not degradation.get("good_event_contract"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "DEGRADED_SUCCESS_UNDEFINED", "degradation",
            "Manual fallback is counted as success without an approved service-contract definition.",
            json.dumps(degradation, sort_keys=True), "Service owner",
            "Count degradation as good only where the owned service contract explicitly permits it.",
        ))
    autonomy_rank = {"manual": 0, "proposal": 1, "automatic": 2}
    if degradation and (
        autonomy_rank.get(str(degradation.get("degraded_autonomy")), 0)
        > autonomy_rank.get(str(degradation.get("normal_autonomy")), 0)
        or degradation.get("skips_controls")
    ):
        findings.append(_draft(
            Severity.BLOCKING, "autonomy", "DEGRADATION_WEAKENS_CONTROL", "degradation",
            "Dependency uncertainty increases autonomy or skips an independent control.",
            json.dumps(degradation, sort_keys=True), "Service and policy owners",
            "Maintain or reduce autonomy and preserve work until required controls recover.",
        ))
    return tuple(findings)


def review_evaluation_and_gate(payload: dict[str, Any]) -> tuple[DraftFinding, ...]:
    """Review population coverage, claim scope, and non-binary evidence states."""
    findings: list[DraftFinding] = []
    evaluation = payload.get("evaluation", {})
    deployment = set(evaluation.get("deployment_population", []))
    evaluated = set(evaluation.get("evaluated_population", []))
    if deployment - evaluated and evaluation.get("automatic_behavior"):
        findings.append(_draft(
            Severity.BLOCKING, "verifiability", "EVALUATION_DEPLOYMENT_POPULATION_MISMATCH", "evaluation",
            "Automatic deployment includes population dimensions absent from evaluation.",
            ", ".join(sorted(deployment - evaluated)), "AI Quality and release owners",
            "Disable or manually route unsupported populations until representative evidence exists.",
        ))
    deployed_exclusions = set(evaluation.get("excluded_features", [])) & set(evaluation.get("enabled_features", []))
    if deployed_exclusions:
        findings.append(_draft(
            Severity.BLOCKING, "consistency", "EVALUATION_EXCLUSION_DEPLOYED", "evaluation",
            "A feature explicitly excluded from evaluation is enabled for automatic behavior.",
            ", ".join(sorted(deployed_exclusions)), "Product and release owners",
            "Disable, manually route, or evaluate the excluded population before enablement.",
        ))
    if evaluation.get("claim_scope") == "general" and int(evaluation.get("sample_size", 0)) <= 10:
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "SAMPLE_CLAIM_OVERREACH", "evaluation",
            "A tiny bounded sample is presented as a general accuracy claim.",
            f"sample_size={evaluation.get('sample_size')}", "AI Quality",
            "Report the exact numerator, denominator, fixture/population, slices, and limitations.",
        ))
    dashboard = payload.get("dashboard", {})
    if dashboard.get("decision") == "ready" and any(
        gate.get("state") in {"measured", "blocked", "unresolved"} for gate in dashboard.get("gates", [])
    ):
        findings.append(_draft(
            Severity.BLOCKING, "authority", "UNRESOLVED_GATE_REPORTED_READY", "dashboard",
            "The dashboard reports readiness while a required gate lacks an authorized pass decision.",
            json.dumps(dashboard.get("gates", []), sort_keys=True), "Release gate owner",
            "Preserve measurement and decision authority as separate states.",
        ))
    if dashboard.get("decision") == "ready" and any(
        item.get("state") in {"not_run", "not_measured", "missing", "stale"}
        for item in dashboard.get("evidence", [])
    ):
        findings.append(_draft(
            Severity.BLOCKING, "verifiability", "MISSING_EVIDENCE_INTERPRETED_AS_PASS", "dashboard",
            "Absent, stale, or unexecuted evidence is collapsed into a green decision.",
            json.dumps(dashboard.get("evidence", []), sort_keys=True), "Evidence and release owners",
            "Retain PASS, FAIL, BLOCKED, NOT_MEASURED, STALE, and NOT_APPLICABLE as distinct states.",
        ))
    for decision in payload.get("applicability", []):
        if decision.get("evidence_state") == "uncertain" and decision.get("result") == "not_applicable":
            findings.append(_draft(
                Severity.BLOCKING, "correctness", "UNKNOWN_MISCLASSIFIED_NOT_APPLICABLE",
                str(decision.get("source_id", "applicability")),
                "Unresolved applicability is labelled not applicable and hidden from the gate.",
                json.dumps(decision, sort_keys=True), "Policy resolver owner",
                "Preserve UNCERTAIN and block only the affected capability until applicability is resolved.",
            ))
    return tuple(findings)


def review_lifecycle(payload: dict[str, Any]) -> tuple[DraftFinding, ...]:
    """Review status-aware retrieval, retained history, and ADR consistency."""
    findings: list[DraftFinding] = []
    if payload.get("status_aware_retrieval") is False:
        findings.append(_draft(
            Severity.BLOCKING, "correctness", "REQUIREMENT_STATUS_IGNORED", "artifact-retrieval",
            "Draft, active, and superseded artifacts are treated as equivalent current instructions.",
            json.dumps(payload.get("artifacts", []), sort_keys=True), "Context pipeline owner",
            "Filter current context by lifecycle state while retaining explicit historical provenance.",
        ))
    if payload.get("superseded_artifacts_deleted"):
        findings.append(_draft(
            Severity.REVIEW, "maintainability", "SUPERSEDED_HISTORY_DELETED", "artifact-history",
            "Superseded artifacts are deleted, weakening auditability and release reproducibility.",
            "superseded_artifacts_deleted=true", "Configuration-management owner",
            "Retain immutable historical identity and supersession relationships outside current context.",
        ))
    if payload.get("historical_in_current_context") and not payload.get("lifecycle_metadata_complete"):
        findings.append(_draft(
            Severity.BLOCKING, "consistency", "HISTORICAL_ARTIFACT_PRESENTED_AS_CURRENT", "agent-context",
            "Historical decisions appear as current without status and supersession metadata.",
            json.dumps(payload.get("artifacts", []), sort_keys=True), "Context pipeline owner",
            "Include status, supersedes, and superseded-by metadata or exclude history from current instructions.",
        ))
    for decision in payload.get("design_decisions", []):
        if decision.get("contradicts_requirement"):
            findings.append(_draft(
                Severity.BLOCKING, "consistency", "DESIGN_CONTRADICTS_REQUIREMENT",
                str(decision.get("id", "design-decision")),
                "A design decision conflicts with an applicable requirement.",
                json.dumps(decision, sort_keys=True), "Requirement and architecture owners",
                "Stop implementation and resolve the conflict without letting the agent choose authority.",
            ))
        if decision.get("treated_as_immutable_policy") or not decision.get("review_triggers"):
            findings.append(_draft(
                Severity.REVIEW, "maintainability", "ADR_RECONSIDERATION_UNDEFINED",
                str(decision.get("id", "design-decision")),
                "An ADR has no assumptions or observable reconsideration triggers and is treated as eternal policy.",
                json.dumps(decision, sort_keys=True), "Architecture owner",
                "Record status, assumptions, consequences, supersession, and review triggers.",
            ))
    return tuple(findings)


def review_brownfield_delivery(payload: dict[str, Any]) -> tuple[DraftFinding, ...]:
    """Review repository reconciliation, transition safety, operations, and claims."""
    findings: list[DraftFinding] = []
    repository = payload.get("repository", {})
    if repository.get("discovery_complete") is False:
        findings.append(_draft(
            Severity.REVIEW, "completeness", "REPOSITORY_DISCOVERY_INCOMPLETE", "repository",
            "Detailed implementation planning begins without current architecture, interfaces, ownership, and dependency discovery.",
            json.dumps(repository, sort_keys=True), "Implementation and architecture owners",
            "Inventory existing capabilities and produce requirement/architecture/repository matches, drift, and unknowns.",
        ))
    if repository.get("model_facing_authoritative_mutation"):
        findings.append(_draft(
            Severity.BLOCKING, "correctness", "IMPLEMENTATION_VIOLATES_TRUST_BOUNDARY", "repository",
            "Repository reality bypasses the approved proposal-to-trusted-mutation architecture.",
            str(repository.get("bypass_path", "unknown")), "Security and implementation owners",
            "Remove or constrain the bypass and verify authorization at the trusted mutation boundary.",
        ))
    if repository.get("pattern_reuse_basis") == "prevalence" and not repository.get("pattern_validated_current"):
        findings.append(_draft(
            Severity.REVIEW, "correctness", "REPOSITORY_PATTERN_WORSHIP", "repository-pattern",
            "A prevalent repository pattern is copied without checking current approval or conformance.",
            str(repository.get("pattern", "unknown")), "Architecture owner",
            "Check lifecycle, approved paved roads, applicability, and current requirements before reuse.",
        ))

    migration = payload.get("migration", {})
    if migration.get("desired_state_change") and not migration.get("transition_contract"):
        findings.append(_draft(
            Severity.BLOCKING, "completeness", "MIGRATION_BEHAVIOR_UNDEFINED", "migration",
            "The specification defines a desired state without compatibility and transition behavior.",
            json.dumps(migration, sort_keys=True), "Migration owner",
            "Specify existing data, old/new producers and consumers, rolling states, completion, and recovery.",
        ))
    if migration.get("coexistence_expected") and not migration.get("coexistence_matrix"):
        findings.append(_draft(
            Severity.REVIEW, "completeness", "BIG_BANG_ROLLOUT_ASSUMPTION", "migration",
            "A rolling enterprise change is modelled as an instantaneous replacement.",
            json.dumps(migration, sort_keys=True), "Migration owner",
            "Define supported old/new producer-consumer combinations and their safety behavior.",
        ))
    if migration and not migration.get("rollback_semantics"):
        findings.append(_draft(
            Severity.BLOCKING, "completeness", "ROLLBACK_SEMANTICS_UNDEFINED", "migration",
            "Rollback covers neither changed data/contracts nor events and external effects.",
            json.dumps(migration, sort_keys=True), "Release and migration owners",
            "Define code, data, event, contract, and side-effect recovery or forward-fix behavior.",
        ))
    irreversible = migration.get("irreversible_side_effects", [])
    if irreversible and not migration.get("irreversible_effect_controls"):
        findings.append(_draft(
            Severity.BLOCKING, "authority", "IRREVERSIBLE_EFFECT_UNGOVERNED", "migration",
            "Irreversible external actions lack tighter authorization, idempotency, verification, and recovery boundaries.",
            ", ".join(str(item) for item in irreversible), "Domain risk and integration owners",
            "Govern irreversible actions separately from reversible state changes.",
        ))

    flag = payload.get("feature_flag", {})
    if flag.get("treated_as_complete_safety_control"):
        findings.append(_draft(
            Severity.REVIEW, "correctness", "FEATURE_FLAG_MISTAKEN_FOR_CONTROL", str(flag.get("id", "feature-flag")),
            "A rollout switch is treated as a substitute for authorization, policy, migration, and side-effect controls.",
            json.dumps(flag, sort_keys=True), "Release owner",
            "Use the flag for rollout while preserving all independent safety controls.",
        ))
    if flag:
        required = {"enable_authority", "population", "evidence_gate", "expiry", "disabled_behavior", "cannot_bypass_policy"}
        missing = sorted(field for field in required if flag.get(field) in (None, "", [], False))
        if missing:
            findings.append(_draft(
                Severity.REVIEW, "completeness", "FEATURE_FLAG_SEMANTICS_INCOMPLETE",
                str(flag.get("id", "feature-flag")),
                f"Feature flag governance lacks: {', '.join(missing)}.", json.dumps(flag, sort_keys=True),
                "Release owner", "Define authority, population, evidence, expiry, disable behavior, and policy invariants.",
            ))
    kill_switch = payload.get("kill_switch", {})
    if kill_switch and (not kill_switch.get("tested") or not kill_switch.get("in_flight_behavior")):
        findings.append(_draft(
            Severity.BLOCKING, "verifiability", "KILL_SWITCH_UNVERIFIED", "kill-switch",
            "The emergency stop path lacks execution evidence or in-flight/queued-work semantics.",
            json.dumps(kill_switch, sort_keys=True), "Operations owner",
            "Test activation latency, queued effects, in-flight work, preserved state, and recovery.",
        ))

    fallback = payload.get("manual_fallback", {})
    if fallback and not fallback.get("capacity_evidence"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "FALLBACK_CAPACITY_UNVERIFIED", "manual-fallback",
            "Manual fallback is declared without sustainable load, queue-growth, or outage-duration evidence.",
            json.dumps(fallback, sort_keys=True), "Operations and workforce owners",
            "Measure degraded demand and human capacity; route excess work according to an owned policy.",
        ))
    if fallback and not fallback.get("preserves_work"):
        findings.append(_draft(
            Severity.BLOCKING, "correctness", "FALLBACK_WORK_NOT_PRESERVED", "manual-fallback",
            "Degradation discards the work item or evidence required for manual continuation.",
            json.dumps(fallback, sort_keys=True), "Workflow owner",
            "Preserve work identity, source evidence, subject identity, state, and failure reason.",
        ))

    observability = payload.get("observability", {})
    if observability:
        required = {"request_id", "run_id", "logical_operation_id", "proposal_id", "policy_version", "outcome", "reason_code", "cost", "latency"}
        missing = sorted(field for field in required if not observability.get(field))
        if missing:
            findings.append(_draft(
                Severity.REVIEW, "verifiability", "OBSERVABILITY_CONTRACT_INCOMPLETE", "observability",
                f"The workflow cannot be reconstructed because telemetry lacks: {', '.join(missing)}.",
                json.dumps(observability, sort_keys=True), "Observability owner",
                "Specify minimal correlation, versions, decisions, outcomes, reason codes, cost, and latency.",
            ))
        if observability.get("logs_raw_sensitive_content"):
            findings.append(_draft(
                Severity.BLOCKING, "authority", "SENSITIVE_TELEMETRY_EXPOSURE", "observability",
                "Telemetry records unnecessary sensitive prompts, messages, submissions, or tool output.",
                json.dumps(observability, sort_keys=True), "Privacy and security owners",
                "Use identities, reason codes, digests, and metrics while minimizing and protecting content.",
            ))
        if not all(observability.get(field) for field in ("request_id", "run_id", "logical_operation_id")):
            findings.append(_draft(
                Severity.REVIEW, "traceability", "CORRELATION_IDENTITY_UNDEFINED", "observability",
                "Events cannot be joined across request, run, attempt, and logical side-effect boundaries.",
                json.dumps(observability, sort_keys=True), "Observability owner",
                "Define stable logical IDs separately from per-run and per-attempt IDs.",
            ))
        if observability.get("correlation_reused_across_operations"):
            findings.append(_draft(
                Severity.REVIEW, "correctness", "CORRELATION_SCOPE_INVALID", "observability",
                "One correlation identity merges unrelated logical operations and corrupts evidence and metrics.",
                json.dumps(observability, sort_keys=True), "Observability owner",
                "Define identity cardinality, creation, propagation, and reuse rules.",
            ))

    metrics = payload.get("metrics", {})
    if metrics.get("cost") is not None and not metrics.get("cost_outcome_denominator"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "COST_OUTCOME_DENOMINATOR_MISSING", "metrics",
            "Cost is reported without eligible, successful, compliant, or automated outcome context.",
            json.dumps(metrics, sort_keys=True), "Service owner",
            "Report cost per explicitly defined workflow outcome with a matching attribution boundary.",
        ))
    if metrics.get("latency") is not None and not metrics.get("latency_outcome_context"):
        findings.append(_draft(
            Severity.REVIEW, "verifiability", "LATENCY_OUTCOME_CONTEXT_MISSING", "metrics",
            "Latency is optimized without distinguishing success, failure, quality, or compliance.",
            json.dumps(metrics, sort_keys=True), "Service owner",
            "Slice latency by semantic outcome and interpret it with reliability and quality.",
        ))
    if metrics.get("optimized_independently") and not metrics.get("dependency_graph"):
        findings.append(_draft(
            Severity.REVIEW, "consistency", "CROSS_NFR_TRADEOFF_UNMODELED", "metrics",
            "A single NFR is optimized without modelling its effect on quality, reliability, capacity, or cost.",
            json.dumps(metrics, sort_keys=True), "Service and product owners",
            "Record key NFR dependencies and evaluate feasible trade-offs together.",
        ))

    readiness = payload.get("readiness_claim", {})
    required_claim = {"capability", "population", "autonomy", "environment", "evidence_status", "excluded"}
    if readiness and any(readiness.get(field) in (None, "", []) for field in required_claim):
        findings.append(_draft(
            Severity.BLOCKING, "completeness", "PRODUCTION_READINESS_UNBOUNDED", "readiness-claim",
            "Production-ready is asserted without capability, population, autonomy, environment, current evidence, and exclusions.",
            json.dumps(readiness, sort_keys=True), "Release owner",
            "Issue a bounded readiness claim and retain separate implementation and production gates.",
        ))
    return tuple(findings)


REVIEW_PIPELINE = (
    "source", "authority", "requirement_quality", "conflict", "behavioral_completeness",
    "nfr", "traceability", "evidence", "repository_reconciliation", "agent_readiness",
)


def agent_readiness_by_capability(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep readiness scoped and require evidence links for fixture assertions."""
    required = (
        "scope_bounded", "requirements_approved", "context_current", "autonomy_bounded",
        "protected_decisions_known", "stop_conditions_defined", "verification_defined",
    )
    evidence_index = {
        str(item.get("id")): item
        for item in payload.get("evidence_catalog", [])
    }
    results: list[dict[str, Any]] = []
    for capability in payload.get("capabilities", []):
        missing = [field for field in required if capability.get(field) is not True]
        assertion_evidence = capability.get("assertion_evidence", {})
        evidence_blockers: list[str] = []
        used_evidence_ids: set[str] = set()
        for field in required:
            if capability.get(field) is not True:
                continue
            evidence_ids = assertion_evidence.get(field, [])
            if not evidence_ids:
                evidence_blockers.append(f"{field}:evidence_missing")
                continue
            used_evidence_ids.update(str(identifier) for identifier in evidence_ids)
            for identifier in evidence_ids:
                record = evidence_index.get(str(identifier))
                if record is None:
                    evidence_blockers.append(f"{field}:evidence_target_missing")
                elif record.get("status") != "current":
                    evidence_blockers.append(f"{field}:evidence_not_current")
        blockers = sorted(set(
            missing + evidence_blockers + list(capability.get("blocking_questions", []))
        ))
        results.append({
            "capability": capability.get("id"),
            "decision": "blocked" if blockers else Readiness.READY_FOR_BOUNDED_IMPLEMENTATION.value,
            "blockers": blockers,
            "fixture_evidence_ids": sorted(used_evidence_ids),
            "claim": "implementation_readiness_only_not_production_release",
        })
    return {
        "pipeline": list(REVIEW_PIPELINE),
        "capabilities": results,
        "counts": dict(sorted(Counter(item["decision"] for item in results).items())),
        "evidence_boundary": (
            "synthetic fixture assertions with linked evidence IDs; not authenticated approvals, "
            "attestations, or production-readiness evidence"
        ),
    }


def cluster_findings(findings: Iterable[Finding]) -> list[dict[str, Any]]:
    """Preserve machine findings while grouping symptoms into human remediation themes."""
    buckets: dict[str, list[Finding]] = {identifier: [] for identifier in FINDING_CLUSTER_RULES}
    for finding in findings:
        cluster_id = next(
            (identifier for identifier, codes in FINDING_CLUSTER_RULES.items() if finding.code in codes),
            "unclassified_review_theme",
        )
        buckets.setdefault(cluster_id, []).append(finding)
    clusters: list[dict[str, Any]] = []
    for cluster_id, members in buckets.items():
        if not members:
            continue
        highest = min(members, key=lambda item: SEVERITY_ORDER[item.severity]).severity
        clusters.append({
            "cluster_id": cluster_id,
            "title": FINDING_CLUSTER_TITLES.get(cluster_id, "Review theme requiring triage"),
            "highest_severity": highest.value,
            "finding_ids": [item.finding_id for item in members],
            "finding_codes": sorted({item.code for item in members}),
            "affected_subjects": sorted({item.subject_id for item in members}),
            "accountable_owners": sorted({item.owner for item in members}),
        })
    return clusters


def review_bundle(bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = bundle or load_review_bundle()
    package = bundle["package"]
    drafts: list[DraftFinding] = []
    for statement in package.get("statements", []):
        drafts.extend(review_statement(statement))
    expected_policy_ids = set(
        bundle.get("policy_expectation", {}).get(
            "expected_policy_ids", FIXTURE_EXPECTED_POLICY_IDS,
        )
    )
    drafts.extend(review_package_structure(package, expected_policy_ids=expected_policy_ids))
    drafts.extend(review_autonomy(bundle["autonomy"]))
    traceability, trace_findings = traceability_metrics(package, bundle["traceability"], bundle["evidence"])
    drafts.extend(trace_findings)
    drafts.extend(review_evidence(bundle["evidence"]))
    drafts.extend(review_context(bundle["context"]))
    findings = _finalize(drafts)
    return {
        "review_method": "deterministic_field_aware_training_rules",
        "limitations": [
            "Rules exercise known anti-patterns in labelled fixtures; they do not prove completeness.",
            "Human reviewers and accountable owners retain semantic and decision authority.",
        ],
        "findings": [asdict(item) for item in findings],
        "finding_clusters": cluster_findings(findings),
        "finding_counts": {
            severity.value: sum(item.severity == severity for item in findings)
            for severity in Severity
        },
        "dimensions": dict(sorted(Counter(item.dimension for item in findings).items())),
        "traceability": traceability,
    }


def readiness_decision(review: dict[str, Any]) -> dict[str, Any]:
    findings = review.get("findings", [])
    blocking = [item for item in findings if item.get("severity") == Severity.BLOCKING.value]
    review_items = [item for item in findings if item.get("severity") == Severity.REVIEW.value]
    if blocking:
        decision = Readiness.STOP
    elif review_items:
        decision = Readiness.REVIEW
    else:
        decision = Readiness.READY_FOR_BOUNDED_IMPLEMENTATION
    affected = sorted({item.get("subject_id") for item in blocking})
    return {
        "decision": decision.value,
        "ready": decision == Readiness.READY_FOR_BOUNDED_IMPLEMENTATION,
        "blocking_finding_ids": [item.get("finding_id") for item in blocking],
        "affected_subjects": affected,
        "reason_codes": sorted({str(item.get("code")) for item in blocking or review_items}),
        "score": None,
        "interpretation": "Readiness is a typed decision over findings; it is not a weighted 0–100 score.",
    }


def _case_drafts(case: dict[str, Any]) -> tuple[DraftFinding, ...]:
    kind = case["kind"]
    payload = case["input"]
    if kind == "statement":
        return review_statement(payload)
    if kind == "autonomy":
        return review_autonomy(payload)
    if kind == "evidence":
        return review_evidence({"records": [payload]})
    if kind == "context":
        return review_context(payload)
    if kind == "package":
        return review_package_structure(payload)
    if kind == "normative_context":
        return review_normative_context(payload)
    if kind == "requirement_model":
        return review_requirement_model(payload)
    if kind == "execution_safety":
        return review_execution_safety(payload)
    if kind == "evaluation_gate":
        return review_evaluation_and_gate(payload)
    if kind == "lifecycle":
        return review_lifecycle(payload)
    if kind == "brownfield_delivery":
        return review_brownfield_delivery(payload)
    raise ValueError(f"unknown evaluation case kind: {kind}")


def evaluate_review_rules(cases: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
    population = list(cases or load_json(EVALUATION_PATH)["cases"])
    true_positive = false_positive = false_negative = 0
    case_results: list[dict[str, Any]] = []
    for case in population:
        predicted = {item.code for item in _case_drafts(case)}
        expected = set(case.get("expected_codes", []))
        tp = len(predicted & expected)
        fp = len(predicted - expected)
        fn = len(expected - predicted)
        true_positive += tp
        false_positive += fp
        false_negative += fn
        case_results.append({
            "case_id": case["id"],
            "expected_codes": sorted(expected),
            "predicted_codes": sorted(predicted),
            "exact_match": predicted == expected,
        })
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    return {
        "claim": "labelled_fixture_rule_coverage_not_general_spec_review_accuracy",
        "population": len(population),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": {
            "numerator": true_positive,
            "denominator": precision_denominator,
            "value": true_positive / precision_denominator if precision_denominator else None,
        },
        "recall": {
            "numerator": true_positive,
            "denominator": recall_denominator,
            "value": true_positive / recall_denominator if recall_denominator else None,
        },
        "exact_case_matches": {
            "numerator": sum(item["exact_match"] for item in case_results),
            "denominator": len(case_results),
        },
        "cases": case_results,
    }


def stable_bundle_digest(bundle: dict[str, Any]) -> str:
    payload = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_demo() -> dict[str, Any]:
    candidate_bundle = load_review_bundle()
    repaired_bundle = load_review_bundle(repaired=True)
    baseline = lexical_presence_baseline(candidate_bundle["package"])
    candidate_review = review_bundle(candidate_bundle)
    repaired_review = review_bundle(repaired_bundle)
    return {
        "fixture_status": "synthetic_specification_review_training_fixture",
        "thesis": "presence_is_not_quality_and_findings_are_not_a_composite_score",
        "candidate_bundle_digest": stable_bundle_digest(candidate_bundle),
        "baseline": baseline,
        "candidate_review": candidate_review,
        "candidate_readiness": readiness_decision(candidate_review),
        "repaired_review": repaired_review,
        "repaired_readiness": readiness_decision(repaired_review),
        "evaluation": evaluate_review_rules(),
        "capability_readiness": agent_readiness_by_capability(load_json(CAPABILITY_READINESS_PATH)),
    }


def main() -> None:
    print(json.dumps(run_demo(), indent=2, default=lambda value: value.value if isinstance(value, Enum) else str(value)))


if __name__ == "__main__":
    main()
