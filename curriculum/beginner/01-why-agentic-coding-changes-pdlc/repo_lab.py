"""Course 01 Lab B: run a governed change against a realistic repository fixture.

The lab is deterministic and offline. It copies the fixture to a temporary
workspace, installs one candidate change there, runs its real unit tests, and
writes a JSON evidence bundle. It never mutates the source fixture.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum, IntEnum
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


def run_candidate_tests(name: str, root: Path = FIXTURE) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="northstar-course01-") as temporary:
        workspace = Path(temporary) / "northstar-underwriter"
        shutil.copytree(root, workspace)
        candidate_source = root / "changes" / name / "src"
        shutil.copytree(candidate_source, workspace / "src", dirs_exist_ok=True)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(workspace / "src")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "command": "python3 -m unittest discover -s tests -v",
        "output": (result.stdout + result.stderr).strip(),
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
) -> dict[str, object]:
    evidence_map = dict(candidate.get("evidence_map", {}))
    required = set(assembly.applicable_ids)
    linked = set(evidence_map)
    missing = sorted(required - linked)
    unknown = sorted(linked - required)
    return {
        "passed": not missing and not unknown,
        "coverage": round(len(required & linked) / len(required), 3) if required else 1.0,
        "missing_requirement_ids": missing,
        "unknown_requirement_ids": unknown,
        "links": evidence_map,
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


def evaluate_approvals(candidate: Mapping[str, object], approve: bool) -> dict[str, object]:
    approvals = [dict(item) for item in candidate.get("required_approvals", [])]
    if approve:
        for item in approvals:
            item["status"] = "approved-for-training"
            item["attestation"] = "CLI --approve flag; not a production signature"
    pending = [item["role"] for item in approvals if item["status"] != "approved-for-training"]
    return {"passed": not pending, "pending_roles": pending, "approvals": approvals}


def run_candidate(
    name: str,
    output_root: Path,
    *,
    approve: bool = False,
    change_context: Mapping[str, object] | None = None,
    extra_requirements: Iterable[Requirement] = (),
    label: str | None = None,
) -> dict[str, object]:
    context = dict(change_context or load_change_context())
    requirements = load_requirements() + tuple(extra_requirements)
    assembly = assemble_context(requirements, context)
    candidate = load_candidate(name)
    decision_check = evaluate_decisions(assembly, candidate)
    policy_check = evaluate_policy(name, candidate)
    architecture_check = evaluate_architecture(candidate)
    test_result = run_candidate_tests(name)
    traceability = evaluate_traceability(assembly, candidate)
    review = independent_review(name)
    approvals = evaluate_approvals(candidate, approve)

    stop = bool(
        assembly.uncertain
        or assembly.conflicts
        or not decision_check["passed"]
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
        "applicable_requirements": len(assembly.applicable_ids),
        "not_applicable_requirements": sum(
            item.outcome is Applicability.NOT_APPLICABLE for item in assembly.decisions
        ),
        "uncertain_requirements": len(assembly.uncertain),
        "conflicts": len(assembly.conflicts),
        "checks": {
            "specification": decision_check["passed"],
            "policy": policy_check["passed"],
            "architecture": architecture_check["passed"],
            "tests": test_result["passed"],
            "traceability": traceability["passed"],
            "independent_review": review["passed"],
            "approvals": approvals["passed"],
        },
        "unverified_risks": review["unverified_risks"],
    }
    for filename, payload in (
        ("requirements.json", requirement_payload),
        ("applicability.json", applicability_payload),
        ("specification-check.json", decision_check),
        ("policy-check.json", policy_check),
        ("architecture-check.json", architecture_check),
        ("test-results.json", test_result),
        ("traceability.json", traceability),
        ("independent-review.json", review),
        ("approvals.json", approvals),
        ("release-summary.json", summary),
    ):
        _write_json(bundle_dir / filename, payload)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=("unsafe", "governed", "all"), default="all")
    parser.add_argument("--approve", action="store_true", help="add training-only approval attestations")
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
                approve=args.approve,
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
                    approve=True,
                    extra_requirements=extra,
                    label="governed-approved",
                ),
            )
        )
    print(json.dumps(runs, indent=2))


if __name__ == "__main__":
    main()
