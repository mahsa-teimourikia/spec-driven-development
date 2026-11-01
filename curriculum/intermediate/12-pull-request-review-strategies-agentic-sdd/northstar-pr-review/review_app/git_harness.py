"""Create and inspect real temporary Git repositories for Course 22."""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "Northstar Fixture", "GIT_AUTHOR_EMAIL": "fixture@northstar.invalid", "GIT_COMMITTER_NAME": "Northstar Fixture", "GIT_COMMITTER_EMAIL": "fixture@northstar.invalid", "GIT_AUTHOR_DATE": "2026-01-15T12:00:00+00:00", "GIT_COMMITTER_DATE": "2026-01-15T12:00:00+00:00"}


@dataclass(frozen=True)
class PathChange:
    status: str
    old_path: str | None
    new_path: str | None

    @property
    def touched_paths(self) -> tuple[str, ...]:
        return tuple(path for path in (self.old_path, self.new_path) if path is not None)


@dataclass(frozen=True)
class GitCandidate:
    repository: str
    base_commit: str
    head_commit: str
    changed_paths: tuple[str, ...]
    path_changes: tuple[PathChange, ...]
    change_types: Mapping[str, str]
    blobs: Mapping[str, str]
    base_is_ancestor: bool
    repository_bundle: bytes = field(repr=False, compare=False)


class TrustedGitHarness:
    """Derive immutable revisions and both sides of path changes from Git."""

    def _run(self, repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=repo, env=GIT_ENV, text=True, capture_output=True, check=check)

    @staticmethod
    def _write(repo: Path, relative: str, content: str) -> None:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def create_candidate(self, repository: str, candidate_files: Mapping[str, str | None], *, baseline_files: Mapping[str, str] | None = None, renames: Mapping[str, str] | None = None) -> GitCandidate:
        baseline = dict(baseline_files or {
            "README.md": f"# {repository}\n\nSynthetic Course 22 repository.\n",
            "src/classifier.py": "def route(ambiguous: bool, confidence: float = 0.0) -> str:\n    return 'review' if ambiguous else 'straight_through'\n",
            "tests/test_classifier.py": "# contributor test placeholder\n",
        })
        with tempfile.TemporaryDirectory(prefix="course22-git-") as tmp:
            repo = Path(tmp) / repository
            repo.mkdir()
            self._run(repo, "init", "-q", "-b", "main")
            for path, content in baseline.items():
                self._write(repo, path, content)
            self._run(repo, "add", ".")
            self._run(repo, "commit", "-q", "-m", "baseline")
            base = self._run(repo, "rev-parse", "HEAD").stdout.strip()
            for source, destination in (renames or {}).items():
                (repo / destination).parent.mkdir(parents=True, exist_ok=True)
                self._run(repo, "mv", source, destination)
            for path, content in candidate_files.items():
                target = repo / path
                if content is None:
                    target.unlink(missing_ok=True)
                else:
                    self._write(repo, path, content)
            self._run(repo, "add", "-A")
            self._run(repo, "commit", "-q", "-m", "candidate")
            head = self._run(repo, "rev-parse", "HEAD").stdout.strip()
            ancestry = self._run(repo, "merge-base", "--is-ancestor", base, head, check=False)
            lines = self._run(repo, "diff", "--name-status", "-M", "-C", base, head).stdout.splitlines()
            changes: list[PathChange] = []
            change_types: dict[str, str] = {}
            touched: set[str] = set()
            blob_paths: set[str] = set()
            for line in lines:
                columns = line.split("\t")
                status = columns[0]
                if status.startswith(("R", "C")):
                    old_path, new_path = columns[1], columns[2]
                elif status.startswith("D"):
                    old_path, new_path = columns[1], None
                else:
                    old_path, new_path = None, columns[1]
                change = PathChange(status, old_path, new_path)
                changes.append(change)
                for path in change.touched_paths:
                    touched.add(path)
                    change_types[path] = status
                if new_path is not None:
                    blob_paths.add(new_path)
            blobs = {path: self._run(repo, "show", f"{head}:{path}").stdout for path in sorted(blob_paths)}
            bundle_path = Path(tmp) / "candidate.bundle"
            self._run(repo, "bundle", "create", str(bundle_path), "--all")
            return GitCandidate(repository, base, head, tuple(sorted(touched)), tuple(changes), change_types, blobs, ancestry.returncode == 0, bundle_path.read_bytes())

    def merge_group_conflicts(self) -> bool:
        with tempfile.TemporaryDirectory(prefix="course22-merge-group-") as tmp:
            repo = Path(tmp) / "review-service"
            repo.mkdir()
            self._run(repo, "init", "-q", "-b", "main")
            self._write(repo, "src/parser.py", "FIELD = 'review_required'\n")
            self._run(repo, "add", ".")
            self._run(repo, "commit", "-q", "-m", "baseline")
            base = self._run(repo, "rev-parse", "HEAD").stdout.strip()
            self._run(repo, "switch", "-q", "-c", "pr-a")
            self._write(repo, "src/parser.py", "FIELD = 'requires_review'\n")
            self._run(repo, "add", ".")
            self._run(repo, "commit", "-q", "-m", "PR A")
            pr_a = self._run(repo, "rev-parse", "HEAD").stdout.strip()
            self._run(repo, "switch", "-q", "-c", "pr-b", base)
            self._write(repo, "src/parser.py", "FIELD = 'human_review_required'\n")
            self._run(repo, "add", ".")
            self._run(repo, "commit", "-q", "-m", "PR B")
            pr_b = self._run(repo, "rev-parse", "HEAD").stdout.strip()
            self._run(repo, "switch", "-q", "--detach", pr_a)
            return self._run(repo, "merge", "--no-commit", "--no-ff", pr_b, check=False).returncode != 0
