"""Course 02 lab: turn mixed prose into an executable, governed artifact stack.

The module is intentionally deterministic and dependency-free. It demonstrates that
keywords are weak signals: authority, ownership, scope, rationale, and evidence decide
where a statement belongs and whether an implementation agent may act on it.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
import re
from typing import Iterable


class ArtifactType(str, Enum):
    PROMPT = "prompt"
    PRODUCT_INTENT = "product_intent"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    SPECIFICATION = "specification"
    DESIGN = "design"
    ADR = "adr"
    TASK = "task"
    TEST_EVAL = "test_or_evaluation"
    AGENT_INSTRUCTION = "agent_instruction"
    EVIDENCE = "evidence"
    OPEN_QUESTION = "open_question"


class Authority(str, Enum):
    INFORMAL = "informal"
    PRODUCT = "product"
    ENGINEERING = "engineering"
    DOMAIN = "domain"
    POLICY = "policy"
    EXECUTION = "execution"
    EVIDENCE = "evidence"


class Lifecycle(str, Enum):
    EPHEMERAL = "ephemeral"
    CHANGE = "change"
    LIVING_SYSTEM = "living_system"
    DECISION_HISTORY = "decision_history"
    EXECUTION = "execution"
    EVIDENCE = "evidence"


@dataclass(frozen=True)
class RawStatement:
    id: str
    text: str
    source: str
    owner: str | None = None
    authority: Authority = Authority.INFORMAL
    rationale: str | None = None


@dataclass(frozen=True)
class Classification:
    statement_id: str
    artifact_type: ArtifactType
    lifecycle: Lifecycle
    reason_codes: tuple[str, ...]
    needs_clarification: bool = False
    recommended_owner: str | None = None


@dataclass(frozen=True)
class RequirementCandidate:
    id: str
    statement: str
    owner: str | None
    source: str | None
    measurement: str | None = None
    acceptance: tuple[str, ...] = ()
    authoritative_constraint: bool = False


@dataclass(frozen=True)
class DecisionCandidate:
    id: str
    statement: str
    consequence: str
    reversible: bool
    authority: Authority
    is_exception: bool = False


@dataclass(frozen=True)
class DecisionRoute:
    action: str
    reason_code: str
    owner: str


@dataclass(frozen=True)
class ADR:
    id: str
    context: str
    options: tuple[str, ...]
    decision: str
    consequences: tuple[str, ...]


@dataclass(frozen=True)
class Task:
    id: str
    text: str
    requirement_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceCheck:
    id: str
    kind: str
    claim: str
    requirement_ids: tuple[str, ...]


@dataclass
class ArtifactStack:
    requirements: list[RequirementCandidate] = field(default_factory=list)
    design: list[str] = field(default_factory=list)
    adrs: list[ADR] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)
    evidence: list[EvidenceCheck] = field(default_factory=list)
    agent_instructions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    artifact: str
    message: str


VAGUE_TERMS = {
    "accurate",
    "appropriate",
    "fast",
    "important",
    "probably",
    "reasonable",
    "robust",
    "seamless",
    "soon",
    "user-friendly",
}
IMPLEMENTATION_TERMS = {
    "bedrock",
    "cache",
    "class",
    "dynamodb",
    "langchain",
    "pydantic",
    "rag",
    "redis",
    "new service",
    "sql",
}


def ticket_statements() -> list[RawStatement]:
    """Return the deliberately mixed statements from ticket AI-1842."""
    return [
        RawStatement(
            "S1",
            "Add policy comparison to Underwriter Assistant.",
            "JIRA AI-1842",
            "product manager",
            Authority.PRODUCT,
        ),
        RawStatement(
            "S2",
            "Users select two policies and ask AI to compare coverage.",
            "JIRA AI-1842",
            "product manager",
            Authority.PRODUCT,
        ),
        RawStatement(
            "S3",
            "Use the existing RAG pipeline.",
            "JIRA AI-1842",
            "product manager",
            Authority.INFORMAL,
        ),
        RawStatement(
            "S4",
            "The response should be accurate and explain the differences.",
            "JIRA AI-1842",
            "product manager",
            Authority.PRODUCT,
        ),
        RawStatement(
            "S5",
            "It would be good to cache comparisons because LLM calls are expensive.",
            "JIRA AI-1842",
            "product manager",
            Authority.INFORMAL,
        ),
        RawStatement(
            "S6",
            "Sarah mentioned commercial comparisons probably need human approval.",
            "JIRA AI-1842",
            None,
            Authority.INFORMAL,
        ),
        RawStatement(
            "S7",
            "Try to keep latency under 3 seconds.",
            "JIRA AI-1842",
            "product manager",
            Authority.PRODUCT,
        ),
        RawStatement(
            "S8",
            "Use Redis because another team uses it.",
            "JIRA AI-1842",
            "product manager",
            Authority.INFORMAL,
            "technology precedent in another team",
        ),
    ]


def keyword_classify(statement: RawStatement) -> Classification:
    """A deliberately weak baseline that mistakes wording for authority."""
    text = statement.text.lower()
    if any(word in text for word in ("use ", "redis", "rag", "cache")):
        kind = ArtifactType.REQUIREMENT
        reason = "KEYWORD_USE_MEANS_REQUIREMENT"
    elif any(word in text for word in ("test", "verify", "evaluate")):
        kind = ArtifactType.TEST_EVAL
        reason = "KEYWORD_TEST"
    else:
        kind = ArtifactType.PRODUCT_INTENT
        reason = "DEFAULT_PRODUCT_INTENT"
    return Classification(statement.id, kind, Lifecycle.CHANGE, (reason,))


def _contains_vagueness(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in VAGUE_TERMS)


def _implementation_terms(text: str) -> list[str]:
    lowered = text.lower()
    return sorted(
        term for term in IMPLEMENTATION_TERMS if re.search(rf"\b{re.escape(term)}\b", lowered)
    )


def classify_statement(statement: RawStatement) -> Classification:
    """Classify using provenance and authority as well as language."""
    text = statement.text.lower()
    reasons: list[str] = []

    if "sarah mentioned" in text or "probably" in text:
        return Classification(
            statement.id,
            ArtifactType.OPEN_QUESTION,
            Lifecycle.CHANGE,
            ("HEARSAY_NOT_POLICY", "AUTHORITATIVE_SOURCE_REQUIRED"),
            True,
            "underwriting domain owner",
        )

    if statement.authority == Authority.POLICY:
        return Classification(
            statement.id,
            ArtifactType.CONSTRAINT,
            Lifecycle.LIVING_SYSTEM,
            ("POLICY_AUTHORITY", "INHERITED_CONSTRAINT"),
            statement.owner is None,
            statement.owner or "policy owner",
        )

    if statement.authority == Authority.EXECUTION:
        return Classification(
            statement.id,
            ArtifactType.AGENT_INSTRUCTION,
            Lifecycle.EXECUTION,
            ("EXECUTION_SCOPE",),
            statement.owner is None,
            statement.owner or "repository maintainer",
        )

    design_signal = bool(_implementation_terms(text))
    if design_signal:
        reasons.append("IMPLEMENTATION_CHOICE")
        if statement.rationale:
            reasons.append("RATIONALE_REQUIRES_EVALUATION")
        return Classification(
            statement.id,
            ArtifactType.DESIGN,
            Lifecycle.CHANGE,
            tuple(reasons),
            statement.authority == Authority.INFORMAL,
            "solution architect",
        )

    if statement.authority == Authority.PRODUCT:
        if _contains_vagueness(text) or text.startswith("try "):
            return Classification(
                statement.id,
                ArtifactType.OPEN_QUESTION,
                Lifecycle.CHANGE,
                ("CANDIDATE_REQUIREMENT", "NOT_MEASURABLE"),
                True,
                "product owner and evidence owner",
            )
        if text.startswith(("add ", "enable ", "allow ")):
            return Classification(
                statement.id,
                ArtifactType.PRODUCT_INTENT,
                Lifecycle.CHANGE,
                ("PRODUCT_OUTCOME",),
                False,
                statement.owner,
            )
        return Classification(
            statement.id,
            ArtifactType.REQUIREMENT,
            Lifecycle.CHANGE,
            ("PRODUCT_AUTHORITY", "OBSERVABLE_BEHAVIOR_CANDIDATE"),
            statement.owner is None,
            statement.owner or "product owner",
        )

    return Classification(
        statement.id,
        ArtifactType.PROMPT,
        Lifecycle.EPHEMERAL,
        ("NO_DURABLE_AUTHORITY",),
        True,
        "request owner",
    )


def validate_requirement(requirement: RequirementCandidate) -> list[Finding]:
    findings: list[Finding] = []
    lowered = requirement.statement.lower()
    if not requirement.owner:
        findings.append(
            Finding("error", "REQ_OWNER_MISSING", requirement.id, "No accountable owner.")
        )
    if not requirement.source:
        findings.append(
            Finding("error", "REQ_SOURCE_MISSING", requirement.id, "No authoritative source.")
        )
    if _contains_vagueness(lowered):
        findings.append(
            Finding(
                "error",
                "REQ_AMBIGUOUS_TERM",
                requirement.id,
                "Vague quality term is not operationalized.",
            )
        )
    leaked = _implementation_terms(lowered)
    if leaked and not requirement.authoritative_constraint:
        findings.append(
            Finding(
                "error",
                "REQ_IMPLEMENTATION_LEAKAGE",
                requirement.id,
                f"Solution choice appears in outcome requirement: {', '.join(leaked)}.",
            )
        )
    performance_signal = any(
        term in lowered for term in ("latency", "second", "millisecond", "response time")
    )
    if performance_signal:
        measurement = (requirement.measurement or "").lower()
        missing = [token for token in ("p95", "workload", "scope") if token not in measurement]
        if missing:
            findings.append(
                Finding(
                    "error",
                    "REQ_PERFORMANCE_CONTEXT_MISSING",
                    requirement.id,
                    f"Performance target lacks {', '.join(missing)}.",
                )
            )
    if not requirement.acceptance and not requirement.measurement:
        findings.append(
            Finding(
                "error",
                "REQ_NOT_OBSERVABLE",
                requirement.id,
                "No acceptance scenario or measurement is defined.",
            )
        )
    return findings


def route_decision(decision: DecisionCandidate) -> DecisionRoute:
    """Route a decision without confusing agent capability with decision authority."""
    if decision.is_exception or decision.authority == Authority.POLICY:
        return DecisionRoute("escalate", "POLICY_AUTHORITY_REQUIRED", "policy owner")
    consequential = {"cross-system", "security", "data-retention"}
    if not decision.reversible or decision.consequence in consequential:
        return DecisionRoute(
            "propose_adr", "CONSEQUENTIAL_ARCHITECTURE_DECISION", "architecture owner"
        )
    return DecisionRoute("agent_may_decide", "LOCAL_REVERSIBLE_CHOICE", "implementation owner")


def _validate_adr(adr: ADR) -> list[Finding]:
    findings: list[Finding] = []
    if not adr.context.strip():
        findings.append(
            Finding("error", "ADR_CONTEXT_MISSING", adr.id, "Decision context is absent.")
        )
    if len(adr.options) < 2:
        findings.append(
            Finding(
                "error",
                "ADR_OPTIONS_MISSING",
                adr.id,
                "Fewer than two options were considered.",
            )
        )
    if not adr.decision.strip():
        findings.append(
            Finding("error", "ADR_DECISION_MISSING", adr.id, "No decision is recorded.")
        )
    if not adr.consequences:
        findings.append(
            Finding("error", "ADR_CONSEQUENCES_MISSING", adr.id, "Consequences are absent.")
        )
    return findings


def validate_stack(stack: ArtifactStack) -> list[Finding]:
    findings: list[Finding] = []
    requirement_ids = {item.id for item in stack.requirements}
    for requirement in stack.requirements:
        findings.extend(validate_requirement(requirement))
    for adr in stack.adrs:
        findings.extend(_validate_adr(adr))
    for task in stack.tasks:
        unknown = sorted(set(task.requirement_ids) - requirement_ids)
        if not task.requirement_ids:
            findings.append(
                Finding("error", "TASK_UNLINKED", task.id, "Task does not trace to a requirement.")
            )
        if unknown:
            findings.append(
                Finding(
                    "error",
                    "TASK_UNKNOWN_REQUIREMENT",
                    task.id,
                    f"Unknown links: {', '.join(unknown)}.",
                )
            )
    for check in stack.evidence:
        unknown = sorted(set(check.requirement_ids) - requirement_ids)
        if not check.requirement_ids:
            findings.append(
                Finding(
                    "error",
                    "EVIDENCE_UNLINKED",
                    check.id,
                    "Evidence does not trace to a requirement.",
                )
            )
        if unknown:
            findings.append(
                Finding(
                    "error",
                    "EVIDENCE_UNKNOWN_REQUIREMENT",
                    check.id,
                    f"Unknown links: {', '.join(unknown)}.",
                )
            )
        if "defines the requirement" in check.claim.lower():
            findings.append(
                Finding(
                    "error",
                    "TEST_TREATED_AS_SPEC",
                    check.id,
                    "A test can provide evidence; it cannot own product intent.",
                )
            )
    for index, instruction in enumerate(stack.agent_instructions, start=1):
        lowered = instruction.lower()
        overreach_phrases = (
            "waive policy",
            "ignore policy",
            "no human approval",
            "may change requirements",
        )
        if any(phrase in lowered for phrase in overreach_phrases):
            findings.append(
                Finding(
                    "error",
                    "AGENT_INSTRUCTION_EXCEEDS_AUTHORITY",
                    f"AGENT-{index}",
                    "Execution guidance attempts to grant product or policy authority.",
                )
            )
    return findings


def traceability_metrics(stack: ArtifactStack) -> dict[str, dict[str, int | float]]:
    requirement_ids = {item.id for item in stack.requirements}
    task_links = {
        rid for task in stack.tasks for rid in task.requirement_ids if rid in requirement_ids
    }
    evidence_links = {
        rid for check in stack.evidence for rid in check.requirement_ids if rid in requirement_ids
    }

    def metric(covered: set[str]) -> dict[str, int | float]:
        total = len(requirement_ids)
        return {
            "covered": len(covered),
            "total": total,
            "percent": round(100 * len(covered) / total, 1) if total else 100.0,
        }

    return {
        "requirements_to_tasks": metric(task_links),
        "requirements_to_evidence": metric(evidence_links),
    }


def reference_stack() -> ArtifactStack:
    requirements = [
        RequirementCandidate(
            "REQ-CMP-001",
            (
                "An authenticated underwriter can select exactly two tenant-authorized "
                "policy documents for comparison."
            ),
            "product owner",
            "approved specification v1",
            acceptance=(
                "Given two authorized policies, comparison accepts both identifiers.",
            ),
        ),
        RequirementCandidate(
            "REQ-CMP-002",
            (
                "Every comparison claim cites supporting passages from the applicable "
                "policy document or documents."
            ),
            "underwriting domain owner",
            "approved specification v1",
            acceptance=(
                "Each rendered difference links to evidence for the side or sides it describes.",
            ),
        ),
        RequirementCandidate(
            "REQ-CMP-003",
            (
                "When evidence for either side is absent, the system reports insufficient "
                "evidence for that difference and does not infer one."
            ),
            "underwriting domain owner",
            "approved specification v1",
            acceptance=(
                "A one-sided retrieval result produces an abstention for the unsupported side.",
            ),
        ),
        RequirementCandidate(
            "REQ-CMP-004",
            (
                "A commercial-policy comparison is reviewed by an authorized underwriter "
                "before consequential use."
            ),
            "underwriting policy owner",
            "AI-021 approved clarification",
            acceptance=(
                "The result cannot enter the decision record without a reviewer receipt.",
            ),
        ),
        RequirementCandidate(
            "PERF-CMP-001",
            "The complete comparison response meets the approved service objective.",
            "service owner",
            "SLO-CMP-001",
            measurement=(
                "p95 complete response <= 5 seconds; workload W1; "
                "scope production-like comparison requests"
            ),
        ),
        RequirementCandidate(
            "SEC-CMP-001",
            (
                "Comparison retrieval never returns content outside the authenticated "
                "tenant and document authorization boundary."
            ),
            "security owner",
            "SEC-014",
            acceptance=("Cross-tenant and unauthorized-document probes return no content.",),
        ),
        RequirementCandidate(
            "OBS-CMP-001",
            (
                "Comparison traces record requirement and evidence identifiers without "
                "policy content or personal data."
            ),
            "observability owner",
            "OBS-008 and PRIV-003",
            acceptance=(
                "A trace contains IDs and timing fields but no document passages or prompts.",
            ),
        ),
    ]
    return ArtifactStack(
        requirements=requirements,
        design=[
            "Extend the existing retrieval boundary with a two-document comparison orchestrator.",
            "Generate claim-level citation metadata before presentation.",
            "Keep generated comparison responses uncached in the first release.",
        ],
        adrs=[
            ADR(
                "ADR-007",
                (
                    "Repeated comparisons may increase cost, but generated content can "
                    "become stale or cross authorization and retention boundaries."
                ),
                ("No response cache", "Redis full-response cache", "Cache retrieval results only"),
                (
                    "Do not cache generated comparison responses in the first release; "
                    "measure repeated retrieval before reconsidering."
                ),
                (
                    "Higher initial model cost",
                    "No cache invalidation or generated-content retention boundary yet",
                    "Decision will be revisited with telemetry",
                ),
            )
        ],
        tasks=[
            Task(
                "TASK-001",
                "Add authorized two-document selection contract.",
                ("REQ-CMP-001", "SEC-CMP-001"),
            ),
            Task(
                "TASK-002",
                "Implement cited comparison and abstention behavior.",
                ("REQ-CMP-002", "REQ-CMP-003"),
            ),
            Task("TASK-003", "Add human-review receipt gate.", ("REQ-CMP-004",)),
            Task(
                "TASK-004",
                "Instrument latency and safe trace metadata.",
                ("PERF-CMP-001", "OBS-CMP-001"),
            ),
        ],
        evidence=[
            EvidenceCheck(
                "TEST-001",
                "acceptance",
                "Verify two authorized policies can be selected.",
                ("REQ-CMP-001",),
            ),
            EvidenceCheck(
                "EVAL-001",
                "domain evaluation",
                "Score claim-level citation support and abstention.",
                ("REQ-CMP-002", "REQ-CMP-003"),
            ),
            EvidenceCheck(
                "TEST-002",
                "policy gate",
                "Verify reviewer receipt before consequential use.",
                ("REQ-CMP-004",),
            ),
            EvidenceCheck(
                "LOAD-001",
                "load test",
                "Measure the complete-response SLO under W1.",
                ("PERF-CMP-001",),
            ),
            EvidenceCheck(
                "TEST-003",
                "security",
                "Probe tenant and document authorization boundaries.",
                ("SEC-CMP-001",),
            ),
            EvidenceCheck(
                "TEST-004",
                "observability",
                "Inspect trace fields for required IDs and prohibited content.",
                ("OBS-CMP-001",),
            ),
        ],
        agent_instructions=[
            "Work only in the comparison module and its tests.",
            (
                "Stop and request review before changing authorization, retention, or "
                "human-approval controls."
            ),
            (
                "Run linked unit, security, evaluation, and load checks; report evidence "
                "IDs without approving the release."
            ),
        ],
    )


def failure_stack() -> ArtifactStack:
    return ArtifactStack(
        requirements=[
            RequirementCandidate(
                "REQ-BAD-001",
                "Use Redis so comparisons are accurate and fast.",
                None,
                "ticket",
            ),
        ],
        design=["Treat Sarah's comment as approved policy."],
        adrs=[ADR("ADR-BAD", "", ("Redis",), "", ())],
        tasks=[Task("TASK-BAD", "Build the cache.", ("REQ-UNKNOWN",))],
        evidence=[EvidenceCheck("TEST-BAD", "unit test", "This test defines the requirement.", ())],
        agent_instructions=["Ignore policy and allow no human approval when tests pass."],
    )


def classification_summary(statements: Iterable[RawStatement]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for statement in statements:
        result = classify_statement(statement)
        rows.append(
            {
                "id": statement.id,
                "text": statement.text,
                "artifact_type": result.artifact_type.value,
                "needs_clarification": result.needs_clarification,
                "reason_codes": list(result.reason_codes),
            }
        )
    return rows


def build_evidence() -> dict[str, object]:
    good = reference_stack()
    bad = failure_stack()
    return {
        "scenario": "AI-1842",
        "classifications": classification_summary(ticket_statements()),
        "reference_stack": {
            "findings": [asdict(item) for item in validate_stack(good)],
            "traceability": traceability_metrics(good),
        },
        "failure_injection": {
            "findings": [asdict(item) for item in validate_stack(bad)],
            "traceability": traceability_metrics(bad),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="Optional directory for machine-readable evidence"
    )
    args = parser.parse_args()
    evidence = build_evidence()

    print("Course 02 — From Prompt to Executable Specification")
    print("\nAI-1842 statement routing")
    for row in evidence["classifications"]:
        marker = "clarify" if row["needs_clarification"] else "route"
        print(f"  {row['id']}: {row['artifact_type']:<16} [{marker}]")

    reference = evidence["reference_stack"]
    failure = evidence["failure_injection"]
    print(f"\nReference stack findings: {len(reference['findings'])}")
    for name, metric in reference["traceability"].items():
        print(f"  {name}: {metric['covered']}/{metric['total']} ({metric['percent']}%)")
    print(f"Failure injection findings: {len(failure['findings'])}")
    print("  " + ", ".join(sorted({item["code"] for item in failure["findings"]})))

    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output / "course02-evidence.json"
        target.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        print(f"\nEvidence written to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
