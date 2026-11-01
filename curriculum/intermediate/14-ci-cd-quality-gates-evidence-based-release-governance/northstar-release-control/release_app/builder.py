"""Deterministic local build and authenticated teaching provenance."""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def deterministic_build(source: Path, destination: Path, source_commit: str) -> str:
    payload = b"NORTHSTAR-AI-SERVICE\n" + source_commit.encode("ascii") + b"\n" + source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return file_digest(destination)


def provenance_statement(
    artifact_digest: str,
    source_commit: str,
    source_branch: str,
    builder_id: str,
    workflow_revision: str,
) -> dict:
    return {
        "subject": {"name": "northstar-ai-service", "digest": artifact_digest},
        "predicate_type": "course24/slsa-provenance-teaching-v1",
        "build": {
            "source_commit": source_commit,
            "source_branch": source_branch,
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
