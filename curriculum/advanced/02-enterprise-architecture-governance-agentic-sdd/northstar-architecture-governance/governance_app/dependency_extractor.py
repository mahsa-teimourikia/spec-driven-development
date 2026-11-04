"""Derive architecture facts from repository content, never candidate labels."""

from __future__ import annotations

import ast
import json
import uuid
from pathlib import Path
from typing import Any

from .models import ArchitectureError, Observation, ServiceEdge
from .registry import file_digest, sign_payload, validate_commit_range


def _imports(path: Path, relative: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    except (OSError, SyntaxError) as exc:
        raise ArchitectureError("SOURCE_UNPARSABLE", f"Cannot parse {relative}: {exc}") from exc
    result: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        for name in names:
            result.append({"file": relative, "module": name, "line": node.lineno})
    return result


def _urls(path: Path, relative: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
    except (OSError, SyntaxError):
        return []
    result: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if value.startswith(("https://", "http://")):
                result.append({"file": relative, "url": value, "line": node.lineno})
    return result


def _json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchitectureError("ARCHITECTURE_FACT_UNREADABLE", f"Cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArchitectureError("ARCHITECTURE_FACT_INVALID", f"Expected object in {path}")
    return value


def _technologies(repo: Path) -> list[dict[str, Any]]:
    path = repo / "requirements.txt"
    if not path.exists():
        return []
    result = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split("==", 1)[0].split(">=", 1)[0].strip().lower()
        result.append({"name": name, "file": "requirements.txt", "line": line_number})
    return result


def _service_edges(repo: Path) -> tuple[ServiceEdge, ...]:
    value = _json_if_present(repo / "service-dependencies.json") or {"edges": []}
    edges = value.get("edges", [])
    if not isinstance(edges, list):
        raise ArchitectureError("DEPENDENCY_GRAPH_INVALID", "edges must be an array")
    try:
        return tuple(
            ServiceEdge(source=item["source"], target=item["target"], mode=item.get("mode", "sync"))
            for item in edges
        )
    except (KeyError, TypeError) as exc:
        raise ArchitectureError("DEPENDENCY_GRAPH_INVALID", "Every edge needs source and target") from exc


def extract_observation(
    repo: Path,
    base_commit: str,
    head_commit: str,
    environment: str,
    policy_version: str,
    issued_at: str,
    producer: str,
    signing_key: str,
    runtime_egress_evidence: bool = False,
    runtime_evidence_id: str | None = None,
) -> Observation:
    """Create an independently signed observation from the checked-out Git revision."""

    changed_files = validate_commit_range(repo, base_commit, head_commit)
    imports: list[dict[str, Any]] = []
    urls: list[dict[str, Any]] = []
    digests: dict[str, str] = {}
    for path in sorted((repo / "src").rglob("*.py")):
        relative = path.relative_to(repo).as_posix()
        imports.extend(_imports(path, relative))
        urls.extend(_urls(path, relative))
        digests[relative] = file_digest(path)
    for relative in ("requirements.txt", "service-dependencies.json"):
        path = repo / relative
        if path.exists():
            digests[relative] = file_digest(path)
    for relative in changed_files:
        path = repo / relative
        if path.is_file():
            digests[relative] = file_digest(path)

    shadow_names = {
        "architecture-policy.json",
        "enterprise-principles.json",
        "technology-standards.json",
    }
    shadow_paths = tuple(item for item in changed_files if Path(item).name in shadow_names)
    observation = Observation(
        observation_id="OBS-" + uuid.uuid4().hex[:12].upper(),
        repository=repo.name,
        base_commit=base_commit,
        head_commit=head_commit,
        environment=environment,
        policy_version=policy_version,
        changed_files=changed_files,
        imports=tuple(imports),
        urls=tuple(urls),
        technologies=tuple(_technologies(repo)),
        service_edges=_service_edges(repo),
        file_digests=digests,
        adr_proposal=_json_if_present(repo / "architecture" / "adr-proposal.json"),
        architecture_context=_json_if_present(repo / "architecture" / "context.json"),
        policy_shadow_paths=shadow_paths,
        # This value is supplied only after the control plane validates external,
        # head-bound network evidence. Repository-local flags are ignored.
        runtime_egress_evidence=runtime_egress_evidence,
        runtime_evidence_id=runtime_evidence_id,
        producer=producer,
        issued_at=issued_at,
    )
    return Observation(**{**observation.__dict__, "signature": sign_payload(observation.payload(), signing_key)})
