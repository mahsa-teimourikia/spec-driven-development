"""Deterministic Course 04 lab for requirement ownership and propagation.

The lab is intentionally smaller than a production policy platform. It makes
source ownership, delegated specialization, enforcement, agent boundaries, and
upstream-change impact observable without credentials or external services.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from datetime import date
from enum import Enum
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCENARIO_ROOT = HERE / "northstar-renewal"
RESOLVER_VERSION = "0.5.0-training"


class Layer(str, Enum):
    ENTERPRISE = "enterprise"
    PLATFORM = "platform"
    DOMAIN = "domain"
    PROJECT = "project"
    FEATURE = "feature"


class ArtifactStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class Applicability(str, Enum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNCERTAIN = "uncertain"


class RelationType(str, Enum):
    INHERITS = "inherits"
    SPECIALIZES = "specializes"
    DERIVED_FROM = "derived_from"
    IMPLEMENTS = "implements"
    EVIDENCES = "evidences"
    EXCEPTS = "excepts"
    SUPERSEDES = "supersedes"


class AgentAuthority(str, Enum):
    NONE = "none"
    PROPOSE = "propose"
    DECIDE = "decide"


class Gate(str, Enum):
    READY = "ready"
    REVIEW = "review"
    STOP = "stop"


class Severity(str, Enum):
    INFO = "info"
    REVIEW = "review"
    ERROR = "error"


@dataclass(frozen=True)
class SourceRef:
    repository: str
    path: str
    version: str
    revision: str

    def locator(self) -> str:
        return f"{self.repository}:{self.path}@{self.version}#{self.revision}"

    def complete(self) -> bool:
        return all((self.repository, self.path, self.version, self.revision))


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
class Control:
    field: str
    expected: str


@dataclass(frozen=True)
class DelegatedControl:
    field: str
    owner: str
    agent_authority: AgentAuthority


@dataclass(frozen=True)
class Enforcement:
    plane: str
    mechanism: str
    owner: str
    automated: bool


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    statement: str
    layer: Layer
    meaning_owner: str
    status: ArtifactStatus
    effective_from: date
    source_domain: str
    source: SourceRef
    scope: tuple[ScopeRule, ...]
    fixed_controls: tuple[Control, ...]
    delegated_controls: tuple[DelegatedControl, ...]
    enforcement: tuple[Enforcement, ...]
    evidence_ids: tuple[str, ...]
    recommended_capabilities: tuple[str, ...]
    exception_owner: str


@dataclass(frozen=True)
class ChangeContext:
    id: str
    evaluated_on: date
    facts: tuple[ContextFact, ...]
    requested_write_paths: tuple[str, ...]


@dataclass(frozen=True)
class Binding:
    field: str
    value: str


@dataclass(frozen=True)
class Specialization:
    id: str
    parent_requirement_id: str
    parent_revision: str
    owner: str
    source: SourceRef
    bindings: tuple[Binding, ...]
    supported_parent_controls: tuple[Binding, ...]


@dataclass(frozen=True)
class DerivedRequirement:
    id: str
    owner: str
    source: SourceRef
    derived_from: tuple[str, ...]
    controls: tuple[Control, ...]


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    relation: RelationType
    target_id: str


@dataclass(frozen=True)
class ProjectManifest:
    project: str
    policy_sources: tuple[str, ...]
    specialization_ids: tuple[str, ...]
    exception_ids: tuple[str, ...]
    context_preserve: tuple[str, ...]


@dataclass(frozen=True)
class AgentBoundary:
    repositories: tuple[str, ...]
    writable: tuple[str, ...]
    read_only: tuple[str, ...]
    prohibited: tuple[str, ...]
    stop_conditions: tuple[str, ...]


@dataclass(frozen=True)
class ExceptionRecord:
    id: str
    requirement_id: str
    requirement_revision: str
    project: str
    feature_ids: tuple[str, ...]
    requester: str
    approver: str
    approval_record: str
    modification: Control
    rationale: str
    conditions: tuple[str, ...]
    expires_on: date
    status: str
    source: SourceRef


@dataclass(frozen=True)
class ApplicabilityDecision:
    requirement_id: str
    result: Applicability
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    code: str
    artifact: str
    message: str


@dataclass(frozen=True)
class ImpactItem:
    artifact_id: str
    artifact_type: str
    status: str
    reason: str


@dataclass(frozen=True)
class ImpactReport:
    requirement_id: str
    from_version: str
    to_version: str
    change_type: str
    affected_controls: tuple[str, ...]
    impacted: tuple[ImpactItem, ...]
    migration_required: bool


@dataclass(frozen=True)
class ResolutionReport:
    change_id: str
    candidates: tuple[Requirement, ...]
    decisions: tuple[ApplicabilityDecision, ...]
    applicable: tuple[Requirement, ...]
    specializations: tuple[Specialization, ...]
    exceptions: tuple[ExceptionRecord, ...]
    findings: tuple[Finding, ...]
    context_digest: str

    @property
    def gate(self) -> Gate:
        if any(item.severity is Severity.ERROR for item in self.findings):
            return Gate.STOP
        if any(item.severity is Severity.REVIEW for item in self.findings):
            return Gate.REVIEW
        if any(item.result is Applicability.UNCERTAIN for item in self.decisions):
            return Gate.STOP
        return Gate.READY


def _source(payload: Mapping[str, str]) -> SourceRef:
    return SourceRef(
        repository=payload["repository"],
        path=payload["path"],
        version=payload["version"],
        revision=payload["revision"],
    )


def _controls(payload: Mapping[str, str]) -> tuple[Control, ...]:
    return tuple(Control(field, str(value)) for field, value in sorted(payload.items()))


def _bindings(payload: Mapping[str, str]) -> tuple[Binding, ...]:
    return tuple(Binding(field, str(value)) for field, value in sorted(payload.items()))


def load_requirement(path: Path) -> Requirement:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Requirement(
        id=payload["id"],
        title=payload["title"],
        statement=payload["statement"],
        layer=Layer(payload["layer"]),
        meaning_owner=payload["meaning_owner"],
        status=ArtifactStatus(payload["status"]),
        effective_from=date.fromisoformat(payload["effective_from"]),
        source_domain=payload["source_domain"],
        source=_source(payload["source"]),
        scope=tuple(
            ScopeRule(item["field"], tuple(item["allowed_values"]))
            for item in payload.get("scope", [])
        ),
        fixed_controls=_controls(payload.get("fixed_controls", {})),
        delegated_controls=tuple(
            DelegatedControl(
                field,
                item["owner"],
                AgentAuthority(item["agent_authority"]),
            )
            for field, item in sorted(payload.get("delegated_controls", {}).items())
        ),
        enforcement=tuple(
            Enforcement(
                item["plane"],
                item["mechanism"],
                item["owner"],
                bool(item["automated"]),
            )
            for item in payload.get("enforcement", [])
        ),
        evidence_ids=tuple(payload.get("evidence_ids", [])),
        recommended_capabilities=tuple(payload.get("recommended_capabilities", [])),
        exception_owner=payload["exception_owner"],
    )


def load_change_context(path: Path) -> ChangeContext:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ChangeContext(
        id=payload["id"],
        evaluated_on=date.fromisoformat(payload["evaluated_on"]),
        facts=tuple(
            ContextFact(
                item["field"],
                tuple(item["values"]),
                tuple(item["evidence_ids"]),
            )
            for item in payload["facts"]
        ),
        requested_write_paths=tuple(payload["requested_write_paths"]),
    )


def load_specialization(path: Path) -> Specialization:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Specialization(
        id=payload["id"],
        parent_requirement_id=payload["parent_requirement_id"],
        parent_revision=payload["parent_revision"],
        owner=payload["owner"],
        source=_source(payload["source"]),
        bindings=_bindings(payload["bindings"]),
        supported_parent_controls=_bindings(payload["supported_parent_controls"]),
    )


def load_derived_requirement(path: Path) -> DerivedRequirement:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DerivedRequirement(
        id=payload["id"],
        owner=payload["owner"],
        source=_source(payload["source"]),
        derived_from=tuple(payload["derived_from"]),
        controls=_controls(payload["controls"]),
    )


def load_exception(path: Path) -> ExceptionRecord:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExceptionRecord(
        id=payload["id"],
        requirement_id=payload["requirement_id"],
        requirement_revision=payload["requirement_revision"],
        project=payload["scope"]["project"],
        feature_ids=tuple(payload["scope"]["feature_ids"]),
        requester=payload["requester"],
        approver=payload["approver"],
        approval_record=payload["approval_record"],
        modification=Control(**payload["modification"]),
        rationale=payload["rationale"],
        conditions=tuple(payload["conditions"]),
        expires_on=date.fromisoformat(payload["expires_on"]),
        status=payload["status"],
        source=_source(payload["source"]),
    )


def load_manifest(path: Path) -> ProjectManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ProjectManifest(
        project=payload["project"],
        policy_sources=tuple(payload["policy_sources"]),
        specialization_ids=tuple(payload["specialization_ids"]),
        exception_ids=tuple(payload["exception_ids"]),
        context_preserve=tuple(payload["context_preserve"]),
    )


def load_boundary(path: Path) -> AgentBoundary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AgentBoundary(
        repositories=tuple(payload["repositories"]),
        writable=tuple(payload["writable"]),
        read_only=tuple(payload["read_only"]),
        prohibited=tuple(payload["prohibited"]),
        stop_conditions=tuple(payload["stop_conditions"]),
    )


def load_graph(path: Path) -> tuple[GraphEdge, ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(
            GraphEdge(
                row["source_id"],
                RelationType(row["relation"]),
                row["target_id"],
            )
            for row in csv.DictReader(handle)
        )


def load_scenario(root: Path = SCENARIO_ROOT) -> dict[str, object]:
    requirements = tuple(
        load_requirement(path)
        for path in sorted((root / "catalog").glob("**/*.json"))
    )
    specializations = tuple(
        load_specialization(path)
        for path in sorted((root / "project" / "architecture").glob("*.json"))
        if "weakening" not in path.name
    )
    derived = tuple(
        load_derived_requirement(path)
        for path in sorted((root / "feature").glob("REQ-*.json"))
    )
    exceptions = tuple(
        load_exception(path)
        for path in sorted((root / "exceptions").glob("*.json"))
    )
    return {
        "change": load_change_context(root / "ticket" / "change-context.json"),
        "requirements": requirements,
        "specializations": specializations,
        "derived": derived,
        "exceptions": exceptions,
        "manifest": load_manifest(root / "project" / "policy-manifest.json"),
        "boundary": load_boundary(root / "project" / "agent-boundary.json"),
        "graph": load_graph(root / "reference" / "requirement-graph.csv"),
    }


def discover_candidates(
    requirements: Iterable[Requirement], manifest: ProjectManifest
) -> tuple[Requirement, ...]:
    sources = set(manifest.policy_sources)
    return tuple(item for item in requirements if item.source_domain in sources)


def validate_manifest(
    manifest: ProjectManifest,
    requirements: Iterable[Requirement],
    specializations: Iterable[Specialization],
    exceptions: Iterable[ExceptionRecord],
) -> list[Finding]:
    """Reject selections that cannot be resolved into the effective context."""
    findings: list[Finding] = []
    requirement_sources = {item.source_domain for item in requirements}
    specialization_ids = {item.id for item in specializations}
    exception_ids = {item.id for item in exceptions}
    for source in manifest.policy_sources:
        if source not in requirement_sources:
            findings.append(
                Finding(Severity.ERROR, "POLICY_SOURCE_EMPTY", source, "No requirement records were discovered for the selected source.")
            )
    for specialization_id in manifest.specialization_ids:
        if specialization_id not in specialization_ids:
            findings.append(
                Finding(Severity.ERROR, "SPECIALIZATION_SELECTION_MISSING", specialization_id, "The manifest selects an unavailable specialization.")
            )
    for exception_id in manifest.exception_ids:
        if exception_id not in exception_ids:
            findings.append(
                Finding(Severity.ERROR, "EXCEPTION_SELECTION_MISSING", exception_id, "The manifest selects an unavailable exception.")
            )
    required_context = {
        "requirement_id",
        "source_revision",
        "meaning_owner",
        "fixed_controls",
        "delegated_controls",
        "enforcement",
        "evidence_ids",
    }
    missing_context = sorted(required_context - set(manifest.context_preserve))
    if missing_context:
        findings.append(
            Finding(Severity.ERROR, "CONTEXT_PRESERVATION_INCOMPLETE", manifest.project, ", ".join(missing_context))
        )
    return findings


def evaluate_applicability(
    requirement: Requirement, change: ChangeContext
) -> ApplicabilityDecision:
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

    facts = {item.field: item for item in change.facts}
    reasons: list[str] = []
    evidence: set[str] = set()
    mismatch = False
    unknown = False
    for rule in requirement.scope:
        fact = facts.get(rule.field)
        if fact is None:
            unknown = True
            reasons.append(f"SCOPE_UNKNOWN_{rule.field.upper()}")
            continue
        evidence.update(fact.evidence_ids)
        if not set(fact.values) & set(rule.allowed_values):
            mismatch = True
            reasons.append(f"SCOPE_MISMATCH_{rule.field.upper()}")
    if mismatch:
        result = Applicability.NOT_APPLICABLE
    elif unknown:
        result = Applicability.UNCERTAIN
    else:
        result = Applicability.APPLICABLE
        reasons.append("SCOPE_MATCH" if requirement.scope else "GLOBAL_SCOPE")
    return ApplicabilityDecision(
        requirement.id,
        result,
        tuple(reasons),
        tuple(sorted(evidence)),
    )


def validate_catalog(requirements: Iterable[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    by_id: dict[str, list[Requirement]] = defaultdict(list)
    for item in requirements:
        by_id[item.id].append(item)
        if not item.meaning_owner:
            findings.append(
                Finding(Severity.ERROR, "REQUIREMENT_OWNER_MISSING", item.id, "No meaning owner.")
            )
        if not item.source.complete():
            findings.append(
                Finding(
                    Severity.ERROR,
                    "REQUIREMENT_SOURCE_INCOMPLETE",
                    item.id,
                    "Source locator is incomplete.",
                )
            )
    for requirement_id, records in by_id.items():
        if len(records) > 1:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "DUPLICATE_ACTIVE_REQUIREMENT_ID",
                    requirement_id,
                    "The active catalog contains competing records for one stable ID.",
                )
            )
    return findings


def validate_specialization(
    specialization: Specialization, parent: Requirement | None
) -> list[Finding]:
    if parent is None:
        return [
            Finding(
                Severity.ERROR,
                "UNKNOWN_PARENT_REQUIREMENT",
                specialization.id,
                specialization.parent_requirement_id,
            )
        ]
    findings: list[Finding] = []
    if parent.status is not ArtifactStatus.ACTIVE:
        findings.append(
            Finding(
                Severity.ERROR,
                "SPECIALIZATION_PARENT_INVALID",
                specialization.id,
                f"Parent status is {parent.status.value}.",
            )
        )
    if specialization.parent_revision != parent.source.revision:
        findings.append(
            Finding(
                Severity.REVIEW,
                "SPECIALIZATION_PARENT_STALE",
                specialization.id,
                "The specialization was reviewed against a different parent revision.",
            )
        )

    fixed = {item.field: item.expected for item in parent.fixed_controls}
    delegated = {item.field: item for item in parent.delegated_controls}
    for binding in specialization.bindings:
        if binding.field in fixed:
            if binding.value != fixed[binding.field]:
                findings.extend(
                    [
                        Finding(
                            Severity.ERROR,
                            "SPECIALIZATION_FIELD_NOT_DELEGATED",
                            specialization.id,
                            f"{binding.field} is fixed by {parent.id}.",
                        ),
                        Finding(
                            Severity.ERROR,
                            "SPECIALIZATION_WEAKENS_PARENT",
                            specialization.id,
                            f"{fixed[binding.field]} cannot become {binding.value}.",
                        ),
                    ]
                )
        elif binding.field in delegated:
            decision = delegated[binding.field]
            if specialization.owner != decision.owner:
                findings.append(
                    Finding(
                        Severity.ERROR,
                        "SPECIALIZATION_OWNER_UNAUTHORIZED",
                        specialization.id,
                        f"{binding.field} belongs to {decision.owner}.",
                    )
                )
        else:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "UNKNOWN_SPECIALIZATION_FIELD",
                    specialization.id,
                    binding.field,
                )
            )
    return findings


def validate_graph(edges: Iterable[GraphEdge], known_ids: set[str]) -> list[Finding]:
    edge_list = list(edges)
    findings: list[Finding] = []
    edge_keys = [(edge.source_id, edge.relation, edge.target_id) for edge in edge_list]
    if len(edge_keys) != len(set(edge_keys)):
        findings.append(
            Finding(Severity.ERROR, "REQUIREMENT_RELATION_DUPLICATE", "graph", "The graph contains a duplicate typed edge.")
        )
    for edge in edge_list:
        code = None
        if edge.source_id not in known_ids:
            code = (
                "DERIVATION_SOURCE_UNKNOWN"
                if edge.relation is RelationType.DERIVED_FROM
                else "REQUIREMENT_RELATION_SOURCE_UNKNOWN"
            )
            artifact = edge.source_id
        elif edge.target_id not in known_ids:
            code = (
                "UNKNOWN_PARENT_REQUIREMENT"
                if edge.relation is RelationType.SPECIALIZES
                else "REQUIREMENT_RELATION_TARGET_UNKNOWN"
            )
            artifact = edge.target_id
        else:
            artifact = edge.source_id
        if code:
            findings.append(Finding(Severity.ERROR, code, artifact, str(edge)))

    adjacency: dict[str, set[str]] = defaultdict(set)
    for edge in edge_list:
        if edge.relation is RelationType.SPECIALIZES:
            adjacency[edge.source_id].add(edge.target_id)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(parent) for parent in adjacency[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if any(visit(node) for node in tuple(adjacency)):
        findings.append(
            Finding(
                Severity.ERROR,
                "REQUIREMENT_RELATION_CYCLE",
                "graph",
                "Specialization relationships contain a cycle.",
            )
        )
    return findings


def validate_derived_requirement(
    item: DerivedRequirement, requirements: Mapping[str, Requirement]
) -> list[Finding]:
    findings: list[Finding] = []
    unknown = [source_id for source_id in item.derived_from if source_id not in requirements]
    if unknown:
        findings.append(Finding(Severity.ERROR, "DERIVATION_SOURCE_UNKNOWN", item.id, ", ".join(unknown)))
    if not item.derived_from:
        findings.append(Finding(Severity.REVIEW, "DERIVATION_SOURCE_MISSING", item.id, "Feature behavior is not linked to a governing requirement."))
    if not item.owner or not item.source.complete():
        findings.append(Finding(Severity.ERROR, "DERIVED_REQUIREMENT_PROVENANCE_INCOMPLETE", item.id, "Owner or source locator is incomplete."))
    return findings


def validate_enforcement(requirements: Iterable[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    for item in requirements:
        machine_controls = [control for control in item.enforcement if control.automated]
        if not machine_controls or not item.evidence_ids:
            findings.append(
                Finding(
                    Severity.REVIEW,
                    "CONTROL_DOCUMENTED_BUT_UNEVIDENCED",
                    item.id,
                    "No automated enforcement/evidence path establishes conformance.",
                )
            )
    return findings


def validate_agent_instruction(
    instruction_id: str,
    proposed_controls: Mapping[str, str],
    applicable: Iterable[Requirement],
) -> list[Finding]:
    fixed: dict[str, str] = {}
    for item in applicable:
        fixed.update({control.field: control.expected for control in item.fixed_controls})
    findings: list[Finding] = []
    for field, value in proposed_controls.items():
        if field in fixed and value != fixed[field]:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "AGENT_INSTRUCTION_EXCEEDS_AUTHORITY",
                    instruction_id,
                    f"Instruction proposes {field}={value}; governing value is {fixed[field]}.",
                )
            )
    return findings


def validate_exception(
    exception: ExceptionRecord,
    requirements: Mapping[str, Requirement],
    project: str | None = None,
    evaluated_on: date | None = None,
) -> list[Finding]:
    parent = requirements.get(exception.requirement_id)
    findings: list[Finding] = []
    if parent is None:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_REQUIREMENT_UNKNOWN",
                exception.id,
                exception.requirement_id,
            )
        )
        return findings
    if exception.requester == exception.approver:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_SELF_APPROVED",
                exception.id,
                "Requester and approver cannot be the same principal.",
            )
        )
    if exception.approver != parent.exception_owner:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_APPROVER_UNAUTHORIZED",
                exception.id,
                f"Expected {parent.exception_owner}.",
            )
        )
    if exception.requirement_revision != parent.source.revision:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_PARENT_STALE",
                exception.id,
                f"Bound to {exception.requirement_revision}; current revision is {parent.source.revision}.",
            )
        )
    if project is not None and exception.project != project:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_PROJECT_SCOPE_MISMATCH",
                exception.id,
                f"Exception names project {exception.project}, not {project}.",
            )
        )
    if not exception.feature_ids:
        findings.append(
            Finding(Severity.ERROR, "EXCEPTION_SCOPE_EMPTY", exception.id, "No feature scope is named.")
        )
    if exception.status != "active":
        findings.append(
            Finding(Severity.ERROR, "EXCEPTION_INACTIVE", exception.id, exception.status)
        )
    if evaluated_on is not None and exception.expires_on < evaluated_on:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_EXPIRED",
                exception.id,
                exception.expires_on.isoformat(),
            )
        )
    if not exception.approval_record or not exception.source.complete():
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_PROVENANCE_INCOMPLETE",
                exception.id,
                "Approval record or immutable source locator is incomplete.",
            )
        )
    parent_controls = {
        item.field: item.expected
        for item in (*parent.fixed_controls,)
    }
    if exception.modification.field not in parent_controls:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_CONTROL_UNKNOWN",
                exception.id,
                exception.modification.field,
            )
        )
    elif exception.modification.expected == parent_controls[exception.modification.field]:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_NO_DEVIATION",
                exception.id,
                "The exception does not modify the named base control.",
            )
        )
    if not exception.rationale or not exception.conditions:
        findings.append(
            Finding(
                Severity.ERROR,
                "EXCEPTION_SAFEGUARDS_INCOMPLETE",
                exception.id,
                "A bounded exception needs a rationale and compensating conditions.",
            )
        )
    return findings


def path_disposition(path: str, boundary: AgentBoundary) -> str:
    if any(fnmatch.fnmatch(path, pattern) for pattern in boundary.prohibited):
        return "prohibited"
    if any(fnmatch.fnmatch(path, pattern) for pattern in boundary.read_only):
        return "read_only"
    if any(fnmatch.fnmatch(path, pattern) for pattern in boundary.writable):
        return "writable"
    return "outside_scope"


def validate_write_paths(paths: Iterable[str], boundary: AgentBoundary) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        disposition = path_disposition(path, boundary)
        if disposition != "writable":
            findings.append(
                Finding(
                    Severity.ERROR,
                    "SCOPE_EXPANSION_REQUIRED",
                    path,
                    f"Path is {disposition}; request re-authorization before writing.",
                )
            )
    return findings


def create_scope_expansion_request(
    path: str, affected_requirements: Iterable[str]
) -> dict[str, object]:
    return {
        "id": "SCOPE-004",
        "blocked_task": "TASK-REN-03",
        "requested_change": path,
        "reason": "Review Service requires a reviewer-role mapping outside approved scope.",
        "affected_requirements": sorted(set(affected_requirements)),
        "required_reviewers": ["identity-platform", "product-security"],
        "status": "proposed_not_authorized",
    }


def copied_policy_drift(copy_path: Path, current: Requirement) -> Finding | None:
    payload = json.loads(copy_path.read_text(encoding="utf-8"))
    if payload["source_revision"] == current.source.revision:
        return None
    return Finding(
        Severity.REVIEW,
        "POLICY_SOURCE_STALE",
        str(copy_path),
        f"Copied {current.id} revision {payload['source_revision']} != {current.source.revision}.",
    )


def possible_policy_duplication(text: str, source_ids: Iterable[str]) -> Finding | None:
    lowered = text.lower()
    resembles_policy = "human review" in lowered and "required" in lowered
    retains_source = any(source_id in text for source_id in source_ids)
    if resembles_policy and not retains_source:
        return Finding(
            Severity.REVIEW,
            "POSSIBLE_POLICY_DUPLICATION",
            "local-copy",
            "Heuristic similarity is not proof; review missing source traceability.",
        )
    return None


def analyze_impact(
    old: Requirement,
    new: Requirement,
    edges: Iterable[GraphEdge],
    artifact_types: Mapping[str, str],
    specialization: Specialization,
) -> ImpactReport:
    old_controls = {item.field: item.expected for item in old.fixed_controls}
    new_controls = {item.field: item.expected for item in new.fixed_controls}
    affected_controls = tuple(
        sorted(
            field
            for field, value in new_controls.items()
            if old_controls.get(field) != value
        )
    )
    reverse: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        reverse[edge.target_id].add(edge.source_id)
    impacted_ids: list[str] = []
    queue: deque[str] = deque([old.id])
    seen = {old.id}
    while queue:
        parent = queue.popleft()
        for child in sorted(reverse[parent]):
            if child not in seen:
                seen.add(child)
                impacted_ids.append(child)
                queue.append(child)

    support = {
        item.field: item.value for item in specialization.supported_parent_controls
    }
    impacted: list[ImpactItem] = []
    for artifact_id in impacted_ids:
        status = "requires_review"
        reason = f"Depends on changed {old.id} controls: {', '.join(affected_controls)}"
        if artifact_id == specialization.id:
            missing = [field for field in affected_controls if support.get(field) != "supported"]
            uncertain = [field for field in affected_controls if support.get(field) == "unknown"]
            details = []
            if missing:
                details.append("missing=" + ",".join(missing))
            if uncertain:
                details.append("uncertain=" + ",".join(uncertain))
            reason = "; ".join(details) or "specialization remains compatible"
            status = "requires_review" if details else "compatible"
        impacted.append(
            ImpactItem(
                artifact_id,
                artifact_types.get(artifact_id, "unknown"),
                status,
                reason,
            )
        )
    return ImpactReport(
        requirement_id=old.id,
        from_version=old.source.version,
        to_version=new.source.version,
        change_type="obligation_changed",
        affected_controls=affected_controls,
        impacted=tuple(impacted),
        migration_required=bool(affected_controls),
    )


def percentage(covered: int, total: int) -> float | None:
    return round(100 * covered / total, 1) if total else None


def evaluation_metrics(
    report: ResolutionReport,
    manifest: ProjectManifest,
    graph: Iterable[GraphEdge],
) -> dict[str, object]:
    applicable_ids = {item.id for item in report.applicable}
    owned = sum(bool(item.meaning_owner) for item in report.applicable)
    enforceable = len(report.applicable)
    enforced = sum(
        bool(item.evidence_ids and any(control.automated for control in item.enforcement))
        for item in report.applicable
    )
    graph_edges = tuple(graph)
    linked = sum(
        any(
            edge.source_id == item.id
            and edge.target_id == item.parent_requirement_id
            and edge.relation is RelationType.SPECIALIZES
            for edge in graph_edges
        )
        for item in report.specializations
    )
    fresh = sum(
        item.parent_revision
        == next(
            parent.source.revision
            for parent in report.candidates
            if parent.id == item.parent_requirement_id
        )
        for item in report.specializations
        if item.parent_requirement_id in {parent.id for parent in report.candidates}
    )
    invalid_exception_ids = {
        item.artifact
        for item in report.findings
        if item.code.startswith("EXCEPTION_")
    }
    valid_exceptions = sum(
        item.id not in invalid_exception_ids for item in report.exceptions
    )
    return {
        "applicable_requirements": len(applicable_ids),
        "ownership_completeness": {
            "covered": owned,
            "total": len(applicable_ids),
            "percent": percentage(owned, len(applicable_ids)),
        },
        "specialization_traceability": {
            "covered": linked,
            "total": len(report.specializations),
            "percent": percentage(linked, len(report.specializations)),
        },
        "machine_enforcement_coverage": {
            "covered": enforced,
            "total": enforceable,
            "percent": percentage(enforced, enforceable),
        },
        "policy_freshness": {
            "covered": fresh,
            "total": len(manifest.specialization_ids),
            "percent": percentage(fresh, len(manifest.specialization_ids)),
        },
        "valid_exception_coverage": {
            "covered": valid_exceptions,
            "total": len(report.exceptions),
            "percent": percentage(valid_exceptions, len(report.exceptions)),
        },
    }


def impact_recall(
    predicted_ids: Iterable[str], gold_ids: Iterable[str]
) -> dict[str, object]:
    predicted = set(predicted_ids)
    gold = set(gold_ids)
    true_positive = len(predicted & gold)
    return {
        "true_positive": true_positive,
        "predicted_total": len(predicted),
        "gold_total": len(gold),
        "recall_percent": percentage(true_positive, len(gold)),
        "missed_ids": tuple(sorted(gold - predicted)),
        "extra_ids": tuple(sorted(predicted - gold)),
    }


def location_accuracy(
    predicted: Mapping[str, str], labelled: Mapping[str, str]
) -> dict[str, object]:
    correct = sum(predicted.get(item_id) == layer for item_id, layer in labelled.items())
    return {
        "correct": correct,
        "total": len(labelled),
        "percent": percentage(correct, len(labelled)),
    }


def agent_behavior_metrics(events: Iterable[Mapping[str, str]]) -> dict[str, object]:
    """Count operational signals without collapsing them into a governance score."""
    recognized = (
        "scope_expansion_request",
        "unauthorized_path_attempt",
        "policy_conflict",
        "clarification_request",
        "late_requirement_discovery",
        "agent_proposed_adr",
        "agent_proposed_exception",
        "tool_retry",
        "review_rework",
        "human_correction",
    )
    counts = {name: 0 for name in recognized}
    unknown = 0
    for event in events:
        event_type = event.get("type", "")
        if event_type in counts:
            counts[event_type] += 1
        else:
            unknown += 1
    return {
        "event_total": sum(counts.values()) + unknown,
        "by_type": counts,
        "unknown_event_types": unknown,
        "interpretation": (
            "Counts are signals, not scores: clarification and scope-expansion "
            "events may indicate effective bounded autonomy."
        ),
    }


def runtime_control_effectiveness(evidence: Mapping[str, object]) -> dict[str, object]:
    """Evaluate one observed window without overstating what telemetry proves."""
    consequential = int(evidence["consequential_recommendations"])
    receipts = int(evidence["review_receipts"])
    authorized = int(evidence["authorized_review_receipts"])
    bypasses = int(evidence["legacy_endpoint_bypasses"])
    if min(consequential, receipts, authorized, bypasses) < 0:
        raise ValueError("runtime counts cannot be negative")
    if receipts > consequential or authorized > receipts:
        raise ValueError("runtime counts violate their denominators")
    effective = receipts == consequential and authorized == receipts and bypasses == 0
    return {
        "observed_window": evidence["observed_window"],
        "review_receipt_coverage": {
            "covered": receipts,
            "total": consequential,
            "percent": percentage(receipts, consequential),
        },
        "authorized_reviewer_coverage": {
            "covered": authorized,
            "total": receipts,
            "percent": percentage(authorized, receipts),
        },
        "legacy_endpoint_bypasses": bypasses,
        "status": "effective_in_observed_window" if effective else "control_gap_detected",
        "limitations": (
            "Telemetry does not prove review quality, complete instrumentation, "
            "or the authenticity of the evidence producer."
        ),
    }


def _context_material(
    applicable: Iterable[Requirement],
    specializations: Iterable[Specialization],
    exceptions: Iterable[ExceptionRecord],
) -> str:
    payload = {
        "resolver_version": RESOLVER_VERSION,
        "requirements": [
            [item.id, item.source.revision] for item in sorted(applicable, key=lambda x: x.id)
        ],
        "specializations": [
            [item.id, item.source.revision]
            for item in sorted(specializations, key=lambda x: x.id)
        ],
        "exceptions": [
            [
                item.id,
                item.source.revision,
                item.requirement_revision,
                item.expires_on.isoformat(),
            ]
            for item in sorted(exceptions, key=lambda x: x.id)
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def resolve_project(root: Path = SCENARIO_ROOT) -> ResolutionReport:
    scenario = load_scenario(root)
    change = scenario["change"]
    requirements = scenario["requirements"]
    specializations = scenario["specializations"]
    derived = scenario["derived"]
    exceptions = scenario["exceptions"]
    manifest = scenario["manifest"]
    boundary = scenario["boundary"]
    graph = scenario["graph"]
    assert isinstance(change, ChangeContext)
    assert isinstance(manifest, ProjectManifest)
    assert isinstance(boundary, AgentBoundary)
    requirements = tuple(requirements)
    specializations = tuple(specializations)
    derived = tuple(derived)
    exceptions = tuple(exceptions)
    graph = tuple(graph)

    candidates = discover_candidates(requirements, manifest)
    decisions = tuple(evaluate_applicability(item, change) for item in candidates)
    applicable_ids = {
        item.requirement_id
        for item in decisions
        if item.result is Applicability.APPLICABLE
    }
    applicable = tuple(item for item in candidates if item.id in applicable_ids)
    by_id = {item.id: item for item in candidates}
    findings = validate_catalog(candidates)
    findings.extend(validate_manifest(manifest, requirements, specializations, exceptions))

    selected_specializations = tuple(
        item for item in specializations if item.id in manifest.specialization_ids
    )
    selected_exceptions = tuple(
        item for item in exceptions if item.id in manifest.exception_ids
    )
    for item in selected_specializations:
        findings.extend(validate_specialization(item, by_id.get(item.parent_requirement_id)))
    for item in derived:
        findings.extend(validate_derived_requirement(item, by_id))
    for item in selected_exceptions:
        findings.extend(
            validate_exception(item, by_id, manifest.project, change.evaluated_on)
        )

    known_ids = set(by_id)
    known_ids.update(item.id for item in selected_specializations)
    known_ids.update(item.id for item in derived)
    known_ids.update(item.id for item in selected_exceptions)
    known_ids.update(
        {
            "ReviewServiceAdapter",
            "GatewayAdapter",
            "TEST-REVIEW-004",
            "EVAL-RENEWAL-002",
            "SEC-AUTH-011",
            "GATEWAY-TELEMETRY-007",
        }
    )
    findings.extend(validate_graph(graph, known_ids))
    findings.extend(validate_enforcement(applicable))
    findings.extend(validate_write_paths(change.requested_write_paths, boundary))

    context_material = _context_material(
        applicable,
        selected_specializations,
        selected_exceptions,
    )
    digest = hashlib.sha256(context_material.encode("utf-8")).hexdigest()
    return ResolutionReport(
        change.id,
        candidates,
        decisions,
        applicable,
        selected_specializations,
        selected_exceptions,
        tuple(findings),
        digest,
    )


def compose_agent_context(report: ResolutionReport) -> str:
    if report.gate is not Gate.READY:
        raise ValueError(f"cannot compose context while gate is {report.gate.value}")
    specialization_by_parent = {
        item.parent_requirement_id: item for item in report.specializations
    }
    lines = [
        "# GENERATED EFFECTIVE CONTEXT — DO NOT EDIT",
        f"# resolver = {RESOLVER_VERSION}",
        f"# change = {report.change_id}",
        f"# context_digest = sha256:{report.context_digest}",
        "# source metadata is structurally validated, not authenticated in this lab.",
    ]
    for requirement in sorted(report.applicable, key=lambda item: item.id):
        lines.append(
            f"[{requirement.id} | {requirement.layer.value} | {requirement.source.locator()}]"
        )
        lines.append(f"meaning_owner = {requirement.meaning_owner}")
        for control in requirement.fixed_controls:
            lines.append(f"fixed.{control.field} = {control.expected}")
        for delegated in requirement.delegated_controls:
            lines.append(
                "delegated."
                f"{delegated.field} = owner:{delegated.owner}; "
                f"agent:{delegated.agent_authority.value}"
            )
        specialization = specialization_by_parent.get(requirement.id)
        if specialization:
            lines.append(f"specialization = {specialization.id}")
            for binding in specialization.bindings:
                lines.append(f"binding.{binding.field} = {binding.value}")
        for enforcement in requirement.enforcement:
            lines.append(
                f"enforcement.{enforcement.plane} = {enforcement.mechanism} "
                f"(owner:{enforcement.owner})"
            )
        if requirement.evidence_ids:
            lines.append("evidence = " + ", ".join(requirement.evidence_ids))
    if report.exceptions:
        lines.append("# authorized exceptions")
        for exception in sorted(report.exceptions, key=lambda item: item.id):
            lines.append(
                f"exception = {exception.id}; requirement:{exception.requirement_id}; "
                f"revision:{exception.requirement_revision}; "
                f"modify:{exception.modification.field}={exception.modification.expected}; "
                f"expires:{exception.expires_on.isoformat()}"
            )
            for condition in exception.conditions:
                lines.append(f"exception_condition = {condition}")
    return "\n".join(lines) + "\n"


def release_context(report: ResolutionReport) -> dict[str, object]:
    return {
        "release": "underwriter-assistant:3.2.0-training",
        "change": report.change_id,
        "resolver": {"version": RESOLVER_VERSION},
        "governing_requirements": [
            {
                "id": item.id,
                "revision": item.source.revision,
                "disposition": (
                    "specialized"
                    if any(
                        spec.parent_requirement_id == item.id
                        for spec in report.specializations
                    )
                    else "inherited"
                ),
            }
            for item in sorted(report.applicable, key=lambda value: value.id)
        ],
        "specializations": [item.id for item in report.specializations],
        "exceptions": [
            {
                "id": item.id,
                "requirement_id": item.requirement_id,
                "requirement_revision": item.requirement_revision,
                "modification": asdict(item.modification),
                "conditions": list(item.conditions),
                "expires_on": item.expires_on.isoformat(),
            }
            for item in report.exceptions
        ],
        "evidence": sorted(
            {
                evidence_id
                for item in report.applicable
                for evidence_id in item.evidence_ids
            }
        ),
        "context_digest": f"sha256:{report.context_digest}",
        "gate": report.gate.value,
        "limitations": [
            "Fixture revisions, identities, and approvals are not authenticated.",
            "Release evidence does not prove runtime control effectiveness.",
        ],
    }


def _jsonable(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def run_demo(output: Path | None = None) -> None:
    scenario = load_scenario()
    report = resolve_project()
    manifest = scenario["manifest"]
    graph = scenario["graph"]
    assert isinstance(manifest, ProjectManifest)
    metrics = evaluation_metrics(report, manifest, tuple(graph))
    print("Course 04 — Company vs Project vs Feature Requirements")
    print(f"Change: {report.change_id}")
    print(f"Candidates: {len(report.candidates)}")
    for result in Applicability:
        count = sum(item.result is result for item in report.decisions)
        print(f"  {result.value:16} {count}")
    print(f"Findings: {len(report.findings)}")
    print(f"Gate: {report.gate.value.upper()}")
    print(json.dumps(metrics, indent=2))
    if report.gate is Gate.READY:
        print("\n" + compose_agent_context(report))

    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        payload = {
            "report": _jsonable(asdict(report)),
            "metrics": metrics,
            "release_context": release_context(report),
        }
        (output / "course04-evidence.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Evidence written to {output / 'course04-evidence.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run_demo(args.output)


if __name__ == "__main__":
    main()
