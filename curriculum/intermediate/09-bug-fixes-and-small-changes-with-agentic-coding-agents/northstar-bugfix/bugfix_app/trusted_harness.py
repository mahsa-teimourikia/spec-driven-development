"""Trusted fixture runner: protected inputs, real Git diff, and independent execution."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from .api import risk_response
from .contracts import DiffEntry, RootCauseEvidence, TrustedEvaluationContext
from .workflow import build_evidence_receipt, observe_test, validate_repository_path


BASELINE_RISK_SOURCE = '''def validate_score(score):
    if type(score) is not int or not 0 <= score <= 100:
        raise ValueError("score must be an integer from 0 through 100")

def classify_risk(score):
    validate_score(score)
    if score > 80:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"
'''

FIXED_RISK_SOURCE = BASELINE_RISK_SOURCE.replace("score > 80", "score >= 80")
IDENTITY_API_SOURCE = "def normalize_score(score):\n    return score\n"
OFF_BY_ONE_API_SOURCE = "def normalize_score(score):\n    return score - 1\n"


def _run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if ".git" not in path.parts and path.is_file():
            path.unlink()
    for relative, content in files.items():
        if validate_repository_path(relative) is None:
            raise ValueError(f"unsafe repository fixture path: {relative}")
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def _load_callable(source: str, name: str):
    namespace: dict[str, object] = {
        "__builtins__": {"type": type, "int": int, "ValueError": ValueError}
    }
    exec(compile(source, f"<trusted-fixture:{name}>", "exec"), namespace)
    return namespace[name]


class TrustedBugfixHarness:
    """Run curated lesson fixtures outside candidate declarations.

    A production evaluator must execute untrusted candidate code in an isolated
    sandbox. This compact harness deliberately supports only the lesson's pure
    classifier and normalizer fixtures.
    """

    def __init__(self, root: Path):
        self.root = root
        self.bug_contract = json.loads((root / "specs/BUG-2415/bug-contract.json").read_text(encoding="utf-8"))
        self.acceptance_contract = json.loads((root / "specs/BUG-2415/acceptance-contract.json").read_text(encoding="utf-8"))
        self.work_unit = json.loads((root / "specs/BUG-2415/work-unit.json").read_text(encoding="utf-8"))
        self.baseline_files = MappingProxyType({
            "app/risk_engine.py": BASELINE_RISK_SOURCE,
            "app/api.py": IDENTITY_API_SOURCE,
            "app/authorization.py": "REVIEW_REQUIRED = True\n",
            "database/migrations/schema.sql": "-- protected schema\n",
            "specs/BUG-2415/acceptance-contract.json": json.dumps(self.acceptance_contract, indent=2) + "\n",
        })

    def observe(self, candidate: dict[str, object]) -> TrustedEvaluationContext:
        candidate_files = dict(candidate["files"])
        actual_diff, baseline_commit, candidate_commit = self._git_observation(candidate_files, candidate["purpose_declarations"])

        baseline_classifier = _load_callable(self.baseline_files["app/risk_engine.py"], "classify_risk")
        candidate_classifier = _load_callable(candidate_files["app/risk_engine.py"], "classify_risk")
        baseline_normalizer = _load_callable(self.baseline_files["app/api.py"], "normalize_score")
        candidate_normalizer = _load_callable(candidate_files["app/api.py"], "normalize_score")

        before = observe_test(
            test_id="REG-RISK-80",
            revision=baseline_commit,
            classifier=baseline_classifier,
            score=80,
            expected="HIGH",
        )
        after = observe_test(
            test_id="REG-RISK-80",
            revision=candidate_commit,
            classifier=candidate_classifier,
            score=80,
            expected="HIGH",
        )
        boundaries = {score: candidate_classifier(score) for score in (0, 49, 50, 79, 80, 81, 100)}

        unit_status = "UNIT_CAUSE_CONFIRMED" if before.actual == "MEDIUM" and after.actual == "HIGH" else "UNRESOLVED"
        unit_cause = RootCauseEvidence(
            "HYP-OPERATOR",
            "EXP-DIRECT-BOUNDARY",
            "baseline=MEDIUM,candidate=HIGH",
            f"baseline={before.actual},candidate={after.actual}",
            unit_status,
        )
        baseline_response = risk_response("SUB-2415", 80, classifier=baseline_classifier, normalizer=baseline_normalizer)
        candidate_response = risk_response("SUB-2415", 80, classifier=candidate_classifier, normalizer=candidate_normalizer)
        production_status = (
            "PRODUCTION_PATH_CAUSE_CONFIRMED"
            if baseline_response["risk_category"] == "MEDIUM"
            and candidate_response["risk_category"] == "HIGH"
            and candidate_response["normalized_score"] == 80
            else "UNRESOLVED"
        )
        production_cause = RootCauseEvidence(
            "HYP-OPERATOR",
            "EXP-PRODUCTION-PATH",
            "baseline=MEDIUM,candidate=HIGH,normalized=80",
            f"baseline={baseline_response['risk_category']},candidate={candidate_response['risk_category']},normalized={candidate_response['normalized_score']}",
            production_status,
        )

        receipt = build_evidence_receipt(
            bug_id="BUG-2415",
            baseline_revision=baseline_commit,
            candidate_revision=candidate_commit,
            acceptance_contract=self.acceptance_contract,
            before=before,
            after=after,
        )
        registry = MappingProxyType({
            "CI-RUN-BUG-2415": receipt,
            "CI-RUN-OLD-CANDIDATE": replace(receipt, candidate_revision="candidate:old-fix", after=replace(after, revision="candidate:old-fix")),
            "CI-RUN-STALE-ORACLE": replace(receipt, acceptance_digest="sha256:stale"),
        })
        candidate_contract = json.loads(candidate_files["specs/BUG-2415/acceptance-contract.json"])
        return TrustedEvaluationContext(
            bug_contract=MappingProxyType(self.bug_contract),
            acceptance_contract=MappingProxyType(self.acceptance_contract),
            candidate_acceptance_contract=MappingProxyType(candidate_contract),
            work_unit=MappingProxyType(self.work_unit),
            baseline_commit=baseline_commit,
            candidate_commit=candidate_commit,
            actual_diff_entries=tuple(actual_diff),
            before_observation=before,
            after_observation=after,
            boundary_results=MappingProxyType(boundaries),
            unit_cause_evidence=unit_cause,
            production_cause_evidence=production_cause,
            evidence_registry=registry,
        )

    def _git_observation(self, candidate_files: dict[str, str], purposes: dict[str, str]) -> tuple[list[DiffEntry], str, str]:
        with tempfile.TemporaryDirectory(prefix="course19-git-") as temporary:
            repository = Path(temporary)
            _run(["git", "init", "-q"], cwd=repository)
            _run(["git", "config", "user.name", "Northstar CI"], cwd=repository)
            _run(["git", "config", "user.email", "ci@northstar.example"], cwd=repository)
            fixed_env = os.environ.copy()
            fixed_env.update({
                "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
                "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
            })
            _write_tree(repository, dict(self.baseline_files))
            _run(["git", "add", "-A"], cwd=repository)
            _run(["git", "commit", "-q", "-m", "approved baseline"], cwd=repository, env=fixed_env)
            baseline_commit = _run(["git", "rev-parse", "HEAD"], cwd=repository)
            _write_tree(repository, candidate_files)
            _run(["git", "add", "-A"], cwd=repository)
            _run(["git", "commit", "-q", "--allow-empty", "-m", "candidate patch"], cwd=repository, env=fixed_env)
            candidate_commit = _run(["git", "rev-parse", "HEAD"], cwd=repository)
            output = _run(["git", "diff", "--name-status", "-M", baseline_commit, candidate_commit], cwd=repository)

        entries: list[DiffEntry] = []
        for line in output.splitlines():
            fields = line.split("\t")
            status = fields[0][0]
            if status == "R":
                old_path, new_path = fields[1], fields[2]
            else:
                old_path = None if status == "A" else fields[1]
                new_path = fields[1]
            entries.append(DiffEntry(status, old_path, new_path, purposes.get(new_path, "undeclared")))
        return entries, baseline_commit, candidate_commit
