"""Typed results used by the trusted multi-repository control plane."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal, Mapping


DecisionState = Literal["BLOCKED", "READY_FOR_INTEGRATION_REVIEW"]


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


@dataclass(frozen=True)
class Decision:
    state: DecisionState
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class RepositoryRevision:
    repository: str
    baseline_commit: str
    candidate_commit: str
    changed_paths: tuple[str, ...]


@dataclass(frozen=True)
class IntegrationReceipt:
    producer: str
    change_id: str
    contract_revision: int
    component_commits: Mapping[str, str]
    scenario_results: Mapping[str, bool]


@dataclass(frozen=True)
class TrustedContext:
    parent_change: Mapping[str, object]
    canonical_contract: Mapping[str, object]
    trusted_work_units: Mapping[str, object]
    repositories: Mapping[str, RepositoryRevision]
    compatibility_matrix: Mapping[str, bool]
    scenario_results: Mapping[str, bool]
    evidence_registry: Mapping[str, IntegrationReceipt]


def protected(value: dict) -> Mapping:
    """Expose a shallow read-only view of a protected fixture."""
    return MappingProxyType(value)
