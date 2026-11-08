"""Create and load exact Git-backed Northstar service revisions."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

from .models import QualityError


SERVICES = ("ai-service", "review-service", "underwriting-api")
FIXED_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Northstar Quality Fixture",
    "GIT_AUTHOR_EMAIL": "quality-fixture@northstar.invalid",
    "GIT_COMMITTER_NAME": "Northstar Quality Fixture",
    "GIT_COMMITTER_EMAIL": "quality-fixture@northstar.invalid",
    "GIT_AUTHOR_DATE": "2026-11-08T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-11-08T00:00:00+00:00",
}


@dataclass(frozen=True)
class RevisionFixture:
    root: Path
    repositories: dict[str, Path]
    commits: dict[str, str]
    modules: dict[str, ModuleType]


def _git(repository: Path, *arguments: str) -> str:
    environment = os.environ.copy()
    environment.update(FIXED_GIT_ENV)
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repository,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise QualityError("GIT_FIXTURE_FAILED", str(exc)) from exc
    return result.stdout.strip()


def _load_module(name: str, path: Path) -> ModuleType:
    module_name = "course27_" + name.replace("-", "_")
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise QualityError("SERVICE_IMPORT_FAILED", str(path))
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def create_revision_fixture(course_root: Path, workspace: Path) -> RevisionFixture:
    """Copy service sources, commit them reproducibly, and load those exact files."""

    source_root = course_root / "repositories"
    repositories: dict[str, Path] = {}
    commits: dict[str, str] = {}
    modules: dict[str, ModuleType] = {}
    for service in SERVICES:
        source = source_root / service
        target = workspace / service
        shutil.copytree(source, target)
        _git(target, "init", "--quiet", "--initial-branch=main")
        _git(target, "add", "service.py")
        _git(target, "commit", "--quiet", "-m", "Northstar AI-2605 fixture")
        revision = _git(target, "rev-parse", "HEAD")
        if len(revision) != 40:
            raise QualityError("GIT_REVISION_INVALID", service)
        repositories[service] = target
        commits[service] = revision
        modules[service] = _load_module(service, target / "service.py")
    return RevisionFixture(
        root=workspace,
        repositories=repositories,
        commits=commits,
        modules=modules,
    )


def dirty_repository(fixture: RevisionFixture, service: str) -> None:
    """Change a tracked service after evidence collection without committing it."""

    path = fixture.repositories[service] / "service.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# post-evidence change\n", encoding="utf-8")


def repository_is_clean(fixture: RevisionFixture, service: str) -> bool:
    return _git(fixture.repositories[service], "status", "--porcelain") == ""
