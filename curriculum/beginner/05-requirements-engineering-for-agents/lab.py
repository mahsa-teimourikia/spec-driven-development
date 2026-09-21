"""Deterministic Course 05 lab for evidence-backed requirements engineering.

Model-facing artifacts are proposals. Trusted application code owns validation,
readiness, approval checks, and any simulated execution decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

LESSON_ROOT = Path(__file__).resolve().parent
SCENARIO_ROOT = LESSON_ROOT / "northstar-broker-follow-up"
REFERENCE_PATH = SCENARIO_ROOT / "reference" / "requirements-package.json"
DRAFT_PATH = SCENARIO_ROOT / "workshop" / "starter" / "requirements-package.json"
EVALUATION_PATH = SCENARIO_ROOT / "evaluation-cases.json"


class Severity(str, Enum):
    REVIEW = "review"
    STOP = "stop"


class Outcome(str, Enum):
    PROCEED = "proceed"
    ABSTAIN = "abstain"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


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

    def __getitem__(self, key: str) -> int | float | None:
        if key not in {"numerator", "denominator", "value"}:
            raise KeyError(key)
        return getattr(self, key)


@dataclass(frozen=True)
class ClassificationMetrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def precision(self) -> float | None:
        denominator = self.true_positive + self.false_positive
        return self.true_positive / denominator if denominator else None

    @property
    def recall(self) -> float | None:
        denominator = self.true_positive + self.false_negative
        return self.true_positive / denominator if denominator else None


@dataclass(frozen=True)
class CapabilityStatus:
    capability: str
    ready: bool
    blocking_question_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class MissingItem:
    id: str
    requirement_id: str
    label: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class Draft:
    broker_id: str
    subject: str
    body: str
    missing_item_ids: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalReceipt:
    reviewer_id: str
    decision: str
    rationale: str
    draft_digest: str
    broker_id: str
    submission_id: str
    submission_revision: str
    requirements_revision: str
    issued_at: str
    expires_at: str
    consumed: bool = False


@dataclass(frozen=True)
class SendContext:
    submission_id: str
    submission_revision: str
    requirements_revision: str
    broker_id: str
    broker_authorized: bool
    send_policy_enabled: bool
    logical_operation_id: str
    prior_delivery_state: str = "none"


@dataclass(frozen=True)
class Decision:
    outcome: Outcome
    reason_codes: tuple[str, ...]


VAGUE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\baccurate\b",
        r"\bquick(?:ly)?\b",
        r"\bprofessional\b",
        r"\ball\b",
        r"\bevery\b",
        r"\bsimple\b",
    )
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_package(path: Path = REFERENCE_PATH) -> dict[str, Any]:
    return load_json(path)


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def structural_findings(package: dict[str, Any]) -> tuple[Finding, ...]:
    """Check the package contract without pretending structure proves meaning."""
    findings: list[Finding] = []
    required_sections = {
        "specification",
        "problem",
        "scope",
        "glossary",
        "sources",
        "capabilities",
        "requirements",
        "invariants",
        "questions",
        "failure_matrix",
        "tasks",
        "agent_authority",
    }
    for section in sorted(required_sections - package.keys()):
        findings.append(Finding("SECTION_MISSING", section, f"Required section {section!r} is absent."))
    if findings:
        return tuple(findings)

    specification = package.get("specification", {})
    for field in ("id", "revision", "status", "owner"):
        if not specification.get(field) or specification.get(field) == "TODO":
            findings.append(
                Finding("SPEC_FIELD_INCOMPLETE", field, f"Specification field {field!r} is incomplete.")
            )

    collections = ("sources", "capabilities", "requirements", "invariants", "questions", "tasks")
    for collection in collections:
        values = package.get(collection)
        if not isinstance(values, list) or not values:
            findings.append(
                Finding("COLLECTION_EMPTY", collection, f"{collection!r} must be a non-empty list.")
            )
            continue
        identifiers = [str(item.get("id", "")) for item in values if isinstance(item, dict)]
        for duplicate in sorted(_duplicates(identifiers)):
            findings.append(
                Finding("DUPLICATE_ID", duplicate, f"ID {duplicate!r} is duplicated in {collection}.")
            )
    return tuple(findings)


def lexical_findings(requirement: dict[str, Any]) -> tuple[Finding, ...]:
    statement = str(requirement.get("statement", ""))
    subject = str(requirement.get("id", "unknown"))
    findings = []
    for pattern in VAGUE_PATTERNS:
        match = pattern.search(statement)
        if match:
            findings.append(
                Finding(
                    "VAGUE_TERM",
                    subject,
                    f"Review vague term {match.group(0)!r}; a lexical flag is not proof of a defect.",
                    Severity.REVIEW,
                )
            )
    return tuple(findings)


def requirement_quality_findings(package: dict[str, Any]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    source_ids = {source.get("id") for source in package.get("sources", [])}
    capability_ids = {capability.get("id") for capability in package.get("capabilities", [])}
    for requirement in package.get("requirements", []):
        identifier = str(requirement.get("id", "unknown"))
        missing = [
            field
            for field in (
                "revision",
                "capability",
                "normative_strength",
                "priority",
                "status",
                "owner",
                "statement",
                "preconditions",
                "behavior",
                "postconditions",
                "evidence",
            )
            if not requirement.get(field) or requirement.get(field) == "TODO"
        ]
        if missing:
            findings.append(
                Finding(
                    "REQUIREMENT_INCOMPLETE",
                    identifier,
                    f"Missing or incomplete fields: {', '.join(missing)}.",
                )
            )
        unknown_sources = sorted(set(requirement.get("source_ids", [])) - source_ids)
        if not requirement.get("source_ids"):
            findings.append(
                Finding("REQUIREMENT_UNSUPPORTED", identifier, "No evidence source supports the requirement.")
            )
        elif unknown_sources:
            findings.append(
                Finding(
                    "SOURCE_REFERENCE_UNKNOWN",
                    identifier,
                    "Requirement cites unknown sources.",
                    evidence_ids=tuple(unknown_sources),
                )
            )
        if requirement.get("capability") not in capability_ids:
            findings.append(
                Finding(
                    "CAPABILITY_REFERENCE_UNKNOWN",
                    identifier,
                    "Requirement refers to an undeclared capability.",
                )
            )
        findings.extend(lexical_findings(requirement))
    return tuple(findings)


def capability_readiness(package: dict[str, Any]) -> tuple[CapabilityStatus, ...]:
    """Block only capabilities affected by open questions or incomplete requirements."""
    blocked_by_quality: dict[str, set[str]] = {}
    requirements = {item.get("id"): item for item in package.get("requirements", [])}
    for finding in requirement_quality_findings(package):
        requirement = requirements.get(finding.subject_id)
        if requirement and finding.severity == Severity.STOP:
            blocked_by_quality.setdefault(str(requirement.get("capability")), set()).add(finding.code)

    results = []
    for capability in package.get("capabilities", []):
        identifier = str(capability.get("id"))
        open_questions = sorted(
            str(question.get("id"))
            for question in package.get("questions", [])
            if question.get("status") == "open" and identifier in question.get("blocks_capabilities", [])
        )
        reasons = set(blocked_by_quality.get(identifier, set()))
        if open_questions:
            reasons.add("OPEN_BLOCKING_QUESTION")
        if int(capability.get("autonomy_level", 0)) == 0 and identifier == "send_message":
            reasons.add("CAPABILITY_DISABLED")
        results.append(
            CapabilityStatus(identifier, not reasons, tuple(open_questions), tuple(sorted(reasons)))
        )
    return tuple(results)


def validate_missing_items(
    items: Iterable[MissingItem],
    current_requirement_ids: set[str],
    observed_evidence_ids: set[str] | None = None,
) -> tuple[Finding, ...]:
    items = tuple(items)
    observed_evidence_ids = observed_evidence_ids or {
        evidence_id for item in items for evidence_id in item.evidence_ids
    }
    findings: list[Finding] = []
    for item in items:
        if item.requirement_id not in current_requirement_ids:
            findings.append(
                Finding(
                    "UNSUPPORTED_MISSING_ITEM",
                    item.id,
                    "MissingItem does not trace to a current underwriting requirement.",
                    evidence_ids=(item.requirement_id,),
                )
            )
        if not item.evidence_ids or not set(item.evidence_ids).issubset(observed_evidence_ids):
            findings.append(
                Finding(
                    "MISSING_ITEM_EVIDENCE_INVALID",
                    item.id,
                    "MissingItem lacks observed evidence from the current submission revision.",
                    evidence_ids=item.evidence_ids,
                )
            )
    return tuple(findings)


def correspondence_metrics(plan_ids: Iterable[str], draft_ids: Iterable[str]) -> dict[str, Ratio]:
    plan = set(plan_ids)
    draft = set(draft_ids)
    return {
        "precision": Ratio(len(plan & draft), len(draft)),
        "recall": Ratio(len(plan & draft), len(plan)),
    }


def validate_draft(plan: Iterable[MissingItem], draft: Draft) -> tuple[Finding, ...]:
    plan_ids = {item.id for item in plan}
    draft_ids = set(draft.missing_item_ids)
    findings = []
    additions = tuple(sorted(draft_ids - plan_ids))
    omissions = tuple(sorted(plan_ids - draft_ids))
    if additions:
        findings.append(
            Finding("DRAFT_UNSUPPORTED_ADDITION", "draft", "Draft adds unsupported items.", evidence_ids=additions)
        )
    if omissions:
        findings.append(
            Finding("DRAFT_OMISSION", "draft", "Draft omits validated items.", evidence_ids=omissions)
        )
    if not draft.subject.strip() or not draft.body.strip():
        findings.append(Finding("DRAFT_CONTENT_EMPTY", "draft", "Draft subject and body are required."))
    return tuple(findings)


def draft_digest(draft: Draft) -> str:
    canonical = json.dumps(asdict(draft), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def authorize_send(
    draft: Draft,
    receipt: ApprovalReceipt | None,
    context: SendContext,
    *,
    now: datetime | None = None,
) -> Decision:
    """Simulate the trusted pre-effect gate; no external action is performed."""
    reasons: list[str] = []
    if not context.send_policy_enabled:
        reasons.append("SEND_POLICY_DISABLED")
    if not context.broker_authorized or context.broker_id != draft.broker_id:
        reasons.append("BROKER_NOT_AUTHORIZED")
    if context.prior_delivery_state in {"delivered", "unknown"}:
        reasons.append(
            "DUPLICATE_OPERATION" if context.prior_delivery_state == "delivered" else "DELIVERY_OUTCOME_UNKNOWN"
        )
    if not context.logical_operation_id:
        reasons.append("OPERATION_ID_MISSING")
    if receipt is None:
        reasons.append("APPROVAL_MISSING")
    else:
        current_time = now or datetime.now(timezone.utc)
        if receipt.decision != "approved":
            reasons.append("APPROVAL_DENIED")
        if not receipt.rationale.strip():
            reasons.append("APPROVAL_RATIONALE_MISSING")
        if receipt.consumed:
            reasons.append("APPROVAL_ALREADY_USED")
        if receipt.draft_digest != draft_digest(draft):
            reasons.append("DRAFT_CHANGED_AFTER_APPROVAL")
        if receipt.broker_id != context.broker_id:
            reasons.append("APPROVAL_BROKER_MISMATCH")
        if receipt.submission_id != context.submission_id:
            reasons.append("APPROVAL_SUBMISSION_MISMATCH")
        if receipt.submission_revision != context.submission_revision:
            reasons.append("SUBMISSION_CONTEXT_STALE")
        if receipt.requirements_revision != context.requirements_revision:
            reasons.append("REQUIREMENTS_CONTEXT_STALE")
        if _parse_time(receipt.expires_at) <= current_time:
            reasons.append("APPROVAL_EXPIRED")
    if reasons:
        escalate = {
            "SEND_POLICY_DISABLED",
            "BROKER_NOT_AUTHORIZED",
            "DELIVERY_OUTCOME_UNKNOWN",
            "APPROVAL_DENIED",
        }
        outcome = Outcome.ESCALATE if escalate.intersection(reasons) else Outcome.ABSTAIN
        return Decision(outcome, tuple(dict.fromkeys(reasons)))
    return Decision(Outcome.PROCEED, ())


def failure_decision(
    package_or_category: dict[str, Any] | str,
    category_or_attempts: str | int = 0,
    attempts_or_matrix: int | list[dict[str, Any]] | None = None,
    *,
    attempts: int | None = None,
) -> Decision:
    if isinstance(package_or_category, dict):
        package = package_or_category
        category = str(category_or_attempts)
        attempt_count = attempts if attempts is not None else int(attempts_or_matrix or 0)
    else:
        category = package_or_category
        attempt_count = attempts if attempts is not None else int(category_or_attempts)
        package = {"failure_matrix": attempts_or_matrix or []}
    rows = {item.get("category"): item for item in package.get("failure_matrix", [])}
    row = rows.get(category)
    if row is None:
        return Decision(Outcome.ESCALATE, ("FAILURE_CATEGORY_UNKNOWN",))
    retryable = bool(row.get("retryable")) and attempt_count < int(row.get("max_attempts", 0))
    if retryable:
        return Decision(Outcome.PROCEED, ("BOUNDED_RETRY_ALLOWED",))
    return Decision(Outcome(str(row.get("terminal_outcome"))), (str(row.get("reason_code")),))


def traceability_findings(package: dict[str, Any]) -> tuple[Finding, ...]:
    approved = {
        str(requirement.get("id"))
        for requirement in package.get("requirements", [])
        if requirement.get("status") == "approved"
    }
    task_links = {
        str(requirement_id)
        for task in package.get("tasks", [])
        for requirement_id in task.get("requirement_ids", [])
    }
    findings: list[Finding] = []
    for task in package.get("tasks", []):
        if not task.get("requirement_ids"):
            findings.append(Finding("ORPHAN_TASK", str(task.get("id")), "Task has no requirement link."))
    for identifier in sorted(approved - task_links):
        findings.append(
            Finding("UNIMPLEMENTED_REQUIREMENT", identifier, "Approved requirement has no task link.")
        )
    known = {str(item.get("id")) for item in package.get("requirements", [])}
    for identifier in sorted(task_links - known):
        findings.append(Finding("TASK_LINK_UNKNOWN", identifier, "Task cites an unknown requirement."))
    return tuple(findings)


def semantic_requirement_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Report changed obligation fields; this is impact evidence, not a migration decision."""
    fields = (
        "statement",
        "preconditions",
        "behavior",
        "postconditions",
        "source_ids",
        "status",
        "owner",
    )
    changes = [field for field in fields if before.get(field) != after.get(field)]
    return {"requirement_id": (str(after.get("id") or before.get("id")),), "changed_fields": tuple(changes)}


