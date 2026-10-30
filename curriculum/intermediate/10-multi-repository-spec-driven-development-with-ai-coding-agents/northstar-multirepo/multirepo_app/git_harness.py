"""Build real local Git repositories and derive integration evidence from them."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
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
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
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
        self.repository_dispositions = json.loads(
            (root / "parent-change/repository-dispositions.json").read_text(encoding="utf-8")
        )
        self.rollout_policy = json.loads(
            (root / "integration/rollout-transitions.json").read_text(encoding="utf-8")
        )
        self.requirement_obligations = json.loads(
            (root / "integration/requirement-evidence.json").read_text(encoding="utf-8")
        )

    def observe(self, candidate: dict[str, object]) -> TrustedContext:
        revisions: dict[str, RepositoryRevision] = {}
        configs: dict[str, dict[str, object]] = {}
        local_ci: dict[str, bool] = {}
        with tempfile.TemporaryDirectory(prefix="course20-multirepo-") as temporary:
            workspace = Path(temporary)
            for repository in REPOSITORIES:
                revision, config, tests_passed = self._build_repository(
                    workspace,
                    repository,
                    dict(candidate["repository_configs"][repository]),
                    dict(candidate.get("repository_extra_files", {}).get(repository, {})),
                )
                revisions[repository] = revision
                configs[repository] = config
                local_ci[repository] = tests_passed

            compatibility = self._compatibility_matrix(workspace)
            scenarios = self._integration_scenarios(workspace, compatibility)
        requirement_evidence = self._requirement_evidence(scenarios)
        component_commits = {
            repository: revision.candidate_commit
            for repository, revision in revisions.items()
        }
        contract_digest = canonical_digest(self.canonical_contract)
        result_digest = canonical_digest(
            {
                "compatibility": compatibility,
                "scenarios": scenarios,
                "component_commits": component_commits,
                "contract_digest": contract_digest,
            }
        )
        claim_coverage = {
            requirement_id: tuple(evidence["test_ids"])
            for requirement_id, evidence in requirement_evidence.items()
        }
        receipt = IntegrationReceipt(
            producer="northstar-integration-ci",
            change_id="AI-2500",
            contract_revision=2,
            contract_digest=contract_digest,
            component_commits=MappingProxyType(component_commits),
            scenario_results=MappingProxyType(scenarios),
            compatibility_results=MappingProxyType(compatibility),
            result_artifact_digest=result_digest,
            claim_coverage=MappingProxyType(claim_coverage),
        )
        registry = MappingProxyType(
            {
                "INT-RUN-AI2500": receipt,
                "INT-RUN-OLD": IntegrationReceipt(
                    producer=receipt.producer,
                    change_id=receipt.change_id,
                    contract_revision=1,
                    contract_digest=receipt.contract_digest,
                    component_commits=receipt.component_commits,
                    scenario_results=receipt.scenario_results,
                    compatibility_results=receipt.compatibility_results,
                    result_artifact_digest=receipt.result_artifact_digest,
                    claim_coverage=receipt.claim_coverage,
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
            repository_dispositions=protected(self.repository_dispositions),
            rollout_policy=protected(self.rollout_policy),
            repositories=MappingProxyType(revisions),
            compatibility_matrix=MappingProxyType(compatibility),
            scenario_results=MappingProxyType(scenarios),
            local_ci_results=MappingProxyType(local_ci),
            requirement_evidence=MappingProxyType(requirement_evidence),
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
    ) -> tuple[RepositoryRevision, dict[str, object], bool]:
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
        baseline_snapshot = workspace / ".baseline-snapshots" / repository
        for source_path in (repository_root / "src").rglob("*.py"):
            destination = baseline_snapshot / source_path.relative_to(repository_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)

        candidate_template = template_root / "candidate"
        if candidate_template.exists():
            for path in candidate_template.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
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
        test_result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
            cwd=repository_root,
            text=True,
            capture_output=True,
            check=False,
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
            test_result.returncode == 0,
        )

    @staticmethod
    def _load_module(path: Path, label: str):
        module_name = f"course20_{label}_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _modules(self, workspace: Path) -> dict[str, object]:
        return {
            "ai_v1": self._load_module(
                workspace / ".baseline-snapshots/ai-service/src/classifier.py",
                "ai_v1",
            ),
            "ai_v2": self._load_module(
                workspace / "ai-service/src/classifier.py", "ai_v2"
            ),
            "review_v1": self._load_module(
                workspace / ".baseline-snapshots/review-service/src/review.py",
                "review_v1",
            ),
            "review_v2": self._load_module(
                workspace / "review-service/src/review.py", "review_v2"
            ),
            "document": self._load_module(
                workspace / "document-service/src/document.py", "document"
            ),
            "underwriting": self._load_module(
                workspace / "underwriting-api/src/state.py", "underwriting"
            ),
            "ui": self._load_module(
                workspace / "underwriter-ui/src/view.py", "ui"
            ),
        }

    @staticmethod
    def _passed(action, expected_exception: type[BaseException] | None = None) -> bool:
        try:
            result = action()
        except Exception as error:  # the scenario result, not an exception name, is evidence
            return expected_exception is not None and isinstance(error, expected_exception)
        return expected_exception is None and result is not False

    @staticmethod
    def _review_arguments(
        module,
        proposal: dict[str, object],
        *,
        evidence_tenant: str = "TENANT-A",
    ) -> dict[str, object]:
        now = datetime(2026, 2, 1, tzinfo=timezone.utc)
        proposal_digest = hashlib.sha256(
            json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return {
            "contract_revision": 2,
            "submission_id": "submission:DOC-1",
            "authorized_tenant": "TENANT-A",
            "evidence_tenants": {"evidence:DOC-1": evidence_tenant},
            "approval_receipt": {
                "receipt_id": "approval:DOC-1",
                "tenant_id": "TENANT-A",
                "reviewer_id": "reviewer-17",
                "reviewer_roles": [module.AUTHORIZED_REVIEW_ROLE],
                "proposal_digest": proposal_digest,
                "expires_at": now + timedelta(minutes=5),
            },
            "now": now,
        }

    @staticmethod
    def _v2_proposal(ai_module, status: str = "SUPPORTED", tenant: str = "TENANT-A"):
        return ai_module.propose(
            "DOC-1",
            ["REQ-45"],
            ["evidence:DOC-1"],
            status,
            tenant_id=tenant,
            model_confidence=0.99,
        )

    def _compatibility_matrix(self, workspace: Path) -> dict[str, bool]:
        modules = self._modules(workspace)
        v1_proposal = modules["ai_v1"].propose("DOC-1", 0.99)
        v2_proposal = self._v2_proposal(modules["ai_v2"])

        def review_v2_consumes(proposal, revision: int) -> bool:
            arguments = self._review_arguments(modules["review_v2"], proposal)
            arguments.update(
                {
                    "contract_revision": revision,
                    "submission_id": f"compat:{revision}",
                }
            )
            result = modules["review_v2"].ReviewEngine().process(proposal, **arguments)
            return result["status"] == "PROPOSAL_ACCEPTED"

        return {
            "ai-v1/review-v1": self._passed(
                lambda: modules["review_v1"].consume(v1_proposal, 1) == "ACCEPTED"
            ),
            "ai-v1/review-v2": self._passed(lambda: review_v2_consumes(v1_proposal, 1)),
            "ai-v2/review-v1": self._passed(
                lambda: modules["review_v1"].consume(v2_proposal, 2) == "ACCEPTED"
            ),
            "ai-v2/review-v2": self._passed(lambda: review_v2_consumes(v2_proposal, 2)),
        }

    def _integration_scenarios(
        self,
        workspace: Path,
        compatibility: dict[str, bool],
    ) -> dict[str, bool]:
        modules = self._modules(workspace)
        ai = modules["ai_v2"]
        review = modules["review_v2"]

        def process(
            status: str,
            *,
            tenant: str = "TENANT-A",
            evidence_tenant: str = "TENANT-A",
            receipt_updates: dict[str, object] | None = None,
            **updates,
        ):
            proposal = self._v2_proposal(ai, status, tenant)
            arguments = self._review_arguments(
                review, proposal, evidence_tenant=evidence_tenant
            )
            if receipt_updates:
                arguments["approval_receipt"].update(receipt_updates)
            arguments.update(updates)
            return review.ReviewEngine().process(proposal, **arguments)

        def supported_document() -> bool:
            document = modules["document"].extract("DOC-1", "TENANT-A")
            proposal = ai.propose(
                document["document_id"],
                ["REQ-45"],
                [document["text_ref"]],
                "SUPPORTED",
                tenant_id=document["tenant_id"],
                model_confidence=0.97,
            )
            result = review.ReviewEngine().process(
                proposal,
                **{
                    **self._review_arguments(review, proposal),
                    "approval_receipt": None,
                },
            )
            return result["status"] == "PROPOSAL_ACCEPTED"

        def ambiguous_mapping() -> bool:
            proposal = self._v2_proposal(ai, "AMBIGUOUS")
            result = review.ReviewEngine().process(
                proposal, **self._review_arguments(review, proposal)
            )
            return (
                proposal["model_confidence"] == 0.99
                and result["review_required"] is True
                and result["status"] == "ROUTED_TO_REVIEW"
            )

        def duplicate_event() -> bool:
            proposal = self._v2_proposal(ai, "AMBIGUOUS")
            engine = review.ReviewEngine()
            arguments = self._review_arguments(review, proposal)
            first = engine.process(proposal, **arguments)
            second = engine.process(proposal, **arguments)
            return first["side_effect_count"] == 1 and second["side_effect_count"] == 0

        def missing_provenance_rejected() -> None:
            proposal = self._v2_proposal(ai, "AMBIGUOUS")
            proposal.pop("model_provenance")
            review.ReviewEngine().process(
                proposal, **self._review_arguments(review, proposal)
            )

        def stale_approval_rejected() -> None:
            now = datetime(2026, 2, 1, tzinfo=timezone.utc)
            process(
                "AMBIGUOUS",
                now=now,
                receipt_updates={"expires_at": now - timedelta(seconds=1)},
            )

        def unauthorized_reviewer_rejected() -> None:
            process("AMBIGUOUS", receipt_updates={"reviewer_roles": []})

        def single_authority() -> bool:
            result = process("AMBIGUOUS")
            blocked = modules["underwriting"].apply_review_decision(
                authorized=False, current=True
            )
            rendered = modules["ui"].label(self._v2_proposal(ai, "SUPPORTED"))
            return (
                result["authoritative_mutation_count"] == 0
                and blocked == "BLOCKED"
                and rendered != "Approved"
            )

        return {
            "supported_document": self._passed(supported_document),
            "unsupported_document": self._passed(
                lambda: process("UNSUPPORTED")["status"] == "ROUTED_TO_REVIEW"
            ),
            "ambiguous_mapping": self._passed(ambiguous_mapping),
            "duplicate_event": self._passed(duplicate_event),
            "missing_provenance": self._passed(
                missing_provenance_rejected, ValueError
            ),
            "cross_tenant_reference": self._passed(
                lambda: process("AMBIGUOUS", tenant="TENANT-B", evidence_tenant="TENANT-B"),
                PermissionError,
            ),
            "review_service_unavailable": self._passed(
                lambda: process("AMBIGUOUS", review_available=False), RuntimeError
            ),
            "old_producer_new_consumer": compatibility["ai-v1/review-v2"],
            "new_producer_old_consumer_blocked": not compatibility["ai-v2/review-v1"],
            "stale_approval": self._passed(stale_approval_rejected, PermissionError),
            "unauthorized_reviewer": self._passed(
                unauthorized_reviewer_rejected, PermissionError
            ),
            "single_authority": self._passed(single_authority),
        }

    def _requirement_evidence(self, scenarios: dict[str, bool]) -> dict[str, object]:
        mapping = json.loads(json.dumps(self.requirement_obligations))
        for evidence in mapping.values():
            evidence["passed"] = all(scenarios[test_id] for test_id in evidence["test_ids"])
        return mapping
