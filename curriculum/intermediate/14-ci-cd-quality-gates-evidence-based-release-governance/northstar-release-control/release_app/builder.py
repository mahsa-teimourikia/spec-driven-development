"""Deterministic executable artifacts and authenticated teaching provenance."""
from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from pathlib import Path
from types import MappingProxyType
from typing import Callable


ARTIFACT_FORMAT = "course24-python-application-v2"


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def deterministic_build(
    source: Path,
    destination: Path,
    source_commit: str,
    repository: str = "https://github.com/northstar/underwriting-ai.git",
) -> str:
    """Package source as a canonical executable teaching artifact."""
    source_bytes = source.read_bytes()
    payload = {
        "format": ARTIFACT_FORMAT,
        "repository": repository,
        "source_commit": source_commit,
        "source_digest": "sha256:" + hashlib.sha256(source_bytes).hexdigest(),
        "entrypoint": "classifier:classify",
        "source": source_bytes.decode("utf-8"),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return file_digest(destination)


def build_from_git(
    checkout: Path,
    source_relative: str,
    destination: Path,
    repository: str,
    expected_branch: str,
) -> tuple[str, str]:
    """Derive source identity from a clean trusted checkout, never caller metadata."""
    def git(*arguments: str) -> str:
        result = subprocess.run(
            ("git", "-C", str(checkout), *arguments),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    branch = git("symbolic-ref", "--short", "HEAD")
    if branch != expected_branch:
        raise ValueError(f"unexpected source branch: {branch}")
    if git("status", "--porcelain"):
        raise ValueError("trusted source checkout is dirty")
    commit = git("rev-parse", "HEAD")
    tracked_source = subprocess.run(
        ("git", "-C", str(checkout), "show", f"{commit}:{source_relative}"),
        check=True,
        capture_output=True,
    ).stdout
    source = checkout / source_relative
    if source.read_bytes() != tracked_source:
        raise ValueError("working source differs from verified commit")
    return deterministic_build(source, destination, commit, repository), commit


def load_classifier_from_artifact(path: Path, expected_digest: str) -> Callable[[str], dict]:
    """Verify and execute the exact packaged implementation under evaluation."""
    if file_digest(path) != expected_digest:
        raise ValueError("artifact digest does not match the release subject")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != ARTIFACT_FORMAT:
        raise ValueError("unsupported artifact format")
    source = payload.get("source", "").encode("utf-8")
    if "sha256:" + hashlib.sha256(source).hexdigest() != payload.get("source_digest"):
        raise ValueError("packaged source digest mismatch")
    namespace: dict = {"__builtins__": MappingProxyType({"any": any, "len": len, "str": str})}
    exec(compile(source, f"{path}!classifier.py", "exec"), namespace)
    classify = namespace.get("classify")
    if not callable(classify):
        raise ValueError("artifact entrypoint is missing")
    return classify


def provenance_statement(
    artifact_digest: str,
    source_commit: str,
    source_branch: str,
    source_repository: str,
    builder_id: str,
    workflow_revision: str,
) -> dict:
    return {
        "subject": {"name": "northstar-ai-service", "digest": artifact_digest},
        "predicate_type": "course24/slsa-provenance-teaching-v2",
        "build": {
            "source_commit": source_commit,
            "source_branch": source_branch,
            "source_repository": source_repository,
            "builder_id": builder_id,
            "workflow_revision": workflow_revision,
            "dependencies_locked": True,
        },
    }


def sign_statement(statement: dict, key: str) -> str:
    material = json.dumps(statement, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "hmac-sha256:" + hmac.new(key.encode("utf-8"), material, hashlib.sha256).hexdigest()


def verify_statement(statement: dict, signature: str, key: str) -> bool:
    return hmac.compare_digest(sign_statement(statement, key), signature)


def create_sbom(lockfile: Path, destination: Path) -> dict:
    components = []
    for line in lockfile.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        name, version = item.split("==", 1)
        components.append({"name": name, "version": version})
    sbom = {"format": "course24-cyclonedx-teaching-v1", "components": components}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(sbom, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return sbom