def spec_context_findings(
    package_or_task: dict[str, Any], pinned_revision_or_package: str | dict[str, Any]
) -> tuple[Finding, ...]:
    if isinstance(pinned_revision_or_package, dict):
        pinned_revision = str(package_or_task.get("specification_revision", ""))
        package = pinned_revision_or_package
    else:
        package = package_or_task
        pinned_revision = pinned_revision_or_package
    current = str(package.get("specification", {}).get("revision", ""))
    if current != pinned_revision:
        return (
            Finding(
                "SPEC_CONTEXT_STALE",
                str(package.get("specification", {}).get("id", "specification")),
                f"Execution pinned {pinned_revision!r}, but current revision is {current!r}.",
                Severity.REVIEW,
            ),
        )
    return ()


def keyword_baseline(case: dict[str, Any]) -> bool:
    return any(pattern.search(str(case.get("statement", ""))) for pattern in VAGUE_PATTERNS)


def baseline_ticket_findings(ticket: str) -> tuple[Finding, ...]:
    findings = []
    for pattern in VAGUE_PATTERNS:
        match = pattern.search(ticket)
        if match:
            findings.append(
                Finding(
                    "VAGUE_TERM",
                    "AI-2176",
                    f"Ticket term {match.group(0)!r} needs accountable clarification.",
                    Severity.REVIEW,
                )
            )
    if re.search(r"automatically send", ticket, re.IGNORECASE):
        findings.append(
            Finding(
                "UNBOUNDED_EXTERNAL_EFFECT",
                "AI-2176",
                "Automatic delivery lacks a declared authority and execution boundary.",
            )
        )
    return tuple(findings)


