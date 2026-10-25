"""A recording effect boundary used to prove blocked attempts stay non-effects."""

from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import ModelProposal, ValidationReport


@dataclass
class EffectRecorder:
    """Training spy. Production effects require their own authorization service."""

    invocations: list[str] = field(default_factory=list)

    def execute_validated(self, proposal: ModelProposal, report: ValidationReport) -> None:
        if report.status != "PASS":
            return
        # This slice intentionally has no externally executable model action.
        # A PASS only means the proposal may advance to human review.
        if proposal.attempted_actions:
            raise RuntimeError("validated proposals cannot contain effect requests")

