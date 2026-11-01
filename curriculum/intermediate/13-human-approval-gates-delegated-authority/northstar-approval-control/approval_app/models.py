"""Typed contracts for the Course 23 approval control plane."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


RISK_ORDER = {"LOW": 1, "MODERATE": 2, "CONSEQUENTIAL": 3, "CRITICAL": 4}


@dataclass(frozen=True)
class ActionSubject:
    change_id: str
    action: str
    resource: str
    environment: str
    artifact_digest: str
    specification_digest: str
    policy_revision: str
    risk_tier: str
    incident_id: str | None = None

    @property
    def digest(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class AuthorityGrant:
    grant_id: str
    principal: str
    role: str
    actions: frozenset[str]
    resources: frozenset[str]
    environments: frozenset[str]
    max_risk: str
    starts_at: str
    expires_at: str
    delegable: bool
    state: str = "ACTIVE"


@dataclass(frozen=True)
class DelegationGrant:
    delegation_id: str
    parent_grant_id: str
    delegator: str
    delegate: str
    role: str
    actions: frozenset[str]
    resources: frozenset[str]
    environments: frozenset[str]
    max_risk: str
    starts_at: str
    expires_at: str
    may_redelegate: bool
    state: str = "ACTIVE"


@dataclass(frozen=True)
class Decision:
    state: str
    reason_code: str
    request_id: str
    receipt_ids: tuple[str, ...] = ()
    execution_id: str | None = None


class ControlError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
