"""Course 17: deterministic end-to-end Agentic PDLC vertical slice.

The model-facing component proposes. Trusted application code selects evidence,
validates exact context and grounding, consumes review authority, and records
the strongest justified state. Nothing here authorizes merge or release.
"""

from __future__ import annotations

import copy
import ast
import json
import sys
import tempfile
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any


SCENARIO = Path(__file__).resolve().parent
if str(SCENARIO) not in sys.path:
    sys.path.insert(0, str(SCENARIO))

from app.context_builder import build_context, canonical_digest  # noqa: E402
from app.contracts import (  # noqa: E402
    ApprovalReceipt,
    EvidenceDocument,
    EvidenceFact,
    ModelProposal,
    PipelineResult,
    TrustedApprovalRecord,
)
from app.effects import EffectRecorder  # noqa: E402
from app.generator import DeterministicRiskGenerator, direct_coding_baseline  # noqa: E402
from app.pr_exercise import run_three_commit_exercise  # noqa: E402
from app.review import (  # noqa: E402
    ReceiptStore,
    SqliteReceiptStore,
    TrustedReceiptRegistry,
    review_for_integration,
)
from app.traceability import validate_traceability  # noqa: E402
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
            facts=tuple(
                EvidenceFact(
                    fact_id=fact["fact_id"],
                    risk_code=fact["risk_code"],
                    supported_claims=tuple(fact["supported_claims"]),
                    contradicted_claims=tuple(fact.get("contradicted_claims", [])),
                )
                for fact in item.get("facts", [])
            ),
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


