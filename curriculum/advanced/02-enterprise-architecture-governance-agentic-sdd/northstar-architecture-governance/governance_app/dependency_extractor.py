"""Derive architecture facts from committed Git objects, never candidate labels."""

from __future__ import annotations

import ast
import json
import re
import uuid
from pathlib import Path
from typing import Any

from .models import ArchitectureError, Observation, ServiceEdge
from .registry import git_object, git_tree_entries, sha256_bytes, sign_payload, validate_commit_range


SCANNED_SOURCE_SUFFIXES = {".py"}
KNOWN_SOURCE_SUFFIXES = {
    ".c", ".clj", ".cpp", ".cs", ".ex", ".exs", ".go", ".java", ".js",
    ".kt", ".php", ".rb", ".rs", ".scala", ".swift", ".ts", ".tsx",
}
CONFIG_SUFFIXES = {".env", ".ini", ".json", ".toml", ".yaml", ".yml"}
URL_PATTERN = re.compile(r"https?://[^\\s\\\"'<>]+")


def _source_facts(
    content: str, relative: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    try:
        tree = ast.parse(content, filename=relative)
    except SyntaxError as exc:
        raise ArchitectureError("SOURCE_UNPARSABLE", f"Cannot parse {relative}: {exc}") from exc
    imports: list[dict[str, Any]] = []
    urls: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        for name in names:
            imports.append({"file": relative, "module": name, "line": node.lineno})
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value.strip()
            if value.startswith(("https://", "http://")):
                urls.append({"file": relative, "url": value, "line": node.lineno})
        if isinstance(node, ast.Call):
            dynamic = isinstance(node.func, ast.Name) and node.func.id == "__import__"
            dynamic = dynamic or (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
                and node.func.attr == "import_module"
            )
            if dynamic:
                unresolved.append(f"DYNAMIC_IMPORT:{relative}:{node.lineno}")
    return imports, urls, unresolved


def _decode(raw: bytes, relative: str) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArchitectureError("ARCHITECTURE_FACT_UNREADABLE", f"Cannot decode {relative}") from exc


def _config_facts(content: str, relative: str) -> tuple[list[dict[str, Any]], list[str]]:
    urls: list[dict[str, Any]] = []
    unresolved: list[str] = []
    endpoint_terms = ("endpoint", "base_url", "destination", "host")
    for line_number, line in enumerate(content.splitlines(), start=1):
        matches = URL_PATTERN.findall(line)
        urls.extend({"file": relative, "url": value.rstrip(",]})"), "line": line_number} for value in matches)
        if any(term in line.lower() for term in endpoint_terms) and not matches:
            unresolved.append(f"CONFIG_ENDPOINT_UNRESOLVED:{relative}:{line_number}")
    return urls, unresolved


def _json_if_present(objects: dict[str, bytes], relative: str) -> dict[str, Any] | None:
    raw = objects.get(relative)
    if raw is None:
        return None
    try:
        value = json.loads(_decode(raw, relative))
    except json.JSONDecodeError as exc:
        raise ArchitectureError("ARCHITECTURE_FACT_UNREADABLE", f"Cannot read {relative}: {exc}") from exc
    if not isinstance(value, dict):
        raise ArchitectureError("ARCHITECTURE_FACT_INVALID", f"Expected object in {relative}")
    return value


def _technologies(objects: dict[str, bytes]) -> list[dict[str, Any]]:
    raw = objects.get("requirements.txt")
    if raw is None:
        return []
    result = []
    for line_number, source in enumerate(_decode(raw, "requirements.txt").splitlines(), start=1):
        line = source.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split("==", 1)[0].split(">=", 1)[0].strip().lower()
        result.append({"name": name, "file": "requirements.txt", "line": line_number})
    return result


def _service_edges(objects: dict[str, bytes]) -> tuple[ServiceEdge, ...]:
    value = _json_if_present(objects, "service-dependencies.json") or {"edges": []}
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
    """Create a signed observation exclusively from objects at head_commit."""

    changed_files = validate_commit_range(repo, base_commit, head_commit)
    entries = git_tree_entries(repo, head_commit)
    objects: dict[str, bytes] = {}
    imports: list[dict[str, Any]] = []
    urls: list[dict[str, Any]] = []
    unresolved: list[str] = []
    python_files = 0
    unsupported_files = 0
    config_files = 0

    for entry in entries:
        relative = entry["path"]
        suffix = Path(relative).suffix.lower()
        is_source = relative.startswith("src/")
        if is_source and entry["mode"] == "120000":
            raise ArchitectureError("SOURCE_SYMLINK_UNSUPPORTED", f"Tracked source symlink: {relative}")
        if is_source and suffix in KNOWN_SOURCE_SUFFIXES:
            unsupported_files += 1
            unresolved.append(f"LANGUAGE_SCANNER_UNAVAILABLE:{suffix}:{relative}")
        if is_source and suffix in SCANNED_SOURCE_SUFFIXES:
            python_files += 1
            raw = git_object(repo, head_commit, relative)
            objects[relative] = raw
            found_imports, found_urls, found_unresolved = _source_facts(_decode(raw, relative), relative)
            imports.extend(found_imports)
            urls.extend(found_urls)
            unresolved.extend(found_unresolved)
        if relative.startswith("config/") and suffix in CONFIG_SUFFIXES:
            config_files += 1
            raw = git_object(repo, head_commit, relative)
            objects[relative] = raw
            found_urls, found_unresolved = _config_facts(_decode(raw, relative), relative)
            urls.extend(found_urls)
            unresolved.extend(found_unresolved)

    metadata_paths = {
        "requirements.txt",
        "service-dependencies.json",
        "architecture/adr-proposal.json",
        "architecture/context.json",
    }
    tracked_paths = {entry["path"] for entry in entries}
    for relative in metadata_paths & tracked_paths:
        objects[relative] = git_object(repo, head_commit, relative)
    for relative in changed_files:
        if relative in tracked_paths and relative not in objects:
            objects[relative] = git_object(repo, head_commit, relative)

    technologies = _technologies(objects)
    service_edges = _service_edges(objects)
    digests = {relative: sha256_bytes(raw) for relative, raw in objects.items()}
    shadow_names = {
        "architecture-policy.json",
        "enterprise-principles.json",
        "technology-standards.json",
    }
    shadow_paths = tuple(item for item in changed_files if Path(item).name in shadow_names)
    coverage: dict[str, Any] = {
        "source_basis": "git_objects",
        "tracked_source_files": python_files + unsupported_files,
        "python_files_parsed": python_files,
        "unsupported_source_files": unsupported_files,
        "config_files_scanned": config_files,
        "direct_imports_observed": len(imports),
        "literal_urls_observed": len(urls),
        "declared_technologies_observed": len(technologies),
        "declared_service_edges_observed": len(service_edges),
        "transitive_dependencies": "not_assessed",
    }
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
        technologies=tuple(technologies),
        service_edges=service_edges,
        file_digests=digests,
        adr_proposal=_json_if_present(objects, "architecture/adr-proposal.json"),
        architecture_context=_json_if_present(objects, "architecture/context.json"),
        policy_shadow_paths=shadow_paths,
        scanner_coverage=coverage,
        unresolved_dependency_categories=tuple(sorted(unresolved)),
        runtime_egress_evidence=runtime_egress_evidence,
        runtime_evidence_id=runtime_evidence_id,
        producer=producer,
        issued_at=issued_at,
    )
    return Observation(**{**observation.__dict__, "signature": sign_payload(observation.payload(), signing_key)})
