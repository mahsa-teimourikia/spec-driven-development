"""Governed JIRA-4821 candidate using the approved model-gateway boundary."""

from __future__ import annotations

import re
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


class Telemetry(Protocol):
    def record(self, event: str, attributes: dict[str, object]) -> None: ...


class NullTelemetry:
    def record(self, event: str, attributes: dict[str, object]) -> None:
        del event, attributes


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9]+", text.lower()) if len(term) > 3}


def ask_policy_question(
    question: str,
    passages: Sequence[dict[str, str]],
    gateway: ModelGateway,
    telemetry: Telemetry | None = None,
) -> dict[str, object]:
    telemetry = telemetry or NullTelemetry()
    if not question.strip():
        raise ValueError("question is required")
    question_terms = _terms(question)
    relevant = [passage for passage in passages if question_terms & _terms(passage["text"])]
    if not relevant:
        result = {"answer": None, "citations": [], "status": "insufficient_evidence"}
        telemetry.record(
            "policy_qa.completed",
            {
                "status": "insufficient_evidence",
                "citation_count": 0,
                "route": "not_called",
                "region": "ca-central-1",
                "prompt_version": "policy-qa-v1",
            },
        )
        return result
    answer = gateway.generate(
        question,
        relevant,
        route="approved_ai_gateway",
        region="ca-central-1",
        prompt_version="policy-qa-v1",
    )
    result = {
        "answer": answer,
        "citations": [passage["id"] for passage in relevant],
        "status": "answered",
    }
    telemetry.record(
        "policy_qa.completed",
        {
            "status": "answered",
            "citation_count": len(relevant),
            "route": "approved_ai_gateway",
            "region": "ca-central-1",
            "prompt_version": "policy-qa-v1",
        },
    )
    return result
