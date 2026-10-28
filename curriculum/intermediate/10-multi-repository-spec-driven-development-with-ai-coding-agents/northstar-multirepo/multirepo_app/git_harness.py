"""Build real local Git repositories and derive integration evidence from them."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import MappingProxyType

from .contracts import IntegrationReceipt, RepositoryRevision, TrustedContext, protected


REPOSITORIES = (
    "document-service",
    "ai-service",
    "review-service",
    "underwriting-api",
    "underwriter-ui",
)


def canonical_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


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


def _copy_tree(source: Path, destination: Path) -> None:
    for path in sorted(destination.rglob("*"), reverse=True):
        if ".git" not in path.parts and path.is_file():
            path.unlink()
    for path in source.rglob("*"):
        if path.is_file():
            target = destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


class TrustedGitHarness:
    """Create five isolated repositories and execute protected compatibility checks."""

    def __init__(self, root: Path):
        self.root = root
        self.parent_change = json.loads(
            (root / "parent-change/AI-2500.json").read_text(encoding="utf-8")
        )
        self.canonical_contract = json.loads(
            (root / "contracts/classification-v2.schema.json").read_text(encoding="utf-8")
        )
        self.work_units = json.loads(
            (root / "parent-change/work-units.json").read_text(encoding="utf-8")
        )

    def observe(self, candidate: dict[str, object]) -> TrustedContext:
        revisions: dict[str, RepositoryRevision] = {}
        configs: dict[str, dict[str, object]] = {}
        with tempfile.TemporaryDirectory(prefix="course20-multirepo-") as temporary:
            workspace = Path(temporary)
            for repository in REPOSITORIES:
                revision, config = self._build_repository(
                    workspace,
                    repository,
                    dict(candidate["repository_configs"][repository]),
                    dict(candidate.get("repository_extra_files", {}).get(repository, {})),
                )
                revisions[repository] = revision
                configs[repository] = config

        compatibility = self._compatibility_matrix(configs)
        scenarios = self._integration_scenarios(configs, compatibility)
        component_commits = {
            repository: revision.candidate_commit
            for repository, revision in revisions.items()
        }
        receipt = IntegrationReceipt(
            producer="northstar-integration-ci",
            change_id="AI-2500",
            contract_revision=2,
            component_commits=MappingProxyType(component_commits),
            scenario_results=MappingProxyType(scenarios),
        )
        registry = MappingProxyType(
            {
                "INT-RUN-AI2500": receipt,
                "INT-RUN-OLD": IntegrationReceipt(
                    producer=receipt.producer,
                    change_id=receipt.change_id,
                    contract_revision=1,
                    component_commits=receipt.component_commits,
                    scenario_results=receipt.scenario_results,
                ),
            }
        )
        trusted_work_units = json.loads(json.dumps(self.work_units))
        for repository, work_unit in trusted_work_units.items():
            work_unit["base_commit"] = revisions[repository].baseline_commit
        return TrustedContext(
            parent_change=protected(self.parent_change),
            canonical_contract=protected(self.canonical_contract),
            trusted_work_units=MappingProxyType(trusted_work_units),
            repositories=MappingProxyType(revisions),
            compatibility_matrix=MappingProxyType(compatibility),
            scenario_results=MappingProxyType(scenarios),
            evidence_registry=registry,
        )

    def baseline_configs(self) -> dict[str, dict[str, object]]:
        return {
            repository: json.loads(
                (self.root / "repositories" / repository / "baseline/config.json").read_text(
                    encoding="utf-8"
                )
            )
            for repository in REPOSITORIES
        }

    def reference_configs(self) -> dict[str, dict[str, object]]:
        configs = self.baseline_configs()
        for repository in ("ai-service", "review-service"):
            configs[repository] = json.loads(
                (self.root / "repositories" / repository / "candidate/config.json").read_text(
                    encoding="utf-8"
                )
            )
        return configs

    def _build_repository(
        self,
        workspace: Path,
        repository: str,
        candidate_config: dict[str, object],
        extra_files: dict[str, str],
    ) -> tuple[RepositoryRevision, dict[str, object]]:
        repository_root = workspace / repository
        repository_root.mkdir()
        _run(["git", "init", "-q"], cwd=repository_root)
        _run(["git", "config", "user.name", "Northstar Integration CI"], cwd=repository_root)
        _run(["git", "config", "user.email", "integration-ci@northstar.example"], cwd=repository_root)
        fixed_env = os.environ.copy()
        fixed_env.update(
            {
                "GIT_AUTHOR_DATE": "2026-02-01T00:00:00+0000",
                "GIT_COMMITTER_DATE": "2026-02-01T00:00:00+0000",
            }
        )
        template_root = self.root / "repositories" / repository
        _copy_tree(template_root / "baseline", repository_root)
        _run(["git", "add", "-A"], cwd=repository_root)
        _run(["git", "commit", "-q", "-m", f"{repository} approved baseline"], cwd=repository_root, env=fixed_env)
        baseline_commit = _run(["git", "rev-parse", "HEAD"], cwd=repository_root)

        candidate_template = template_root / "candidate"
        if candidate_template.exists():
            for path in candidate_template.rglob("*"):
                if path.is_file():
                    target = repository_root / path.relative_to(candidate_template)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
        (repository_root / "config.json").write_text(
            json.dumps(candidate_config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for relative, content in extra_files.items():
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe candidate path: {relative}")
            destination = repository_root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
        _run(["git", "add", "-A"], cwd=repository_root)
        _run(
            ["git", "commit", "-q", "--allow-empty", "-m", f"{repository} AI-2500 candidate"],
            cwd=repository_root,
            env=fixed_env,
        )
        candidate_commit = _run(["git", "rev-parse", "HEAD"], cwd=repository_root)
        _run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=repository_root,
        )
        changed = _run(
            ["git", "diff", "--name-only", baseline_commit, candidate_commit],
            cwd=repository_root,
        )
        return (
            RepositoryRevision(
                repository=repository,
                baseline_commit=baseline_commit,
                candidate_commit=candidate_commit,
                changed_paths=tuple(path for path in changed.splitlines() if path),
            ),
            candidate_config,
        )

    @staticmethod
    def _compatibility_matrix(configs: dict[str, dict[str, object]]) -> dict[str, bool]:
        producer_v2 = int(configs["ai-service"]["contract_revision"])
        consumer_v2 = set(configs["review-service"]["accepted_contract_revisions"])
        return {
            "ai-v1/review-v1": 1 in {1},
            "ai-v1/review-v2": 1 in consumer_v2,
            "ai-v2/review-v1": producer_v2 in {1},
            "ai-v2/review-v2": producer_v2 in consumer_v2,
        }

    @staticmethod
    def _integration_scenarios(
        configs: dict[str, dict[str, object]],
        compatibility: dict[str, bool],
    ) -> dict[str, bool]:
        ai = configs["ai-service"]
        review = configs["review-service"]
        underwriting = configs["underwriting-api"]
        return {
            "supported_document": int(ai["contract_revision"]) == 2,
            "unsupported_document": bool(review["unsupported_routes_to_review"]),
            "ambiguous_mapping": bool(ai["ambiguous_requires_review"]),
            "duplicate_event": bool(review["idempotent_submission"]),
            "missing_provenance": bool(review["requires_evidence_refs"]),
            "cross_tenant_reference": bool(review["enforces_tenant_scope"]),
            "review_service_unavailable": bool(ai["fail_closed_when_review_unavailable"]),
            "old_producer_new_consumer": compatibility["ai-v1/review-v2"],
            "new_producer_old_consumer_blocked": not compatibility["ai-v2/review-v1"],
            "stale_approval": bool(review["rejects_stale_approval"]),
            "single_authority": (
                not bool(ai["writes_authoritative_state"])
                and bool(underwriting["only_authoritative_state_owner"])
            ),
        }
