"""Executable Course 22 scenarios and event-based strategy comparison."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Iterable

from .control_plane import ProtectedControlPlane, REVIEWER_GRANTS, SCOPE_APPROVERS, TRUSTED_PR_AUTHORS
from .git_harness import GitCandidate, TrustedGitHarness
from .review_engine import ApprovalRecord, EvidenceRecord, PullRequestSubject, ReviewerGrant, ReviewEngine

NOW = datetime(2026, 2, 2, 15, 0, tzinfo=timezone.utc)
TRUSTED_REVIEWERS = {principal: frozenset({role}) for principal, role, _, _ in SCOPE_APPROVERS.values()}
ROOT = Path(__file__).resolve().parents[1]


def approved_digests(root: Path) -> tuple[str, str]:
    return (
        ReviewEngine.digest((root / "specifications/approved-requirements.json").read_bytes()),
        ReviewEngine.digest((root / "contracts/classification-v2.schema.json").read_bytes()),
    )


def reference_candidate(root: Path) -> GitCandidate:
    del root
    return TrustedGitHarness().create_candidate("ai-service", {
        "src/classifier.py": "def route(ambiguous: bool, confidence: float = 0.0) -> str:\n    return 'review' if ambiguous else 'straight_through'\n\ndef provenance(document_id: str) -> dict[str, str]:\n    return {'document_id': document_id}\n",
        "tests/test_classifier.py": "from src.classifier import route\n\ndef test_ambiguous_routes_to_review():\n    assert route(ambiguous=True, confidence=0.98) == 'review'\n",
    })


def make_subject(root: Path, candidate: GitCandidate, *, allowed_paths: tuple[str, ...] = ("src", "tests"), work_unit: str = "WU-AI") -> PullRequestSubject:
    spec, contract = approved_digests(root)
    return PullRequestSubject("PR-AI-2500-03", "AI-2500", work_unit, "agent-ai-a", candidate.repository, candidate.base_commit, candidate.head_commit, "REQ-DOC-2500", spec, "CONTRACT-CLASSIFICATION-001", contract, allowed_paths)


def protected_context(subject: PullRequestSubject, candidate: GitCandidate, root: Path = ROOT) -> ProtectedControlPlane:
    return ProtectedControlPlane(root, subject, candidate, now=NOW)


def approval(subject: PullRequestSubject, candidate: GitCandidate, scope: str) -> ApprovalRecord:
    return protected_context(subject, candidate).approval(scope)


def ci_evidence(subject: PullRequestSubject, candidate: GitCandidate) -> EvidenceRecord:
    return protected_context(subject, candidate).acceptance_evidence()


def evaluate(subject: PullRequestSubject, candidate: GitCandidate, approvals: Iterable[ApprovalRecord], evidence: Iterable[EvidenceRecord], *, grants: tuple[ReviewerGrant, ...] = REVIEWER_GRANTS, approval_registry: dict[str, ApprovalRecord] | None = None, evidence_registry: dict[str, EvidenceRecord] | None = None):
    control = protected_context(subject, candidate)
    if approval_registry is not None:
        control.approvals = dict(approval_registry)
    if evidence_registry is not None:
        control.evidence = dict(evidence_registry)
    return control.engine(grants=grants).evaluate(subject, candidate, approvals, evidence, now=NOW)


def reference_assessment(root: Path):
    candidate = reference_candidate(root)
    subject = make_subject(root, candidate)
    approved = approval(subject, candidate, "implementation")
    evidence = ci_evidence(subject, candidate)
    return candidate, subject, evaluate(subject, candidate, [approved], [evidence])


def git_backed_experiments(root: Path) -> dict[str, bool]:
    harness = TrustedGitHarness()
    results: dict[str, bool] = {}

    protected_spec = harness.create_candidate("ai-service", {"specifications/new-policy.json": "{}\n"})
    subject = make_subject(root, protected_spec, allowed_paths=("specifications",), work_unit="WU-SPEC")
    decision = evaluate(subject, protected_spec, [], [ci_evidence(subject, protected_spec)])
    results["unauthorized_spec_change"] = "UNAUTHORIZED_SPEC_CHANGE" in {f.code for f in decision.findings}

    contract = harness.create_candidate("ai-service", {"contracts/classification-v3.schema.json": "{}\n"})
    subject = make_subject(root, contract, allowed_paths=("contracts",), work_unit="WU-CONTRACT")
    decision = evaluate(subject, contract, [], [ci_evidence(subject, contract)])
    results["contract_owner_missing"] = "CONTRACT_APPROVAL_MISSING" in {f.code for f in decision.findings}

    candidate = reference_candidate(root)
    subject = make_subject(root, candidate)
    stale = replace(approval(subject, candidate, "implementation"), head_commit=subject.base_commit)
    decision = evaluate(subject, candidate, [stale], [ci_evidence(subject, candidate)], approval_registry={stale.approval_id: stale})
    results["stale_approval"] = "STALE_REVIEW_APPROVAL" in {f.code for f in decision.findings}

    oracle = harness.create_candidate("ai-service", {"tests/protected/new_oracle.py": "assert True\n"})
    subject = make_subject(root, oracle, allowed_paths=("tests/protected",), work_unit="WU-ORACLE")
    decision = evaluate(subject, oracle, [], [ci_evidence(subject, oracle)])
    results["test_oracle_changed"] = "TEST_ORACLE_CHANGED" in {f.code for f in decision.findings}
    results["merge_group_conflict"] = harness.merge_group_conflicts()

    out_of_scope = harness.create_candidate("ai-service", {"infra/production-admin.tf": "allow = true\n"})
    subject = make_subject(root, out_of_scope)
    decision = evaluate(subject, out_of_scope, [], [ci_evidence(subject, out_of_scope)])
    results["awu_scope_violation"] = "AWU_SCOPE_VIOLATION" in {f.code for f in decision.findings}

    candidate = reference_candidate(root)
    subject = make_subject(root, candidate)
    wrong = replace(ci_evidence(subject, candidate), head_commit=subject.base_commit)
    decision = evaluate(subject, candidate, [approval(subject, candidate, "implementation")], [wrong], evidence_registry={wrong.evidence_id: wrong})
    results["evidence_subject_mismatch"] = "EVIDENCE_SUBJECT_MISMATCH" in {f.code for f in decision.findings}
    decision = evaluate(subject, candidate, [], [ci_evidence(subject, candidate)])
    results["required_review_missing"] = "REQUIRED_REVIEW_MISSING" in {f.code for f in decision.findings}

    self_record = replace(approval(subject, candidate, "implementation"), reviewer=subject.author)
    self_grant = ReviewerGrant(subject.author, self_record.role, self_record.resource, self_record.decision)
    decision = evaluate(subject, candidate, [self_record], [ci_evidence(subject, candidate)], grants=REVIEWER_GRANTS + (self_grant,), approval_registry={self_record.approval_id: self_record})
    results["self_approval_denied"] = "SELF_APPROVAL_DENIED" in {f.code for f in decision.findings}
    decision = evaluate(subject, candidate, [approval(subject, candidate, "implementation")], [ci_evidence(subject, candidate)])
    results["deployment_authority_separate"] = decision.state == "ELIGIBLE_FOR_MERGE_REVIEW" and not decision.deployment_authorized
    return results


def conformance_checks(root: Path) -> dict[str, bool]:
    candidate, subject, decision = reference_assessment(root)
    experiments = git_backed_experiments(root)
    return {
        "CONF-001-real-full-git-subject": len(candidate.base_commit) == len(candidate.head_commit) == 40,
        "CONF-002-actual-diff-derived": set(candidate.changed_paths) == {"src/classifier.py", "tests/test_classifier.py"},
        "CONF-003-exact-head-approval": decision.state == "ELIGIBLE_FOR_MERGE_REVIEW",
        "CONF-004-spec-change-blocked": experiments["unauthorized_spec_change"],
        "CONF-005-contract-owner-required": experiments["contract_owner_missing"],
        "CONF-006-stale-approval-blocked": experiments["stale_approval"],
        "CONF-007-oracle-integrity": experiments["test_oracle_changed"],
        "CONF-008-merge-group-tested": experiments["merge_group_conflict"],
        "CONF-009-work-unit-scope": experiments["awu_scope_violation"],
        "CONF-010-evidence-exact-subject": experiments["evidence_subject_mismatch"],
        "CONF-011-separation-of-duties": experiments["self_approval_denied"],
        "CONF-012-merge-is-not-deployment": experiments["deployment_authority_separate"],
    }


def evaluation_checks(root: Path) -> dict[str, bool]:
    candidate, subject, decision = reference_assessment(root)
    experiments = git_backed_experiments(root)
    good_approval = approval(subject, candidate, "implementation")
    good_evidence = ci_evidence(subject, candidate)
    expired = replace(good_approval, expires_at=NOW - timedelta(seconds=1))
    expired_decision = evaluate(subject, candidate, [expired], [good_evidence], approval_registry={expired.approval_id: expired})
    forged_approval = replace(good_approval, approval_id="APR-FORGED-999")
    forged_evidence = replace(good_evidence, evidence_id="EVID-FORGED-999", result_digest=ReviewEngine.digest("claimed pass"))
    bad_records = evaluate(subject, candidate, [forged_approval], [forged_evidence])
    checks = {
        "EVAL-001-reference-eligible": decision.state == "ELIGIBLE_FOR_MERGE_REVIEW",
        "EVAL-002-base-ancestry": candidate.base_is_ancestor,
        "EVAL-003-two-changed-paths": len(candidate.changed_paths) == 2,
        "EVAL-004-implementation-scope": decision.required_scopes == ("implementation",),
        "EVAL-005-protected-evidence-recorded": decision.evidence_ids == ("EVID-PR-001",),
        "EVAL-006-merge-not-authorized": not decision.merge_authorized,
        "EVAL-007-deploy-not-authorized": not decision.deployment_authorized,
        "EVAL-008-release-not-authorized": not decision.release_authorized,
        "EVAL-009-unauthorized-spec": experiments["unauthorized_spec_change"],
        "EVAL-010-contract-owner": experiments["contract_owner_missing"],
        "EVAL-011-stale-approval": experiments["stale_approval"],
        "EVAL-012-oracle-change": experiments["test_oracle_changed"],
        "EVAL-013-merge-conflict": experiments["merge_group_conflict"],
        "EVAL-014-scope-violation": experiments["awu_scope_violation"],
        "EVAL-015-evidence-mismatch": experiments["evidence_subject_mismatch"],
        "EVAL-016-required-review": experiments["required_review_missing"],
        "EVAL-017-self-approval": experiments["self_approval_denied"],
        "EVAL-018-deploy-separate": experiments["deployment_authority_separate"],
        "EVAL-019-expired-approval": "STALE_REVIEW_APPROVAL" in {f.code for f in expired_decision.findings},
        "EVAL-020-forged-approval": "APPROVAL_RECORD_UNVERIFIED" in {f.code for f in bad_records.findings},
        "EVAL-021-forged-evidence": "EVIDENCE_RECORD_UNVERIFIED" in {f.code for f in bad_records.findings},
        "EVAL-022-protected-test-executed": good_evidence.execution_id == f"RUN-{subject.head_commit[:12]}",
        "EVAL-023-author-not-reviewer": subject.author != good_approval.reviewer,
        "EVAL-024-git-observed-not-declared": tuple(sorted(candidate.changed_paths)) == decision.actual_changed_paths,
        "EVAL-025-no-production-credential": all("token" not in value.lower() for value in candidate.blobs.values()),
        "EVAL-026-review-state-typed": decision.state in {"ELIGIBLE_FOR_MERGE_REVIEW", "BLOCKED"},
        "EVAL-027-findings-structured": all(f.code and f.severity and f.detail for f in expired_decision.findings),
        "EVAL-028-independent-artifact-digests": len(subject.specification_digest) == len(subject.contract_digest) == 71,
    }
    return checks


@dataclass(frozen=True)
class ChangeNode:
    name: str
    build: int
    review: int
    rework: int
    dependencies: tuple[str, ...] = ()
    review_lane: int = 0


def _simulate(nodes: tuple[ChangeNode, ...], late_conflicts: int) -> dict[str, object]:
    completed: dict[str, int] = {}
    lane_available: dict[int, int] = {}
    events: list[dict[str, int | str]] = []
    for node in nodes:
        build_start = max((completed[item] for item in node.dependencies), default=0)
        build_end = build_start + node.build
        review_start = max(build_end, lane_available.get(node.review_lane, 0))
        done = review_start + node.review + node.rework
        lane_available[node.review_lane] = review_start + node.review
        completed[node.name] = done
        events.append({"change": node.name, "build_start": build_start, "review_start": review_start, "completed": done})
    return {
        "lead_time_hours": max(completed.values()),
        "review_effort_hours": sum(node.review for node in nodes),
        "rework_hours": sum(node.rework for node in nodes),
        "late_contract_conflicts": late_conflicts,
        "review_cycles": len(nodes) + sum(1 for node in nodes if node.rework),
        "events": events,
        "model": "deterministic event simulation",
        "source": "synthetic teaching workload",
    }


def strategy_comparison(root: Path = ROOT) -> dict[str, dict[str, object]]:
    results = {}
    for path in sorted((root / "strategies").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        nodes = tuple(ChangeNode(
            item["id"], item["build_hours"], item["review_hours"], item["rework_hours"],
            tuple(item.get("dependencies", ())), item.get("review_lane", 0),
        ) for item in payload["nodes"])
        results[payload["id"]] = _simulate(nodes, payload["late_contract_conflicts"])
    return results


def run_reference(root: Path) -> dict[str, object]:
    candidate, subject, decision = reference_assessment(root)
    conformance, evaluation, experiments = conformance_checks(root), evaluation_checks(root), git_backed_experiments(root)
    passed = all(conformance.values()) and all(evaluation.values()) and all(experiments.values())
    return {
        "course_validation": {"status": "PASS" if passed else "FAIL", "fixture_boundary": "credential-free protected-control-plane teaching system"},
        "candidate_assessment": {
            "state": decision.state, "pull_request": subject.pull_request, "repository": subject.repository,
            "base_commit": subject.base_commit, "head_commit": subject.head_commit,
            "specification_digest": subject.specification_digest, "contract_digest": subject.contract_digest,
            "actual_changed_paths": list(decision.actual_changed_paths), "required_scopes": list(decision.required_scopes),
            "evidence_ids": list(decision.evidence_ids), "merge_authorized": False, "deployment_authorized": False, "release_authorized": False,
        },
        "git_experiments": {"passed": sum(experiments.values()), "total": len(experiments), "results": experiments},
        "conformance": {"passed": sum(conformance.values()), "total": len(conformance), "results": conformance},
        "evaluation": {"passed": sum(evaluation.values()), "total": len(evaluation), "population": {"positive": 8, "negative": 12, "boundary": 4, "failure_recovery": 4}, "results": evaluation},
        "strategy_comparison": strategy_comparison(root),
        "non_authorities": {"merge": False, "deployment": False, "release": False},
    }
