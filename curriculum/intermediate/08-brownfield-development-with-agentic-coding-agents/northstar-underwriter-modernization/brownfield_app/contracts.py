"""Typed contracts for the Northstar brownfield modernization lab."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Disposition = Literal["PRESERVE", "MODIFY", "RETIRE", "DEFECT", "UNKNOWN"]
Confidence = Literal["CONFIRMED", "PARTIAL", "UNKNOWN"]
MigrationStatus = Literal["APPLIED", "ALREADY_APPLIED", "IDEMPOTENCY_CONFLICT"]
ShadowClassification = Literal["EXPECTED", "ACCEPTABLE", "UNEXPECTED", "UNRESOLVED"]


@dataclass(frozen=True)
class Submission:
    submission_id: str
    score: int
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionContext:
    repository_revision: str
    specification_revision: int
    actor: str
    feature_flags: frozenset[str] = field(default_factory=frozenset)
    capabilities: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SummaryProposal:
    submission_id: str
    source: str
    text: str
    evidence: tuple[str, ...]
    authoritative: bool = False


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: Literal["BLOCK", "REVIEW", "INFO"] = "BLOCK"


@dataclass(frozen=True)
class Decision:
    state: Literal["PASS", "BLOCKED", "REVIEW_REQUIRED"]
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class BehaviorRecord:
    behavior_id: str
    disposition: Disposition
    owner: str | None
    evidence: tuple[str, ...]
    requirement_id: str | None = None


@dataclass(frozen=True)
class AuthorizationGrant:
    """Trusted synthetic grant bound to an exact subject, operation, and policy."""

    principal: str
    submission_id: str
    operation: str
    policy_revision: int


@dataclass(frozen=True)
class RegressionPlan:
    selected_tests: frozenset[str]
    unmapped_consumers: frozenset[str]
    state: Literal["PASS", "BLOCKED", "REVIEW_REQUIRED"]


@dataclass(frozen=True)
class ShadowResult:
    classification: ShadowClassification
    differences: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class RollbackEvidence:
    ai_path_observed: bool
    legacy_path_restored: bool
    authoritative_state_unchanged: bool
    legacy_reads_preserved: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.ai_path_observed,
                self.legacy_path_restored,
                self.authoritative_state_unchanged,
                self.legacy_reads_preserved,
            )
        )
