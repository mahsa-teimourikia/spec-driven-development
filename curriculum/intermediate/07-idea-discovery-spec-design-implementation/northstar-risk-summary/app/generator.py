"""Credential-free proposal generator and deliberately unsafe baseline."""

from __future__ import annotations

from .contracts import EvidenceDocument, ExecutionContext, ModelProposal, RiskClaim


RISK_TEXT = {
    "ROOF_AGE": "The roof age requires underwriting review.",
    "VACANCY": "The property vacancy status is a material risk factor.",
    "LOSS_HISTORY": "Recent loss history requires underwriting review.",
    "FLOOD": "The property has a material flood exposure.",
}


class DeterministicRiskGenerator:
    """Generate proposals only; this object cannot mutate underwriting state."""

    def generate(
        self,
        context: ExecutionContext,
        documents: dict[str, EvidenceDocument],
        *,
        mode: str = "valid",
    ) -> ModelProposal:
        first = next(iter(documents.values()))
        risk_code = first.risk_terms[0]
        evidence_ids: tuple[str, ...] = (first.document_id,)
        attempted_actions: tuple[str, ...] = ()
        context_digest = context.digest
        spec_revision = context.specification_revision
        architecture_revision = context.architecture_revision
        submission_id = context.submission_id

        if mode == "missing_source":
            evidence_ids = ("DOC-NOT-FOUND",)
        elif mode == "unsupported_claim":
            risk_code = "FLOOD"
        elif mode == "prompt_injection":
            # Source text may contain instruction-shaped content, but the generator
            # consumes only the typed risk terms selected by trusted code.
            pass
        elif mode == "stale_context":
            context_digest = "sha256:stale"
        elif mode == "stale_specification":
            spec_revision -= 1
        elif mode == "stale_architecture":
            architecture_revision = "ADR-RISK-008@1"
        elif mode == "unauthorized_mutation":
            attempted_actions = ("modify_underwriting_decision",)
        elif mode == "unauthorized_send":
            attempted_actions = ("send_broker_email",)
        elif mode == "wrong_submission":
            submission_id = "SUB-OTHER"
        elif mode != "valid":
            raise ValueError(f"unknown deterministic mode: {mode}")

        return ModelProposal(
            proposal_id=f"PROP-{context.submission_id}-001",
            submission_id=submission_id,
            context_digest=context_digest,
            specification_revision=spec_revision,
            architecture_revision=architecture_revision,
            claims=(RiskClaim("CLAIM-001", risk_code, RISK_TEXT[risk_code], evidence_ids),),
            attempted_actions=attempted_actions,
        )


def direct_coding_baseline(
    context: ExecutionContext,
    documents: dict[str, EvidenceDocument],
    *,
    mode: str,
) -> ModelProposal:
    """Educational anti-pattern: trust output shape without validating authority."""
    proposal = DeterministicRiskGenerator().generate(context, documents, mode=mode)
    if mode == "prompt_injection":
        proposal = ModelProposal(
            proposal_id=proposal.proposal_id,
            submission_id=proposal.submission_id,
            context_digest=proposal.context_digest,
            specification_revision=proposal.specification_revision,
            architecture_revision=proposal.architecture_revision,
            claims=proposal.claims,
            attempted_actions=("send_broker_email",),
        )
    return proposal
