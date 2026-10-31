"""Trusted evidence execution for exact component and system revisions."""

from __future__ import annotations

from typing import Mapping

from .control_plane import (
    EvidenceReceipt,
    SystemEvidenceReceipt,
    canonical_digest,
)
from .git_harness import TrustedGitService


class ExecutedEvidenceService:
    """Generate receipts from observed checks; callers cannot supply receipts."""

    def __init__(self, git_service: TrustedGitService):
        self.git_service = git_service

    def attest_candidate(
        self,
        *,
        producer_identity: str,
        work_unit_id: str,
        repository: str,
        base_commit: str,
        candidate_commit: str,
        contract_revision: int,
        contract_digest: str,
    ) -> EvidenceReceipt:
        observation = self.git_service.resolve(repository, base_commit, candidate_commit)
        checks = (
            "candidate-commit-exists",
            "approved-base-is-ancestor",
            "repository-tests-executed",
        )
        passed = (
            observation.candidate_exists
            and observation.base_is_ancestor
            and observation.tests_passed
        )
        return EvidenceReceipt(
            evidence_id=f"EVID-{work_unit_id}-{candidate_commit[:12]}",
            producer_identity=producer_identity,
            work_unit_id=work_unit_id,
            repository=repository,
            candidate_commit=candidate_commit,
            contract_revision=contract_revision,
            contract_digest=contract_digest,
            result_digest=observation.test_result_digest,
            checks=checks,
            passed=passed,
        )

    def attest_system(
        self,
        *,
        producer_identity: str,
        component_commits: Mapping[str, str],
    ) -> SystemEvidenceReceipt:
        observations = {
            repository: self.git_service.resolve_candidate(repository, candidate)
            for repository, candidate in component_commits.items()
        }
        results = dict(self.git_service.system_results)
        exact_subject = (
            len(observations) == len(component_commits)
            and all(
                observation.candidate_exists
                and observation.base_is_ancestor
                and observation.tests_passed
                for observation in observations.values()
            )
        )
        passed = exact_subject and bool(results) and all(results.values())
        result_digest = canonical_digest(
            {
                "component_commits": dict(component_commits),
                "results": results,
            }
        )
        return SystemEvidenceReceipt(
            evidence_id=f"SYSTEM-{result_digest.split(':', 1)[1][:16]}",
            producer_identity=producer_identity,
            component_commits=dict(component_commits),
            results=results,
            result_digest=result_digest,
            passed=passed,
        )
