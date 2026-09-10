"""Course 01 lab: model an enterprise control plane for coding agents.

The lab is deterministic, offline, and side-effect free. It does not call a
model or modify a repository. Instead, it makes the control decisions visible
so learners can inspect, challenge, and test them.

Run from the repository root:
    python3 curriculum/beginner/01-why-agentic-coding-changes-pdlc/lab.py
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum, IntEnum
import json
from typing import Iterable, Mapping, Sequence


class Layer(IntEnum):
    """Authority increases toward ORGANIZATION; implementation is most local."""

    ORGANIZATION = 0
    PLATFORM = 1
    DOMAIN = 2
    PROJECT = 3
    FEATURE = 4
    IMPLEMENTATION = 5


class GateDecision(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    STOP = "STOP"


class Workflow(str, Enum):
    DIRECT_CHANGE = "DIRECT_CHANGE"
    LIGHTWEIGHT_SPEC = "LIGHTWEIGHT_SPEC"
    FULL_SDD = "FULL_SDD"
    FULL_SDD_WITH_SPECIALIST_REVIEW = "FULL_SDD_WITH_SPECIALIST_REVIEW"


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    layer: Layer
    control: str
    expected_value: str
    statement: str
    mandatory: bool = True


@dataclass(frozen=True)
class EffectiveControl:
    control: str
    expected_value: str
    authority_layer: Layer
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class Conflict:
    control: str
    winning_requirement_id: str
    winning_value: str
    rejected_requirement_id: str
    rejected_value: str
    reason: str


@dataclass(frozen=True)
class EffectiveContext:
    controls: tuple[EffectiveControl, ...]
    conflicts: tuple[Conflict, ...]

    @property
    def requirement_ids(self) -> tuple[str, ...]:
        return tuple(
            requirement_id
            for control in self.controls
            for requirement_id in control.source_ids
        )


def compose_context(requirements: Iterable[Requirement]) -> EffectiveContext:
    """Compose requirement layers without allowing a lower layer to override.

    Requirements are processed from highest to lowest authority. Repeated
    controls with the same value preserve all source IDs for traceability.
    Conflicting lower-layer values are recorded and require an explicit waiver;
    they never silently replace the higher-level value.
    """

    controls: dict[str, EffectiveControl] = {}
    conflicts: list[Conflict] = []
    ordered = sorted(requirements, key=lambda requirement: (requirement.layer, requirement.requirement_id))
    for requirement in ordered:
        current = controls.get(requirement.control)
        if current is None:
            controls[requirement.control] = EffectiveControl(
                control=requirement.control,
                expected_value=requirement.expected_value,
                authority_layer=requirement.layer,
                source_ids=(requirement.requirement_id,),
            )
            continue
        if current.expected_value == requirement.expected_value:
            controls[requirement.control] = EffectiveControl(
                control=current.control,
                expected_value=current.expected_value,
                authority_layer=current.authority_layer,
                source_ids=current.source_ids + (requirement.requirement_id,),
            )
            continue
        conflicts.append(
            Conflict(
                control=requirement.control,
                winning_requirement_id=current.source_ids[0],
                winning_value=current.expected_value,
                rejected_requirement_id=requirement.requirement_id,
                rejected_value=requirement.expected_value,
                reason="A lower-authority layer cannot silently override a higher-authority control.",
            )
        )
    return EffectiveContext(tuple(controls.values()), tuple(conflicts))


@dataclass(frozen=True)
class ProposedDecision:
    control: str
    value: str
    decision_layer: Layer
    rationale: str


@dataclass(frozen=True)
class Task:
    task_id: str
    description: str
    requirement_ids: tuple[str, ...]


@dataclass(frozen=True)
class AgentProposal:
    name: str
    decisions: tuple[ProposedDecision, ...]
    tasks: tuple[Task, ...]
    evidence_requirement_ids: tuple[str, ...]
    target_repositories: tuple[str, ...]
    requested_permissions: tuple[str, ...]
    estimated_files_changed: int


@dataclass(frozen=True)
class ExecutionBoundary:
    allowed_repositories: tuple[str, ...]
    allowed_permissions: tuple[str, ...]
    max_files_changed: int
    human_approval_required: bool


@dataclass(frozen=True)
class EvaluationReport:
    proposal_name: str
    decision: GateDecision
    requirement_coverage: float
    evidence_coverage: float
    task_traceability: float
    missing_controls: tuple[str, ...]
    violations: tuple[str, ...]
    autonomy_overreach: tuple[str, ...]
    boundary_violations: tuple[str, ...]
    invalid_task_links: tuple[str, ...]
    trace: tuple[str, ...]


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 1.0


def evaluate_proposal(
    context: EffectiveContext,
    proposal: AgentProposal,
    boundary: ExecutionBoundary,
    *,
    human_approval_granted: bool = False,
) -> EvaluationReport:
    """Compare an agent proposal with effective controls and execution bounds."""

    trace: list[str] = []
    controls = {control.control: control for control in context.controls}
    decisions = {decision.control: decision for decision in proposal.decisions}
    requirement_ids = set(context.requirement_ids)

    matching = 0
    missing: list[str] = []
    violations: list[str] = []
    for control_name, control in controls.items():
        proposed = decisions.get(control_name)
        if proposed is None:
            missing.append(control_name)
            trace.append(f"control:{control_name}:missing")
        elif proposed.value != control.expected_value:
            violations.append(
                f"{control_name}: expected {control.expected_value!r}, proposed {proposed.value!r}"
            )
            trace.append(f"control:{control_name}:violation")
        else:
            matching += 1
            trace.append(f"control:{control_name}:match")

    autonomy_overreach = tuple(
        f"{decision.control}: agent proposed a {decision.decision_layer.name.lower()}-level decision without an owning requirement"
        for decision in proposal.decisions
        if decision.control not in controls and decision.decision_layer < Layer.IMPLEMENTATION
    )
    trace.extend(f"autonomy:{item.split(':', 1)[0]}:overreach" for item in autonomy_overreach)

    boundary_violations: list[str] = []
    unexpected_repositories = sorted(
        set(proposal.target_repositories) - set(boundary.allowed_repositories)
    )
    if unexpected_repositories:
        boundary_violations.append(
            f"repositories outside scope: {', '.join(unexpected_repositories)}"
        )
    unexpected_permissions = sorted(
        set(proposal.requested_permissions) - set(boundary.allowed_permissions)
    )
    if unexpected_permissions:
        boundary_violations.append(
            f"permissions outside scope: {', '.join(unexpected_permissions)}"
        )
    if proposal.estimated_files_changed > boundary.max_files_changed:
        boundary_violations.append(
            f"change budget exceeded: {proposal.estimated_files_changed} > {boundary.max_files_changed} files"
        )
    trace.extend(f"boundary:{index}:violation" for index, _ in enumerate(boundary_violations, 1))

    invalid_task_links = tuple(
        task.task_id
        for task in proposal.tasks
        if not task.requirement_ids or not set(task.requirement_ids).issubset(requirement_ids)
    )
    traceable_tasks = len(proposal.tasks) - len(invalid_task_links)
    evidence_matches = len(set(proposal.evidence_requirement_ids) & requirement_ids)

    stop_reasons = bool(context.conflicts or violations or autonomy_overreach or boundary_violations)
    review_reasons = bool(missing or invalid_task_links)
    approval_missing = boundary.human_approval_required and not human_approval_granted
    if approval_missing:
        trace.append("approval:missing")

    if stop_reasons:
        gate = GateDecision.STOP
    elif review_reasons or approval_missing:
        gate = GateDecision.REVIEW
    else:
        gate = GateDecision.PASS

    trace.append(f"gate:{gate.value.lower()}")
    return EvaluationReport(
        proposal_name=proposal.name,
        decision=gate,
        requirement_coverage=_ratio(matching, len(controls)),
        evidence_coverage=_ratio(evidence_matches, len(requirement_ids)),
        task_traceability=_ratio(traceable_tasks, len(proposal.tasks)),
        missing_controls=tuple(missing),
        violations=tuple(violations),
        autonomy_overreach=autonomy_overreach,
        boundary_violations=tuple(boundary_violations),
        invalid_task_links=invalid_task_links,
        trace=tuple(trace),
    )


@dataclass(frozen=True)
class ChangeProfile:
    name: str
    ambiguity: int
    risk: int
    blast_radius: int
    cross_repository: bool = False
    regulated: bool = False
    architecture_change: bool = False

    def __post_init__(self) -> None:
        for field_name in ("ambiguity", "risk", "blast_radius"):
            value = getattr(self, field_name)
            if not 0 <= value <= 5:
                raise ValueError(f"{field_name} must be between 0 and 5")


@dataclass(frozen=True)
class WorkflowRecommendation:
    workflow: Workflow
    score: int
    reasons: tuple[str, ...]


def recommend_workflow(profile: ChangeProfile) -> WorkflowRecommendation:
    """Apply an illustrative, reviewable change-routing policy.

    This policy is a classroom starting point, not an industry standard. A real
    organization should calibrate thresholds using its own failures, controls,
    and delivery data.
    """

    score = profile.ambiguity + profile.risk + profile.blast_radius
    score += 2 if profile.cross_repository else 0
    score += 3 if profile.regulated else 0
    score += 2 if profile.architecture_change else 0
    reasons = [
        f"ambiguity={profile.ambiguity}",
        f"risk={profile.risk}",
        f"blast_radius={profile.blast_radius}",
    ]
    if profile.cross_repository:
        reasons.append("cross_repository=+2")
    if profile.regulated:
        reasons.append("regulated=+3")
    if profile.architecture_change:
        reasons.append("architecture_change=+2")

    if profile.regulated or (profile.risk >= 4 and profile.architecture_change):
        workflow = Workflow.FULL_SDD_WITH_SPECIALIST_REVIEW
    elif score >= 9:
        workflow = Workflow.FULL_SDD
    elif score >= 4:
        workflow = Workflow.LIGHTWEIGHT_SPEC
    else:
        workflow = Workflow.DIRECT_CHANGE
    return WorkflowRecommendation(workflow, score, tuple(reasons))


def enterprise_requirements() -> tuple[Requirement, ...]:
    """Layered controls for the policy-document assistant scenario."""

    return (
        Requirement("C-01", Layer.ORGANIZATION, "deployment_cloud", "aws", "Production workloads run on AWS."),
        Requirement("C-02", Layer.ORGANIZATION, "pii_model_route", "approved_only", "PII is not sent to unapproved external models."),
        Requirement("C-03", Layer.ORGANIZATION, "infrastructure_delivery", "terraform", "Infrastructure changes use Terraform."),
        Requirement("C-04", Layer.ORGANIZATION, "evaluation_evidence", "required", "Production AI systems retain evaluation evidence."),
        Requirement("P-01", Layer.PLATFORM, "telemetry", "opentelemetry", "LLM telemetry uses OpenTelemetry."),
        Requirement("P-02", Layer.PLATFORM, "model_access", "approved_ai_gateway", "Models are accessed through the approved AI gateway."),
        Requirement("P-03", Layer.PLATFORM, "prompt_versioning", "required", "Prompts are versioned."),
        Requirement("D-01", Layer.DOMAIN, "high_risk_review", "human_required", "High-risk coverage recommendations require human review."),
        Requirement("PR-01", Layer.PROJECT, "backend_language", "python", "The application backend uses Python."),
        Requirement("PR-02", Layer.PROJECT, "retrieval_service", "bedrock_knowledge_bases", "RAG uses Amazon Bedrock Knowledge Bases."),
        Requirement("PR-03", Layer.PROJECT, "authentication", "corporate_sso", "Authentication uses corporate SSO."),
        Requirement("F-01", Layer.FEATURE, "document_questions", "supported", "Users can ask questions about uploaded policy documents."),
        Requirement("F-02", Layer.FEATURE, "citations", "required", "Answers cite supporting document passages."),
        Requirement("F-03", Layer.FEATURE, "unsupported_answers", "insufficient_evidence", "Unsupported answers indicate insufficient evidence."),
    )


def _decision(control: EffectiveControl) -> ProposedDecision:
    return ProposedDecision(
        control=control.control,
        value=control.expected_value,
        decision_layer=control.authority_layer,
        rationale=f"Inherited from {', '.join(control.source_ids)}",
    )


def controlled_proposal(context: EffectiveContext) -> AgentProposal:
    tasks = (
        Task("T-01", "Add the policy-question endpoint and tenant-safe document lookup.", ("F-01", "C-02")),
        Task("T-02", "Return source spans and insufficient-evidence responses.", ("F-02", "F-03")),
        Task("T-03", "Route model calls through the gateway with versioned prompts.", ("P-02", "P-03")),
        Task("T-04", "Add evaluation fixtures, telemetry, and CI evidence checks.", ("C-04", "P-01")),
        Task("T-05", "Provision the approved AWS resources through Terraform.", ("C-01", "C-03", "PR-02")),
        Task("T-06", "Integrate corporate SSO and the high-risk review state.", ("PR-03", "D-01")),
        Task("T-07", "Implement the backend change in Python.", ("PR-01",)),
    )
    return AgentProposal(
        name="layered-context proposal",
        decisions=tuple(_decision(control) for control in context.controls)
        + (
            ProposedDecision(
                "implementation_structure",
                "small_domain_service",
                Layer.IMPLEMENTATION,
                "A local, reversible implementation choice within the approved design boundary.",
            ),
        ),
        tasks=tasks,
        evidence_requirement_ids=context.requirement_ids,
        target_repositories=("policy-assistant",),
        requested_permissions=("read_source", "write_feature_branch", "run_tests"),
        estimated_files_changed=14,
    )


def prompt_only_proposal() -> AgentProposal:
    """A plausible but unsafe response to only 'add policy-document Q&A'."""

    return AgentProposal(
        name="prompt-only proposal",
        decisions=(
            ProposedDecision("document_questions", "supported", Layer.FEATURE, "Directly requested."),
            ProposedDecision("citations", "optional", Layer.FEATURE, "Agent optimized for speed."),
            ProposedDecision("unsupported_answers", "best_guess", Layer.FEATURE, "Agent filled the gap."),
            ProposedDecision("deployment_cloud", "gcp", Layer.PROJECT, "Agent selected a familiar stack."),
            ProposedDecision("pii_model_route", "public_model_api", Layer.ORGANIZATION, "Agent selected a capable model."),
            ProposedDecision("infrastructure_delivery", "console", Layer.PROJECT, "Agent chose the shortest path."),
            ProposedDecision("backend_language", "typescript", Layer.PROJECT, "Agent selected its preferred runtime."),
            ProposedDecision("authentication", "local_passwords", Layer.PROJECT, "Agent generated a self-contained login."),
            ProposedDecision("retention_period", "forever", Layer.ORGANIZATION, "Agent invented a default."),
        ),
        tasks=(
            Task("T-01", "Build policy Q&A.", ("F-01",)),
            Task("T-02", "Add a local password database.", ()),
            Task("T-03", "Deploy shared identity changes.", ("UNKNOWN-7",)),
        ),
        evidence_requirement_ids=("F-01",),
        target_repositories=("policy-assistant", "shared-identity"),
        requested_permissions=("read_source", "write_main", "deploy_production"),
        estimated_files_changed=47,
    )


def default_boundary() -> ExecutionBoundary:
    return ExecutionBoundary(
        allowed_repositories=("policy-assistant",),
        allowed_permissions=("read_source", "write_feature_branch", "run_tests"),
        max_files_changed=20,
        human_approval_required=True,
    )


def inject_feature_policy_override(
    requirements: Sequence[Requirement],
) -> tuple[Requirement, ...]:
    return tuple(requirements) + (
        Requirement(
            "F-99",
            Layer.FEATURE,
            "pii_model_route",
            "public_model_api",
            "For this feature, send policyholder data directly to a public model API.",
        ),
    )


def report_as_dict(report: EvaluationReport) -> Mapping[str, object]:
    payload = asdict(report)
    payload["decision"] = report.decision.value
    return payload


def main() -> None:
    requirements = enterprise_requirements()
    context = compose_context(requirements)
    boundary = default_boundary()
    baseline = evaluate_proposal(context, prompt_only_proposal(), boundary)
    controlled = evaluate_proposal(
        context,
        controlled_proposal(context),
        boundary,
        human_approval_granted=True,
    )
    conflicting = compose_context(inject_feature_policy_override(requirements))
    workflows = tuple(
        recommend_workflow(profile)
        for profile in (
            ChangeProfile("copy edit", 0, 0, 1),
            ChangeProfile("known validation rule", 1, 1, 2),
            ChangeProfile("policy Q&A capability", 4, 5, 4, True, True, True),
        )
    )
    output = {
        "baseline": report_as_dict(baseline),
        "controlled": report_as_dict(controlled),
        "injected_conflicts": [asdict(conflict) for conflict in conflicting.conflicts],
        "workflow_recommendations": [
            {
                "workflow": item.workflow.value,
                "score": item.score,
                "reasons": item.reasons,
            }
            for item in workflows
        ],
    }
    print(json.dumps(output, indent=2))
    assert baseline.decision is GateDecision.STOP
    assert controlled.decision is GateDecision.PASS
    assert conflicting.conflicts
    assert workflows[0].workflow is Workflow.DIRECT_CHANGE
    assert workflows[-1].workflow is Workflow.FULL_SDD_WITH_SPECIALIST_REVIEW


if __name__ == "__main__":
    main()