def evidence_aware_detector(case: dict[str, Any]) -> bool:
    return (
        keyword_baseline(case)
        or not case.get("source_supported", False)
        or not case.get("owner_present", False)
        or not case.get("observable", False)
    )


def classification_metrics(cases: list[dict[str, Any]], predictions: Iterable[bool]) -> ClassificationMetrics:
    predicted = list(predictions)
    if len(predicted) != len(cases):
        raise ValueError("predictions must match the labelled population")
    true_positive = false_positive = true_negative = false_negative = 0
    for case, prediction in zip(cases, predicted, strict=True):
        expected = bool(case.get("expected_finding"))
        true_positive += prediction and expected
        false_positive += prediction and not expected
        true_negative += not prediction and not expected
        false_negative += not prediction and expected
    return ClassificationMetrics(true_positive, false_positive, true_negative, false_negative)


def evaluate_cases(path: Path = EVALUATION_PATH) -> dict[str, Any]:
    cases = load_json(path)["cases"]
    baseline = classification_metrics(cases, (keyword_baseline(case) for case in cases))
    evidence_aware = classification_metrics(cases, (evidence_aware_detector(case) for case in cases))

    def report(metrics: ClassificationMetrics) -> dict[str, Any]:
        return {**asdict(metrics), "precision": metrics.precision, "recall": metrics.recall}

    return {
        "population": len(cases),
        "labelled_findings": sum(bool(case["expected_finding"]) for case in cases),
        "keyword_baseline": report(baseline),
        "evidence_aware": report(evidence_aware),
        "limitations": [
            "Eight synthetic labelled cases are regression evidence, not a benchmark.",
            "Rules cannot establish stakeholder truth, feasibility, or production quality.",
        ],
    }


