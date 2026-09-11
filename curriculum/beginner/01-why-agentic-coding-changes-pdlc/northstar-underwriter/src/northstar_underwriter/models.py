"""Stable domain records that predate JIRA-4821."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyPassage:
    passage_id: str
    tenant_id: str
    text: str
