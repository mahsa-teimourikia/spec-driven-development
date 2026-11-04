"""Trusted registry, Git, digest, and signature helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ArchitectureError


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_payload(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def sign_payload(value: Any, key: str) -> str:
    body = canonical_json(value).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_signature(value: Any, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign_payload(value, key), signature)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchitectureError("REGISTRY_UNREADABLE", f"Could not read {path}: {exc}") from exc


def parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise ArchitectureError("TIME_INVALID", f"Invalid RFC 3339 time: {value}") from exc


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ArchitectureError(
            "GIT_EVIDENCE_UNAVAILABLE",
            result.stderr.strip() or f"git {' '.join(args)} failed",
        )
    return result.stdout.strip()


def current_head(repo: Path) -> str:
    return git(repo, "rev-parse", "HEAD")


def validate_commit_range(repo: Path, base_commit: str, head_commit: str) -> tuple[str, ...]:
    actual = current_head(repo)
    if actual != head_commit:
        raise ArchitectureError(
            "HEAD_BINDING_MISMATCH",
            f"Requested {head_commit}, but repository HEAD is {actual}",
        )
    result = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", base_commit, head_commit],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ArchitectureError("BASE_NOT_ANCESTOR", "The base is not an ancestor of HEAD")
    changed = git(repo, "diff", "--name-only", base_commit, head_commit)
    return tuple(line for line in changed.splitlines() if line)


def file_digest(path: Path) -> str:
    return sha256_bytes(path.read_bytes())
