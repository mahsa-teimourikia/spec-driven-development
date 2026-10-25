"""Typed contracts for the isolated BUG-2415 maintenance workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


WorkflowMode = Literal["LIGHTWEIGHT", "STRUCTURED", "GOVERNED"]
DecisionState = Literal["PASS", "BLOCKED", "REVIEW_REQUIRED"]


@dataclass(frozen=True)
class ChangeRisk:
    consequence: int
    authority: int
    scope: int
    reversibility: int
    uncertainty: int
    exposure: int


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: Literal["BLOCK", "REVIEW", "INFO"] = "BLOCK"


@dataclass(frozen=True)
class Decision:
    state: DecisionState
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class TestObservation:
    test_id: str
    revision: str
    expected: str
    actual: str
    result: Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class RootCauseEvidence:
    hypothesis_id: str
    experiment_id: str
    predicted: str
    observed: str
    status: Literal["CONFIRMED", "NOT_SUPPORTED", "UNRESOLVED"]


@dataclass(frozen=True)
class DiffEntry:
    status: Literal["A", "M", "D", "R"]
    old_path: str | None
    new_path: str
    purpose: str


@dataclass(frozen=True)
class EvidenceReceipt:
    producer: str
    bug_id: str
    baseline_revision: str
    candidate_revision: str
    acceptance_digest: str
    before: TestObservation
    after: TestObservation
