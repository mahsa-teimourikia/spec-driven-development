"""Trusted validation for pinned context, grounding, and authority boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from .context_builder import canonical_digest, context_is_canonical
from .contracts import EvidenceDocument, ExecutionContext, ModelProposal, ValidationFinding, ValidationReport


ALLOWED_MODEL_ACTIONS = {"create_summary_proposal"}


def proposal_digest(proposal: ModelProposal) -> str:
    return canonical_digest(asdict(proposal))


def validate_proposal(
    proposal: ModelProposal,
    context: ExecutionContext,
    documents: Mapping[str, EvidenceDocument],
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
    if proposal.generation_outcome != "PROPOSED":
        for reason in proposal.generation_reasons or (proposal.generation_outcome,):
            findings.append(ValidationFinding(reason, proposal.proposal_id, "The generator abstained instead of asserting an unsupported conclusion."))

    forbidden = sorted(set(proposal.attempted_actions) - ALLOWED_MODEL_ACTIONS)
    if forbidden:
        findings.append(ValidationFinding("UNAUTHORIZED_SIDE_EFFECT", proposal.proposal_id, "Model output requested protected actions: " + ", ".join(forbidden)))

    cited: set[str] = set()
    approved_revisions = dict(context.document_revisions)
    for claim in proposal.claims:
        if not claim.evidence_ids:
            findings.append(ValidationFinding("CITATION_REQUIRED", claim.claim_id, "Every material claim requires source evidence."))
            continue
        resolved = [documents[item] for item in claim.evidence_ids if item in documents]
        missing = sorted(set(claim.evidence_ids) - set(documents))
        if missing:
            findings.append(ValidationFinding("CITATION_NOT_FOUND", claim.claim_id, "Referenced evidence is absent or unauthorized: " + ", ".join(missing)))
        cited.update(item.document_id for item in resolved)
        for document in resolved:
            if not document.authorized:
                findings.append(ValidationFinding("EVIDENCE_NOT_AUTHORIZED", document.document_id, "The cited document is not authorized by the trusted evidence service."))
            if document.submission_id != context.submission_id:
                findings.append(ValidationFinding("EVIDENCE_SUBMISSION_MISMATCH", document.document_id, "The cited document belongs to a different submission."))
            if document.document_id not in approved_revisions:
                findings.append(ValidationFinding("EVIDENCE_OUTSIDE_APPROVED_CONTEXT", document.document_id, "The cited document was not selected into the approved execution context."))
            expected_revision = approved_revisions.get(document.document_id)
            if expected_revision != document.revision:
                findings.append(ValidationFinding("EVIDENCE_REVISION_MISMATCH", document.document_id, "Evidence changed after context compilation."))

        relevant_facts = [
            fact
            for document in resolved
            for fact in document.facts
            if fact.risk_code == claim.risk_code
        ]
        if resolved and not relevant_facts:
            findings.append(ValidationFinding("CITATION_NOT_RELEVANT", claim.claim_id, "The cited evidence exists but does not concern the claimed risk topic."))
            findings.append(ValidationFinding("EVIDENCE_DOES_NOT_SUPPORT_CLAIM", claim.claim_id, "Citation existence does not establish claim support."))
        elif relevant_facts and not any(claim.text in fact.supported_claims for fact in relevant_facts):
            if any(claim.text in fact.contradicted_claims for fact in relevant_facts):
                findings.append(ValidationFinding("EVIDENCE_CONTRADICTS_CLAIM", claim.claim_id, "Structured source facts contradict the exact claim text."))
            else:
                findings.append(ValidationFinding("EVIDENCE_INSUFFICIENT_FOR_CLAIM", claim.claim_id, "The evidence concerns the topic but does not support the exact claim."))
            findings.append(ValidationFinding("EVIDENCE_DOES_NOT_SUPPORT_CLAIM", claim.claim_id, "The exact claim is not supported by a cited structured fact."))

    status = "PASS" if not findings else "BLOCKED"
    return ValidationReport(status, proposal_digest(proposal), tuple(findings), tuple(sorted(cited)))
