"""Trusted validation for pinned context, grounding, and authority boundaries."""

from __future__ import annotations

from dataclasses import asdict

from .context_builder import canonical_digest, context_is_canonical
from .contracts import EvidenceDocument, ExecutionContext, ModelProposal, ValidationFinding, ValidationReport


ALLOWED_MODEL_ACTIONS = {"create_summary_proposal"}


def proposal_digest(proposal: ModelProposal) -> str:
    return canonical_digest(asdict(proposal))


def validate_proposal(
    proposal: ModelProposal,
    context: ExecutionContext,
    documents: dict[str, EvidenceDocument],
) -> ValidationReport:
    findings: list[ValidationFinding] = []
    if not context_is_canonical(context):
        findings.append(ValidationFinding("CONTEXT_DIGEST_INVALID", context.context_id, "The trusted context is not canonical."))
    if proposal.context_digest != context.digest:
        findings.append(ValidationFinding("STALE_CONTEXT", proposal.proposal_id, "The proposal is not bound to the current execution context."))
    if proposal.specification_revision != context.specification_revision:
        findings.append(ValidationFinding("STALE_SPECIFICATION", proposal.proposal_id, "The proposal uses a different specification revision."))
    if proposal.architecture_revision != context.architecture_revision:
        findings.append(ValidationFinding("STALE_ARCHITECTURE", proposal.proposal_id, "The proposal uses a different architecture revision."))
    if proposal.submission_id != context.submission_id:
        findings.append(ValidationFinding("SUBMISSION_SCOPE_MISMATCH", proposal.proposal_id, "The proposal crosses the authorized submission boundary."))

    forbidden = sorted(set(proposal.attempted_actions) - ALLOWED_MODEL_ACTIONS)
    if forbidden:
        findings.append(ValidationFinding("UNAUTHORIZED_SIDE_EFFECT", proposal.proposal_id, "Model output requested protected actions: " + ", ".join(forbidden)))

    cited: set[str] = set()
    for claim in proposal.claims:
        if not claim.evidence_ids:
            findings.append(ValidationFinding("CITATION_REQUIRED", claim.claim_id, "Every material claim requires source evidence."))
            continue
        resolved = [documents[item] for item in claim.evidence_ids if item in documents]
        missing = sorted(set(claim.evidence_ids) - set(documents))
        if missing:
            findings.append(ValidationFinding("CITATION_NOT_FOUND", claim.claim_id, "Referenced evidence is absent or unauthorized: " + ", ".join(missing)))
        cited.update(item.document_id for item in resolved)
        if resolved and not any(claim.risk_code in item.risk_terms for item in resolved):
            findings.append(ValidationFinding("EVIDENCE_DOES_NOT_SUPPORT_CLAIM", claim.claim_id, "The cited evidence does not support the declared risk code."))
        for document in resolved:
            expected_revision = dict(context.document_revisions).get(document.document_id)
            if expected_revision != document.revision:
                findings.append(ValidationFinding("EVIDENCE_REVISION_MISMATCH", document.document_id, "Evidence changed after context compilation."))

    status = "PASS" if not findings else "BLOCKED"
    return ValidationReport(status, proposal_digest(proposal), tuple(findings), tuple(sorted(cited)))
