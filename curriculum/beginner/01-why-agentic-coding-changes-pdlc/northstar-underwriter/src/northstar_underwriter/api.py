"""Existing API boundary that JIRA-4821 will extend."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .auth import require_underwriter
from .policy_qa import ModelGateway, ask_policy_question


def question_endpoint(
    payload: Mapping[str, str],
    claims: Mapping[str, str],
    passages: Sequence[dict[str, str]],
    gateway: ModelGateway,
) -> dict[str, object]:
    require_underwriter(claims)
    return ask_policy_question(payload.get("question", ""), passages, gateway)