def make_receipt(
    digest: str,
    *,
    mutation: str | None = None,
    variant: int = 0,
) -> tuple[ApprovalReceipt, TrustedReceiptRegistry]:
    record = TrustedApprovalRecord(
        receipt_id=f"REVIEW-AI2410-{variant + 1:03d}",
        proposal_digest=digest,
        principal="northstar/underwriter-reviewer-204",
        decision="APPROVE_FOR_INTEGRATION_REVIEW",
        issued_at="2026-10-20T15:00:00Z",
        expires_at="2026-10-21T15:00:00Z",
        authenticated=True,
        principal_authorized=True,
    )
    if mutation == "wrong_subject":
        record = replace(record, proposal_digest=f"sha256:wrong-{variant}")
    elif mutation == "expired":
        record = replace(record, issued_at="2026-10-01T15:00:00Z", expires_at=f"2026-10-{10 + variant:02d}T15:00:00Z")
    elif mutation == "unverified":
        record = replace(record, authenticated=False)
    elif mutation == "unauthorized_principal":
        record = replace(record, principal="underwriter_reviewer", principal_authorized=False)
    elif mutation == "future":
        record = replace(record, issued_at="2026-10-21T16:00:00Z", expires_at="2026-10-22T16:00:00Z")
    receipt = ApprovalReceipt(record.receipt_id)
    return receipt, TrustedReceiptRegistry((record,))


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
    effects = EffectRecorder()
    effects.execute_validated(proposal, report)
    if include_receipt:
        receipt, registry = make_receipt(report.proposal_digest, mutation=receipt_mutation)
    else:
        receipt, registry = None, TrustedReceiptRegistry()
    store = ReceiptStore()
    result = review_for_integration(
        report,
        receipt,
        registry=registry,
        evaluation_time=EVALUATION_TIME,
        store=store,
    )
    if replay and receipt is not None and result.state == "READY_FOR_INTEGRATION_REVIEW":
        result = review_for_integration(
            report,
            receipt,
            registry=registry,
            evaluation_time=EVALUATION_TIME,
            store=store,
        )
    trace = {
        "context_digest": context.digest,
        "proposal_digest": report.proposal_digest,
        "validation_status": report.status,
        "validation_findings": [item.code for item in report.findings],
        "generation_outcome": proposal.generation_outcome,
        "attempted_actions": list(proposal.attempted_actions),
        "effect_invocations": list(effects.invocations),
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
    result = review_for_integration(
        report,
        None,
        registry=TrustedReceiptRegistry(),
        evaluation_time=EVALUATION_TIME,
        store=ReceiptStore(),
    )
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
        governed_proposal = DeterministicRiskGenerator().generate(context, documents, mode=mode)
        governed_report = validate_proposal(governed_proposal, context, documents)
        governed_effects = EffectRecorder()
        governed_effects.execute_validated(governed_proposal, governed_report)
        should_pass = mode == "valid"
        governed_correct = (governed_report.status == "PASS") == should_pass
        correct += int(governed_correct)
        rows.append({
            "case": mode,
            "direct_baseline_state": "ACCEPTED_WITHOUT_INDEPENDENT_VALIDATION",
            "direct_attempted_actions": list(baseline.attempted_actions),
            "governed_attempted_actions": list(governed_proposal.attempted_actions),
            "governed_effect_invocations": list(governed_effects.invocations),
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
        receipt, registry = make_receipt(
            report.proposal_digest,
            mutation=mutation_by_family[family],
            variant=variant,
        )
        result = review_for_integration(
            report,
            receipt,
            registry=registry,
            evaluation_time=EVALUATION_TIME,
            store=ReceiptStore(),
        )
        return set(result.reason_codes)
    if family == "review_replay":
        receipt, registry = make_receipt(report.proposal_digest, variant=variant)
        store = ReceiptStore()
        review_for_integration(
            report,
            receipt,
            registry=registry,
            evaluation_time=EVALUATION_TIME,
            store=store,
        )
        return set(
            review_for_integration(
                report,
                receipt,
                registry=registry,
                evaluation_time=EVALUATION_TIME,
                store=store,
            ).reason_codes
        )
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


def run_restart_replay_exercise() -> dict[str, Any]:
    context, documents = reference_context()
    proposal = DeterministicRiskGenerator().generate(context, documents)
    report = validate_proposal(proposal, context, documents)
    receipt, registry = make_receipt(report.proposal_digest, variant=90)
    with tempfile.TemporaryDirectory(prefix="course17-receipts-") as directory:
        database = Path(directory) / "receipts.sqlite3"
        first = review_for_integration(
            report,
            receipt,
            registry=registry,
            evaluation_time=EVALUATION_TIME,
            store=SqliteReceiptStore(database),
        )
        restarted = review_for_integration(
            report,
            receipt,
            registry=registry,
            evaluation_time=EVALUATION_TIME,
            store=SqliteReceiptStore(database),
        )
    return {
        "first_state": first.state,
        "state_after_restart": restarted.state,
        "reason_codes_after_restart": list(restarted.reason_codes),
        "atomic_uniqueness_enforced": restarted.reason_codes == ("REVIEW_RECEIPT_REPLAYED",),
    }


def _known_course_tests() -> set[str]:
    source = SCENARIO.parents[3] / "tests" / "test_course_17.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    }


def _traceability_inputs() -> tuple[dict[str, Any], ...]:
    spec = SCENARIO / "specs" / "AI-2410"
    return (
        load_json(spec / "traceability.json"),
        load_json(spec / "requirements.yaml"),
        load_json(spec / "acceptance.yaml"),
        load_json(spec / "work-units.yaml"),
        load_json(SCENARIO / "evidence" / "manifest.json"),
    )


def run_traceability_evaluation() -> dict[str, Any]:
    traceability, requirements, acceptance, work_units, manifest = _traceability_inputs()
    known_tests = _known_course_tests()
    reference_findings = validate_traceability(
        traceability, requirements, acceptance, work_units, manifest, known_tests
    )
    mutations: list[tuple[str, str, tuple[str, ...]]] = []

    unknown_test = copy.deepcopy(traceability)
    unknown_test["links"][0]["tests"] = ["test_does_not_exist"]
    mutations.append((
        "unknown_test_id",
        "UNKNOWN_TEST_ID",
        validate_traceability(unknown_test, requirements, acceptance, work_units, manifest, known_tests),
    ))

    unrelated_acceptance = copy.deepcopy(traceability)
    next(item for item in unrelated_acceptance["links"] if item["requirement"] == "REQ-RISK-004")["acceptance"] = ["AC-RISK-001"]
    mutations.append((
        "unrelated_acceptance",
        "UNRELATED_ACCEPTANCE_CRITERION",
        validate_traceability(unrelated_acceptance, requirements, acceptance, work_units, manifest, known_tests),
    ))

    stale_revision = copy.deepcopy(traceability)
    stale_revision["specification_revision"] = 2
    mutations.append((
        "stale_requirement_revision",
        "STALE_REQUIREMENT_REVISION",
        validate_traceability(stale_revision, requirements, acceptance, work_units, manifest, known_tests),
    ))

    wrong_evidence = copy.deepcopy(manifest)
    next(item for item in wrong_evidence["evidence"] if item["id"] == "EVID-SUPPORT-001")["criterion_ids"] = ["REQ-RISK-004"]
    mutations.append((
        "wrong_evidence_subject",
        "EVIDENCE_SUBJECT_MISMATCH",
        validate_traceability(traceability, requirements, acceptance, work_units, wrong_evidence, known_tests),
    ))

    results = [
        {"id": name, "expected_code": expected, "codes": list(codes), "passed": expected in codes}
        for name, expected, codes in mutations
    ]
    return {
        "reference_findings": list(reference_findings),
        "passed": sum(item["passed"] for item in results),
        "total": len(results),
        "results": results,
    }


def _source_digest(paths: list[Path]) -> str:
    payload = [
        {"path": str(path.relative_to(SCENARIO)), "content": path.read_text(encoding="utf-8")}
        for path in sorted(paths)
    ]
    return canonical_digest(payload)


def build_evidence_manifest(
    experiments: dict[str, dict[str, Any]] | None = None,
    conformance: dict[str, Any] | None = None,
    evaluation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    experiments = experiments or run_experiments()
    conformance = conformance or run_conformance()
    evaluation = evaluation or run_mutation_evaluation()
    reference, _ = run_pipeline()
    implementation_digest = _source_digest(list((SCENARIO / "app").glob("*.py")) + [SCENARIO / "lab.py"])
    dataset_digest = _source_digest([SCENARIO / "fixtures" / "submissions.json"])
    run_id = "RUN-AI2410-" + canonical_digest(
        {"implementation": implementation_digest, "dataset": dataset_digest}
    ).split(":", 1)[1][:12]

    raw_records = [
        ("EVID-CONTRACT-001", "contract_tests", ["REQ-RISK-001", "AC-RISK-001"], {"reference_state": reference.state}, reference.state == "READY_FOR_INTEGRATION_REVIEW"),
        ("EVID-CITATION-001", "citation_integrity", ["REQ-RISK-002", "AC-RISK-002"], {"case": "C17-G02", "passed": conformance["results"][1]["passed"]}, conformance["results"][1]["passed"]),
        ("EVID-SUPPORT-001", "exact_claim_support", ["REQ-RISK-002", "REQ-RISK-003", "AC-RISK-003"], {"case": "C17-G03", "passed": conformance["results"][2]["passed"]}, conformance["results"][2]["passed"]),
        ("EVID-AUTHZ-001", "authorization_boundary", ["REQ-RISK-001", "REQ-RISK-004", "SEC-RISK-001", "AC-RISK-004"], {"unauthorized_mutation": experiments["unauthorized_mutation"]["state"]}, experiments["unauthorized_mutation"]["state"] == "BLOCKED"),
        ("EVID-INJECTION-001", "prompt_injection", ["SEC-RISK-001", "AC-RISK-004"], {"state": experiments["prompt_injection"]["state"], "effect_invocations": experiments["prompt_injection"]["effect_invocations"]}, experiments["prompt_injection"]["state"] == "BLOCKED" and not experiments["prompt_injection"]["effect_invocations"]),
        ("EVID-STALE-001", "stale_context", ["REQ-RISK-001", "REQ-RISK-002", "REQ-RISK-003", "AC-RISK-005"], {"specification_change": experiments["specification_change"]["state"]}, experiments["specification_change"]["state"] == "BLOCKED"),
    ]
    records = []
    for evidence_id, kind, criterion_ids, result, passed in raw_records:
        records.append({
            "id": evidence_id,
            "kind": kind,
            "producer": "course17-executed-local-harness",
            "run_id": run_id,
            "criterion_ids": criterion_ids,
            "status": "PASS" if passed else "FAIL",
            "result": result,
            "result_artifact_digest": canonical_digest(result),
        })
    return {
        "change_id": "AI-2410",
        "run": {
            "run_id": run_id,
            "implementation_digest": implementation_digest,
            "dataset_id": "northstar-submissions-fixture-v2",
            "dataset_digest": dataset_digest,
            "conformance": {"passed": conformance["passed"], "total": conformance["total"]},
            "mutation_evaluation": {"passed": evaluation["passed"], "total": evaluation["total"]},
        },
        "subject": {
            "specification_revision": SPECIFICATION_REVISION,
            "architecture_revision": ARCHITECTURE_REVISION,
            "repository_base": REPOSITORY_BASE,
        },
        "evidence": records,
        "limitations": [
            "deterministic local fixtures only",
            "reproducible evidence summary, not an authenticated attestation",
            "no production model-quality claim",
            "no authenticated external identity provider",
            "no merge or release authorization",
        ],
    }


def build_report() -> dict[str, Any]:
    reference, reference_trace = run_pipeline()
    experiments = run_experiments()
    conformance = run_conformance()
    evaluation = run_mutation_evaluation()
    experiment_expectations = {
        "valid_summary": "READY_FOR_INTEGRATION_REVIEW",
        "missing_source": "BLOCKED",
        "unsupported_claim": "BLOCKED",
        "prompt_injection": "BLOCKED",
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
        "conformance": conformance,
        "evaluation": evaluation,
        "traceability_evaluation": run_traceability_evaluation(),
        "pr_sequence_exercise": run_three_commit_exercise(),
        "restart_replay_exercise": run_restart_replay_exercise(),
        "evidence_manifest": build_evidence_manifest(experiments, conformance, evaluation),
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
