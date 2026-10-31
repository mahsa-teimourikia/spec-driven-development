"""Create and inspect real temporary Git repositories for Course 22."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Northstar Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@northstar.invalid",
    "GIT_COMMITTER_NAME": "Northstar Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@northstar.invalid",
    "GIT_AUTHOR_DATE": "2026-01-15T12:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-01-15T12:00:00+00:00",
}


@dataclass(frozen=True)
class GitCandidate:
    repository: str
    base_commit: str
    head_commit: str
    changed_paths: tuple[str, ...]
    change_types: Mapping[str, str]
    blobs: Mapping[str, str]
    base_is_ancestor: bool


class TrustedGitHarness:
    """Derive immutable revision subjects and diffs from Git, not PR metadata."""

    def _run(
        self,
        repo: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            env=GIT_ENV,
            text=True,
            capture_output=True,
            check=check,
        )

    @staticmethod
    def _write(repo: Path, relative: str, content: str) -> None:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def create_candidate(
        self,
        repository: str,
        candidate_files: Mapping[str, str],
        *,
        baseline_files: Mapping[str, str] | None = None,
    ) -> GitCandidate:
        baseline = dict(
            baseline_files
            or {
                "README.md": f"# {repository}\n\nSynthetic Course 22 repository.\n",
                "src/classifier.py": "def route(ambiguous: bool) -> str:\n    return 'review' if ambiguous else 'straight_through'\n",
                "tests/test_classifier.py": "# contributor test placeholder\n",
            }
        )
        with tempfile.TemporaryDirectory(prefix="course22-git-") as tmp:
            repo = Path(tmp) / repository
            repo.mkdir()
            self._run(repo, "init", "-q", "-b", "main")
            for path, content in baseline.items():
                self._write(repo, path, content)
            self._run(repo, "add", ".")
            self._run(repo, "commit", "-q", "-m", "baseline")
            base = self._run(repo, "rev-parse", "HEAD").stdout.strip()

            for path, content in candidate_files.items():
                self._write(repo, path, content)
            self._run(repo, "add", "-A")
            self._run(repo, "commit", "-q", "-m", "candidate")
            head = self._run(repo, "rev-parse", "HEAD").stdout.strip()
            ancestry = self._run(repo, "merge-base", "--is-ancestor", base, head, check=False)
            diff = self._run(repo, "diff", "--name-status", "-M", base, head).stdout.splitlines()
            change_types: dict[str, str] = {}
            changed_paths: list[str] = []
            for line in diff:
                columns = line.split("\t")
                status = columns[0]
                path = columns[-1]
                change_types[path] = status
                changed_paths.append(path)
            blobs = {
                path: self._run(repo, "show", f"{head}:{path}").stdout
                for path in changed_paths
                if not change_types[path].startswith("D")
            }
            return GitCandidate(
                repository=repository,
                base_commit=base,
                head_commit=head,
                changed_paths=tuple(sorted(changed_paths)),
                change_types=change_types,
                blobs=blobs,
                base_is_ancestor=ancestry.returncode == 0,
            )

    def merge_group_conflicts(self) -> bool:
        """Prove that two individually valid branches conflict when combined."""

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
            merge = self._run(repo, "merge", "--no-commit", "--no-ff", pr_b, check=False)
            return merge.returncode != 0
