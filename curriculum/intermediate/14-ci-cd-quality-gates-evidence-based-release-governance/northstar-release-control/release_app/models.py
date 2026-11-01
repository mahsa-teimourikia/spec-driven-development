"""Typed contracts for evidence-based release governance."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field


def canonical_digest(value: object) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


class ReleaseError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class ReleaseManifest:
    release_id: str
    source_commit: str
    artifact_digest: str
    model_revision: str
    prompt_digest: str
    retrieval_revision: str
    tool_policy_revision: str
    schema_revision: str
    evaluation_contract_revision: str
    dataset_digest: str
    environment: str = "production"
    risk_tier: str = "CONSEQUENTIAL"

    @property
    def dependencies(self) -> dict[str, str]:
        return {
            "source_commit": self.source_commit,
            "artifact_digest": self.artifact_digest,
            "model_revision": self.model_revision,
            "prompt_digest": self.prompt_digest,
            "retrieval_revision": self.retrieval_revision,
            "tool_policy_revision": self.tool_policy_revision,
            "schema_revision": self.schema_revision,
            "evaluation_contract_revision": self.evaluation_contract_revision,
            "dataset_digest": self.dataset_digest,
            "environment": self.environment,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(asdict(self))


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    kind: str
    subject_digest: str
    producer: str
    result: str
    dependencies: dict[str, str] = field(default_factory=dict)
    details: dict = field(default_factory=dict)

    @property
    def digest(self) -> str:
        return canonical_digest(asdict(self))


@dataclass(frozen=True)
class Decision:
    state: str
    reason_codes: tuple[str, ...]
    release_id: str
    manifest_digest: str
    operation_id: str | None = None
