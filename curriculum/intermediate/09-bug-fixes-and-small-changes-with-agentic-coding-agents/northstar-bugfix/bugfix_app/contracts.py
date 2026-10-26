"""Typed contracts for the isolated BUG-2415 maintenance workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping


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
    status: Literal[
        "UNIT_CAUSE_CONFIRMED",
        "PRODUCTION_PATH_CAUSE_CONFIRMED",
        "NOT_SUPPORTED",
        "UNRESOLVED",
    ]


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


@dataclass(frozen=True)
class TrustedEvaluationContext:
    """Inputs produced by the trusted harness, never accepted from the candidate."""

    bug_contract: Mapping[str, object]
    acceptance_contract: Mapping[str, object]
    candidate_acceptance_contract: Mapping[str, object]
    work_unit: Mapping[str, object]
    baseline_commit: str
    candidate_commit: str
    actual_diff_entries: tuple[DiffEntry, ...]
    before_observation: TestObservation
    after_observation: TestObservation
    boundary_results: Mapping[int, str]
    unit_cause_evidence: RootCauseEvidence
    production_cause_evidence: RootCauseEvidence
    evidence_registry: Mapping[str, EvidenceReceipt]
