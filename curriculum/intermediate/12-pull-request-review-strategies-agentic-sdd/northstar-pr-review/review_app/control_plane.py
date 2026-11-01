"""Independently maintained authority, policy, artifact, work-unit, and evidence stores."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from .ci_harness import ProtectedAcceptanceRunner
from .git_harness import GitCandidate
from .review_engine import ApprovalRecord, ArtifactRecord, OwnershipRule, PullRequestSubject, ReviewerGrant, ReviewEngine, WorkUnitRecord

_EVIDENCE_CACHE = {}

REVIEWER_GRANTS = (
    ReviewerGrant("reviewer-engineering", "engineering_reviewer", "repository:ai-service", "approve_implementation"),
    ReviewerGrant("reviewer-domain", "domain_owner", "REQ-DOC-2500-01", "approve_requirement_revision"),
    ReviewerGrant("reviewer-contract", "contract_owner", "CONTRACT-CLASSIFICATION-001", "approve_contract_revision"),
    ReviewerGrant("reviewer-quality", "quality_owner", "AC-DOC-2500-02", "approve_acceptance_oracle"),
    ReviewerGrant("reviewer-security", "security_owner", "SECURITY-AUTHORIZATION", "approve_security_change"),
)
TRUSTED_PR_AUTHORS = {"PR-AI-2500-03": "agent-ai-a"}
WORK_UNIT_SCOPES = {
    "WU-AI": ("src", "tests"),
    "WU-SPEC": ("specifications",),
    "WU-CONTRACT": ("contracts",),
    "WU-ORACLE": ("tests/protected",),
}
SCOPE_APPROVERS = {
    "implementation": ("reviewer-engineering", "engineering_reviewer", "repository:ai-service", "approve_implementation"),
    "intent": ("reviewer-domain", "domain_owner", "REQ-DOC-2500-01", "approve_requirement_revision"),
    "contract": ("reviewer-contract", "contract_owner", "CONTRACT-CLASSIFICATION-001", "approve_contract_revision"),
    "acceptance_oracle": ("reviewer-quality", "quality_owner", "AC-DOC-2500-02", "approve_acceptance_oracle"),
    "security": ("reviewer-security", "security_owner", "SECURITY-AUTHORIZATION", "approve_security_change"),
}


class ProtectedControlPlane:
    """Build protected registries without reading candidate-submitted records."""

    def __init__(self, root: Path, subject: PullRequestSubject, candidate: GitCandidate, *, now: datetime) -> None:
        self.root, self.subject, self.candidate, self.now = root, subject, candidate, now
        policy = json.loads((root / "review-policy/ownership.json").read_text(encoding="utf-8"))
        self.rules = tuple(OwnershipRule(**item) for item in policy["rules"])
        self.artifacts = {
            "REQ-DOC-2500": ArtifactRecord("REQ-DOC-2500", ReviewEngine.digest((root / "specifications/approved-requirements.json").read_bytes()), frozenset({"ai-service"})),
            "CONTRACT-CLASSIFICATION-001": ArtifactRecord("CONTRACT-CLASSIFICATION-001", ReviewEngine.digest((root / "contracts/classification-v2.schema.json").read_bytes()), frozenset({"ai-service"})),
        }
        allowed = WORK_UNIT_SCOPES.get(subject.work_unit, ())
        self.work_units = {subject.work_unit: WorkUnitRecord(subject.work_unit, subject.pull_request, subject.repository, subject.base_commit, allowed)}
        self.approvals = {record.approval_id: record for record in (self._issue(scope) for scope in SCOPE_APPROVERS)}
        evidence_key = (subject.repository, subject.head_commit, subject.specification_digest, subject.contract_digest)
        evidence = _EVIDENCE_CACHE.get(evidence_key)
        if evidence is None:
            evidence = ProtectedAcceptanceRunner().run(candidate, subject, observed_at=now)
            _EVIDENCE_CACHE[evidence_key] = evidence
        self.evidence = {evidence.evidence_id: evidence}

    def _issue(self, scope: str) -> ApprovalRecord:
        reviewer, role, resource, decision = SCOPE_APPROVERS[scope]
        return ApprovalRecord(
            approval_id=f"APR-{scope.upper()}-001", reviewer=reviewer, role=role, scope=scope,
            resource=resource, decision=decision, repository=self.subject.repository,
            head_commit=self.subject.head_commit, specification_digest=self.subject.specification_digest,
            contract_digest=self.subject.contract_digest, issued_at=self.now - timedelta(minutes=10),
            expires_at=self.now + timedelta(hours=2),
        )

    def engine(self, *, grants: tuple[ReviewerGrant, ...] = REVIEWER_GRANTS) -> ReviewEngine:
        return ReviewEngine(grants, TRUSTED_PR_AUTHORS, self.approvals, self.evidence, self.artifacts, self.work_units, self.rules)

    def approval(self, scope: str) -> ApprovalRecord:
        return self.approvals[f"APR-{scope.upper()}-001"]

    def acceptance_evidence(self):
        return self.evidence["EVID-PR-001"]
