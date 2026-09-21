"""Deterministic Course 06 lab for executable requirement representations.

The model-facing object is a proposal. Trusted code owns validation, status,
authorization, transitions, and the simulated in-memory mutation boundary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

LESSON_ROOT = Path(__file__).resolve().parent
SCENARIO_ROOT = LESSON_ROOT / "northstar-broker-response"
REFERENCE_ROOT = SCENARIO_ROOT / "reference"
CONTRACT_PATH = REFERENCE_ROOT / "behavior-contract.json"
TABLE_PATH = REFERENCE_ROOT / "decision-table.json"
SCENARIOS_PATH = REFERENCE_ROOT / "scenarios.json"
STATE_MACHINE_PATH = REFERENCE_ROOT / "state-machine.json"
TRACEABILITY_PATH = REFERENCE_ROOT / "traceability.csv"
FIELD_RULES_PATH = SCENARIO_ROOT / "sources" / "field-rules.json"
EVALUATION_PATH = SCENARIO_ROOT / "evaluation-cases.json"


class Severity(str, Enum):
    INFO = "info"
    REVIEW = "review"
    STOP = "stop"


class Outcome(str, Enum):
    PROCEED = "proceed"
    BLOCK = "block"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


class ProposalStatus(str, Enum):
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    CONFLICTING = "conflicting"
    MAPPING_AMBIGUOUS = "mapping_ambiguous"
    SOURCE_CONFLICT = "source_conflict"
    ATTACHMENT_REVIEW_REQUIRED = "attachment_review_required"
    UNMAPPED = "unmapped"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    STALE = "stale"


class Disposition(str, Enum):
    AUTO_APPLY_ELIGIBLE = "auto_apply_eligible"
    PROPOSE = "propose"
    NO_CHANGE = "no_change"
    CONFLICT = "conflict"
    REJECT = "reject"
    CLARIFY = "clarify"
    BLOCK = "block"


class ChangeKind(str, Enum):
    EDITORIAL = "editorial"
    CLARIFICATION = "clarification"
    OBLIGATION_ADDED = "obligation_added"
    OBLIGATION_REMOVED = "obligation_removed"
    CONDITION_CHANGED = "condition_changed"
    THRESHOLD_CHANGED = "threshold_changed"
    SCOPE_CHANGED = "scope_changed"
    FAILURE_BEHAVIOR_CHANGED = "failure_behavior_changed"
    AUTHORITY_CHANGED = "authority_changed"


@dataclass(frozen=True)
class Finding:
    code: str
    subject_id: str
    message: str
    severity: Severity = Severity.STOP
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Ratio:
    numerator: int
    denominator: int

    @property
    def value(self) -> float | None:
        return self.numerator / self.denominator if self.denominator else None


@dataclass(frozen=True)
class ClassificationMetrics:
    correct: int
    total: int
    unsafe_auto_apply: int

    @property
    def accuracy(self) -> float | None:
        return self.correct / self.total if self.total else None


@dataclass(frozen=True)
class SourceEvidence:
    evidence_id: str
    response_id: str
    source_span: str


@dataclass(frozen=True)
class ModelProposal:
    proposal_id: str
    submission_id: str
    submission_revision: str
    requirement_context_digest: str
    field_candidates: tuple[str, ...]
    proposed_value: Any
    source_response_id: str
    evidence: tuple[SourceEvidence, ...]
    requirement_id: str
    model_version: str
    candidate_values: tuple[Any, ...] = ()
    attachment_only: bool = False
    model_status: str = "extracted"


@dataclass(frozen=True)
class ExistingField:
    value: Any
    verified: bool


@dataclass(frozen=True)
class DecisionContext:
    current_submission_revision: str
    current_requirement_context_digest: str
    broker_authorized: bool
    response_authenticated: bool
    outstanding_fields: frozenset[str]
    supported_fields: frozenset[str]
    automatic_acceptance_fields: frozenset[str]
    existing_fields: dict[str, ExistingField]
    processed_response_ids: frozenset[str] = frozenset()
    response_sequence: int = 1
    latest_applied_sequence: int = 0


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    status: ProposalStatus
    disposition: Disposition
    reason_codes: tuple[str, ...]
    matched_rule_id: str | None = None


@dataclass(frozen=True)
class ProposedUpdate:
    proposal_id: str
    submission_id: str
    submission_revision: str
    requirement_context_digest: str
    field: str
    proposed_value: Any
    source_response_id: str
    source_span: str
    requirement_id: str
    model_version: str
    evidence_ids: tuple[str, ...]
    status: ProposalStatus


@dataclass(frozen=True)
class ApprovalReceipt:
    reviewer_id: str
    decision: str
    rationale: str
    proposal_digest: str
    submission_id: str
    submission_revision: str
    requirement_context_digest: str
    issued_at: str
    expires_at: str
    consumed: bool = False


@dataclass(frozen=True)
class CapabilityReadiness:
    capability: str
    declared_status: str
    implementation_ready: bool
    requirement_ids: tuple[str, ...]
    blocking_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


VAGUE_TERMS = re.compile(
    r"\b(?:quickly|appropriately|efficiently|securely|normally|usually|reasonable|adequate|simple|significant)\b",
    re.IGNORECASE,
)
AMBIGUOUS_PRONOUN = re.compile(r"\b(?:it|they|them|this|that)\b", re.IGNORECASE)
UNIVERSAL_QUANTIFIER = re.compile(r"\b(?:all|every|never)\b", re.IGNORECASE)
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract() -> dict[str, Any]:
    return load_json(CONTRACT_PATH)


def load_table() -> dict[str, Any]:
    return load_json(TABLE_PATH)


def load_scenarios() -> dict[str, Any]:
    return load_json(SCENARIOS_PATH)


def load_state_machine() -> dict[str, Any]:
    return load_json(STATE_MACHINE_PATH)


def load_field_rules() -> dict[str, Any]:
    return load_json(FIELD_RULES_PATH)


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def writing_findings(requirement: dict[str, Any]) -> tuple[Finding, ...]:
    """Diagnostic writing lint; findings do not adjudicate domain meaning."""
    identifier = str(requirement.get("id", "unknown"))
    statement = str(requirement.get("statement", ""))
    findings: list[Finding] = []
    if "and/or" in statement.lower():
        findings.append(Finding("AND_OR_AMBIGUOUS", identifier, "Replace and/or with explicit conditions."))
    if re.search(r"\betc\.?\b", statement, re.IGNORECASE):
        findings.append(Finding("OPEN_ENDED_LIST", identifier, "Replace etc. with an explicit list."))
    vague = VAGUE_TERMS.search(statement)
    if vague:
        findings.append(
            Finding(
                "UNDEFINED_MODIFIER",
                identifier,
                f"Term {vague.group(0)!r} needs an owned definition or measurable meaning.",
                Severity.REVIEW,
            )
        )
    if requirement.get("check_pronouns"):
        pronoun = AMBIGUOUS_PRONOUN.search(statement)
        if pronoun:
            findings.append(
                Finding(
                    "AMBIGUOUS_REFERENT",
                    identifier,
                    f"Pronoun {pronoun.group(0)!r} needs an explicit referent.",
                    Severity.REVIEW,
                )
            )
    quantifier = UNIVERSAL_QUANTIFIER.search(statement)
    if quantifier and not requirement.get("population"):
        findings.append(
            Finding(
                "UNBOUNDED_QUANTIFIER",
                identifier,
                f"Quantifier {quantifier.group(0)!r} needs an explicit population.",
                Severity.REVIEW,
            )
        )
    return tuple(findings)


def requirement_findings(contract: dict[str, Any]) -> tuple[Finding, ...]:
    required = {
        "id",
        "revision",
        "status",
        "role",
        "ears_pattern",
        "capability",
        "owner",
        "source_ids",
        "statement",
        "actor",
        "trigger",
        "inputs",
        "preconditions",
        "behavior",
        "prohibited",
        "postconditions",
        "frame_conditions",
        "failure_behavior",
        "evidence_ids",
    }
    source_ids = {item.get("id") for item in contract.get("sources", [])}
    capability_ids = {item.get("id") for item in contract.get("capabilities", [])}
    findings: list[Finding] = []
    requirements = contract.get("requirements", [])
    for duplicate in sorted(_duplicates(str(item.get("id")) for item in requirements)):
        findings.append(Finding("DUPLICATE_REQUIREMENT_ID", duplicate, "Requirement IDs must be unique."))
    for requirement in requirements:
        identifier = str(requirement.get("id", "unknown"))
        missing = sorted(field for field in required if not requirement.get(field))
        if missing:
            findings.append(
                Finding("REQUIREMENT_NOT_READY", identifier, f"Missing readiness fields: {', '.join(missing)}.")
            )
        unknown_sources = sorted(set(requirement.get("source_ids", [])) - source_ids)
        if unknown_sources:
            findings.append(
                Finding(
                    "UNKNOWN_REQUIREMENT_SOURCE",
                    identifier,
                    "Requirement cites an unknown source.",
                    evidence_ids=tuple(unknown_sources),
                )
            )
        if requirement.get("capability") not in capability_ids:
            findings.append(Finding("UNKNOWN_CAPABILITY", identifier, "Capability is not declared."))
        if requirement.get("role") != "normative_requirement":
            findings.append(Finding("REQUIREMENT_ROLE_INVALID", identifier, "Requirement role must be normative."))
        findings.extend(writing_findings(requirement))
    return tuple(findings)


def _row_matches(row: dict[str, Any], facts: dict[str, Any]) -> bool:
    for key in (
        "existing_value",
        "existing_verified",
        "proposed_valid",
        "same_value",
        "auto_accept_allowed",
    ):
        if row.get(key) != "any" and row.get(key) != facts.get(key):
            return False
    return True


def decision_table_outcome(
    facts: dict[str, Any], table: dict[str, Any] | None = None
) -> tuple[str | None, str | None]:
    table = table or load_table()
    matches = [row for row in table.get("rows", []) if _row_matches(row, facts)]
    if len(matches) != 1:
        return None, None
    return str(matches[0]["outcome"]), str(matches[0]["id"])


def artifact_consistency_findings(
    contract: dict[str, Any] | None = None,
    table: dict[str, Any] | None = None,
    scenarios: dict[str, Any] | None = None,
    state_machine: dict[str, Any] | None = None,
) -> tuple[Finding, ...]:
    contract = contract or load_contract()
    table = table or load_table()
    scenarios = scenarios or load_scenarios()
    state_machine = state_machine or load_state_machine()
    findings: list[Finding] = []
    requirements = {item["id"]: item for item in contract.get("requirements", [])}
    state_requirements = {item["id"]: item for item in contract.get("state_requirements", [])}
    known_normative_ids = set(requirements) | {
        str(item.get("id")) for item in contract.get("invariants", [])
    } | {str(item.get("id")) for item in contract.get("state_requirements", [])}
    if table.get("role") != "normative_elaboration" or table.get("status") != "approved":
        findings.append(Finding("TABLE_ROLE_INVALID", str(table.get("id")), "Normative table role is invalid."))
    for identifier in table.get("governs", []):
        requirement = requirements.get(identifier)
        if not requirement or table.get("id") not in requirement.get("elaboration_ids", []):
            findings.append(
                Finding(
                    "NORMATIVE_ELABORATION_UNLINKED",
                    str(table.get("id")),
                    "Binding elaboration must be explicitly referenced by its requirement.",
                )
            )
    for artifact in contract.get("contracts", []):
        artifact_id = str(artifact.get("id"))
        if artifact.get("role") != "normative_elaboration":
            findings.append(
                Finding("CONTRACT_ROLE_INVALID", artifact_id, "Contract role must be normative elaboration.")
            )
        for identifier in artifact.get("governs", []):
            requirement = requirements.get(identifier)
            if not requirement or artifact_id not in requirement.get("elaboration_ids", []):
                findings.append(
                    Finding(
                        "NORMATIVE_ELABORATION_UNLINKED",
                        artifact_id,
                        "Binding contract must be explicitly referenced by its requirement.",
                        evidence_ids=(str(identifier),),
                    )
                )
    if state_machine.get("role") != "normative_elaboration":
        findings.append(
            Finding(
                "STATE_MACHINE_ROLE_INVALID",
                str(state_machine.get("id")),
                "State-machine role must be normative elaboration.",
            )
        )
    for identifier in state_machine.get("governs", []):
        requirement = state_requirements.get(identifier)
        if not requirement or state_machine.get("id") not in requirement.get("elaboration_ids", []):
            findings.append(
                Finding(
                    "NORMATIVE_ELABORATION_UNLINKED",
                    str(state_machine.get("id")),
                    "Binding state machine must be explicitly referenced by its state requirement.",
                    evidence_ids=(str(identifier),),
                )
            )
    conflict_facts = {
        "existing_value": "present",
        "existing_verified": True,
        "proposed_valid": True,
        "same_value": False,
        "auto_accept_allowed": True,
    }
    outcome, row_id = decision_table_outcome(conflict_facts, table)
    expected = requirements.get("REQ-BR-005", {}).get("semantic_contract", {}).get(
        "verified_conflict_outcome"
    )
    if outcome != expected:
        findings.append(
            Finding(
                "NORMATIVE_ARTIFACT_CONFLICT",
                str(table.get("id")),
                f"Verified-conflict row {row_id!r} says {outcome!r}; requirement says {expected!r}.",
                evidence_ids=("REQ-BR-005", str(row_id)),
            )
        )
    for scenario in scenarios.get("scenarios", []):
        role = scenario.get("role")
        if role not in {"normative_example", "informative"}:
            findings.append(Finding("SCENARIO_ROLE_INVALID", str(scenario.get("id")), "Scenario role is unknown."))
        unknown = sorted(set(scenario.get("requirement_ids", [])) - known_normative_ids)
        if unknown:
            findings.append(
                Finding(
                    "SCENARIO_REQUIREMENT_UNKNOWN",
                    str(scenario.get("id")),
                    "Scenario cites unknown requirements.",
                    evidence_ids=tuple(unknown),
                )
            )
        if role == "normative_example" and set(table.get("governs", [])) & set(
            scenario.get("requirement_ids", [])
        ):
            scenario_outcome = scenario.get("then", {}).get("outcome")
            table_outcome, _ = decision_table_outcome(scenario.get("given", {}), table)
            if scenario_outcome != table_outcome:
                findings.append(
                    Finding(
                        "SCENARIO_CONTRADICTS_REQUIREMENT",
                        str(scenario.get("id")),
                        f"Scenario expects {scenario_outcome!r}; normative table yields {table_outcome!r}.",
                        evidence_ids=(str(table.get("id")),),
                    )
                )
    forbidden = {
        ("extracted", "apply", "applied"),
        ("conflicting", "apply", "applied"),
        ("rejected", "apply", "applied"),
        ("stale", "apply", "applied"),
    }
    declared = {
        (item.get("current"), item.get("event"), item.get("next"))
        for item in state_machine.get("transitions", [])
    }
    for current, event, next_state in sorted(forbidden & declared):
        findings.append(
            Finding(
                "INVALID_STATE_TRANSITION_DECLARED",
                str(state_machine.get("id")),
                f"Forbidden transition {current} --{event}--> {next_state} is declared valid.",
            )
        )
    return tuple(findings)


def domain_value_valid(field: str, value: Any, rules: dict[str, Any] | None = None) -> bool:
    rules = rules or load_field_rules()
    rule = rules.get("fields", {}).get(field)
    if not rule:
        return False
    expected_type = rule.get("type")
    if expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        return int(rule.get("minimum", value)) <= value <= int(rule.get("maximum", value))
    if expected_type == "string":
        return isinstance(value, str) and value in rule.get("enum", [])
    return False


def validate_model_proposal(proposal: ModelProposal) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    required_strings = {
        "proposal_id": proposal.proposal_id,
        "submission_id": proposal.submission_id,
        "submission_revision": proposal.submission_revision,
        "source_response_id": proposal.source_response_id,
        "requirement_id": proposal.requirement_id,
        "model_version": proposal.model_version,
    }
    for field, value in required_strings.items():
        if not value.strip():
            findings.append(Finding("PROPOSAL_FIELD_EMPTY", proposal.proposal_id, f"{field} is empty."))
    if not DIGEST.fullmatch(proposal.requirement_context_digest):
        findings.append(Finding("CONTEXT_DIGEST_INVALID", proposal.proposal_id, "Context digest is invalid."))
    if not proposal.attachment_only and not proposal.evidence:
        findings.append(Finding("SOURCE_EVIDENCE_MISSING", proposal.proposal_id, "Source evidence is required."))
    for evidence in proposal.evidence:
        if evidence.response_id != proposal.source_response_id or not evidence.source_span.strip():
            findings.append(
                Finding(
                    "SOURCE_EVIDENCE_INVALID",
                    proposal.proposal_id,
                    "Evidence must bind a non-empty span to the proposal response.",
                    evidence_ids=(evidence.evidence_id,),
                )
            )
    return tuple(findings)


def classify_proposal(
    proposal: ModelProposal,
    context: DecisionContext,
    table: dict[str, Any] | None = None,
    field_rules: dict[str, Any] | None = None,
) -> Decision:
    """Recompute application-owned status; never trust proposal.model_status."""
    structural = validate_model_proposal(proposal)
    if structural:
        return Decision(Outcome.BLOCK, ProposalStatus.EXTRACTED, Disposition.BLOCK, tuple(item.code for item in structural))
    if not context.response_authenticated or not context.broker_authorized:
        return Decision(Outcome.BLOCK, ProposalStatus.EXTRACTED, Disposition.BLOCK, ("BROKER_NOT_AUTHORIZED",))
    if proposal.source_response_id in context.processed_response_ids:
        return Decision(Outcome.BLOCK, ProposalStatus.EXTRACTED, Disposition.BLOCK, ("DUPLICATE_RESPONSE",))
    if context.response_sequence <= context.latest_applied_sequence:
        return Decision(Outcome.BLOCK, ProposalStatus.STALE, Disposition.BLOCK, ("OUT_OF_ORDER_RESPONSE",))
    if (
        proposal.submission_revision != context.current_submission_revision
        or proposal.requirement_context_digest != context.current_requirement_context_digest
    ):
        return Decision(Outcome.BLOCK, ProposalStatus.STALE, Disposition.BLOCK, ("PROPOSAL_CONTEXT_STALE",))
    if proposal.attachment_only:
        return Decision(
            Outcome.CLARIFY,
            ProposalStatus.ATTACHMENT_REVIEW_REQUIRED,
            Disposition.CLARIFY,
            ("ATTACHMENT_UNSUPPORTED",),
        )
    unique_values = {json.dumps(item, sort_keys=True) for item in proposal.candidate_values}
    if len(unique_values) > 1:
        return Decision(Outcome.ESCALATE, ProposalStatus.SOURCE_CONFLICT, Disposition.CONFLICT, ("SOURCE_VALUES_CONFLICT",))
    if not proposal.field_candidates:
        return Decision(Outcome.CLARIFY, ProposalStatus.UNMAPPED, Disposition.CLARIFY, ("FIELD_UNMAPPED",))
    if len(set(proposal.field_candidates)) > 1:
        return Decision(
            Outcome.CLARIFY,
            ProposalStatus.MAPPING_AMBIGUOUS,
            Disposition.CLARIFY,
            ("FIELD_MAPPING_AMBIGUOUS",),
        )
    field = proposal.field_candidates[0]
    if field not in context.supported_fields or field not in context.outstanding_fields:
        return Decision(Outcome.CLARIFY, ProposalStatus.UNMAPPED, Disposition.CLARIFY, ("FIELD_NOT_APPLICABLE",))
    valid = domain_value_valid(field, proposal.proposed_value, field_rules)
    existing = context.existing_fields.get(field)
    facts = {
        "existing_value": "present" if existing else "none",
        "existing_verified": existing.verified if existing else "any",
        "proposed_valid": valid,
        "same_value": existing.value == proposal.proposed_value if existing else "any",
        "auto_accept_allowed": field in context.automatic_acceptance_fields,
    }
    disposition_value, rule_id = decision_table_outcome(facts, table)
    if disposition_value is None:
        return Decision(Outcome.ESCALATE, ProposalStatus.EXTRACTED, Disposition.BLOCK, ("DECISION_TABLE_NONDETERMINISTIC",))
    disposition = Disposition(disposition_value)
    mapping = {
        Disposition.AUTO_APPLY_ELIGIBLE: (Outcome.PROCEED, ProposalStatus.VALIDATED),
        Disposition.PROPOSE: (Outcome.PROCEED, ProposalStatus.AWAITING_REVIEW),
        Disposition.NO_CHANGE: (Outcome.PROCEED, ProposalStatus.VALIDATED),
        Disposition.CONFLICT: (Outcome.ESCALATE, ProposalStatus.CONFLICTING),
        Disposition.REJECT: (Outcome.BLOCK, ProposalStatus.REJECTED),
    }
    outcome, status = mapping[disposition]
    return Decision(outcome, status, disposition, (f"TABLE_RULE_{rule_id}",), rule_id)


def materialize_update(
    proposal: ModelProposal, decision: Decision
) -> ProposedUpdate | None:
    if len(proposal.field_candidates) != 1 or not proposal.evidence:
        return None
    return ProposedUpdate(
        proposal.proposal_id,
        proposal.submission_id,
        proposal.submission_revision,
        proposal.requirement_context_digest,
        proposal.field_candidates[0],
        proposal.proposed_value,
        proposal.source_response_id,
        proposal.evidence[0].source_span,
        proposal.requirement_id,
        proposal.model_version,
        tuple(item.evidence_id for item in proposal.evidence),
        decision.status,
    )


def proposal_digest(proposal: ProposedUpdate) -> str:
    canonical = json.dumps(asdict(proposal), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_receipt(
    proposal: ProposedUpdate,
    receipt: ApprovalReceipt | None,
    *,
    now: datetime | None = None,
) -> tuple[str, ...]:
    if receipt is None:
        return ("APPROVAL_MISSING",)
    reasons: list[str] = []
    if receipt.decision != "approved":
        reasons.append("APPROVAL_DENIED")
    if not receipt.rationale.strip():
        reasons.append("APPROVAL_RATIONALE_MISSING")
    if receipt.consumed:
        reasons.append("APPROVAL_ALREADY_USED")
    if receipt.proposal_digest != proposal_digest(proposal):
        reasons.append("PROPOSAL_CHANGED_AFTER_APPROVAL")
    if receipt.submission_id != proposal.submission_id:
        reasons.append("APPROVAL_SUBMISSION_MISMATCH")
    if receipt.submission_revision != proposal.submission_revision:
        reasons.append("APPROVAL_SUBMISSION_STALE")
    if receipt.requirement_context_digest != proposal.requirement_context_digest:
        reasons.append("APPROVAL_REQUIREMENT_CONTEXT_STALE")
    try:
        issued_at = _parse_time(receipt.issued_at)
        expires_at = _parse_time(receipt.expires_at)
        if issued_at.tzinfo is None or expires_at.tzinfo is None:
            raise ValueError("timezone required")
    except ValueError:
        reasons.append("APPROVAL_TIME_INVALID")
    else:
        current = now or datetime.now(timezone.utc)
        if issued_at > current:
            reasons.append("APPROVAL_NOT_YET_VALID")
        if expires_at <= issued_at:
            reasons.append("APPROVAL_WINDOW_INVALID")
        if expires_at <= current:
            reasons.append("APPROVAL_EXPIRED")
    return tuple(reasons)


def transition_status(
    current: ProposalStatus,
    event: str,
    guard: str,
    state_machine: dict[str, Any] | None = None,
) -> ProposalStatus | None:
    state_machine = state_machine or load_state_machine()
    matches = [
        item
        for item in state_machine.get("transitions", [])
        if item.get("current") == current.value
        and item.get("event") == event
        and item.get("guard") in {guard, "always"}
    ]
    if len(matches) != 1:
        return None
    return ProposalStatus(matches[0]["next"])


def authorize_application(
    proposal: ProposedUpdate,
    context: DecisionContext,
    receipt: ApprovalReceipt | None = None,
    *,
    now: datetime | None = None,
) -> Decision:
    reasons: list[str] = []
    if not context.response_authenticated or not context.broker_authorized:
        reasons.append("BROKER_NOT_AUTHORIZED")
    if proposal.source_response_id in context.processed_response_ids:
        reasons.append("DUPLICATE_RESPONSE")
    if context.response_sequence <= context.latest_applied_sequence:
        reasons.append("OUT_OF_ORDER_RESPONSE")
    if proposal.submission_revision != context.current_submission_revision:
        reasons.append("PROPOSAL_SUBMISSION_STALE")
    if proposal.requirement_context_digest != context.current_requirement_context_digest:
        reasons.append("PROPOSAL_REQUIREMENT_CONTEXT_STALE")
    forbidden = {
        ProposalStatus.EXTRACTED,
        ProposalStatus.CONFLICTING,
        ProposalStatus.MAPPING_AMBIGUOUS,
        ProposalStatus.SOURCE_CONFLICT,
        ProposalStatus.ATTACHMENT_REVIEW_REQUIRED,
        ProposalStatus.UNMAPPED,
        ProposalStatus.AWAITING_REVIEW,
        ProposalStatus.REJECTED,
        ProposalStatus.APPLIED,
        ProposalStatus.STALE,
    }
    if proposal.status in forbidden:
        reasons.append("STATE_NOT_APPLICABLE")
    if proposal.status == ProposalStatus.VALIDATED and proposal.field not in context.automatic_acceptance_fields:
        reasons.append("AUTOMATIC_ACCEPTANCE_NOT_AUTHORIZED")
    if proposal.status == ProposalStatus.APPROVED:
        reasons.extend(validate_receipt(proposal, receipt, now=now))
    if reasons:
        return Decision(Outcome.BLOCK, proposal.status, Disposition.BLOCK, tuple(dict.fromkeys(reasons)))
    return Decision(Outcome.PROCEED, ProposalStatus.APPLIED, Disposition.AUTO_APPLY_ELIGIBLE, ())


def apply_in_memory(
    submission: dict[str, Any],
    proposal: ProposedUpdate,
    authorization: Decision,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Return a copy and changed fields; this is not a production mutation service."""
    if authorization.outcome != Outcome.PROCEED or authorization.status != ProposalStatus.APPLIED:
        return dict(submission), ()
    updated = dict(submission)
    updated[proposal.field] = proposal.proposed_value
    changed = tuple(sorted(key for key in set(submission) | set(updated) if submission.get(key) != updated.get(key)))
    return updated, changed


