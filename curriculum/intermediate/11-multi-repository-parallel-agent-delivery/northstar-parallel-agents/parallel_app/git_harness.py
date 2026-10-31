"""Create real temporary Git repositories for Course 21 evidence subjects."""

from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Mapping

from .control_plane import PathChange, RevisionObservation
from .system_harness import execute_repository_system_scenarios


REPOSITORIES = (
    "document-service",
    "ai-service",
    "review-service",
    "underwriting-api",
    "underwriter-ui",
)


RepositoryRevision = RevisionObservation


class ObservedRepositorySet(dict[str, RepositoryRevision]):
    """Exact repository observations plus system results executed before cleanup."""

    def __init__(
        self,
        revisions: Mapping[str, RepositoryRevision],
        *,
        system_results: Mapping[str, bool],
    ) -> None:
        super().__init__(revisions)
        self.system_results = dict(system_results)


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


def _succeeds(command: list[str], *, cwd: Path) -> bool:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    ).returncode == 0


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
    ) -> ObservedRepositorySet:
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
            system_results = execute_repository_system_scenarios(workspace)
        return ObservedRepositorySet(revisions, system_results=system_results)

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
            ["git", "diff", "--name-status", "-M", baseline_commit, candidate_commit],
            cwd=root,
        )
        changes: list[PathChange] = []
        for line in changed.splitlines():
            fields = line.split("\t")
            status = fields[0]
            source_path: str | None = None
            if status.startswith("R"):
                source_path, path = fields[1], fields[2]
            else:
                path = fields[1]
            object_type = "deleted" if status == "D" else self._object_type(root, candidate_commit, path)
            changes.append(
                PathChange(
                    status=status,
                    path=path,
                    source_path=source_path,
                    object_type=object_type,
                )
            )
        test_payload = {
            "returncode": test.returncode,
            "stdout": test.stdout,
            "stderr": test.stderr,
        }
        return RepositoryRevision(
            repository=repository,
            baseline_commit=baseline_commit,
            candidate_commit=candidate_commit,
            changes=tuple(changes),
            candidate_exists=_succeeds(
                ["git", "cat-file", "-e", f"{candidate_commit}^{{commit}}"],
                cwd=root,
            ),
            base_is_ancestor=_succeeds(
                ["git", "merge-base", "--is-ancestor", baseline_commit, candidate_commit],
                cwd=root,
            ),
            tests_passed=test.returncode == 0,
            test_result_digest="sha256:"
            + hashlib.sha256(
                json.dumps(test_payload, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        )

    @staticmethod
    def _object_type(root: Path, candidate_commit: str, path: str) -> str:
        entry = _run(["git", "ls-tree", candidate_commit, "--", path], cwd=root)
        if not entry:
            return "unknown"
        mode = entry.split(maxsplit=1)[0]
        return {
            "120000": "symlink",
            "160000": "submodule",
        }.get(mode, "blob")

    @staticmethod
    def _component_source(repository: str, payload: Mapping[str, object]) -> str:
        common = (
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
        if repository == "document-service":
            return common + (
                "\ndef extract_document(document_id, tenant_id):\n"
                "    if not document_id or not tenant_id:\n"
                "        raise ValueError('DOCUMENT_IDENTITY_REQUIRED')\n"
                "    return {'document_id': document_id, 'tenant_id': tenant_id, "
                "'evidence_ref': f'evidence:{document_id}'}\n"
            )
        if repository == "ai-service":
            return common + (
                "\ndef propose_classification(document, *, ambiguity_status, model_confidence):\n"
                "    if ambiguity_status not in {'SUPPORTED', 'AMBIGUOUS', 'UNSUPPORTED'}:\n"
                "        raise ValueError('AMBIGUITY_STATUS_INVALID')\n"
                "    if not 0.0 <= model_confidence <= 1.0:\n"
                "        raise ValueError('MODEL_CONFIDENCE_INVALID')\n"
                "    return {\n"
                "        'proposal_id': f\"proposal:{document['tenant_id']}:{document['document_id']}\",\n"
                "        'document_id': document['document_id'],\n"
                "        'tenant_id': document['tenant_id'],\n"
                "        'candidate_requirement_ids': ['REQ-7'],\n"
                "        'ambiguity_status': ambiguity_status,\n"
                "        'model_confidence': model_confidence,\n"
                "        'review_required': ambiguity_status in {'AMBIGUOUS', 'UNSUPPORTED'},\n"
                "        'evidence_refs': [document['evidence_ref']],\n"
                "        'model_provenance': {'model_id': 'northstar-classifier', 'model_revision': '2026-02'},\n"
                "        'authoritative': False,\n"
                "    }\n"
            )
        if repository == "review-service":
            return common + (
                "\nimport hashlib\nimport json\n\n"
                "def _digest(value):\n"
                "    payload = json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()\n"
                "    return 'sha256:' + hashlib.sha256(payload).hexdigest()\n\n"
                "def issue_approval(proposal, *, receipt_id, tenant_id, expires_at):\n"
                "    return {'receipt_id': receipt_id, 'tenant_id': tenant_id, 'reviewer_id': 'reviewer-17', "
                "'reviewer_roles': ['AUTHORIZED_DOCUMENT_REVIEWER'], 'proposal_digest': _digest(proposal), "
                "'expires_at': expires_at}\n\n"
                "class ReviewService:\n"
                "    def __init__(self):\n"
                "        self.submissions = {}\n"
                "        self.consumed_approvals = set()\n"
                "        self.side_effect_count = 0\n\n"
                "    def process(self, proposal, *, submission_id, authorized_tenant, evidence_tenants, approval_receipt, now):\n"
                "        if proposal.get('tenant_id') != authorized_tenant:\n"
                "            raise PermissionError('CROSS_TENANT_PROPOSAL')\n"
                "        if any(evidence_tenants.get(ref) != authorized_tenant for ref in proposal.get('evidence_refs', [])):\n"
                "            raise PermissionError('CROSS_TENANT_EVIDENCE')\n"
                "        digest = _digest(proposal)\n"
                "        if submission_id in self.submissions:\n"
                "            previous_digest, previous = self.submissions[submission_id]\n"
                "            if previous_digest != digest:\n"
                "                raise ValueError('SUBMISSION_ID_REUSED_FOR_DIFFERENT_PROPOSAL')\n"
                "            return {**previous, 'duplicate': True, 'side_effect_count': 0}\n"
                "        if proposal.get('review_required'):\n"
                "            if not approval_receipt:\n"
                "                raise PermissionError('APPROVAL_REQUIRED')\n"
                "            if 'AUTHORIZED_DOCUMENT_REVIEWER' not in approval_receipt.get('reviewer_roles', []):\n"
                "                raise PermissionError('AUTHORIZED_REVIEWER_REQUIRED')\n"
                "            if approval_receipt.get('tenant_id') != authorized_tenant:\n"
                "                raise PermissionError('APPROVAL_TENANT_MISMATCH')\n"
                "            if approval_receipt.get('proposal_digest') != digest:\n"
                "                raise PermissionError('APPROVAL_SUBJECT_MISMATCH')\n"
                "            if approval_receipt.get('expires_at') <= now:\n"
                "                raise PermissionError('APPROVAL_EXPIRED')\n"
                "            receipt_id = approval_receipt.get('receipt_id')\n"
                "            if not receipt_id or receipt_id in self.consumed_approvals:\n"
                "                raise PermissionError('APPROVAL_REPLAYED')\n"
                "            self.consumed_approvals.add(receipt_id)\n"
                "        self.side_effect_count += 1\n"
                "        result = {'status': 'REVIEW_COMPLETED' if proposal.get('review_required') else 'PROPOSAL_ACCEPTED', "
                "'review_required': bool(proposal.get('review_required')), 'tenant_id': authorized_tenant, "
                "'authoritative_mutation_count': 0, 'side_effect_count': 1, 'duplicate': False}\n"
                "        self.submissions[submission_id] = (digest, result)\n"
                "        return dict(result)\n"
            )
        if repository == "underwriting-api":
            return common + (
                "\nclass UnderwritingAPI:\n"
                "    def __init__(self):\n"
                "        self.mutation_count = 0\n\n"
                "    def apply_review_result(self, result, *, authenticated_identity, authorized_tenant):\n"
                "        if authenticated_identity != 'review-service':\n"
                "            raise PermissionError('AUTHORITATIVE_WRITER_DENIED')\n"
                "        if result.get('tenant_id') != authorized_tenant:\n"
                "            raise PermissionError('AUTHORITATIVE_TENANT_MISMATCH')\n"
                "        if result.get('status') not in {'REVIEW_COMPLETED', 'PROPOSAL_ACCEPTED'}:\n"
                "            raise ValueError('REVIEW_RESULT_NOT_CURRENT')\n"
                "        self.mutation_count += 1\n"
                "        return 'APPLIED'\n"
            )
        if repository == "underwriter-ui":
            return common + (
                "\ndef render(proposal, authoritative_state):\n"
                "    return {'proposal_label': 'AI proposal — not authoritative', "
                "'authoritative_state': authoritative_state}\n"
            )
        return common

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


class TrustedGitService:
    """Resolve only observations independently derived from real Git history."""

    def __init__(self, revisions: Mapping[str, RepositoryRevision]):
        self._observations = {
            (revision.repository, revision.baseline_commit, revision.candidate_commit): revision
            for revision in revisions.values()
        }
        self.system_results = dict(getattr(revisions, "system_results", {}))

    def resolve(
        self,
        repository: str,
        base_commit: str,
        candidate_commit: str,
    ) -> RepositoryRevision:
        observation = self._observations.get((repository, base_commit, candidate_commit))
        if observation is None:
            raise ValueError("CANDIDATE_COMMIT_NOT_FOUND")
        return observation

    def resolve_candidate(
        self,
        repository: str,
        candidate_commit: str,
    ) -> RepositoryRevision:
        matches = [
            observation
            for (name, _, candidate), observation in self._observations.items()
            if name == repository and candidate == candidate_commit
        ]
        if len(matches) != 1:
            raise ValueError("CANDIDATE_COMMIT_NOT_FOUND")
        return matches[0]
