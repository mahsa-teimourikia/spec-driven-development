"""Current production boundary before JIRA-4821 is implemented."""

from __future__ import annotations

from typing import Protocol, Sequence


class ModelGateway(Protocol):
    def generate(
        self,
        question: str,
        passages: Sequence[dict[str, str]],
        *,
        route: str,
        region: str,
        prompt_version: str,
    ) -> str: ...


def ask_policy_question(
    question: str,
    passages: Sequence[dict[str, str]],
    gateway: ModelGateway,
) -> dict[str, object]:
    """JIRA-4821 has not been implemented in the baseline."""

    raise NotImplementedError("JIRA-4821 is not implemented")
