"""Create real temporary Git repositories for Course 21 evidence subjects."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


REPOSITORIES = (
    "document-service",
    "ai-service",
    "review-service",
    "underwriting-api",
    "underwriter-ui",
)


@dataclass(frozen=True)
class RepositoryRevision:
    repository: str
    baseline_commit: str
    candidate_commit: str
    changed_paths: tuple[str, ...]
    tests_passed: bool


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TrustedGitHarness:
    """Build immutable evidence subjects from maintained repository fixtures."""

    def __init__(self, root: Path):
        self.root = root
        self.fixtures = {
            path.stem: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((root / "repositories").glob("*.json"))
        }
        if set(self.fixtures) != set(REPOSITORIES):
            raise ValueError("repository fixture set is incomplete")

    def observe(
        self,
        *,
        extra_files: Mapping[str, Mapping[str, str]] | None = None,
    ) -> dict[str, RepositoryRevision]:
        extra_files = extra_files or {}
        revisions: dict[str, RepositoryRevision] = {}
        with tempfile.TemporaryDirectory(prefix="course21-parallel-") as temporary:
            workspace = Path(temporary)
            for repository in REPOSITORIES:
                revisions[repository] = self._build_repository(
                    workspace / repository,
                    repository,
                    self.fixtures[repository],
                    extra_files.get(repository, {}),
                )
        return revisions

    def _build_repository(
        self,
        root: Path,
        repository: str,
        fixture: Mapping[str, object],
        extra_files: Mapping[str, str],
    ) -> RepositoryRevision:
        root.mkdir(parents=True)
        _run(["git", "init", "-q"], cwd=root)
        _run(["git", "config", "user.name", "Northstar Parallel Delivery CI"], cwd=root)
        _run(["git", "config", "user.email", "parallel-ci@northstar.example"], cwd=root)
        fixed_env = os.environ.copy()
        fixed_env.update(
            {
                "GIT_AUTHOR_DATE": "2026-10-30T00:00:00+0000",
                "GIT_COMMITTER_DATE": "2026-10-30T00:00:00+0000",
            }
        )

        baseline = dict(fixture["baseline"])
        candidate = dict(fixture["candidate"])
        _write(root / "README.md", f"# {repository}\n\nSynthetic Course 21 repository.\n")
        _write(root / "src/__init__.py", "")
        _write(
            root / "src/component.py",
            self._component_source(repository, baseline),
        )
        _write(
            root / "tests/test_component.py",
            self._test_source(baseline),
        )
        _write(
            root / "spec/work-unit.json",
            json.dumps(
                {
                    "change_id": "AI-2500",
                    "repository": repository,
                    "contract_revision": baseline["contract_revision"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        _run(["git", "add", "-A"], cwd=root)
        _run(
            ["git", "commit", "-q", "-m", f"{repository} approved baseline"],
            cwd=root,
            env=fixed_env,
        )
        baseline_commit = _run(["git", "rev-parse", "HEAD"], cwd=root)

        _write(root / "src/component.py", self._component_source(repository, candidate))
        _write(root / "tests/test_component.py", self._test_source(candidate))
        _write(
            root / "spec/work-unit.json",
            json.dumps(
                {
                    "change_id": "AI-2500",
                    "repository": repository,
                    "contract_revision": candidate["contract_revision"],
                    "behavior": candidate["behavior"],
                    "authoritative": candidate["authoritative"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        for relative, content in extra_files.items():
            target = Path(relative)
            if target.is_absolute() or ".." in target.parts:
                raise ValueError(f"unsafe fixture path: {relative}")
            _write(root / target, content)
        _run(["git", "add", "-A"], cwd=root)
        _run(
            ["git", "commit", "-q", "--allow-empty", "-m", f"{repository} AI-2500 candidate"],
            cwd=root,
            env=fixed_env,
        )
        candidate_commit = _run(["git", "rev-parse", "HEAD"], cwd=root)
        test = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        changed = _run(
            ["git", "diff", "--name-only", baseline_commit, candidate_commit],
            cwd=root,
        )
        return RepositoryRevision(
            repository=repository,
            baseline_commit=baseline_commit,
            candidate_commit=candidate_commit,
            changed_paths=tuple(path for path in changed.splitlines() if path),
            tests_passed=test.returncode == 0,
        )

    @staticmethod
    def _component_source(repository: str, payload: Mapping[str, object]) -> str:
        return (
            f'REPOSITORY = "{repository}"\n'
            f'CONTRACT_REVISION = {int(payload["contract_revision"])}\n'
            f'BEHAVIOR = {payload["behavior"]!r}\n'
            f'AUTHORITATIVE = {bool(payload["authoritative"])}\n\n'
            "def describe():\n"
            "    return {\n"
            "        'repository': REPOSITORY,\n"
            "        'contract_revision': CONTRACT_REVISION,\n"
            "        'behavior': BEHAVIOR,\n"
            "        'authoritative': AUTHORITATIVE,\n"
            "    }\n"
        )

    @staticmethod
    def _test_source(payload: Mapping[str, object]) -> str:
        return (
            "import unittest\n"
            "from src.component import describe\n\n"
            "class ComponentContractTest(unittest.TestCase):\n"
            "    def test_contract_revision_and_behavior(self):\n"
            "        observed = describe()\n"
            f"        self.assertEqual(observed['contract_revision'], {int(payload['contract_revision'])})\n"
            f"        self.assertEqual(observed['behavior'], {payload['behavior']!r})\n"
        )
