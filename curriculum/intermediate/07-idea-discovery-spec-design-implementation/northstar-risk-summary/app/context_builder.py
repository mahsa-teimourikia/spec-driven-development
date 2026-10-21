"""Build exact, authorized execution context from trusted application facts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Iterable

from .contracts import EvidenceDocument, ExecutionContext


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_context(
    submission_id: str,
    documents: Iterable[EvidenceDocument],
    *,
    specification_revision: int,
    architecture_revision: str,
    repository_base: str,
    permissions: tuple[str, ...] = ("read_submission_evidence", "create_summary_proposal"),
) -> tuple[ExecutionContext, dict[str, EvidenceDocument]]:
    selected = {
        document.document_id: document
        for document in documents
        if document.authorized and document.submission_id == submission_id
    }
    core = {
        "context_id": "CTX-AI-2410@3-training",
        "submission_id": submission_id,
        "specification_revision": specification_revision,
        "architecture_revision": architecture_revision,
        "repository_base": repository_base,
        "document_revisions": tuple(sorted((item.document_id, item.revision) for item in selected.values())),
        "permissions": tuple(sorted(permissions)),
    }
    return ExecutionContext(**core, digest=canonical_digest(core)), selected


def context_payload(context: ExecutionContext) -> dict[str, object]:
    payload = asdict(context)
    return {key: payload[key] for key in payload if key != "digest"}


def context_is_canonical(context: ExecutionContext) -> bool:
    return context.digest == canonical_digest(context_payload(context))
