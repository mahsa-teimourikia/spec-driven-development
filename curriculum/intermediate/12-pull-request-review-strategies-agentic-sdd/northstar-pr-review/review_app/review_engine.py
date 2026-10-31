"""Deterministic, authority-aware PR review controls for Course 22."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .git_harness import GitCandidate


UTC = timezone.utc


@dataclass(frozen=True)
class PullRequestSubject:
    pull_request: str
    change_id: str
    work_unit: str
    author: str
    repository: str
    base_commit: str
    head_commit: str
    specification_digest: str
    contract_digest: str
    allowed_paths: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    reviewer: str
    role: str
    scope: str
    repository: str
    head_commit: str
    specification_digest: str
    contract_digest: str
    issued_at: datetime
    expires_at: datetime
    state: str = "ACTIVE"


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    producer: str
    repository: str
    head_commit: str
    specification_digest: str
    contract_digest: str
    check_name: str
    result: str
    result_digest: str


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    detail: str


@dataclass(frozen=True)
class ReviewDecision:
    state: str
    findings: tuple[Finding, ...]
    actual_changed_paths: tuple[str, ...]
    required_scopes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    merge_authorized: bool = False
    deployment_authorized: bool = False
    release_authorized: bool = False


class ReviewEngine:
    """Establish merge-review eligibility without granting merge authority."""

    TRUSTED_EVIDENCE_PRODUCERS = frozenset({"trusted-ci", "protected-acceptance-runner"})
    PROTECTED_PATHS = {
        "specifications/approved-requirements.json": ("intent", "UNAUTHORIZED_SPEC_CHANGE"),
        "contracts/classification-v2.schema.json": ("contract", "CONTRACT_APPROVAL_MISSING"),
        "tests/protected/test_acceptance.py": ("acceptance_oracle", "TEST_ORACLE_CHANGED"),
        "src/authorization.py": ("security", "REQUIRED_REVIEW_MISSING"),
    }

    def __init__(
        self,
        trusted_reviewers: Mapping[str, frozenset[str]],
        trusted_pr_authors: Mapping[str, str],
        approval_registry: Mapping[str, ApprovalRecord] | None = None,
        evidence_registry: Mapping[str, EvidenceRecord] | None = None,
    ) -> None:
        self.trusted_reviewers = dict(trusted_reviewers)
        self.trusted_pr_authors = dict(trusted_pr_authors)
        self.approval_registry = dict(approval_registry or {})
        self.evidence_registry = dict(evidence_registry or {})

    @staticmethod
    def digest(content: bytes | str) -> str:
        raw = content.encode("utf-8") if isinstance(content, str) else content
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _path_allowed(path: str, allowed: Iterable[str]) -> bool:
        return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in allowed)

    def _required_scopes(self, changed_paths: Iterable[str]) -> set[str]:
        scopes = {"implementation"}
        for path in changed_paths:
            protected = self.PROTECTED_PATHS.get(path)
            if protected:
                scopes.add(protected[0])
        return scopes

    def evaluate(
        self,
        subject: PullRequestSubject,
        observed: GitCandidate,
        approvals: Iterable[ApprovalRecord],
        evidence: Iterable[EvidenceRecord],
        *,
        now: datetime,
    ) -> ReviewDecision:
        findings: list[Finding] = []
        approvals = tuple(approvals)
        evidence = tuple(evidence)

        authenticated_author = self.trusted_pr_authors.get(subject.pull_request)
        if authenticated_author is None or authenticated_author != subject.author:
            findings.append(Finding("UNAUTHENTICATED_PR_AUTHOR", "BLOCK", "PR author does not match trusted application state."))
        effective_author = authenticated_author or "<untrusted-author>"

        registered_approvals: list[ApprovalRecord] = []
        for record in approvals:
            if self.approval_registry.get(record.approval_id) != record:
                findings.append(Finding("APPROVAL_RECORD_UNVERIFIED", "BLOCK", record.approval_id))
            else:
                registered_approvals.append(record)
        registered_evidence: list[EvidenceRecord] = []
        for record in evidence:
            if self.evidence_registry.get(record.evidence_id) != record:
                findings.append(Finding("EVIDENCE_RECORD_UNVERIFIED", "BLOCK", record.evidence_id))
            else:
                registered_evidence.append(record)

        if subject.repository != observed.repository or subject.base_commit != observed.base_commit or subject.head_commit != observed.head_commit:
            findings.append(Finding("PR_SUBJECT_MISMATCH", "BLOCK", "Declared revision subject differs from trusted Git observation."))
        if len(observed.base_commit) != 40 or len(observed.head_commit) != 40 or not observed.base_is_ancestor:
            findings.append(Finding("UNVERIFIED_GIT_ANCESTRY", "BLOCK", "Base/head commits are unresolved or unrelated."))

        unauthorized = [path for path in observed.changed_paths if not self._path_allowed(path, subject.allowed_paths)]
        if unauthorized:
            findings.append(Finding("AWU_SCOPE_VIOLATION", "BLOCK", ", ".join(unauthorized)))

        required_scopes = self._required_scopes(observed.changed_paths)
        valid_scopes: set[str] = set()
        for scope in sorted(required_scopes):
            scoped = [approval for approval in registered_approvals if approval.scope == scope and approval.repository == subject.repository]
            exact = [
                approval
                for approval in scoped
                if approval.head_commit == subject.head_commit
                and approval.specification_digest == subject.specification_digest
                and approval.contract_digest == subject.contract_digest
            ]
            for approval in exact:
                if approval.reviewer == effective_author:
                    findings.append(Finding("SELF_APPROVAL_DENIED", "BLOCK", f"{approval.approval_id} is authored and approved by the same principal."))
                    continue
                if approval.state != "ACTIVE" or approval.expires_at <= now:
                    findings.append(Finding("STALE_REVIEW_APPROVAL", "BLOCK", f"{approval.approval_id} is expired or inactive."))
                    continue
                if approval.role not in self.trusted_reviewers.get(approval.reviewer, frozenset()):
                    findings.append(Finding("REVIEWER_AUTHORITY_UNVERIFIED", "BLOCK", f"{approval.reviewer} lacks trusted {approval.role} authority."))
                    continue
                expected_role = {
                    "intent": "domain_owner",
                    "contract": "contract_owner",
                    "acceptance_oracle": "quality_owner",
                    "security": "security_owner",
                    "implementation": "engineering_reviewer",
                }[scope]
                if approval.role != expected_role:
                    continue
                valid_scopes.add(scope)
            if scope not in valid_scopes:
                if scoped and not exact:
                    code = "STALE_REVIEW_APPROVAL"
                else:
                    protected_codes = {
                        "intent": "UNAUTHORIZED_SPEC_CHANGE",
                        "contract": "CONTRACT_APPROVAL_MISSING",
                        "acceptance_oracle": "TEST_ORACLE_CHANGED",
                        "security": "REQUIRED_REVIEW_MISSING",
                        "implementation": "REQUIRED_REVIEW_MISSING",
                    }
                    code = protected_codes[scope]
                findings.append(Finding(code, "BLOCK", f"No current authorized approval for {scope}."))

        matching_evidence = [
            record
            for record in registered_evidence
            if record.repository == subject.repository
            and record.head_commit == subject.head_commit
            and record.specification_digest == subject.specification_digest
            and record.contract_digest == subject.contract_digest
        ]
        if registered_evidence and not matching_evidence:
            findings.append(Finding("EVIDENCE_SUBJECT_MISMATCH", "BLOCK", "Evidence does not bind the exact review subject."))
        elif not matching_evidence:
            findings.append(Finding("TRUSTED_CI_EVIDENCE_MISSING", "BLOCK", "No exact-subject trusted CI evidence exists."))
        for record in matching_evidence:
            expected = self.digest(f"{record.repository}|{record.head_commit}|{record.check_name}|{record.result}")
            if record.producer not in self.TRUSTED_EVIDENCE_PRODUCERS:
                findings.append(Finding("UNTRUSTED_EVIDENCE_PRODUCER", "BLOCK", record.producer))
            elif record.result != "PASS" or record.result_digest != expected:
                findings.append(Finding("EVIDENCE_RESULT_INVALID", "BLOCK", record.evidence_id))

        unique = {(finding.code, finding.severity, finding.detail): finding for finding in findings}
        ordered = tuple(sorted(unique.values(), key=lambda finding: (finding.code, finding.detail)))
        state = "ELIGIBLE_FOR_MERGE_REVIEW" if not ordered else "BLOCKED"
        return ReviewDecision(
            state=state,
            findings=ordered,
            actual_changed_paths=observed.changed_paths,
            required_scopes=tuple(sorted(required_scopes)),
            evidence_ids=tuple(sorted(record.evidence_id for record in matching_evidence)),
        )