def capability_readiness(
    contract: dict[str, Any] | None = None,
    consistency: tuple[Finding, ...] | None = None,
) -> tuple[CapabilityReadiness, ...]:
    contract = contract or load_contract()
    all_findings = requirement_findings(contract) + (
        consistency if consistency is not None else artifact_consistency_findings(contract=contract)
    )
    requirements = {item["id"]: item for item in contract.get("requirements", [])}
    results: list[CapabilityReadiness] = []
    for capability in contract.get("capabilities", []):
        identifier = str(capability.get("id"))
        requirement_ids = tuple(str(item) for item in capability.get("requirement_ids", []))
        blockers = {
            finding.subject_id
            for finding in all_findings
            if finding.severity == Severity.STOP
            and (
                finding.subject_id in requirement_ids
                or finding.code in {"NORMATIVE_ARTIFACT_CONFLICT", "INVALID_STATE_TRANSITION_DECLARED"}
            )
        }
        questions = {
            str(item.get("id"))
            for item in contract.get("questions", [])
            if item.get("status") == "open" and identifier in item.get("blocks_capabilities", [])
        }
        declared = str(capability.get("status"))
        reasons = set()
        if blockers:
            reasons.add("BLOCKING_SPEC_FINDING")
        if questions:
            reasons.add("OPEN_BLOCKING_QUESTION")
        if declared == "review_required":
            reasons.add("REVIEW_REQUIRED")
        if declared == "prohibited":
            reasons.add("CAPABILITY_PROHIBITED")
        results.append(
            CapabilityReadiness(
                identifier,
                declared,
                declared == "ready" and not blockers and not questions,
                requirement_ids,
                tuple(sorted(blockers | questions)),
                tuple(sorted(reasons)),
            )
        )
    return tuple(results)


