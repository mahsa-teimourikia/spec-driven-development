"""Deterministic conformance evaluation for the installed policy-Q&A candidate."""

from __future__ import annotations

import json
from pathlib import Path

from northstar_underwriter.policy_qa import ask_policy_question


HERE = Path(__file__).resolve().parent


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def generate(self, question, passages, *, route, region, prompt_version):
        self.calls.append(
            {
                "route": route,
                "region": region,
                "prompt_version": prompt_version,
            }
        )
        return f"Evidence-linked answer for {question!r} from {len(passages)} passage(s)."


def evaluate() -> dict[str, object]:
    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    safety_violations = 0
    for case in cases:
        gateway = RecordingGateway()
        try:
            result = ask_policy_question(case["question"], case["passages"], gateway)
            status = result.get("status")
            citations = result.get("citations", [])
            provider_route = result.get("provider_route")
            passed = (
                status == case["expected_status"]
                and len(citations) >= case["minimum_citations"]
                and len(gateway.calls) == case["gateway_calls"]
                and provider_route is None
            )
            if status == "answered" and not citations:
                safety_violations += 1
        except Exception as exc:
            result = {"error": type(exc).__name__}
            passed = False
        results.append(
            {
                "case_id": case["case_id"],
                "passed": passed,
                "observed_status": result.get("status"),
                "citation_count": len(result.get("citations", [])),
                "gateway_calls": len(gateway.calls),
            }
        )
    passed_cases = sum(item["passed"] for item in results)
    total_cases = len(results)
    return {
        "population": "four labelled deterministic contract cases",
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "conformance_rate": passed_cases / total_cases if total_cases else 0.0,
        "safety_violations": safety_violations,
        "cases": results,
        "limitations": [
            "not a model-quality benchmark",
            "does not establish tenant isolation or deployed residency",
            "does not represent the distribution of production underwriting questions",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
