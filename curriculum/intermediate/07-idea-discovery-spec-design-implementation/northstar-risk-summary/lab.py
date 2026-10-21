"""Course 17: deterministic end-to-end Agentic PDLC vertical slice.

The model-facing component proposes. Trusted application code selects evidence,
validates exact context and grounding, consumes review authority, and records
the strongest justified state. Nothing here authorizes merge or release.
"""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any


SCENARIO = Path(__file__).resolve().parent
if str(SCENARIO) not in sys.path:
    sys.path.insert(0, str(SCENARIO))

from app.context_builder import build_context, canonical_digest  # noqa: E402
from app.contracts import ApprovalReceipt, EvidenceDocument, ModelProposal, PipelineResult  # noqa: E402
from app.generator import DeterministicRiskGenerator, direct_coding_baseline  # noqa: E402
from app.review import ReceiptStore, review_for_integration  # noqa: E402
from app.validator import proposal_digest, validate_proposal  # noqa: E402


EVALUATION_TIME = "2026-10-20T16:00:00Z"
SPECIFICATION_REVISION = 3
ARCHITECTURE_REVISION = "ADR-RISK-008@2"
REPOSITORY_BASE = "northstar-training-base-2410"
EXPECTED_EXPERIMENTS = (
    "valid_summary",
    "missing_source",
    "unsupported_claim",
    "prompt_injection",
    "stale_context",
    "unauthorized_mutation",
    "specification_change",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_documents() -> list[EvidenceDocument]:
    fixture = load_json(SCENARIO / "fixtures" / "submissions.json")
    return [
        EvidenceDocument(
            document_id=item["document_id"],
            submission_id=item["submission_id"],
            revision=item["revision"],
            content=item["content"],
            risk_terms=tuple(item["risk_terms"]),
            authorized=item["authorized"],
        )
        for item in fixture["documents"]
    ]


def reference_context(*, specification_revision: int = SPECIFICATION_REVISION):
    return build_context(
        "SUB-2410-001",
        load_documents(),
        specification_revision=specification_revision,
        architecture_revision=ARCHITECTURE_REVISION,
        repository_base=REPOSITORY_BASE,
    )


def make_receipt(digest: str, *, mutation: str | None = None, variant: int = 0) -> ApprovalReceipt:
    receipt = ApprovalReceipt(
        receipt_id=f"REVIEW-AI2410-{variant + 1:03d}",
        proposal_digest=digest,
        principal="northstar/underwriter-reviewer-204",
        decision="APPROVE_FOR_INTEGRATION_REVIEW",
        issued_at="2026-10-20T15:00:00Z",
        expires_at="2026-10-21T15:00:00Z",
        identity_verified=True,
        attestation_verified=True,
    )
    if mutation == "wrong_subject":
        receipt = replace(receipt, proposal_digest=f"sha256:wrong-{variant}")
    elif mutation == "expired":
        receipt = replace(receipt, issued_at="2026-10-01T15:00:00Z", expires_at=f"2026-10-{10 + variant:02d}T15:00:00Z")
    elif mutation == "unverified":
        receipt = replace(
            receipt,
            identity_verified=variant % 2 == 1,
            attestation_verified=variant % 2 == 0,
        )
    return receipt


def run_pipeline(
    *,
    mode: str = "valid",
    context=None,
    documents: dict[str, EvidenceDocument] | None = None,
    receipt_mutation: str | None = None,
    include_receipt: bool = True,
    replay: bool = False,
) -> tuple[PipelineResult, dict[str, Any]]:
    if context is None or documents is None:
        context, documents = reference_context()
    proposal = DeterministicRiskGenerator().generate(context, documents, mode=mode)
    report = validate_proposal(proposal, context, documents)
    receipt = make_receipt(report.proposal_digest, mutation=receipt_mutation) if include_receipt else None
    store = ReceiptStore()
    result = review_for_integration(report, receipt, evaluation_time=EVALUATION_TIME, store=store)
    if replay and receipt is not None and result.state == "READY_FOR_INTEGRATION_REVIEW":
        result = review_for_integration(report, receipt, evaluation_time=EVALUATION_TIME, store=store)
    trace = {
        "context_digest": context.digest,
        "proposal_digest": report.proposal_digest,
        "validation_status": report.status,
        "validation_findings": [item.code for item in report.findings],
        "result_state": result.state,
        "reason_codes": list(result.reason_codes),
        "release_authorized": result.release_authorized,
    }
    return result, trace


def run_specification_change() -> tuple[PipelineResult, dict[str, Any]]:
    old_context, old_documents = reference_context(specification_revision=3)
    proposal = DeterministicRiskGenerator().generate(old_context, old_documents)
    new_context, new_documents = reference_context(specification_revision=4)
    report = validate_proposal(proposal, new_context, new_documents)
    result = review_for_integration(report, None, evaluation_time=EVALUATION_TIME, store=ReceiptStore())
    return result, {
        "old_context_digest": old_context.digest,
        "new_context_digest": new_context.digest,
        "proposal_digest": report.proposal_digest,
        "validation_findings": [item.code for item in report.findings],
        "revalidation_required": True,
        "specification_authority_preserved": True,
    }


def run_experiments() -> dict[str, dict[str, Any]]:
    modes = {
        "valid_summary": "valid",
        "missing_source": "missing_source",
        "unsupported_claim": "unsupported_claim",
        "prompt_injection": "prompt_injection",
        "stale_context": "stale_context",
        "unauthorized_mutation": "unauthorized_mutation",
    }
    experiments: dict[str, dict[str, Any]] = {}
    for name, mode in modes.items():
        result, trace = run_pipeline(mode=mode)
        experiments[name] = {"state": result.state, **trace}
    result, trace = run_specification_change()
    experiments["specification_change"] = {"state": result.state, **trace}
    return experiments


def compare_baseline() -> dict[str, Any]:
    context, documents = reference_context()
    cases = ("valid", "missing_source", "unsupported_claim", "prompt_injection", "stale_context", "unauthorized_mutation", "unauthorized_send")
    rows: list[dict[str, Any]] = []
    correct = 0
    for mode in cases:
        baseline = direct_coding_baseline(context, documents, mode=mode)
        governed_report = validate_proposal(DeterministicRiskGenerator().generate(context, documents, mode=mode), context, documents)
        should_pass = mode in {"valid", "prompt_injection"}
        governed_correct = (governed_report.status == "PASS") == should_pass
        correct += int(governed_correct)
        rows.append({
            "case": mode,
            "direct_baseline_state": "ACCEPTED_WITHOUT_INDEPENDENT_VALIDATION",
            "direct_attempted_actions": list(baseline.attempted_actions),
            "governed_state": governed_report.status,
            "governed_findings": [item.code for item in governed_report.findings],
            "expected_pass": should_pass,
            "governed_correct": governed_correct,
        })
    return {
        "population": len(rows),
        "governed_correct": correct,
        "governed_accuracy": {"numerator": correct, "denominator": len(rows), "value": correct / len(rows)},
        "direct_baseline_validated": 0,
        "claim": "deterministic teaching cases, not a model-quality or production-readiness benchmark",
        "cases": rows,
    }


def _case_outcome(case: dict[str, Any]) -> tuple[str, set[str]]:
    kind = case["kind"]
    if kind == "specification_change":
        result, trace = run_specification_change()
        return result.state, set(trace["validation_findings"])
    result, trace = run_pipeline(
        mode=case.get("mode", "valid"),
        receipt_mutation=case.get("receipt_mutation"),
        include_receipt=case.get("include_receipt", True),
        replay=case.get("replay", False),
    )
    return result.state, set(trace["validation_findings"]) | set(result.reason_codes)


def run_conformance() -> dict[str, Any]:
    cases = load_json(SCENARIO / "conformance-suite.json")["cases"]
    results = []
    for case in cases:
        state, codes = _case_outcome(case)
        passed = state == case["expected_state"] and set(case.get("expected_codes", [])).issubset(codes)
        results.append({"id": case["id"], "passed": passed, "actual_state": state, "actual_codes": sorted(codes)})
    return {
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "claim": "twelve named end-to-end fixtures, not general PDLC assurance",
        "results": results,
    }


def _mutation_codes(family: str, variant: int) -> set[str]:
    context, documents = reference_context()
    generator = DeterministicRiskGenerator()
    mode_by_family = {
        "unknown_citation": "missing_source",
        "unsupported_claim": "unsupported_claim",
        "stale_specification": "stale_specification",
        "stale_architecture": "stale_architecture",
        "stale_context": "stale_context",
        "wrong_submission": "wrong_submission",
        "unauthorized_mutation": "unauthorized_mutation",
        "unauthorized_send": "unauthorized_send",
    }
    if family in mode_by_family:
        proposal = generator.generate(context, documents, mode=mode_by_family[family])
        report = validate_proposal(proposal, context, documents)
        return {item.code for item in report.findings}
    proposal = generator.generate(context, documents)
    if family == "evidence_revision":
        key = next(iter(documents))
        documents = copy.deepcopy(documents)
        documents[key] = replace(documents[key], revision=documents[key].revision + variant + 1)
        return {item.code for item in validate_proposal(proposal, context, documents).findings}
    report = validate_proposal(proposal, context, documents)
    mutation_by_family = {
        "review_subject": "wrong_subject",
        "expired_review": "expired",
        "unverified_review": "unverified",
    }
    if family in mutation_by_family:
        result = review_for_integration(
            report,
            make_receipt(report.proposal_digest, mutation=mutation_by_family[family], variant=variant),
            evaluation_time=EVALUATION_TIME,
            store=ReceiptStore(),
        )
        return set(result.reason_codes)
    if family == "review_replay":
        receipt = make_receipt(report.proposal_digest, variant=variant)
        store = ReceiptStore()
        review_for_integration(report, receipt, evaluation_time=EVALUATION_TIME, store=store)
        return set(review_for_integration(report, receipt, evaluation_time=EVALUATION_TIME, store=store).reason_codes)
    raise ValueError(f"unknown mutation family: {family}")


def run_mutation_evaluation() -> dict[str, Any]:
    cases = load_json(SCENARIO / "evaluation-cases.json")["cases"]
    results = []
    for case in cases:
        codes = _mutation_codes(case["family"], case["variant"])
        passed = case["expected_code"] in codes
        results.append({"id": case["id"], "passed": passed, "codes": sorted(codes)})
    return {
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "claim": "labelled mutation-fixture coverage, not general workflow correctness",
        "results": results,
    }


def build_report() -> dict[str, Any]:
    reference, reference_trace = run_pipeline()
    experiments = run_experiments()
    experiment_expectations = {
        "valid_summary": "READY_FOR_INTEGRATION_REVIEW",
        "missing_source": "BLOCKED",
        "unsupported_claim": "BLOCKED",
        "prompt_injection": "READY_FOR_INTEGRATION_REVIEW",
        "stale_context": "BLOCKED",
        "unauthorized_mutation": "BLOCKED",
        "specification_change": "BLOCKED",
    }
    experiment_passed = sum(experiments[name]["state"] == expected for name, expected in experiment_expectations.items())
    return {
        "change_id": "AI-2410",
        "thesis": "intent becomes bounded implementation and independently verified evidence without transferring underwriting or release authority to a model",
        "reference": {"state": reference.state, **reference_trace},
        "experiments": {
            "passed": experiment_passed,
            "total": len(experiment_expectations),
            "results": experiments,
        },
        "baseline_comparison": compare_baseline(),
        "conformance": run_conformance(),
        "evaluation": run_mutation_evaluation(),
        "release_boundary": {
            "integration_review_eligible": reference.state == "READY_FOR_INTEGRATION_REVIEW",
            "merge_authorized": False,
            "deployment_authorized": False,
            "business_outcome_proven": False,
        },
        "report_digest": canonical_digest({"change": "AI-2410", "reference_proposal": reference.proposal_digest}),
    }


def main() -> None:
    print(json.dumps(build_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