def requirement_change(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed_fields = tuple(sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key)))
    kinds: set[ChangeKind] = set()
    if not changed_fields:
        kinds.add(ChangeKind.EDITORIAL)
    if "owner" in changed_fields or "source_ids" in changed_fields:
        kinds.add(ChangeKind.AUTHORITY_CHANGED)
    if "scope" in changed_fields or "population" in changed_fields:
        kinds.add(ChangeKind.SCOPE_CHANGED)
    if "preconditions" in changed_fields or "trigger" in changed_fields:
        kinds.add(ChangeKind.CONDITION_CHANGED)
    if "failure_behavior" in changed_fields:
        kinds.add(ChangeKind.FAILURE_BEHAVIOR_CHANGED)
    before_fields = set(before.get("required_fields", []))
    after_fields = set(after.get("required_fields", []))
    if after_fields - before_fields:
        kinds.add(ChangeKind.OBLIGATION_ADDED)
    if before_fields - after_fields:
        kinds.add(ChangeKind.OBLIGATION_REMOVED)
    if "threshold" in changed_fields:
        kinds.add(ChangeKind.THRESHOLD_CHANGED)
    if changed_fields and not kinds:
        kinds.add(ChangeKind.CLARIFICATION)
    return {
        "artifact_id": str(after.get("id") or before.get("id")),
        "changed_fields": changed_fields,
        "change_kinds": tuple(sorted(item.value for item in kinds)),
        "added_obligations": tuple(sorted(after_fields - before_fields)),
        "removed_obligations": tuple(sorted(before_fields - after_fields)),
    }


