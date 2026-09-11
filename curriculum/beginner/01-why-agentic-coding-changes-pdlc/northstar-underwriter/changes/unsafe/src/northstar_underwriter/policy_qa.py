"""INTENTIONALLY UNSAFE training candidate: expected to fail Course 01 gates.

The credential-like sentinel below is inert and must never be replaced with a
real secret. It exists only so the lab's policy scanner has a safe fixture.
"""

from __future__ import annotations

from typing import Protocol, Sequence


MODEL_API_TOKEN = "EXAMPLE_CREDENTIAL_DO_NOT_USE"


class ModelGateway(Protocol):
    def generate(self, question, passages, *, route, region, prompt_version): ...


def ask_policy_question(
    question: str,
    passages: Sequence[dict[str, str]],
    gateway: ModelGateway,
) -> dict[str, object]:
    del gateway
    if not question.strip():
        raise ValueError("question is required")
    return {
        "answer_text": "A generated best guess from a direct public model call.",
        "citations": [],
        "status": "answered",
        "provider_route": "public_model_api",
        "provider_region": "us-east-1",
    }
