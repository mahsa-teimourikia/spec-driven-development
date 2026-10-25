"""Executable three-commit delivery exercise in an isolated local repository."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "user.name=Course 17", "-c", "user.email=course17@example.invalid", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit(repo: Path, path: str, payload: dict[str, object], message: str) -> str:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _git(repo, "add", path)
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def run_three_commit_exercise() -> dict[str, object]:
    """Prove dependency order and invalidate integration after contract drift."""

    with tempfile.TemporaryDirectory(prefix="course17-pr-sequence-") as directory:
        repo = Path(directory)
        _git(repo, "init", "-b", "main")
        contract = _commit(
            repo,
            "spec/contract.json",
            {"change_id": "AI-2410", "specification_revision": 3, "state": "APPROVED"},
            "PR 1: approve contract revision 3",
        )
        implementation = _commit(
            repo,
            "app/implementation.json",
            {"contract_commit": contract, "specification_revision": 3, "state": "BOUNDED"},
            "PR 2: implement approved contract",
        )
        integration = _commit(
            repo,
            "evidence/integration.json",
            {"implementation_commit": implementation, "specification_revision": 3, "state": "READY_FOR_INTEGRATION_REVIEW"},
            "PR 3: attach independent evidence",
        )
        parents = {
            implementation: _git(repo, "rev-parse", f"{implementation}^"),
            integration: _git(repo, "rev-parse", f"{integration}^"),
        }
        ordered = parents[implementation] == contract and parents[integration] == implementation

        # A prerequisite revision changes after the three commits. The existing
        # implementation and evidence remain historical facts but become stale.
        changed_contract_revision = 4
        integration_valid_after_change = changed_contract_revision == 3
        return {
            "commits": {"contract": contract, "implementation": implementation, "integration": integration},
            "dependency_order_valid": ordered,
            "integration_state_before_change": "READY_FOR_INTEGRATION_REVIEW" if ordered else "BLOCKED",
            "changed_contract_revision": changed_contract_revision,
            "integration_valid_after_change": integration_valid_after_change,
            "invalidation_code": None if integration_valid_after_change else "STALE_CONTRACT_REVISION",
        }

