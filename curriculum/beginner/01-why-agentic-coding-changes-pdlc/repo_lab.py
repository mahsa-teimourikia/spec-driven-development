"""Course 01 Lab B: run a governed change against a realistic repository fixture.

The lab is deterministic and offline. It copies the fixture to a temporary
workspace, installs one candidate change there, runs its real unit tests, and
writes a JSON evidence bundle. It never mutates the source fixture.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from enum import Enum, IntEnum
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable, Mapping


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "northstar-underwriter"
REPOSITORY_ROOT = HERE.parents[2]
AS_OF = date(2026, 9, 10)
AS_OF_TIME = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
REFERENCE_RECEIPTS = FIXTURE / "approvals" / "training-receipts.json"


class Layer(IntEnum):
    ORGANIZATION = 0
    PLATFORM = 1
    DOMAIN = 2
    PROJECT = 3
    FEATURE = 4
    IMPLEMENTATION = 5


class Applicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNCERTAIN = "UNCERTAIN"


class Gate(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    STOP = "STOP"


@dataclass(frozen=True)
class Source:
    repository: str = ""
    path: str = ""
    version: str = ""
    commit: str = ""


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    layer: Layer
    control: str
    expected_value: str
    statement: str
    owner: str
    status: str
    effective_from: str
    mandatory: bool
    scope: Mapping[str, list[str]]
    applies_when: Mapping[str, list[str]]
    exceptions: Mapping[str, object]
    source: Source

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "Requirement":
        return cls(
            requirement_id=str(payload["id"]),
            layer=Layer[str(payload["layer"]).upper()],
            control=str(payload["control"]),
            expected_value=str(payload["expected_value"]),
            statement=str(payload["statement"]),
            owner=str(payload.get("owner", "")),
            status=str(payload.get("status", "")),
            effective_from=str(payload.get("effective_from", "")),
            mandatory=bool(payload.get("mandatory", True)),
            scope=dict(payload.get("scope", {})),
            applies_when=dict(payload.get("applies_when", {})),
            exceptions=dict(payload.get("exceptions", {})),
            source=Source(**dict(payload.get("source", {}))),
        )


@dataclass(frozen=True)
class ApplicabilityDecision:
    requirement_id: str
    outcome: Applicability
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EffectiveControl:
    control: str
    expected_value: str
    authority_layer: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class ContextAssembly:
    requirements: tuple[Requirement, ...]
    decisions: tuple[ApplicabilityDecision, ...]
    controls: tuple[EffectiveControl, ...]
    conflicts: tuple[Mapping[str, str], ...]

    @property
    def uncertain(self) -> tuple[ApplicabilityDecision, ...]:
        return tuple(item for item in self.decisions if item.outcome is Applicability.UNCERTAIN)

    @property
    def applicable_ids(self) -> tuple[str, ...]:
        return tuple(
            item.requirement_id
            for item in self.decisions
            if item.outcome is Applicability.APPLICABLE
        )


def load_change_context(root: Path = FIXTURE) -> dict[str, object]:
    return json.loads((root / "ticket" / "change-context.json").read_text(encoding="utf-8"))


def load_requirements(root: Path = FIXTURE) -> tuple[Requirement, ...]:
    requirements: list[Requirement] = []
    for path in sorted((root / "context").glob("**/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for item in payload:
            requirements.append(Requirement.from_dict(item))
    return tuple(requirements)


def load_experiment_requirement(name: str, root: Path = FIXTURE) -> Requirement:
    payload = json.loads((root / "experiments" / name).read_text(encoding="utf-8"))
    return Requirement.from_dict(payload)


def decide_applicability(
    requirement: Requirement,
    change_context: Mapping[str, object],
) -> ApplicabilityDecision:
    reasons: list[str] = []
    missing_provenance = [
        name
        for name, value in (
            ("owner", requirement.owner),
            ("source.repository", requirement.source.repository),
            ("source.path", requirement.source.path),
            ("source.version", requirement.source.version),
            ("source.commit", requirement.source.commit),
        )
        if not value
    ]
    if missing_provenance:
        return ApplicabilityDecision(
            requirement.requirement_id,
            Applicability.UNCERTAIN,
            (f"missing provenance: {', '.join(missing_provenance)}",),
        )
    if requirement.status != "active":
        return ApplicabilityDecision(
            requirement.requirement_id,
            Applicability.NOT_APPLICABLE,
            (f"status is {requirement.status!r}",),
        )
    try:
        effective = date.fromisoformat(requirement.effective_from)
    except ValueError:
        return ApplicabilityDecision(
            requirement.requirement_id,
            Applicability.UNCERTAIN,
            ("effective_from is missing or invalid",),
        )
    if effective > AS_OF:
        return ApplicabilityDecision(
            requirement.requirement_id,
            Applicability.NOT_APPLICABLE,
            (f"not effective until {requirement.effective_from}",),
        )

    rules: dict[str, list[str]] = {}
    environments = requirement.scope.get("environments", [])
    if environments:
        rules["environment"] = environments
    rules.update(requirement.applies_when)
    for field, allowed in rules.items():
        if field not in change_context:
            reasons.append(f"missing change-context field: {field}")
            continue
        actual = str(change_context[field])
        if actual not in allowed:
            return ApplicabilityDecision(
                requirement.requirement_id,
                Applicability.NOT_APPLICABLE,
                (f"{field}={actual!r} is outside {allowed!r}",),
            )
        reasons.append(f"{field}={actual!r} matches")
    if any(reason.startswith("missing") for reason in reasons):
        return ApplicabilityDecision(
            requirement.requirement_id,
            Applicability.UNCERTAIN,
            tuple(reasons),
        )
    return ApplicabilityDecision(
        requirement.requirement_id,
        Applicability.APPLICABLE,
        tuple(reasons or ("unconditional active requirement",)),
    )


def assemble_context(
    requirements: Iterable[Requirement],
    change_context: Mapping[str, object],
) -> ContextAssembly:
    ordered = tuple(sorted(requirements, key=lambda item: (item.layer, item.requirement_id)))
    decisions = tuple(decide_applicability(item, change_context) for item in ordered)
    outcomes = {item.requirement_id: item.outcome for item in decisions}
    controls: dict[str, EffectiveControl] = {}
    conflicts: list[Mapping[str, str]] = []
    for requirement in ordered:
        if outcomes[requirement.requirement_id] is not Applicability.APPLICABLE:
            continue
        current = controls.get(requirement.control)
        if current is None:
            controls[requirement.control] = EffectiveControl(
                requirement.control,
                requirement.expected_value,
                requirement.layer.name.lower(),
                (requirement.requirement_id,),
            )
        elif current.expected_value == requirement.expected_value:
            controls[requirement.control] = EffectiveControl(
                current.control,
                current.expected_value,
                current.authority_layer,
                current.source_ids + (requirement.requirement_id,),
            )
        else:
            conflicts.append(
                {
                    "control": requirement.control,
                    "winner": current.source_ids[0],
                    "winning_value": current.expected_value,
                    "rejected": requirement.requirement_id,
                    "rejected_value": requirement.expected_value,
                }
            )
    return ContextAssembly(ordered, decisions, tuple(controls.values()), tuple(conflicts))


def load_candidate(name: str, root: Path = FIXTURE) -> dict[str, object]:
    path = root / "changes" / name / "change.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def candidate_digest(
    candidate: Mapping[str, object], root: Path = FIXTURE
) -> str:
    artifact_digests: dict[str, str] = {}
    candidate_name = str(candidate.get("candidate", ""))
    roots = [
        root / "changes" / candidate_name / "src",
        root / "changes" / candidate_name / "tests",
    ]
    change_spec_path = str(candidate.get("change_spec_path", ""))
    if change_spec_path:
        roots.append(root / change_spec_path)
    for artifact_root in roots:
        if not artifact_root.exists():
            continue
        for path in sorted(
            item
            for item in artifact_root.rglob("*")
            if item.is_file()
            and "__pycache__" not in item.parts
            and item.suffix not in {".pyc", ".pyo"}
            and item.name != ".DS_Store"
        ):
            artifact_digests[str(path.relative_to(root))] = (
                "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            )
    return _canonical_digest({"manifest": candidate, "artifacts": artifact_digests})


def policy_snapshot_digest(assembly: ContextAssembly) -> str:
    snapshot = [
        {
            "id": item.requirement_id,
            "value": item.expected_value,
            "source_commit": item.source.commit,
        }
        for item in assembly.requirements
        if item.requirement_id in assembly.applicable_ids
    ]
    return _canonical_digest(snapshot)


def evaluate_change_package(
    candidate: Mapping[str, object], root: Path = FIXTURE
) -> dict[str, object]:
    relative = str(candidate.get("change_spec_path", ""))
    required_files = (
        "proposal.md",
        "clarifications.md",
        "applicability.md",
        "conflict-record.md",
        "requirements.md",
        "design.md",
        "tasks.md",
        "traceability.csv",
    )
    findings: list[str] = []
    if not relative:
        findings.append("candidate declares no durable change package")
        return {"passed": False, "path": None, "findings": findings}
    package = root / relative
    for filename in required_files:
        path = package / filename
        if not path.exists():
            findings.append(f"missing change artifact: {filename}")
        elif "TODO" in path.read_text(encoding="utf-8"):
            findings.append(f"unresolved TODO in change artifact: {filename}")
    requirements_text = (
        (package / "requirements.md").read_text(encoding="utf-8")
        if (package / "requirements.md").exists()
        else ""
    )
    for requirement_id in ("REQ-QA-001", "REQ-QA-002", "REQ-QA-003"):
        if requirement_id not in requirements_text:
            findings.append(f"missing behavior requirement: {requirement_id}")
    return {"passed": not findings, "path": relative, "findings": findings}


def _run_python_check(
    command: list[str], *, cwd: Path, environment: Mapping[str, str]
) -> dict[str, object]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=dict(environment),
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "command": " ".join(command),
        "output": (result.stdout + result.stderr).strip(),
    }


def run_candidate_tests(name: str, root: Path = FIXTURE) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="northstar-course01-") as temporary:
        workspace = Path(temporary) / "northstar-underwriter"
        shutil.copytree(root, workspace)
        candidate_source = root / "changes" / name / "src"
        shutil.copytree(candidate_source, workspace / "src", dirs_exist_ok=True)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(workspace / "src")
        candidate_checks = _run_python_check(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=workspace / "changes" / name,
            environment=environment,
        )
        independent_checks = _run_python_check(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=workspace,
            environment=environment,
        )
        evaluation_process = subprocess.run(
            [sys.executable, "evals/run_evals.py"],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            evaluation = json.loads(evaluation_process.stdout)
        except json.JSONDecodeError:
            evaluation = {
                "population": "evaluation runner failed",
                "total_cases": 0,
                "passed_cases": 0,
                "conformance_rate": 0.0,
                "safety_violations": 0,
                "cases": [],
                "limitations": [evaluation_process.stderr.strip() or "invalid evaluator output"],
            }
        evaluation["passed"] = bool(
            evaluation.get("total_cases")
            and evaluation.get("passed_cases") == evaluation.get("total_cases")
            and evaluation.get("safety_violations") == 0
        )
    return {
        "passed": independent_checks["passed"] and evaluation["passed"],
        "candidate_checks": candidate_checks,
        "independent_checks": independent_checks,
        "evaluation": evaluation,
    }


def evaluate_decisions(
    assembly: ContextAssembly,
    candidate: Mapping[str, object],
) -> dict[str, object]:
    proposed = dict(candidate.get("decisions", {}))
    expected = {item.control: item.expected_value for item in assembly.controls}
    missing = sorted(set(expected) - set(proposed))
    violations = [
        {"control": control, "expected": expected[control], "proposed": proposed[control]}
        for control in sorted(set(expected) & set(proposed))
        if expected[control] != proposed[control]
    ]
    unknown = sorted(set(proposed) - set(expected))
    return {
        "passed": not missing and not violations and not unknown,
        "missing_controls": missing,
        "violations": violations,
        "unauthorized_decisions": unknown,
    }


def evaluate_policy(name: str, candidate: Mapping[str, object], root: Path = FIXTURE) -> dict[str, object]:
    findings: list[str] = []
    allowed_repositories = {"northstar-underwriter"}
    allowed_permissions = {"read_source", "write_feature_branch", "run_tests"}
    unexpected_repositories = sorted(set(candidate["target_repositories"]) - allowed_repositories)
    unexpected_permissions = sorted(set(candidate["requested_permissions"]) - allowed_permissions)
    if unexpected_repositories:
        findings.append(f"repositories outside scope: {', '.join(unexpected_repositories)}")
    if unexpected_permissions:
        findings.append(f"permissions outside scope: {', '.join(unexpected_permissions)}")
    if int(candidate["estimated_files_changed"]) > 20:
        findings.append(f"file budget exceeded: {candidate['estimated_files_changed']} > 20")
    if candidate["dependencies"]:
        findings.append(f"unapproved dependencies: {', '.join(candidate['dependencies'])}")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "changes" / name / "src").glob("**/*.py")
    )
    if "EXAMPLE_CREDENTIAL_DO_NOT_USE" in source_text:
        findings.append("credential-like literal detected by training scanner")
    return {
        "passed": not findings,
        "findings": findings,
        "boundary": {
            "allowed_repositories": sorted(allowed_repositories),
            "allowed_permissions": sorted(allowed_permissions),
            "max_files_changed": 20,
        },
    }


def evaluate_architecture(candidate: Mapping[str, object]) -> dict[str, object]:
    findings: list[str] = []
    decisions = dict(candidate.get("decisions", {}))
    if "ADR-013" not in candidate.get("acknowledged_adrs", []):
        findings.append("ADR-013 model-gateway decision was not acknowledged")
    if decisions.get("model_access") != "approved_ai_gateway":
        findings.append("model access bypasses the approved AI gateway")
    if decisions.get("public_response_contract") != "answer_citations_status":
        findings.append("candidate changes the public response contract")
    if decisions.get("infrastructure_delivery") != "terraform":
        findings.append("infrastructure delivery is not Terraform")
    return {"passed": not findings, "findings": findings}


def evaluate_traceability(
    assembly: ContextAssembly,
    candidate: Mapping[str, object],
    root: Path = FIXTURE,
) -> dict[str, object]:
    relative = str(candidate.get("traceability_path", ""))
    required = set(assembly.applicable_ids)
    if not relative or not (root / relative).exists():
        return {
            "passed": False,
            "path": relative or None,
            "stage_coverage": {
                "design": 0.0,
                "tasks": 0.0,
                "code": 0.0,
                "tests": 0.0,
                "runtime": 0.0,
            },
            "missing_requirement_ids": sorted(required),
            "unknown_requirement_ids": [],
            "broken_references": [],
            "rows": [],
        }

    with (root / relative).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {row["requirement_id"]: row for row in rows}
    linked = set(by_id)
    missing = sorted(required - linked)
    unknown = sorted(linked - required)
    broken: list[str] = []

    def present(reference: str) -> bool:
        return bool(reference.strip()) and not reference.startswith("TODO")

    def validate_reference(requirement_id: str, stage: str, reference: str) -> None:
        if not present(reference):
            broken.append(f"{requirement_id}:{stage}:empty")
            return
        if reference.startswith(("GATE:", "N/A:", "PENDING:")):
            return
        path_part = reference.split("#", maxsplit=1)[0]
        if not (root / path_part).exists():
            broken.append(f"{requirement_id}:{stage}:{reference}")

    applicable_rows = [by_id[item] for item in sorted(required & linked)]
    stage_columns = {
        "design": "design_ref",
        "tasks": "task_ref",
        "code": "code_ref",
        "tests": "test_ref",
    }
    for row in applicable_rows:
        for stage, column in stage_columns.items():
            validate_reference(row["requirement_id"], stage, row.get(column, ""))
    denominator = len(required) or 1
    coverage = {
        stage: round(
            sum(
                present(row.get(column, ""))
                and not row.get(column, "").startswith("N/A:")
                for row in applicable_rows
            )
            / denominator,
            3,
        )
        for stage, column in stage_columns.items()
    }
    runtime_required = [
        row for row in applicable_rows if row.get("runtime_required", "").lower() == "yes"
    ]
    runtime_verified = [
        row
        for row in runtime_required
        if present(row.get("runtime_evidence", ""))
        and not row["runtime_evidence"].startswith("PENDING:")
    ]
    coverage["runtime"] = round(
        len(runtime_verified) / len(runtime_required), 3
    ) if runtime_required else 1.0
    return {
        "passed": not missing
        and not unknown
        and not broken
        and all(
            present(row.get(column, ""))
            for row in applicable_rows
            for column in stage_columns.values()
        ),
        "path": relative,
        "stage_coverage": coverage,
        "missing_requirement_ids": missing,
        "unknown_requirement_ids": unknown,
        "broken_references": broken,
        "rows": rows,
    }


def independent_review(name: str, root: Path = FIXTURE) -> dict[str, object]:
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "changes" / name / "src").glob("**/*.py")
    )
    findings: list[str] = []
    if "public_model_api" in source_text:
        findings.append("direct public-model route appears in implementation")
    if "best guess" in source_text.lower():
        findings.append("implementation generates an answer without supporting evidence")
    return {
        "passed": not findings,
        "findings": findings,
        "unverified_risks": [
            "tenant isolation needs integration evidence against the real retrieval service",
            "data residency needs deployment and gateway-log evidence",
            "answer quality needs a representative domain evaluation set",
        ],
    }


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def evaluate_approvals(
    candidate: Mapping[str, object],
    assembly: ContextAssembly,
    receipt_path: Path | None,
) -> dict[str, object]:
    required_roles = {str(item["role"]) for item in candidate.get("required_approvals", [])}
    expected_candidate_digest = candidate_digest(candidate)
    expected_policy_digest = policy_snapshot_digest(assembly)
    receipts: list[dict[str, object]] = []
    findings: list[str] = []
    if receipt_path is not None:
        try:
            receipts = [dict(item) for item in json.loads(receipt_path.read_text(encoding="utf-8"))]
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            findings.append(f"approval receipt file is invalid: {exc}")

    valid_roles: set[str] = set()
    receipt_ids: set[str] = set()
    verification: list[dict[str, object]] = []
    for receipt in receipts:
        receipt_findings: list[str] = []
        receipt_id = str(receipt.get("receipt_id", ""))
        role = str(receipt.get("role", ""))
        if not receipt_id or receipt_id in receipt_ids:
            receipt_findings.append("receipt ID is empty or duplicated")
        receipt_ids.add(receipt_id)
        if role not in required_roles:
            receipt_findings.append("role is not required for this proposal")
        if receipt.get("candidate") != candidate.get("candidate"):
            receipt_findings.append("candidate binding does not match")
        if receipt.get("proposal_digest") != expected_candidate_digest:
            receipt_findings.append("proposal digest does not match")
        if receipt.get("policy_snapshot_digest") != expected_policy_digest:
            receipt_findings.append("policy snapshot digest does not match")
        if receipt.get("issuer") != "course-fixture-approval-service":
            receipt_findings.append("issuer is not the configured training trust source")
        if receipt.get("state") != "available":
            receipt_findings.append("receipt is not available for single use")
        if not receipt.get("approver_id"):
            receipt_findings.append("approver identity is missing")
        try:
            issued_at = _parse_timestamp(str(receipt.get("issued_at", "")))
            expires_at = _parse_timestamp(str(receipt.get("expires_at", "")))
            if not issued_at <= AS_OF_TIME < expires_at:
                receipt_findings.append("receipt is not valid at the evaluation time")
        except ValueError as exc:
            receipt_findings.append(f"invalid receipt time: {exc}")
        if not receipt_findings:
            valid_roles.add(role)
        verification.append(
            {
                "receipt_id": receipt_id,
                "role": role,
                "valid": not receipt_findings,
                "findings": receipt_findings,
            }
        )
    pending = sorted(required_roles - valid_roles)
    findings.extend(f"missing valid receipt for role: {role}" for role in pending)
    return {
        "passed": not findings,
        "pending_roles": pending,
        "findings": findings,
        "verification": verification,
        "bindings": {
            "proposal_digest": expected_candidate_digest,
            "policy_snapshot_digest": expected_policy_digest,
            "evaluation_time": AS_OF_TIME.isoformat(),
        },
        "limitations": [
            "training receipts are loaded from a configured fixture, not a real identity system",
            "the lab verifies single-use state but does not atomically consume it",
            "production requires authenticated approvers, durable state, signature verification, and replay protection",
        ],
    }


def format_gate_report(summary: Mapping[str, object]) -> str:
    checks = dict(summary["checks"])
    coverage = dict(summary["traceability_coverage"])
    evaluation = dict(summary["evaluation"])
    lines = [
        "NORTHSTAR SDD CHANGE REVIEW",
        "=" * 32,
        f"Candidate: {summary['candidate']}",
        "",
        "Requirements",
        f"  Applicable:      {summary['applicable_requirements']}",
        f"  Not applicable:  {summary['not_applicable_requirements']}",
        f"  Uncertain:       {summary['uncertain_requirements']}",
        f"  Conflicts:       {summary['conflicts']}",
        "",
        "Traceability",
        f"  Requirements -> Design:   {coverage['design']:.0%}",
        f"  Requirements -> Tasks:    {coverage['tasks']:.0%}",
        f"  Requirements -> Code:     {coverage['code']:.0%}",
        f"  Requirements -> Tests:    {coverage['tests']:.0%}",
        f"  Requirements -> Runtime:  {coverage['runtime']:.0%}",
        "",
        "Candidate and independent evidence",
    ]
    for name in (
        "candidate_tests",
        "independent_tests",
        "evaluation",
        "policy",
        "architecture",
        "independent_review",
        "approvals",
    ):
        lines.append(f"  {name.replace('_', ' ').title():24} {'PASS' if checks[name] else 'FAIL'}")
    lines.extend(
        (
            "",
            "Evaluation population",
            f"  Passed: {evaluation['passed_cases']} / {evaluation['total_cases']}",
            f"  Conformance: {evaluation['conformance_rate']:.0%}",
            f"  Safety violations: {evaluation['safety_violations']}",
            "",
            f"MERGE GATE: {summary['merge_gate']}",
            f"PRODUCTION RELEASE: {summary['production_release']}",
        )
    )
    if summary["production_blockers"]:
        lines.append("Production blockers:")
        lines.extend(f"  - {item}" for item in summary["production_blockers"])
    return "\n".join(lines) + "\n"


def run_candidate(
    name: str,
    output_root: Path,
    *,
    approval_receipts: Path | None = None,
    change_context: Mapping[str, object] | None = None,
    extra_requirements: Iterable[Requirement] = (),
    label: str | None = None,
) -> dict[str, object]:
    context = dict(change_context or load_change_context())
    requirements = load_requirements() + tuple(extra_requirements)
    assembly = assemble_context(requirements, context)
    candidate = load_candidate(name)
    decision_check = evaluate_decisions(assembly, candidate)
    change_package = evaluate_change_package(candidate)
    policy_check = evaluate_policy(name, candidate)
    architecture_check = evaluate_architecture(candidate)
    test_result = run_candidate_tests(name)
    traceability = evaluate_traceability(assembly, candidate)
    review = independent_review(name)
    approvals = evaluate_approvals(candidate, assembly, approval_receipts)

    stop = bool(
        assembly.uncertain
        or assembly.conflicts
        or not decision_check["passed"]
        or not change_package["passed"]
        or not policy_check["passed"]
        or not architecture_check["passed"]
        or not test_result["passed"]
        or not traceability["passed"]
        or not review["passed"]
    )
    gate = Gate.STOP if stop else Gate.REVIEW if not approvals["passed"] else Gate.PASS
    bundle_dir = output_root / (label or name)
    applicability_payload = {
        "change_context": context,
        "decisions": [
            {
                "requirement_id": item.requirement_id,
                "outcome": item.outcome.value,
                "reasons": item.reasons,
            }
            for item in assembly.decisions
        ],
        "conflicts": list(assembly.conflicts),
    }
    requirement_payload = [
        {
            **asdict(item),
            "layer": item.layer.name.lower(),
        }
        for item in assembly.requirements
    ]
    summary = {
        "candidate": name,
        "gate": gate.value,
        "merge_gate": gate.value,
        "production_release": "BLOCKED",
        "applicable_requirements": len(assembly.applicable_ids),
        "not_applicable_requirements": sum(
            item.outcome is Applicability.NOT_APPLICABLE for item in assembly.decisions
        ),
        "uncertain_requirements": len(assembly.uncertain),
        "conflicts": len(assembly.conflicts),
        "checks": {
            "specification": decision_check["passed"] and change_package["passed"],
            "policy": policy_check["passed"],
            "architecture": architecture_check["passed"],
            "candidate_tests": test_result["candidate_checks"]["passed"],
            "independent_tests": test_result["independent_checks"]["passed"],
            "evaluation": test_result["evaluation"]["passed"],
            "traceability": traceability["passed"],
            "independent_review": review["passed"],
            "approvals": approvals["passed"],
        },
        "traceability_coverage": traceability["stage_coverage"],
        "evaluation": {
            "total_cases": test_result["evaluation"]["total_cases"],
            "passed_cases": test_result["evaluation"]["passed_cases"],
            "conformance_rate": test_result["evaluation"]["conformance_rate"],
            "safety_violations": test_result["evaluation"]["safety_violations"],
        },
        "unverified_risks": review["unverified_risks"],
        "production_blockers": [
            "runtime traceability evidence is pending",
            *review["unverified_risks"],
        ],
    }
    for filename, payload in (
        ("requirements.json", requirement_payload),
        ("applicability.json", applicability_payload),
        (
            "specification-check.json",
            {"passed": decision_check["passed"] and change_package["passed"], "decisions": decision_check, "change_package": change_package},
        ),
        ("policy-check.json", policy_check),
        ("architecture-check.json", architecture_check),
        ("candidate-test-results.json", test_result["candidate_checks"]),
        ("independent-test-results.json", test_result["independent_checks"]),
        ("evaluation-results.json", test_result["evaluation"]),
        ("traceability.json", traceability),
        ("independent-review.json", review),
        ("approvals.json", approvals),
        ("release-summary.json", summary),
    ):
        _write_json(bundle_dir / filename, payload)
    (bundle_dir / "gate-report.txt").write_text(
        format_gate_report(summary), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=("unsafe", "governed", "all"), default="all")
    parser.add_argument(
        "--approval-receipts",
        type=Path,
        help="verify bound training approval receipts from this JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "build" / "course01-evidence",
        help="evidence-bundle directory",
    )
    parser.add_argument(
        "--inject-conflict",
        action="store_true",
        help="add the F-99 lower-level privacy-policy conflict",
    )
    args = parser.parse_args()
    extra = (
        (load_experiment_requirement("F-99-public-model-override.json"),)
        if args.inject_conflict
        else ()
    )
    runs: list[dict[str, object]] = []
    if args.candidate in ("unsafe", "governed"):
        runs.append(
            run_candidate(
                args.candidate,
                args.output,
                approval_receipts=args.approval_receipts,
                extra_requirements=extra,
            )
        )
    else:
        runs.extend(
            (
                run_candidate("unsafe", args.output, extra_requirements=extra),
                run_candidate("governed", args.output, extra_requirements=extra),
                run_candidate(
                    "governed",
                    args.output,
                    approval_receipts=REFERENCE_RECEIPTS,
                    extra_requirements=extra,
                    label="governed-approved",
                ),
            )
        )
    for run in runs:
        print(format_gate_report(run))


if __name__ == "__main__":
    main()
