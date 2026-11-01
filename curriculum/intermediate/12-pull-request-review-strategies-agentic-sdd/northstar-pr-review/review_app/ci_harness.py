"""Protected acceptance execution over an exact candidate commit."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from .git_harness import GitCandidate
from .review_engine import EvidenceRecord, PullRequestSubject, ReviewEngine

PROTECTED_TEST = """from src.classifier import route
assert route(ambiguous=True, confidence=0.98) == 'review'
assert route(ambiguous=False, confidence=0.98) == 'straight_through'
"""


class ProtectedAcceptanceRunner:
    """Clone the trusted Git bundle and execute an oracle unavailable to the contributor."""

    def run(self, candidate: GitCandidate, subject: PullRequestSubject, *, observed_at: datetime) -> EvidenceRecord:
        with tempfile.TemporaryDirectory(prefix="course22-protected-ci-") as tmp:
            bundle = Path(tmp) / "candidate.bundle"
            bundle.write_bytes(candidate.repository_bundle)
            checkout = Path(tmp) / "checkout"
            clone = subprocess.run(["git", "clone", "-q", str(bundle), str(checkout)], text=True, capture_output=True)
            checkout_result = subprocess.run(["git", "-C", str(checkout), "checkout", "-q", subject.head_commit], text=True, capture_output=True) if clone.returncode == 0 else clone
            actual_head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True, capture_output=True) if checkout_result.returncode == 0 else checkout_result
            execution = subprocess.run([sys.executable, "-c", PROTECTED_TEST], cwd=checkout, text=True, capture_output=True) if actual_head.returncode == 0 and actual_head.stdout.strip() == subject.head_commit else actual_head
            result = "PASS" if execution.returncode == 0 else "FAIL"
            transcript = f"{execution.returncode}|{execution.stdout}|{execution.stderr}"
            return EvidenceRecord(
                evidence_id="EVID-PR-001",
                producer="protected-acceptance-runner",
                repository=subject.repository,
                head_commit=subject.head_commit,
                specification_digest=subject.specification_digest,
                contract_digest=subject.contract_digest,
                check_name="protected-acceptance",
                result=result,
                result_digest=ReviewEngine.digest(transcript),
                execution_id=f"RUN-{subject.head_commit[:12]}",
                observed_at=observed_at,
                protected_test_digest="sha256:" + hashlib.sha256(PROTECTED_TEST.encode()).hexdigest(),
            )
