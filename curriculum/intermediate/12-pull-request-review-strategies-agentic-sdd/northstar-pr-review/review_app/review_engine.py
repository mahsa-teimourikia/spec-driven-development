"""Deterministic, authority-aware PR review controls for Course 22."""
from __future__ import annotations

import hashlib
import posixpath
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Mapping

from .git_harness import GitCandidate


@dataclass(frozen=True)
class PullRequestSubject:
    pull_request: str
    change_id: str
    work_unit: str
    author: str
    repository: str
    base_commit: str
    head_commit: str
    specification_id: str
    specification_digest: str
    contract_id: str
    contract_digest: str
    allowed_paths: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    reviewer: str
    role: str
    scope: str
    resource: str
    decision: str
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
    execution_id: str
    observed_at: datetime
    protected_test_digest: str


@dataclass(frozen=True)
class ReviewerGrant:
    principal: str
    role: str
    resource: str
    decision: str


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    digest: str
    repositories: frozenset[str]
    state: str = "APPROVED"


@dataclass(frozen=True)
class WorkUnitRecord:
    work_unit: str
    pull_request: str
    repository: str
    base_commit: str
    allowed_paths: tuple[str, ...]
    state: str = "ACTIVE"


@dataclass(frozen=True)
class OwnershipRule:
    prefix: str
    scope: str
    role: str
    resource: str
    decision: str
    precedence: int


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
    """Resolve protected state; candidate records can only reference it."""

    TRUSTED_EVIDENCE_PRODUCERS = frozenset({"protected-acceptance-runner"})

    def __init__(self, reviewer_grants: Iterable[ReviewerGrant], trusted_pr_authors: Mapping[str, str], approval_registry: Mapping[str, ApprovalRecord], evidence_registry: Mapping[str, EvidenceRecord], artifact_registry: Mapping[str, ArtifactRecord], work_unit_registry: Mapping[str, WorkUnitRecord], ownership_policy: Iterable[OwnershipRule]) -> None:
        self.reviewer_grants = frozenset(reviewer_grants)
        self.trusted_pr_authors = dict(trusted_pr_authors)
        self.approval_registry = dict(approval_registry)
        self.evidence_registry = dict(evidence_registry)
        self.artifact_registry = dict(artifact_registry)
        self.work_unit_registry = dict(work_unit_registry)
        self.ownership_policy = tuple(ownership_policy)

    @staticmethod
    def digest(content: bytes | str) -> str:
        raw = content.encode() if isinstance(content, str) else content
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _normalized(path: str) -> str | None:
        if not path or path.startswith("/") or "\\" in path:
            return None
        normalized = posixpath.normpath(path)
        return None if normalized in {".", ".."} or normalized.startswith("../") else normalized

    @classmethod
    def _allowed(cls, path: str, prefixes: Iterable[str]) -> bool:
        normalized = cls._normalized(path)
        return bool(normalized and any(normalized == prefix.rstrip("/") or normalized.startswith(prefix.rstrip("/") + "/") for prefix in prefixes))

    def _rule(self, path: str) -> OwnershipRule | None:
        normalized = self._normalized(path)
        matches = [] if normalized is None else [rule for rule in self.ownership_policy if normalized == rule.prefix.rstrip("/") or normalized.startswith(rule.prefix.rstrip("/") + "/")]
        return max(matches, key=lambda rule: (len(rule.prefix.rstrip("/")), rule.precedence)) if matches else None

    def evaluate(self, subject: PullRequestSubject, observed: GitCandidate, approvals: Iterable[ApprovalRecord], evidence: Iterable[EvidenceRecord], *, now: datetime) -> ReviewDecision:
        findings: list[Finding] = []
        approvals, evidence = tuple(approvals), tuple(evidence)
        author = self.trusted_pr_authors.get(subject.pull_request)
        if author != subject.author:
            findings.append(Finding("UNAUTHENTICATED_PR_AUTHOR", "BLOCK", "PR author does not match trusted state."))
        effective_author = author or "<untrusted-author>"

        registered_approvals = []
        for record in approvals:
            if self.approval_registry.get(record.approval_id) != record:
                findings.append(Finding("APPROVAL_RECORD_UNVERIFIED", "BLOCK", record.approval_id))
            else:
                registered_approvals.append(record)
        registered_evidence = []
        for record in evidence:
            if self.evidence_registry.get(record.evidence_id) != record:
                findings.append(Finding("EVIDENCE_RECORD_UNVERIFIED", "BLOCK", record.evidence_id))
            else:
                registered_evidence.append(record)

        if (subject.repository, subject.base_commit, subject.head_commit) != (observed.repository, observed.base_commit, observed.head_commit):
            findings.append(Finding("PR_SUBJECT_MISMATCH", "BLOCK", "Declared subject differs from Git observation."))
        if len(observed.base_commit) != 40 or len(observed.head_commit) != 40 or not observed.base_is_ancestor:
            findings.append(Finding("UNVERIFIED_GIT_ANCESTRY", "BLOCK", "Base/head unresolved or unrelated."))

        for label, artifact_id, declared in (("specification", subject.specification_id, subject.specification_digest), ("contract", subject.contract_id, subject.contract_digest)):
            record = self.artifact_registry.get(artifact_id)
            if not record or record.state != "APPROVED" or subject.repository not in record.repositories:
                findings.append(Finding("AUTHORITATIVE_REVISION_UNRESOLVED", "BLOCK", label))
            elif record.digest != declared:
                findings.append(Finding("AUTHORITATIVE_REVISION_MISMATCH", "BLOCK", label))

        work_unit = self.work_unit_registry.get(subject.work_unit)
        if not work_unit or work_unit.state != "ACTIVE" or (work_unit.pull_request, work_unit.repository, work_unit.base_commit) != (subject.pull_request, subject.repository, subject.base_commit):
            findings.append(Finding("WORK_UNIT_AUTHORITY_UNRESOLVED", "BLOCK", subject.work_unit))
            trusted_paths: tuple[str, ...] = ()
        else:
            trusted_paths = work_unit.allowed_paths
            if any(not self._allowed(path, trusted_paths) for path in subject.allowed_paths):
                findings.append(Finding("AWU_SCOPE_ESCALATION_REQUESTED", "BLOCK", ", ".join(subject.allowed_paths)))
        invalid = [path for path in observed.changed_paths if self._normalized(path) is None]
        unauthorized = [path for path in observed.changed_paths if not self._allowed(path, trusted_paths)]
        if invalid:
            findings.append(Finding("INVALID_CHANGED_PATH", "BLOCK", ", ".join(invalid)))
        if unauthorized:
            findings.append(Finding("AWU_SCOPE_VIOLATION", "BLOCK", ", ".join(unauthorized)))

        obligations = {(rule.scope, rule.role, rule.resource, rule.decision) for path in observed.changed_paths if (rule := self._rule(path))}
        for scope, role, resource, decision in sorted(obligations):
            scoped = [item for item in registered_approvals if (item.scope, item.resource, item.decision, item.repository) == (scope, resource, decision, subject.repository)]
            exact = [item for item in scoped if (item.head_commit, item.specification_digest, item.contract_digest) == (subject.head_commit, subject.specification_digest, subject.contract_digest)]
            valid = False
            for item in exact:
                if item.reviewer == effective_author:
                    findings.append(Finding("SELF_APPROVAL_DENIED", "BLOCK", item.approval_id))
                elif item.state != "ACTIVE" or item.expires_at <= now:
                    findings.append(Finding("STALE_REVIEW_APPROVAL", "BLOCK", item.approval_id))
                elif item.issued_at > now:
                    findings.append(Finding("APPROVAL_NOT_YET_VALID", "BLOCK", item.approval_id))
                elif item.role != role or ReviewerGrant(item.reviewer, item.role, item.resource, item.decision) not in self.reviewer_grants:
                    findings.append(Finding("REVIEWER_AUTHORITY_UNVERIFIED", "BLOCK", item.reviewer))
                else:
                    valid = True
            if not valid:
                codes = {"intent": "UNAUTHORIZED_SPEC_CHANGE", "contract": "CONTRACT_APPROVAL_MISSING", "acceptance_oracle": "TEST_ORACLE_CHANGED"}
                findings.append(Finding("STALE_REVIEW_APPROVAL" if scoped and not exact else codes.get(scope, "REQUIRED_REVIEW_MISSING"), "BLOCK", f"No authorized approval for {scope}:{resource}."))

        matching = [item for item in registered_evidence if (item.repository, item.head_commit, item.specification_digest, item.contract_digest) == (subject.repository, subject.head_commit, subject.specification_digest, subject.contract_digest)]
        if registered_evidence and not matching:
            findings.append(Finding("EVIDENCE_SUBJECT_MISMATCH", "BLOCK", "Evidence does not bind the exact subject."))
        elif not matching:
            findings.append(Finding("TRUSTED_CI_EVIDENCE_MISSING", "BLOCK", "No protected execution record exists."))
        for item in matching:
            if item.producer not in self.TRUSTED_EVIDENCE_PRODUCERS:
                findings.append(Finding("UNTRUSTED_EVIDENCE_PRODUCER", "BLOCK", item.producer))
            elif item.check_name != "protected-acceptance" or item.result != "PASS":
                findings.append(Finding("EVIDENCE_RESULT_INVALID", "BLOCK", item.evidence_id))

        unique = {(item.code, item.severity, item.detail): item for item in findings}
        ordered = tuple(sorted(unique.values(), key=lambda item: (item.code, item.detail)))
        return ReviewDecision("ELIGIBLE_FOR_MERGE_REVIEW" if not ordered else "BLOCKED", ordered, observed.changed_paths, tuple(sorted({item[0] for item in obligations})), tuple(sorted(item.evidence_id for item in matching)))
