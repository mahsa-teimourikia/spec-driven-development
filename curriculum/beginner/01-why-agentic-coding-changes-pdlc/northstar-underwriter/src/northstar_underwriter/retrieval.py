"""Existing tenant filter applied before policy passages reach feature code."""

from __future__ import annotations

from collections.abc import Iterable

from .models import PolicyPassage


def passages_for_tenant(
    passages: Iterable[PolicyPassage], tenant_id: str
) -> tuple[PolicyPassage, ...]:
    return tuple(passage for passage in passages if passage.tenant_id == tenant_id)
