"""Canonical encoding, signed teaching evidence, and registry loading."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Evidence


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def sign_evidence(evidence: Evidence, key: str) -> str:
    return "hmac-sha256:" + hmac.new(
        key.encode("utf-8"), canonical_bytes(evidence.payload()), hashlib.sha256
    ).hexdigest()


def verify_evidence(evidence: Evidence, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign_evidence(evidence, key), signature)
