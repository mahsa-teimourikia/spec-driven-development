"""Executable Course 22 scenarios and review-strategy comparison."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .git_harness import GitCandidate, TrustedGitHarness
from .review_engine import ApprovalRecord, EvidenceRecord, PullRequestSubject, ReviewEngine


NOW = datetime(2026, 2, 2, 15, 0, tzinfo=timezone.utc)
TRUSTED_REVIEWERS = {
    "reviewer-engineering": frozenset({"engineering_reviewer"}),
    "reviewer-domain": frozenset({"domain_owner"}),
    "reviewer-contract": frozenset({"contract_owner"}),
    "reviewer-quality": frozenset({"quality_owner"}),
    "reviewer-security": frozenset({"security_owner"}),
}
TRUSTED_PR_AUTHORS = {"PR-AI-2500-03": "agent-ai-a"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def approved_digests(root: Path) -> tuple[str, str]:
    engine = ReviewEngine(TRUSTED_REVIEWERS, TRUSTED_PR_AUTHORS)
    spec = (root / "specifications/approved-requirements.json").read_bytes()
    contract = (root / "contracts/classification-v2.schema.json").read_bytes()
    return engine.digest(spec), engine.digest(contract)


def reference_candidate(root: Path) -> GitCandidate:
    return TrustedGitHarness().create_candidate(
        "ai-service",
        {
            "src/classifier.py": "def route(ambiguous: bool) -> str:\n    return 'review' if ambiguous else 'straight_through'\n\ndef provenance(document_id: str) -> dict[str, str]:\n    return {'document_id': document_id}\n",
            "tests/test_classifier.py": "def test_ambiguous_routes_to_review():\n    assert True\n",
        },
    )


def make_subject(root: Path, candidate: GitCandidate, *, allowed_paths: tuple[str, ...] = ("src", "tests")) -> PullRequestSubject:
    spec_digest, contract_digest = approved_digests(root)
    return PullRequestSubject(
        pull_request="PR-AI-2500-03",
        change_id="AI-2500",
        work_unit="WU-AI",
        author="agent-ai-a",
        repository=candidate.repository,
        base_commit=candidate.base_commit,
        head_commit=candidate.head_commit,
        specification_digest=spec_digest,
        contract_digest=contract_digest,
        allowed_paths=allowed_paths,
    )


def approval(subject: PullRequestSubject, scope: str, reviewer: str, role: str, *, head_commit: str | None = None) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id=f"APR-{scope.upper()}-001",
        reviewer=reviewer,
        role=role,
        scope=scope,
        repository=subject.repository,
        head_commit=head_commit or subject.head_commit,
        specification_digest=subject.specification_digest,
        contract_digest=subject.contract_digest,
        issued_at=NOW - timedelta(minutes=10),
        expires_at=NOW + timedelta(hours=2),
    )


def ci_evidence(subject: PullRequestSubject, *, head_commit: str | None = None, producer: str = "trusted-ci") -> EvidenceRecord:
    commit = head_commit or subject.head_commit
    check_name = "protected-acceptance-and-unit-suite"
    result = "PASS"
    return EvidenceRecord(
        evidence_id="EVID-PR-001",
        producer=producer,
        repository=subject.repository,
        head_commit=commit,
        specification_digest=subject.specification_digest,
        contract_digest=subject.contract_digest,
        check_name=check_name,
        result=result,
        result_digest=ReviewEngine.digest(f"{subject.repository}|{commit}|{check_name}|{result}"),
    )


def evaluate(
    subject: PullRequestSubject,
    candidate: GitCandidate,
    approvals: list[ApprovalRecord],
    evidence: list[EvidenceRecord],
    *,
    reviewers: dict[str, frozenset[str]] | None = None,
):
    engine = ReviewEngine(
        reviewers or TRUSTED_REVIEWERS,
        TRUSTED_PR_AUTHORS,
        {record.approval_id: record for record in approvals},
        {record.evidence_id: record for record in evidence},
    )
    return engine.evaluate(subject, candidate, approvals, evidence, now=NOW)


def reference_assessment(root: Path):
    candidate = reference_candidate(root)
    subject = make_subject(root, candidate)
    decision = evaluate(
        subject,
        candidate,
        [approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer")],
        [ci_evidence(subject)],
    )
    return candidate, subject, decision


def git_backed_experiments(root: Path) -> dict[str, bool]:
    harness = TrustedGitHarness()
    results: dict[str, bool] = {}

    protected_spec = harness.create_candidate(
        "ai-service",
        {"specifications/approved-requirements.json": '{"ambiguity":"confidence_may_bypass_review"}\n'},
    )
    subject = make_subject(root, protected_spec, allowed_paths=("specifications",))
    decision = evaluate(subject, protected_spec, [], [ci_evidence(subject)])
    results["unauthorized_spec_change"] = "UNAUTHORIZED_SPEC_CHANGE" in {f.code for f in decision.findings}

    contract = harness.create_candidate(
        "ai-service",
        {"contracts/classification-v2.schema.json": '{"required":["confidence"]}\n'},
    )
    subject = make_subject(root, contract, allowed_paths=("contracts",))
    decision = evaluate(
        subject,
        contract,
        [approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer")],
        [ci_evidence(subject)],
    )
    results["contract_owner_missing"] = "CONTRACT_APPROVAL_MISSING" in {f.code for f in decision.findings}

    candidate = reference_candidate(root)
    subject = make_subject(root, candidate)
    stale = approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer", head_commit=subject.base_commit)
    decision = evaluate(subject, candidate, [stale], [ci_evidence(subject)])
    results["stale_approval"] = "STALE_REVIEW_APPROVAL" in {f.code for f in decision.findings}

    oracle = harness.create_candidate(
        "ai-service",
        {"tests/protected/test_acceptance.py": "def test_high_confidence_bypasses_review():\n    assert True\n"},
    )
    subject = make_subject(root, oracle, allowed_paths=("tests/protected",))
    decision = evaluate(subject, oracle, [], [ci_evidence(subject)])
    results["test_oracle_changed"] = "TEST_ORACLE_CHANGED" in {f.code for f in decision.findings}

    results["merge_group_conflict"] = harness.merge_group_conflicts()

    out_of_scope = harness.create_candidate("ai-service", {"infra/production-admin.tf": "allow = true\n"})
    subject = make_subject(root, out_of_scope, allowed_paths=("src", "tests"))
    decision = evaluate(subject, out_of_scope, [], [ci_evidence(subject)])
    results["awu_scope_violation"] = "AWU_SCOPE_VIOLATION" in {f.code for f in decision.findings}

    candidate = reference_candidate(root)
    subject = make_subject(root, candidate)
    wrong_evidence = ci_evidence(subject, head_commit=subject.base_commit)
    decision = evaluate(
        subject,
        candidate,
        [approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer")],
        [wrong_evidence],
    )
    results["evidence_subject_mismatch"] = "EVIDENCE_SUBJECT_MISMATCH" in {f.code for f in decision.findings}

    decision = evaluate(subject, candidate, [], [ci_evidence(subject)])
    results["required_review_missing"] = "REQUIRED_REVIEW_MISSING" in {f.code for f in decision.findings}

    self_approval = approval(subject, "implementation", subject.author, "engineering_reviewer")
    trusted = {**TRUSTED_REVIEWERS, subject.author: frozenset({"engineering_reviewer"})}
    decision = evaluate(subject, candidate, [self_approval], [ci_evidence(subject)], reviewers=trusted)
    results["self_approval_denied"] = "SELF_APPROVAL_DENIED" in {f.code for f in decision.findings}

    decision = evaluate(
        subject,
        candidate,
        [approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer")],
        [ci_evidence(subject)],
    )
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
    expired = replace(
        approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer"),
        expires_at=NOW - timedelta(seconds=1),
    )
    expired_decision = evaluate(subject, candidate, [expired], [ci_evidence(subject)])
    untrusted_decision = evaluate(
        subject,
        candidate,
        [approval(subject, "implementation", "reviewer-engineering", "engineering_reviewer")],
        [ci_evidence(subject, producer="agent-reported-ci")],
    )
    checks = {
        "EVAL-001-reference-eligible": decision.state == "ELIGIBLE_FOR_MERGE_REVIEW",
        "EVAL-002-base-ancestry": candidate.base_is_ancestor,
        "EVAL-003-two-changed-paths": len(candidate.changed_paths) == 2,
        "EVAL-004-implementation-scope": decision.required_scopes == ("implementation",),
        "EVAL-005-trusted-evidence-recorded": decision.evidence_ids == ("EVID-PR-001",),
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
        "EVAL-020-untrusted-evidence": "UNTRUSTED_EVIDENCE_PRODUCER" in {f.code for f in untrusted_decision.findings},
        "EVAL-021-spec-digest-full": len(subject.specification_digest) == 71,
        "EVAL-022-contract-digest-full": len(subject.contract_digest) == 71,
        "EVAL-023-author-not-reviewer": subject.author != "reviewer-engineering",
        "EVAL-024-git-observed-not-declared": tuple(sorted(candidate.changed_paths)) == decision.actual_changed_paths,
        "EVAL-025-no-production-credential": all("token" not in value.lower() for value in candidate.blobs.values()),
        "EVAL-026-review-state-typed": decision.state in {"ELIGIBLE_FOR_MERGE_REVIEW", "BLOCKED"},
        "EVAL-027-findings-structured": all(f.code and f.severity and f.detail for f in expired_decision.findings),
        "EVAL-028-review-expires": expired.expires_at < NOW,
    }
    return checks


def strategy_comparison() -> dict[str, dict[str, int | str]]:
    return {
        "mega_pr": {"lead_time_hours": 30, "review_effort_hours": 11, "rework_hours": 9, "late_contract_conflicts": 3, "source": "synthetic teaching workload"},
        "staged_prs": {"lead_time_hours": 26, "review_effort_hours": 8, "rework_hours": 3, "late_contract_conflicts": 0, "source": "synthetic teaching workload"},
        "parallel_repositories": {"lead_time_hours": 21, "review_effort_hours": 9, "rework_hours": 4, "late_contract_conflicts": 1, "source": "synthetic teaching workload"},
    }


def run_reference(root: Path) -> dict[str, object]:
    candidate, subject, decision = reference_assessment(root)
    conformance = conformance_checks(root)
    evaluation = evaluation_checks(root)
    experiments = git_backed_experiments(root)
    passed = all(conformance.values()) and all(evaluation.values()) and all(experiments.values())
    return {
        "course_validation": {"status": "PASS" if passed else "FAIL", "fixture_boundary": "credential-free deterministic teaching system"},
        "candidate_assessment": {
            "state": decision.state,
            "pull_request": subject.pull_request,
            "repository": subject.repository,
            "base_commit": subject.base_commit,
            "head_commit": subject.head_commit,
            "specification_digest": subject.specification_digest,
            "contract_digest": subject.contract_digest,
            "actual_changed_paths": list(decision.actual_changed_paths),
            "required_scopes": list(decision.required_scopes),
            "evidence_ids": list(decision.evidence_ids),
            "merge_authorized": decision.merge_authorized,
            "deployment_authorized": decision.deployment_authorized,
            "release_authorized": decision.release_authorized,
        },
        "git_experiments": {"passed": sum(experiments.values()), "total": len(experiments), "results": experiments},
        "conformance": {"passed": sum(conformance.values()), "total": len(conformance), "results": conformance},
        "evaluation": {
            "passed": sum(evaluation.values()),
            "total": len(evaluation),
            "population": {"positive": 8, "negative": 12, "boundary": 4, "failure_recovery": 4},
            "results": evaluation,
        },
        "strategy_comparison": strategy_comparison(),
        "non_authorities": {"merge": False, "deployment": False, "release": False},
        "observability": {
            "recorded_fields": ["change_id", "pull_request", "repository", "base_commit", "head_commit", "specification_digest", "contract_digest", "actual_changed_paths", "required_scopes", "approval_id", "reviewer_identity", "evidence_id", "decision", "finding_code"],
            "private_reasoning_recorded": False,
        },
    }
