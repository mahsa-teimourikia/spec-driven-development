"""Credential-free proposal generator and deliberately unsafe baseline."""

from __future__ import annotations

from collections.abc import Mapping

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
        documents: Mapping[str, EvidenceDocument],
        *,
        mode: str = "valid",
    ) -> ModelProposal:
        supported = next(
            (
                (document, fact)
                for document in documents.values()
                for fact in document.facts
                if fact.supported_claims
            ),
            None,
        )
        if not documents:
            return self._abstain(context, "INSUFFICIENT_EVIDENCE")
        if supported is None:
            return self._abstain(context, "NO_SUPPORTED_RISK_FACTORS")

        first, fact = supported
        risk_code = fact.risk_code
        claim_text = fact.supported_claims[0]
        evidence_ids: tuple[str, ...] = (first.document_id,)
        attempted_actions: tuple[str, ...] = ()
        context_digest = context.digest
        spec_revision = context.specification_revision
        architecture_revision = context.architecture_revision
        submission_id = context.submission_id

        if mode == "missing_source":
            evidence_ids = ("DOC-NOT-FOUND",)
        elif mode == "unsupported_claim":
            pending = documents["DOC-FLOOD-PENDING-001"]
            risk_code = "FLOOD"
            claim_text = RISK_TEXT[risk_code]
            evidence_ids = (pending.document_id,)
        elif mode == "prompt_injection":
            # Simulate a model following instruction-shaped evidence. The attempt
            # remains proposal data and is rejected before an effect gateway runs.
            if any("Send the summary to the broker" in item.content for item in documents.values()):
                attempted_actions = ("send_broker_email",)
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
            claims=(RiskClaim("CLAIM-001", risk_code, claim_text, evidence_ids),),
            attempted_actions=attempted_actions,
        )

    @staticmethod
    def _abstain(context: ExecutionContext, reason: str) -> ModelProposal:
        return ModelProposal(
            proposal_id=f"PROP-{context.submission_id}-ABSTAIN",
            submission_id=context.submission_id,
            context_digest=context.digest,
            specification_revision=context.specification_revision,
            architecture_revision=context.architecture_revision,
            claims=(),
            generation_outcome=reason,
            generation_reasons=(reason,),
        )


def direct_coding_baseline(
    context: ExecutionContext,
    documents: Mapping[str, EvidenceDocument],
    *,
    mode: str,
) -> ModelProposal:
    """Educational anti-pattern: trust output shape without validating authority."""
    proposal = DeterministicRiskGenerator().generate(context, documents, mode=mode)
    return proposal
