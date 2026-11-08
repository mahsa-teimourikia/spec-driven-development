"""Canonical serialization, signatures, digests, and time validation."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import QualityError


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_payload(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sign_payload(value: Any, key: str) -> str:
    body = canonical_json(value).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(value: Any, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign_payload(value, key), signature)


def parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise QualityError("TIME_INVALID", value) from exc


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QualityError("REGISTRY_UNREADABLE", str(path)) from exc

