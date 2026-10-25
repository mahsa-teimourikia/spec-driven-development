"""Typed contracts for the Northstar brownfield modernization lab."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Disposition = Literal["PRESERVE", "MODIFY", "RETIRE", "DEFECT", "UNKNOWN"]
Confidence = Literal["CONFIRMED", "PARTIAL", "UNKNOWN"]


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
    authorized_submission_ids: frozenset[str]
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