def package_findings(package: dict[str, Any]) -> tuple[Finding, ...]:
    structural = structural_findings(package)
    if structural:
        return structural
    return requirement_quality_findings(package) + traceability_findings(package)


def demo_objects(
    package: dict[str, Any],
) -> tuple[tuple[MissingItem, ...], Draft, ApprovalReceipt, SendContext]:
    """Return a synthetic happy path for failure-injection exercises."""
    items = (
        MissingItem("MI-001", "REQ-FU-001", "Loss history", ("OBS-loss-history-empty",)),
        MissingItem("MI-002", "REQ-FU-001", "Signed application", ("OBS-application-absent",)),
    )
    draft = Draft(
        "BROKER-7",
        "Information needed for submission SUB-10",
        "Please provide the loss history and signed application.",
        tuple(item.id for item in items),
    )
    receipt = ApprovalReceipt(
        reviewer_id="UW-22",
        decision="approved",
        rationale="Items match the current underwriting requirements.",
        draft_digest=draft_digest(draft),
        broker_id="BROKER-7",
        submission_id="SUB-10",
        submission_revision="7",
        requirements_revision="12.4-training",
        issued_at="2026-09-20T16:00:00Z",
        expires_at="2026-09-20T19:00:00Z",
    )
    context = SendContext(
        submission_id="SUB-10",
        submission_revision="7",
        requirements_revision="12.4-training",
        broker_id="BROKER-7",
        broker_authorized=True,
        send_policy_enabled=True,
        logical_operation_id="OP-42",
    )
    return items, draft, receipt, context


def run_demo(path: Path = REFERENCE_PATH) -> dict[str, Any]:
    package = load_package(path)
    return {
        "package": path.name,
        "findings": [asdict(finding) for finding in package_findings(package)],
        "capabilities": [asdict(item) for item in capability_readiness(package)],
        "evaluation": evaluate_cases(),
        "limitations": [
            "No external model, identity, policy, underwriting, or messaging service is contacted.",
            "A ready capability is not production approval or proof of conformance.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=REFERENCE_PATH)
    args = parser.parse_args()
    print(json.dumps(run_demo(args.package.resolve()), indent=2, default=lambda value: value.value))


if __name__ == "__main__":
    main()
