"""Course 03 lab: resolve an effective specification from layered requirements.

The implementation is intentionally deterministic and dependency-free. It models
explicit conjunctive scope, controlled resources, provenance, lifecycle dates,
domain-bounded authority, conflicts, and scoped exceptions. It does not authenticate
owners, publishers, or approvals and is not a production policy engine.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SCENARIO_ROOT = HERE / "northstar-broker-export"


class Layer(IntEnum):
    ORGANIZATION = 0
    PLATFORM = 1
    DOMAIN = 2
    PROJECT = 3
    FEATURE = 4
    IMPLEMENTATION = 5


class Authority(str, Enum):
    INFORMAL = "informal"
    APPROVED = "approved"
    MANDATORY = "mandatory"


AUTHORITY_PRECEDENCE = {
    Authority.INFORMAL: 1,
    Authority.APPROVED: 2,
    Authority.MANDATORY: 3,
}


class ScopeOperator(str, Enum):
    ALL = "all"


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"
    EXPIRED = "expired"


class Applicability(str, Enum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNCERTAIN = "uncertain"


class ExceptionDisposition(str, Enum):
    VALID = "valid"
    NOT_APPLICABLE = "not_applicable"
    INVALID = "invalid"


class Gate(str, Enum):
    READY = "ready"
    STOP = "stop"


@dataclass(frozen=True)
class SourceRef:
    repository: str
    path: str
    version: str
    revision: str

    def complete(self) -> bool:
        return all(
            value.strip()
            for value in (self.repository, self.path, self.version, self.revision)
        )

    def locator(self) -> str:
        return f"{self.repository}:{self.path}@{self.version}#{self.revision}"


@dataclass(frozen=True)
class ScopeRule:
    field: str
    allowed_values: tuple[str, ...]


@dataclass(frozen=True)
class ContextFact:
    field: str
    values: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ChangeContext:
    id: str
    evaluated_on: date
    facts: tuple[ContextFact, ...]

    def fact(self, field: str) -> ContextFact | None:
        return next((item for item in self.facts if item.field == field), None)


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    statement: str
    layer: Layer
    owner: str
    authority: Authority
    authority_domain: str
    status: ArtifactStatus
    effective_from: date
    effective_until: date | None
    review_due: date | None
    superseded_by: str | None
    source: SourceRef
    scope_operator: ScopeOperator
    scope: tuple[ScopeRule, ...]
    resource: str
    control: str
    expected: str


@dataclass(frozen=True)
class ExceptionRecord:
    id: str
    requirement_id: str
    change_ids: tuple[str, ...]
    resources: tuple[str, ...]
    control: str
    permitted_expected: str
    unaffected_requirement_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    rationale: str
    owner: str
    approver: str
    approval_record: str
    status: ArtifactStatus
    created_on: date
    expires_on: date
    source: SourceRef


@dataclass(frozen=True)
class ApplicabilityDecision:
    requirement_id: str
    result: Applicability
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExceptionDecision:
    exception_id: str
    requirement_id: str
    disposition: ExceptionDisposition
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    artifact: str
    message: str


@dataclass(frozen=True)
class ResolvedRequirement:
    requirement: Requirement
    decision_expected: str
    applicability_evidence_ids: tuple[str, ...]
    exception_id: str | None = None
    exception_conditions: tuple[str, ...] = ()
    unaffected_requirement_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Conflict:
    id: str
    authority_domain: str
    resource: str
    control: str
    requirement_ids: tuple[str, ...]
    owners: tuple[str, ...]
    action: str


@dataclass(frozen=True)
class PrecedenceResolution:
    authority_domain: str
    resource: str
    control: str
    selected_requirement_ids: tuple[str, ...]
    rejected_requirement_ids: tuple[str, ...]
    reason_code: str


@dataclass(frozen=True)
class EffectiveControl:
    authority_domain: str
    resource: str
    control: str
    expected: str
    requirement_ids: tuple[str, ...]
    base_expectations: tuple[str, ...]
    applicability_evidence_ids: tuple[str, ...]
    exception_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    unaffected_requirement_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResolutionReport:
    change_id: str
    decisions: tuple[ApplicabilityDecision, ...]
    exception_decisions: tuple[ExceptionDecision, ...]
    precedence: tuple[PrecedenceResolution, ...]
    conflicts: tuple[Conflict, ...]
    effective_controls: tuple[EffectiveControl, ...]
    findings: tuple[Finding, ...]

    @property
    def gate(self) -> Gate:
        uncertain = any(
            decision.result is Applicability.UNCERTAIN for decision in self.decisions
        )
        errors = any(finding.severity == "error" for finding in self.findings)
        return Gate.STOP if uncertain or self.conflicts or errors else Gate.READY


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _source(payload: dict[str, Any]) -> SourceRef:
    return SourceRef(
        repository=str(payload.get("repository", "")),
        path=str(payload.get("path", "")),
        version=str(payload.get("version", "")),
        revision=str(payload.get("revision", "")),
    )


def load_requirement(path: Path) -> Requirement:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Requirement(
        id=payload["id"],
        title=payload["title"],
        statement=payload["statement"],
        layer=Layer[payload["layer"].upper()],
        owner=payload["owner"],
        authority=Authority(payload["authority"]),
        authority_domain=payload["authority_domain"],
        status=ArtifactStatus(payload["status"]),
        effective_from=date.fromisoformat(payload["effective_from"]),
        effective_until=_parse_date(payload.get("effective_until")),
        review_due=_parse_date(payload.get("review_due")),
        superseded_by=payload.get("superseded_by"),
        source=_source(payload["source"]),
        scope_operator=ScopeOperator(payload["scope_operator"]),
        scope=tuple(
            ScopeRule(item["field"], tuple(item["allowed_values"]))
            for item in payload.get("scope", [])
        ),
        resource=payload["resource"],
        control=payload["control"],
        expected=payload["expected"],
    )


def load_change_context(path: Path) -> ChangeContext:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ChangeContext(
        id=payload["id"],
        evaluated_on=date.fromisoformat(payload["evaluated_on"]),
        facts=tuple(
            ContextFact(
                field=item["field"],
                values=tuple(item["values"]),
                evidence_ids=tuple(item["evidence_ids"]),
            )
            for item in payload["facts"]
        ),
    )


def load_exception(path: Path) -> ExceptionRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    scope = payload["scope"]
    modification = payload["modification"]
    return ExceptionRecord(
        id=payload["id"],
        requirement_id=payload["requirement_id"],
        change_ids=tuple(scope["change_ids"]),
        resources=tuple(scope["resources"]),
        control=modification["control"],
        permitted_expected=modification["permitted_expected"],
        unaffected_requirement_ids=tuple(payload["unaffected_requirement_ids"]),
        conditions=tuple(payload["conditions"]),
        rationale=payload["rationale"],
        owner=payload["owner"],
        approver=payload["approver"],
        approval_record=payload["approval_record"],
        status=ArtifactStatus(payload["status"]),
        created_on=date.fromisoformat(payload["created_on"]),
        expires_on=date.fromisoformat(payload["expires_on"]),
        source=_source(payload["source"]),
    )


def load_scenario(
    root: Path = SCENARIO_ROOT,
) -> tuple[ChangeContext, tuple[Requirement, ...], tuple[ExceptionRecord, ...]]:
    change = load_change_context(root / "ticket" / "change-context.json")
    requirements = tuple(
        load_requirement(path) for path in sorted((root / "catalog").glob("**/*.json"))
    )
    exceptions = tuple(
        load_exception(path) for path in sorted((root / "exceptions").glob("*.json"))
    )
    return change, requirements, exceptions


def validate_catalog(requirements: Iterable[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    items = list(requirements)
    ids = [item.id for item in items]
    for duplicate in sorted({item for item in ids if ids.count(item) > 1}):
        findings.append(
            Finding("error", "REQ_ID_DUPLICATE", duplicate, "Requirement ID is duplicated.")
        )
    for requirement in items:
        if not requirement.owner.strip():
            findings.append(
                Finding("error", "REQ_OWNER_MISSING", requirement.id, "Owner is absent.")
            )
        if not requirement.source.complete():
            findings.append(
                Finding(
                    "error",
                    "REQ_PROVENANCE_INCOMPLETE",
                    requirement.id,
                    "Repository, path, version, and immutable revision are required.",
                )
            )
        if not all(
            value.strip()
            for value in (
                requirement.authority_domain,
                requirement.resource,
                requirement.control,
                requirement.expected,
            )
        ):
            findings.append(
                Finding(
                    "error",
                    "REQ_CONTROL_INCOMPLETE",
                    requirement.id,
                    "Authority domain, resource, control, and expected value are required.",
                )
            )
        if requirement.scope_operator is not ScopeOperator.ALL:
            findings.append(
                Finding(
                    "error",
                    "REQ_SCOPE_OPERATOR_UNSUPPORTED",
                    requirement.id,
                    "The Course 03 resolver supports only explicit ALL expressions.",
                )
            )
        for rule in requirement.scope:
            if not rule.field.strip() or not rule.allowed_values:
                findings.append(
                    Finding(
                        "error",
                        "REQ_SCOPE_INVALID",
                        requirement.id,
                        "Every scope rule needs a field and at least one allowed value.",
                    )
                )
    authority_domains: dict[tuple[str, str], set[str]] = defaultdict(set)
    for requirement in items:
        authority_domains[(requirement.resource, requirement.control)].add(
            requirement.authority_domain
        )
    for (resource, control), domains in sorted(authority_domains.items()):
        if len(domains) > 1:
            findings.append(
                Finding(
                    "error",
                    "REQ_AUTHORITY_DOMAIN_COLLISION",
                    f"{resource}:{control}",
                    "Competing requirements declare different decision-rights domains: "
                    + ", ".join(sorted(domains)),
                )
            )
    return findings


def evaluate_applicability(
    requirement: Requirement, change: ChangeContext
) -> ApplicabilityDecision:
    if not requirement.source.complete():
        return ApplicabilityDecision(
            requirement.id,
            Applicability.UNCERTAIN,
            ("PROVENANCE_INCOMPLETE",),
            (),
        )
    if requirement.status is not ArtifactStatus.ACTIVE:
        return ApplicabilityDecision(
            requirement.id,
            Applicability.NOT_APPLICABLE,
            (f"STATUS_{requirement.status.value.upper()}",),
            (),
        )
    if requirement.effective_from > change.evaluated_on:
        return ApplicabilityDecision(
            requirement.id,
            Applicability.NOT_APPLICABLE,
            ("NOT_YET_EFFECTIVE",),
            (),
        )
    if requirement.effective_until and requirement.effective_until < change.evaluated_on:
        return ApplicabilityDecision(
            requirement.id,
            Applicability.NOT_APPLICABLE,
            ("REQUIREMENT_EFFECTIVE_PERIOD_ENDED",),
            (),
        )
    if requirement.review_due and requirement.review_due < change.evaluated_on:
        return ApplicabilityDecision(
            requirement.id,
            Applicability.UNCERTAIN,
            ("SOURCE_REVIEW_OVERDUE",),
            (),
        )

    uncertain_fields: list[str] = []
    mismatched_fields: list[str] = []
    evidence_ids: set[str] = set()
    for rule in requirement.scope:
        fact = change.fact(rule.field)
        if fact is None or not fact.values:
            uncertain_fields.append(rule.field)
            continue
        evidence_ids.update(fact.evidence_ids)
        if set(fact.values).isdisjoint(rule.allowed_values):
            mismatched_fields.append(rule.field)
    if mismatched_fields:
        reason_codes = [
            f"SCOPE_MISMATCH_{field.upper()}" for field in mismatched_fields
        ]
        reason_codes.extend(
            f"SCOPE_UNKNOWN_{field.upper()}" for field in uncertain_fields
        )
        return ApplicabilityDecision(
            requirement.id,
            Applicability.NOT_APPLICABLE,
            tuple(reason_codes),
            tuple(sorted(evidence_ids)),
        )
    if uncertain_fields:
        return ApplicabilityDecision(
            requirement.id,
            Applicability.UNCERTAIN,
            tuple(f"SCOPE_UNKNOWN_{field.upper()}" for field in uncertain_fields),
            tuple(sorted(evidence_ids)),
        )
    return ApplicabilityDecision(
        requirement.id,
        Applicability.APPLICABLE,
        ("SCOPE_MATCH",) if requirement.scope else ("GLOBAL_SCOPE",),
        tuple(sorted(evidence_ids)),
    )


def evaluate_exception(
    exception: ExceptionRecord,
    change: ChangeContext,
    requirements: dict[str, Requirement],
) -> tuple[ExceptionDecision, list[Finding]]:
    if change.id not in exception.change_ids:
        return (
            ExceptionDecision(
                exception.id,
                exception.requirement_id,
                ExceptionDisposition.NOT_APPLICABLE,
                ("CHANGE_OUTSIDE_EXCEPTION_SCOPE",),
            ),
            [],
        )

    errors: list[str] = []
    requirement = requirements.get(exception.requirement_id)
    if requirement is None:
        errors.append("EXCEPTION_TARGET_UNKNOWN")
    else:
        if exception.control != requirement.control:
            errors.append("EXCEPTION_CONTROL_MISMATCH")
        if requirement.resource not in exception.resources:
            errors.append("EXCEPTION_RESOURCE_MISMATCH")
    if any(item not in requirements for item in exception.unaffected_requirement_ids):
        errors.append("EXCEPTION_UNAFFECTED_REQUIREMENT_UNKNOWN")
    if exception.status is not ArtifactStatus.ACTIVE:
        errors.append(f"EXCEPTION_STATUS_{exception.status.value.upper()}")
    if exception.created_on > change.evaluated_on:
        errors.append("EXCEPTION_NOT_YET_CREATED")
    if exception.expires_on < change.evaluated_on:
        errors.append("EXCEPTION_EXPIRED")
    if not exception.source.complete():
        errors.append("EXCEPTION_PROVENANCE_INCOMPLETE")
    if not all(
        value.strip()
        for value in (
            exception.owner,
            exception.approver,
            exception.approval_record,
            exception.rationale,
            exception.permitted_expected,
        )
    ):
        errors.append("EXCEPTION_METADATA_INCOMPLETE")
    if not exception.resources:
        errors.append("EXCEPTION_RESOURCE_SCOPE_MISSING")
    if not exception.unaffected_requirement_ids:
        errors.append("EXCEPTION_UNAFFECTED_OBLIGATIONS_MISSING")
    if not exception.conditions:
        errors.append("EXCEPTION_CONDITIONS_MISSING")

    if errors:
        findings = [
            Finding(
                "error",
                code,
                exception.id,
                "Scoped exception is not structurally valid for this change.",
            )
            for code in errors
        ]
        return (
            ExceptionDecision(
                exception.id,
                exception.requirement_id,
                ExceptionDisposition.INVALID,
                tuple(errors),
            ),
            findings,
        )
    return (
        ExceptionDecision(
            exception.id,
            exception.requirement_id,
            ExceptionDisposition.VALID,
            ("SCOPED_ACTIVE_EXCEPTION",),
        ),
        [],
    )


def _apply_exceptions(
    applicable: list[Requirement],
    valid_exceptions: list[ExceptionRecord],
    decisions: dict[str, ApplicabilityDecision],
) -> tuple[list[ResolvedRequirement], list[Finding]]:
    findings: list[Finding] = []
    by_requirement: dict[str, list[ExceptionRecord]] = defaultdict(list)
    for exception in valid_exceptions:
        by_requirement[exception.requirement_id].append(exception)

    resolved: list[ResolvedRequirement] = []
    for requirement in applicable:
        matches = by_requirement.get(requirement.id, [])
        if len(matches) > 1:
            findings.append(
                Finding(
                    "error",
                    "MULTIPLE_APPLICABLE_EXCEPTIONS",
                    requirement.id,
                    "More than one active exception attempts to modify the same requirement.",
                )
            )
            continue
        if matches:
            exception = matches[0]
            resolved.append(
                ResolvedRequirement(
                    requirement,
                    exception.permitted_expected,
                    decisions[requirement.id].evidence_ids,
                    exception.id,
                    exception.conditions,
                    exception.unaffected_requirement_ids,
                )
            )
        else:
            resolved.append(
                ResolvedRequirement(
                    requirement,
                    requirement.expected,
                    decisions[requirement.id].evidence_ids,
                )
            )
    return resolved, findings


def _compose_controls(
    resolved: list[ResolvedRequirement],
) -> tuple[list[EffectiveControl], list[Conflict], list[PrecedenceResolution]]:
    groups: dict[tuple[str, str, str], list[ResolvedRequirement]] = defaultdict(list)
    for item in resolved:
        key = (
            item.requirement.authority_domain,
            item.requirement.resource,
            item.requirement.control,
        )
        groups[key].append(item)

    controls: list[EffectiveControl] = []
    conflicts: list[Conflict] = []
    precedence: list[PrecedenceResolution] = []
    for (authority_domain, resource, control), candidates in sorted(groups.items()):
        highest = max(
            AUTHORITY_PRECEDENCE[item.requirement.authority] for item in candidates
        )
        authoritative = [
            item
            for item in candidates
            if AUTHORITY_PRECEDENCE[item.requirement.authority] == highest
        ]
        authoritative_values = {item.decision_expected for item in authoritative}
        if len(authoritative_values) > 1:
            requirement_ids = tuple(sorted(item.requirement.id for item in authoritative))
            conflicts.append(
                Conflict(
                    id=(
                        "CONFLICT-"
                        f"{resource.upper().replace('_', '-')}-"
                        f"{control.upper().replace('_', '-')}"
                    ),
                    authority_domain=authority_domain,
                    resource=resource,
                    control=control,
                    requirement_ids=requirement_ids,
                    owners=tuple(sorted({item.requirement.owner for item in authoritative})),
                    action="Escalate to the named owners; implementation remains blocked.",
                )
            )
            continue

        selected_value = next(iter(authoritative_values))
        selected = [item for item in candidates if item.decision_expected == selected_value]
        rejected = [item for item in candidates if item.decision_expected != selected_value]
        if rejected:
            precedence.append(
                PrecedenceResolution(
                    authority_domain=authority_domain,
                    resource=resource,
                    control=control,
                    selected_requirement_ids=tuple(
                        sorted(item.requirement.id for item in selected)
                    ),
                    rejected_requirement_ids=tuple(
                        sorted(item.requirement.id for item in rejected)
                    ),
                    reason_code="HIGHER_AUTHORITY_WINS_NOT_GREATER_SPECIFICITY",
                )
            )
        controls.append(
            EffectiveControl(
                authority_domain=authority_domain,
                resource=resource,
                control=control,
                expected=selected_value,
                requirement_ids=tuple(
                    sorted(item.requirement.id for item in selected)
                ),
                base_expectations=tuple(
                    sorted(
                        f"{item.requirement.id}={item.requirement.expected}"
                        for item in selected
                    )
                ),
                applicability_evidence_ids=tuple(
                    sorted(
                        {
                            evidence_id
                            for item in selected
                            for evidence_id in item.applicability_evidence_ids
                        }
                    )
                ),
                exception_ids=tuple(
                    sorted(
                        {
                            item.exception_id
                            for item in selected
                            if item.exception_id is not None
                        }
                    )
                ),
                conditions=tuple(
                    sorted(
                        {
                            condition
                            for item in selected
                            for condition in item.exception_conditions
                        }
                    )
                ),
                unaffected_requirement_ids=tuple(
                    sorted(
                        {
                            requirement_id
                            for item in selected
                            for requirement_id in item.unaffected_requirement_ids
                        }
                    )
                ),
            )
        )
    return controls, conflicts, precedence


def resolve_effective_specification(
    change: ChangeContext,
    requirements: Iterable[Requirement],
    exceptions: Iterable[ExceptionRecord] = (),
) -> ResolutionReport:
    requirement_list = list(requirements)
    findings = validate_catalog(requirement_list)
    decisions = [evaluate_applicability(item, change) for item in requirement_list]
    decision_by_id = {item.requirement_id: item for item in decisions}
    requirement_by_id = {item.id: item for item in requirement_list}

    exception_decisions: list[ExceptionDecision] = []
    valid_exceptions: list[ExceptionRecord] = []
    for exception in exceptions:
        decision, exception_findings = evaluate_exception(
            exception, change, requirement_by_id
        )
        exception_decisions.append(decision)
        findings.extend(exception_findings)
        if decision.disposition is ExceptionDisposition.VALID:
            target_decision = decision_by_id.get(exception.requirement_id)
            if target_decision is None or target_decision.result is not Applicability.APPLICABLE:
                findings.append(
                    Finding(
                        "error",
                        "EXCEPTION_TARGET_NOT_APPLICABLE",
                        exception.id,
                        "An exception cannot make a non-applicable requirement applicable.",
                    )
                )
            else:
                valid_exceptions.append(exception)

    applicable = [
        item
        for item in requirement_list
        if decision_by_id[item.id].result is Applicability.APPLICABLE
    ]
    resolved, exception_findings = _apply_exceptions(
        applicable, valid_exceptions, decision_by_id
    )
    findings.extend(exception_findings)
    controls, conflicts, precedence = _compose_controls(resolved)

    return ResolutionReport(
        change_id=change.id,
        decisions=tuple(sorted(decisions, key=lambda item: item.requirement_id)),
        exception_decisions=tuple(
            sorted(exception_decisions, key=lambda item: item.exception_id)
        ),
        precedence=tuple(precedence),
        conflicts=tuple(conflicts),
        effective_controls=tuple(controls),
        findings=tuple(findings),
    )


def naive_concatenation(requirements: Iterable[Requirement]) -> tuple[str, ...]:
    """Show the unsafe baseline: every statement is copied without resolution."""
    return tuple(item.statement for item in requirements)


def compose_agent_context(
    report: ResolutionReport, requirements: Iterable[Requirement]
) -> str:
    if report.gate is not Gate.READY:
        raise ValueError("effective context is unavailable while the resolution gate is STOP")
    by_id = {item.id: item for item in requirements}
    lines = [
        f"# Effective specification for {report.change_id}",
        "# Resolver output is evidence for review; it is not self-authorizing policy.",
        "# Source locators are structurally complete, not authenticated in this lab.",
    ]
    for control in report.effective_controls:
        sources = "; ".join(
            f"{item_id} | {by_id[item_id].authority.value} | "
            f"{by_id[item_id].source.locator()}"
            for item_id in control.requirement_ids
        )
        lines.append(f"[{sources}]")
        lines.append(f"authority_domain = {control.authority_domain}")
        lines.append(f"resource = {control.resource}")
        lines.append(f"{control.control} = {control.expected}")
        if control.applicability_evidence_ids:
            lines.append(
                "applicability_evidence = "
                + ", ".join(control.applicability_evidence_ids)
            )
        if control.exception_ids:
            lines.append(f"exception = {', '.join(control.exception_ids)}")
            lines.append(
                "base_obligations = " + "; ".join(control.base_expectations)
            )
        for requirement_id in control.unaffected_requirement_ids:
            lines.append(f"unaffected_requirement = {requirement_id}")
        for condition in control.conditions:
            lines.append(f"condition = {condition}")
    return "\n".join(lines) + "\n"


def context_selection_metrics(
    gold_applicable_ids: Iterable[str], selected_candidate_ids: Iterable[str]
) -> dict[str, object]:
    """Measure candidate discovery separately from applicability resolution."""
    gold = set(gold_applicable_ids)
    selected = set(selected_candidate_ids)
    true_positive = len(gold & selected)
    precision = round(100 * true_positive / len(selected), 1) if selected else None
    recall = round(100 * true_positive / len(gold), 1) if gold else None
    return {
        "true_positive": true_positive,
        "selected_total": len(selected),
        "gold_applicable_total": len(gold),
        "precision_percent": precision,
        "recall_percent": recall,
        "missed_applicable_ids": tuple(sorted(gold - selected)),
        "irrelevant_selected_ids": tuple(sorted(selected - gold)),
    }


def resolution_metrics(
    report: ResolutionReport, requirements: Iterable[Requirement]
) -> dict[str, object]:
    items = list(requirements)
    counts = {
        state.value: sum(item.result is state for item in report.decisions)
        for state in Applicability
    }
    complete = sum(
        bool(item.owner.strip()) and item.source.complete() for item in items
    )
    total = len(items)
    return {
        "candidate_requirements": total,
        "applicability": counts,
        "effective_controls": len(report.effective_controls),
        "unresolved_conflicts": len(report.conflicts),
        "valid_exceptions": sum(
            item.disposition is ExceptionDisposition.VALID
            for item in report.exception_decisions
        ),
        "provenance_completeness": {
            "covered": complete,
            "total": total,
            "percent": round(100 * complete / total, 1) if total else None,
        },
        "gate": report.gate.value,
    }


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (Enum, date)):
        return value.value if isinstance(value, Enum) else value.isoformat()
    return value


def build_evidence() -> dict[str, object]:
    change, requirements, exceptions = load_scenario()
    report = resolve_effective_specification(change, requirements, exceptions)
    without_exception = resolve_effective_specification(change, requirements)
    applicable_ids = {
        item.requirement_id
        for item in report.decisions
        if item.result is Applicability.APPLICABLE
    }
    discovery_selection = {
        item.id for item in requirements if item.id != "AI-012"
    }
    return {
        "scenario": change.id,
        "baseline_statement_count": len(naive_concatenation(requirements)),
        "reference": {
            "report": _jsonable(report),
            "metrics": resolution_metrics(report, requirements),
            "agent_context": compose_agent_context(report, requirements),
        },
        "failure_without_exception": {
            "report": _jsonable(without_exception),
            "metrics": resolution_metrics(without_exception, requirements),
        },
        "candidate_discovery_failure": context_selection_metrics(
            applicable_ids, discovery_selection
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Optional directory for machine-readable evidence"
    )
    args = parser.parse_args()
    change, requirements, exceptions = load_scenario()
    report = resolve_effective_specification(change, requirements, exceptions)
    metrics = resolution_metrics(report, requirements)

    print("Course 03 — The Specification Hierarchy")
    print(f"Change: {change.id}")
    print(f"Candidates: {metrics['candidate_requirements']}")
    for state, count in metrics["applicability"].items():
        print(f"  {state:<16} {count}")
    print(f"Effective controls: {metrics['effective_controls']}")
    print(f"Unresolved conflicts: {metrics['unresolved_conflicts']}")
    print(f"Valid scoped exceptions: {metrics['valid_exceptions']}")
    print(f"Gate: {report.gate.value.upper()}")
    print("\nEffective agent context\n")
    print(compose_agent_context(report, requirements))

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output / "course03-evidence.json"
        target.write_text(json.dumps(build_evidence(), indent=2) + "\n", encoding="utf-8")
        print(f"Evidence written to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