def impact_analysis(
    source_id: str,
    path: Path = TRACEABILITY_PATH,
) -> dict[str, tuple[str, ...]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    direct = {row["target_id"] for row in rows if row["source_id"] == source_id}
    visited = set(direct)
    frontier = set(direct)
    while frontier:
        next_frontier = {
            row["target_id"]
            for row in rows
            if row["source_id"] in frontier and row["target_id"] not in visited
        }
        visited.update(next_frontier)
        frontier = next_frontier
    return {"direct": tuple(sorted(direct)), "transitive": tuple(sorted(visited - direct))}


def specification_coverage(
    table: dict[str, Any] | None = None,
    scenarios: dict[str, Any] | None = None,
    state_machine: dict[str, Any] | None = None,
) -> dict[str, Ratio]:
    table = table or load_table()
    scenarios = scenarios or load_scenarios()
    state_machine = state_machine or load_state_machine()
    covered_rows: set[str] = set()
    for scenario in scenarios.get("scenarios", []):
        if scenario.get("role") != "normative_example":
            continue
        _, row_id = decision_table_outcome(scenario.get("given", {}), table)
        if row_id:
            covered_rows.add(row_id)
    critical_invalid = state_machine.get("critical_invalid_transitions", [])
    return {
        "decision_table_rows": Ratio(len(covered_rows), len(table.get("rows", []))),
        "critical_invalid_transitions_declared": Ratio(len(critical_invalid), len(critical_invalid)),
    }


def _case_objects(case: dict[str, Any]) -> tuple[ModelProposal, DecisionContext]:
    digest = "sha256:" + "a" * 64
    evidence = (SourceEvidence(f"EV-{case['id']}", f"MSG-{case['id']}", "synthetic span"),)
    proposal = ModelProposal(
        f"PROP-{case['id']}",
        "SUB-42",
        "S17" if case.get("current_revision", True) else "S16",
        digest,
        tuple(case.get("field_candidates", [])),
        case.get("proposed_value"),
        f"MSG-{case['id']}",
        evidence,
        "UW-018",
        "offline-fixture-v1",
        tuple(case.get("candidate_values", [])),
        bool(case.get("attachment_only", False)),
        str(case.get("model_status", "extracted")),
    )
    field = proposal.field_candidates[0] if len(proposal.field_candidates) == 1 else None
    existing = (
        {field: ExistingField(case.get("existing_value"), bool(case.get("existing_verified")))}
        if field and case.get("existing_value") is not None
        else {}
    )
    auto_fields = frozenset({field}) if field and case.get("auto_accept_allowed") else frozenset()
    context = DecisionContext(
        "S17",
        digest,
        True,
        True,
        frozenset({"construction_year", "occupancy", "building_value"}),
        frozenset({"construction_year", "occupancy", "building_value"}),
        auto_fields,
        existing,
    )
    return proposal, context


def evaluate_cases(path: Path = EVALUATION_PATH) -> dict[str, Any]:
    payload = load_json(path)
    cases = payload["cases"]
    governed_correct = baseline_correct = unsafe_baseline = unsafe_governed = 0
    records = []
    for case in cases:
        proposal, context = _case_objects(case)
        governed = classify_proposal(proposal, context)
        baseline_status = str(case.get("model_status"))
        governed_correct += (
            governed.status.value == case["expected_status"]
            and governed.disposition.value == case["expected_disposition"]
        )
        baseline_correct += baseline_status == case["expected_status"]
        unsafe_expected = case["expected_disposition"] in {"conflict", "block", "clarify", "reject"}
        unsafe_baseline += unsafe_expected and baseline_status in {"validated", "approved", "applied"}
        unsafe_governed += unsafe_expected and governed.disposition == Disposition.AUTO_APPLY_ELIGIBLE
        records.append(
            {
                "case_id": case["id"],
                "expected_status": case["expected_status"],
                "baseline_status": baseline_status,
                "governed_status": governed.status.value,
                "governed_disposition": governed.disposition.value,
            }
        )
    baseline = ClassificationMetrics(baseline_correct, len(cases), int(unsafe_baseline))
    governed = ClassificationMetrics(int(governed_correct), len(cases), int(unsafe_governed))
    return {
        "dataset_id": payload["dataset_id"],
        "population": len(cases),
        "baseline": {**asdict(baseline), "accuracy": baseline.accuracy},
        "governed": {**asdict(governed), "accuracy": governed.accuracy},
        "records": records,
        "limitations": payload["limitations"],
    }


def conflict_property(years: Iterable[int] = range(1990, 2005)) -> dict[str, int]:
    checked = violations = 0
    table = load_table()
    for existing in years:
        for proposed in years:
            if existing == proposed:
                continue
            checked += 1
            outcome, _ = decision_table_outcome(
                {
                    "existing_value": "present",
                    "existing_verified": True,
                    "proposed_valid": True,
                    "same_value": False,
                    "auto_accept_allowed": True,
                },
                table,
            )
            violations += outcome != "conflict"
    return {"checked_pairs": checked, "violations": violations}


def mutated_table() -> dict[str, Any]:
    table = load_table()
    changed = json.loads(json.dumps(table))
    for row in changed["rows"]:
        if row["id"] == "DT-07":
            row["outcome"] = "auto_apply_eligible"
    return changed


def run_demo() -> dict[str, Any]:
    contract = load_contract()
    consistency = artifact_consistency_findings(contract=contract)
    return {
        "requirement_findings": [asdict(item) for item in requirement_findings(contract)],
        "consistency_findings": [asdict(item) for item in consistency],
        "capability_readiness": [asdict(item) for item in capability_readiness(contract, consistency)],
        "evaluation": evaluate_cases(),
        "property_check": conflict_property(),
        "coverage": {key: asdict(value) | {"value": value.value} for key, value in specification_coverage().items()},
        "limitations": [
            "The extractor inputs and labels are synthetic; no model or external service is evaluated.",
            "A clean structured consistency check cannot prove natural-language meaning or owner authority.",
            "The mutation boundary is an in-memory teaching fixture, not a production transaction.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(run_demo(), indent=2, default=lambda value: value.value))


if __name__ == "__main__":
    main()
