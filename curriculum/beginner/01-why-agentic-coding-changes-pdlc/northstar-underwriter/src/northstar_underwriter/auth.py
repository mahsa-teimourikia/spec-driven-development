"""Existing authorization boundary."""

from __future__ import annotations

from collections.abc import Mapping


def require_underwriter(claims: Mapping[str, str]) -> str:
    if claims.get("role") != "underwriter" or not claims.get("tenant_id"):
        raise PermissionError("corporate SSO underwriter role and tenant are required")
    return claims["tenant_id"]
