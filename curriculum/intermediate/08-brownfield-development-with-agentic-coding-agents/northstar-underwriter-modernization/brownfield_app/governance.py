"""Trusted application controls around the brownfield implementation."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .contracts import (
    AuthorizationGrant,
    Decision,
    ExecutionContext,
    Finding,
    RollbackEvidence,
    ShadowResult,
    Submission,
    SummaryProposal,
)
from .discovery import required_regression_tests, validate_discovery_manifest
from .legacy import AISummaryProvider, LegacySummaryProvider, legacy_v1_response


EXPECTED_REPOSITORY_REVISION = "9c6a4d8f1e2b7a5036d991ac84f0b234d6a19e72"
EXPECTED_SPECIFICATION_REVISION = 4
POLICY_REVISION = 7
PROTECTED_TESTS = {
    "test_high_risk_requires_review",
    "test_ai_proposal_never_authoritative",
    "test_underwriting_authority_unchanged",
}


class TrustedAuthorizationRegistry:
    """Protected synthetic policy state; callers cannot assert an authorization result."""

    def __init__(self, grants: Iterable[AuthorizationGrant]) -> None:
        self._grants = frozenset(grants)

    def permits(
        self,
        *,
        principal: str,
        submission_id: str,
        operation: str,
        policy_revision: int,
    ) -> bool:
        return AuthorizationGrant(
            principal,
            submission_id,
            operation,
            policy_revision,
        ) in self._grants


def validate_context(context: ExecutionContext) -> Decision:
    findings: list[Finding] = []
    if context.repository_revision != EXPECTED_REPOSITORY_REVISION:
        findings.append(Finding("STALE_REPOSITORY_REVISION", "Implementation context is stale."))
    if context.specification_revision != EXPECTED_SPECIFICATION_REVISION:
        findings.append(Finding("STALE_SPECIFICATION_REVISION", "Specification revision is stale."))
    return Decision("BLOCKED" if findings else "PASS", tuple(findings))


def authorize_operation(
    context: ExecutionContext,
    submission: Submission,
    operation: str,
    registry: TrustedAuthorizationRegistry,
) -> Decision:
    context_decision = validate_context(context)
    findings = list(context_decision.findings)
    if operation not in context.capabilities:
        findings.append(Finding("MISSING_CAPABILITY", f"{context.actor} lacks {operation}."))
    if not registry.permits(
        principal=context.actor,
        submission_id=submission.submission_id,
        operation=operation,
        policy_revision=POLICY_REVISION,
    ):
        findings.append(
            Finding(
                "FEATURE_FLAG_IS_NOT_AUTHORIZATION",
                "No current trusted grant binds the principal, subject, operation, and policy.",
            )
        )
    return Decision("BLOCKED" if findings else "PASS", tuple(findings))


def select_summary_provider(
    context: ExecutionContext,
    submission: Submission,
    registry: TrustedAuthorizationRegistry,
):
    """Resolve trusted authorization before exposing the proposal provider."""
    if "ai_risk_summary" not in context.feature_flags:
        return LegacySummaryProvider(), validate_context(context)
    decision = authorize_operation(context, submission, "create_summary_proposal", registry)
    if decision.state != "PASS":
        return None, decision
    return AISummaryProvider(), decision


def validate_proposal(proposal: SummaryProposal, submission: Submission) -> Decision:
    findings: list[Finding] = []
    if proposal.submission_id != submission.submission_id:
        findings.append(Finding("WRONG_SUBJECT", "Proposal is bound to a different submission."))
    if proposal.authoritative:
        findings.append(Finding("AUTHORITY_ESCALATION", "AI proposal claims authoritative status."))
    if not proposal.evidence:
        findings.append(Finding("UNGROUNDED_PROPOSAL", "Proposal has no evidence references."))
    if not set(proposal.evidence).issubset(set(submission.evidence)):
        findings.append(Finding("UNAUTHORIZED_EVIDENCE", "Proposal cites evidence outside the subject context."))
    return Decision("BLOCKED" if findings else "PASS", tuple(findings))


def persist_proposal(
    *,
    context: ExecutionContext,
    submission: Submission,
    proposal: SummaryProposal,
    source_revision: str,
    registry: TrustedAuthorizationRegistry,
    store: object,
) -> tuple[str | None, Decision]:
    """Re-authorize the exact side effect immediately before persistence."""
    findings = list(validate_proposal(proposal, submission).findings)
    authorization = authorize_operation(context, submission, "persist_summary_proposal", registry)
    findings.extend(authorization.findings)
    if findings:
        return None, Decision("BLOCKED", tuple(findings))
    return store.migrate(proposal, source_revision), Decision("PASS")


def check_v1_semantics(
    submission: Submission,
    candidate: dict[str, object],
    contract: dict[str, object] | None = None,
) -> Decision:
    """Validate explicit v1 obligations; optional additions follow the contract."""
    contract = contract or {
        "required": {
            "submission_id": "string",
            "risk_category": "string",
            "review_required": "boolean",
        },
        "additional_properties": True,
        "exact_response_identity": False,
    }
    findings: list[Finding] = []
    required = contract.get("required", {})
    python_types = {"string": str, "boolean": bool, "integer": int}
    if not isinstance(required, dict):
        required = {}
    for field, type_name in required.items():
        expected_type = python_types.get(str(type_name))
        if field not in candidate or expected_type is None or type(candidate.get(field)) is not expected_type:
            findings.append(Finding("V1_CONTRACT_TYPE_ERROR", f"{field} must be {type_name}."))

    expected = legacy_v1_response(submission)
    semantic_fields = contract.get(
        "semantic_fields",
        ["submission_id", "risk_category", "review_required"],
    )
    for field in semantic_fields:
        if field in candidate and candidate[field] != expected[field]:
            findings.append(
                Finding("SEMANTIC_COMPATIBILITY_BREAK", f"{field} changed an approved v1 obligation.")
            )
    allowed = set(required)
    extra = set(candidate) - allowed
    if extra and not contract.get("additional_properties", False):
        findings.append(Finding("V1_ADDITIONAL_FIELD", f"Additional fields are forbidden: {sorted(extra)}."))
    if contract.get("exact_response_identity") and candidate != expected:
        findings.append(Finding("V1_EXACT_IDENTITY_BREAK", "The approved contract requires exact identity."))
    return Decision("BLOCKED" if findings else "PASS", tuple(findings))


def compare_shadow_outputs(
    legacy: SummaryProposal,
    candidate: SummaryProposal,
    *,
    approved_differences: set[str] | None,
) -> ShadowResult:
    """Classify observed output differences with an explicit compatibility oracle."""
    if approved_differences is None:
        return ShadowResult("UNRESOLVED", (), "No approved comparison oracle was supplied.")
    differences = tuple(
        field
        for field in ("submission_id", "source", "text", "evidence", "authoritative")
        if getattr(legacy, field) != getattr(candidate, field)
    )
    safety_fields = {"submission_id", "evidence", "authoritative"}
    if set(differences) & safety_fields:
        return ShadowResult("UNEXPECTED", differences, "A subject, evidence, or authority invariant changed.")
    if not differences:
        return ShadowResult("EXPECTED", (), "Both providers produced equivalent proposals.")
    if set(differences).issubset(approved_differences):
        classification = "EXPECTED" if set(differences) == approved_differences else "ACCEPTABLE"
        return ShadowResult(classification, differences, "Differences stay within the approved semantic delta.")
    return ShadowResult("UNRESOLVED", differences, "Observed differences exceed the comparison oracle.")


class ProviderRouter:
    def __init__(self) -> None:
        self._ai_enabled = False

    def enable_ai(self) -> None:
        self._ai_enabled = True

    def disable_ai(self) -> None:
        self._ai_enabled = False

    def generate(self, submission: Submission) -> SummaryProposal:
        provider = AISummaryProvider() if self._ai_enabled else LegacySummaryProvider()
        return provider.generate(submission)


def exercise_rollback(
    *,
    submission: Submission,
    context: ExecutionContext,
    registry: TrustedAuthorizationRegistry,
    store: object,
    source_revision: str,
) -> RollbackEvidence:
    """Enable, exercise, and disable the new path while checking legacy authority."""
    router = ProviderRouter()
    before_response = legacy_v1_response(submission)
    before_legacy = router.generate(submission)
    router.enable_ai()
    ai_proposal = router.generate(submission)
    _, persistence = persist_proposal(
        context=context,
        submission=submission,
        proposal=ai_proposal,
        source_revision=source_revision,
        registry=registry,
        store=store,
    )
    router.disable_ai()
    after_legacy = router.generate(submission)
    after_response = legacy_v1_response(submission)
    return RollbackEvidence(
        ai_path_observed=ai_proposal.source == "ai_proposal" and persistence.state == "PASS",
        legacy_path_restored=after_legacy.source == "legacy",
        authoritative_state_unchanged=store.authoritative_count() == 0 and before_response == after_response,
        legacy_reads_preserved=before_legacy == after_legacy,
    )


def evaluate_candidate(candidate: dict[str, object]) -> Decision:
    """Derive findings from artifacts and observed results, never fixture labels."""
    findings: list[Finding] = []
    context = candidate["context"]
    submission = candidate["submission"]
    assert isinstance(context, ExecutionContext)
    assert isinstance(submission, Submission)
    findings.extend(validate_context(context).findings)

    for record in candidate.get("behavior_records", []):
        if not isinstance(record, dict):
            continue
        if record.get("observed_confidence") == "UNKNOWN" and record.get("disposition") == "RETIRE":
            findings.append(Finding("UNAUTHORIZED_RETIREMENT", "Unknown behavior cannot be retired."))
        if record.get("observed_kind") == "DEFECT" and record.get("disposition") == "PRESERVE":
            findings.append(Finding("CHARACTERIZED_DEFECT", "Observed defect was promoted to target behavior."))

    discovery = validate_discovery_manifest(
        candidate["discovery_manifest"],
        actual_repository_revision=EXPECTED_REPOSITORY_REVISION,
        trusted_dependency_evidence=candidate["trusted_dependency_evidence"],
    )
    findings.extend(discovery.findings)

    compatibility = check_v1_semantics(
        submission,
        candidate["candidate_v1_response"],
        candidate["v1_contract"],
    )
    findings.extend(compatibility.findings)

    provider, provider_decision = select_summary_provider(
        context,
        submission,
        candidate["authorization_registry"],
    )
    findings.extend(provider_decision.findings)
    proposal = candidate["proposal"]
    assert isinstance(proposal, SummaryProposal)
    findings.extend(validate_proposal(proposal, submission).findings)

    plan = required_regression_tests(
        impacted_consumers=set(candidate["impacted_consumers"]),
        mapped_tests=candidate["mapped_tests"],
        protected_tests=set(candidate["protected_tests"]),
        critical_consumers=set(candidate["critical_consumers"]),
    )
    if plan.unmapped_consumers:
        findings.append(
            Finding(
                "UNMAPPED_REGRESSION_COVERAGE",
                f"No verification path for {sorted(plan.unmapped_consumers)}.",
                "BLOCK" if plan.state == "BLOCKED" else "REVIEW",
            )
        )
    if not PROTECTED_TESTS.issubset(set(candidate["protected_tests"])):
        findings.append(Finding("PROTECTED_INVARIANT_OMITTED", "A mandatory protected test was removed."))

    store = candidate["migration_store"]
    migration_statuses = [
        store.migrate(attempt["proposal"], attempt["source_revision"])
        for attempt in candidate["migration_attempts"]
    ]
    if "IDEMPOTENCY_CONFLICT" in migration_statuses:
        findings.append(Finding("IDEMPOTENCY_CONFLICT", "The same logical key carried a different payload."))

    shadow = compare_shadow_outputs(
        candidate["legacy_shadow"],
        candidate["candidate_shadow"],
        approved_differences=candidate["approved_shadow_differences"],
    )
    if shadow.classification in {"UNEXPECTED", "UNRESOLVED"}:
        findings.append(Finding("SHADOW_DIVERGENCE", shadow.reason, "REVIEW"))

    rollback = candidate["rollback_evidence"]
    assert isinstance(rollback, RollbackEvidence)
    if not rollback.passed:
        findings.append(Finding("NO_TESTED_ROLLBACK", "The executed rollback did not restore every invariant."))

    if provider is None and not provider_decision.findings:
        findings.append(Finding("PROVIDER_SELECTION_FAILED", "No provider was selected."))

    deduplicated: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (finding.code, finding.message)
        if key not in seen:
            seen.add(key)
            deduplicated.append(finding)
    if any(item.severity == "BLOCK" for item in deduplicated):
        return Decision("BLOCKED", tuple(deduplicated))
    if deduplicated:
        return Decision("REVIEW_REQUIRED", tuple(deduplicated))
    return Decision("PASS")


def direct_agent_baseline(candidate: dict[str, object]) -> Decision:
    """Unsafe baseline: accept a package solely because the agent reports green tests."""
    return Decision("PASS" if candidate.get("agent_tests_passed") else "BLOCKED")


def conflicting_proposal(proposal: SummaryProposal) -> SummaryProposal:
    """Create a semantically different payload for the same migration key."""
    return replace(proposal, text=proposal.text + " (conflicting retry)")
