#!/usr/bin/env python3
"""Deterministic Course 14 lab: govern OpenSpec-style brownfield changes."""

from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent
VALID_OPERATIONS = {"ADDED", "MODIFIED", "REMOVED", "RENAMED"}
KNOWN_STATES = {
    "DRAFT",
    "CLARIFYING",
    "READY_FOR_REVIEW",
    "READY_FOR_OWNER_REVIEW",
    "APPROVED",
    "IMPLEMENTING",
    "VERIFYING",
    "READY_FOR_INTEGRATION",
    "ARCHIVED",
    "BLOCKED",
    "BLOCKED_PENDING_REBASE",
    "REJECTED",
    "SUPERSEDED",
    "WITHDRAWN",
}
CONSEQUENTIAL_STATES = {"APPROVED", "READY_FOR_INTEGRATION", "ARCHIVED"}
REGRESSION_EVIDENCE = {
    "manual_fallback_regression",
    "review_contract_test",
    "unauthorized_persistence_negative_test",
}
DELTA_EVIDENCE = {
    "classification_evaluation",
    "provenance_schema_test",
    "prompt_injection_test",
}
RECEIPT_OPERATION = "INTEGRATE_AND_ARCHIVE"
_RECEIPT_LOCK = threading.Lock()


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    severity: str
    subject: str
    message: str


def finding(code: str, subject: str, message: str, severity: str = "BLOCK") -> Finding:
    return Finding(code, severity, subject, message)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_baseline() -> dict[str, Any]:
    return read_json(ROOT / "baseline" / "baseline.json")


def load_context() -> dict[str, Any]:
    return read_json(ROOT / "enterprise" / "effective-context.json")


def load_authority_map() -> dict[str, Any]:
    return read_json(ROOT / "enterprise" / "authority-map.json")


def load_control_plane() -> dict[str, Any]:
    return read_json(ROOT / "enterprise" / "trusted-control-plane.json")


def load_snapshot() -> dict[str, Any]:
    return read_json(ROOT / "openspec-snapshot" / "manifest.json")


def load_reference() -> dict[str, Any]:
    return read_json(ROOT / "reference" / "change-portfolio.json")


def load_candidate() -> dict[str, Any]:
    descriptor = read_json(ROOT / "candidate" / "change-portfolio.json")
    package = load_reference()
    package["fixture_status"] = descriptor["fixture_status"]
    snapshot = load_snapshot()
    for mutation in descriptor["mutations"]:
        apply_mutation(mutation, package, snapshot)
    package["_candidate_snapshot"] = snapshot
    return package


def primary_change(package: dict[str, Any]) -> dict[str, Any]:
    return next(item for item in package["changes"] if item["id"] == "AI-2310")


def change_by_id(package: dict[str, Any], change_id: str) -> dict[str, Any]:
    return next(item for item in package["changes"] if item["id"] == change_id)


def requirement_index(baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in baseline["requirements"]}


def principal(authority_map: dict[str, Any], principal_id: str | None) -> dict[str, Any] | None:
    return authority_map.get("principals", {}).get(str(principal_id))


def principal_can(authority_map: dict[str, Any], principal_id: str | None, capability: str) -> bool:
    record = principal(authority_map, principal_id)
    return bool(record and capability in record.get("capabilities", []))


def change_identity(change: dict[str, Any]) -> tuple[str, str]:
    return str(change.get("id", "")), str(change.get("revision", ""))


def record_change_identities(record: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (str(item.get("id", "")), str(item.get("revision", "")))
        for item in record.get("changes", [])
        if isinstance(item, dict)
    }


def validate_snapshot(snapshot: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    if snapshot.get("release") != "v1.14.1" or len(snapshot.get("resolved_commit", "")) != 40:
        results.append(finding("SNAPSHOT_UNPINNED", "openspec-snapshot", "The OpenSpec release must be pinned to the observed commit."))
    schema = snapshot.get("default_schema", {})
    expected_artifacts = ["proposal", "specs", "design", "tasks"]
    if schema.get("artifact_order") != expected_artifacts or set(schema.get("delta_operations", [])) != VALID_OPERATIONS:
        results.append(finding("SNAPSHOT_SEMANTIC_DRIFT", "openspec-snapshot", "The pinned schema no longer has the expected artifact and delta semantics."))
    contracts = snapshot.get("semantic_contracts", {})
    critical = {
        "specs": {"full_modified_requirement", "capability_path_identity"},
        "tasks": {"verification_per_task", "not_autonomous_execution_authority"},
        "archive": {"validate_by_default", "not_enterprise_release_authority"},
    }
    for surface, semantics in critical.items():
        if not semantics.issubset(set(contracts.get(surface, []))):
            results.append(finding("SNAPSHOT_SEMANTIC_DRIFT", surface, "A critical OpenSpec semantic contract changed."))
    if len(snapshot.get("source_digests", {})) != 5:
        results.append(finding("SNAPSHOT_PROVENANCE_INCOMPLETE", "openspec-snapshot", "Official schema and documentation digests are incomplete."))
    return results


def validate_context(context: dict[str, Any], package: dict[str, Any], baseline: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    if package.get("context", {}).get("digest") != file_digest(ROOT / "enterprise" / "effective-context.json"):
        results.append(finding("CONTEXT_DIGEST_INVALID", "context", "The package is not bound to the exact effective-context bytes."))
    if package.get("baseline", {}).get("digest") != file_digest(ROOT / "baseline" / "baseline.json"):
        results.append(finding("BASELINE_DIGEST_INVALID", "baseline", "The package is not bound to the exact baseline bytes."))
    if package.get("baseline", {}).get("content_digest") != file_digest(ROOT / "baseline" / "document-processing.md"):
        results.append(finding("BASELINE_CONTENT_DIGEST_INVALID", "baseline", "The human-readable baseline content digest does not match."))
    package_sources = set(package.get("context", {}).get("source_ids", []))
    expected_sources = {f"{item['id']}@{item['revision']}" for item in context.get("sources", [])}
    if package_sources != expected_sources:
        results.append(finding("CONTEXT_SOURCE_MISSING", "context", "The effective-context source set is incomplete or changed."))
    if context.get("baseline_revision") != baseline.get("revision"):
        results.append(finding("CONTEXT_BASELINE_DRIFT", "context", "Context and baseline revisions disagree."))
    ids = [item["id"] for item in baseline.get("requirements", [])]
    if len(ids) != len(set(ids)):
        results.append(finding("BASELINE_REQUIREMENT_DUPLICATE", "baseline", "Baseline requirement identity is not unique."))
    return results


def validate_artifact_digests(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    change = primary_change(package)
    expected = {
        "proposal": (change.get("proposal", {}).get("digest"), ROOT / "changes" / "AI-2310" / "proposal.md"),
        "delta": (change.get("delta_artifact", {}).get("digest"), ROOT / change.get("delta_artifact", {}).get("path", "missing")),
        "design": (change.get("design", {}).get("digest"), ROOT / "changes" / "AI-2310" / "design.md"),
        "tasks": (change.get("tasks_digest"), ROOT / "changes" / "AI-2310" / "tasks.md"),
    }
    for artifact, (observed, path) in expected.items():
        if not path.is_file() or observed != file_digest(path):
            results.append(finding("DELTA_ARTIFACT_DIGEST_INVALID", artifact, "A change artifact is not bound to its exact repository bytes."))
    return results


def validate_delta(
    change: dict[str, Any],
    baseline: dict[str, Any],
    context: dict[str, Any],
    authority_map: dict[str, Any],
) -> list[Finding]:
    results: list[Finding] = []
    requirements = requirement_index(baseline)
    protected = set(context.get("protected_requirement_ids", []))
    if change.get("base_revision") != baseline.get("revision") or change.get("base_digest") != file_digest(ROOT / "baseline" / "baseline.json"):
        results.append(finding("STALE_BASELINE_REVISION", change.get("id", "change"), "The change must be rebased on the exact current baseline."))
    if change.get("context_id") != context.get("id"):
        results.append(finding("CHANGE_CONTEXT_DRIFT", change.get("id", "change"), "The change references a different effective context."))

    delta_ids: list[str] = []
    declared_capabilities = set(change.get("proposal", {}).get("modified_capabilities", [])) | set(change.get("proposal", {}).get("new_capabilities", []))
    if change.get("deltas") and "document-processing" not in declared_capabilities:
        results.append(finding("CAPABILITY_NOT_DECLARED", change.get("id", "change"), "The delta capability is absent from the proposal."))

    for delta in change.get("deltas", []):
        delta_id = delta.get("id", "delta")
        delta_ids.append(delta_id)
        operation = delta.get("operation")
        target = delta.get("target", "")
        if operation not in VALID_OPERATIONS:
            results.append(finding("DELTA_OPERATION_INVALID", delta_id, "The delta operation is not supported by the pinned schema."))
            continue
        if target in protected:
            results.append(finding("PROTECTED_AUTHORITY_MUTATION", delta_id, "A project change cannot modify an enterprise-owned requirement."))
            continue
        current = requirements.get(target)
        if operation == "ADDED":
            if current:
                results.append(finding("ADDED_REQUIREMENT_EXISTS", delta_id, "ADDED targets an existing baseline requirement."))
            if not delta.get("to_text") or not delta.get("to_scenarios"):
                results.append(finding("ADDED_REQUIREMENT_INCOMPLETE", delta_id, "An added requirement needs behavior and scenarios."))
        elif operation == "MODIFIED":
            if not current:
                results.append(finding("MODIFIED_REQUIREMENT_MISSING", delta_id, "MODIFIED targets no baseline requirement."))
                continue
            if delta.get("base_requirement_revision") != current.get("revision"):
                results.append(finding("STALE_REQUIREMENT_REVISION", delta_id, "The requirement revision is stale."))
            if delta.get("from_text") != current.get("text") or delta.get("from_scenarios") != current.get("scenarios"):
                results.append(finding("FROM_STATE_MISMATCH", delta_id, "The complete prior requirement state does not match the baseline."))
            if not delta.get("to_text") or not delta.get("to_scenarios"):
                results.append(finding("MODIFIED_REQUIREMENT_INCOMPLETE", delta_id, "The full target behavior and scenarios are required."))
        elif operation == "REMOVED":
            if not current:
                results.append(finding("REMOVED_REQUIREMENT_MISSING", delta_id, "REMOVED targets no baseline requirement."))
            if not delta.get("reason") or not delta.get("migration"):
                results.append(finding("REMOVAL_PLAN_MISSING", delta_id, "Removal requires a reason and migration."))
        elif operation == "RENAMED":
            if not current or not delta.get("from_name") or not delta.get("to_name"):
                results.append(finding("RENAME_INCOMPLETE", delta_id, "Rename requires an existing target and FROM/TO names."))
            if delta.get("to_text") and delta.get("to_text") != current.get("text"):
                results.append(finding("RENAME_CHANGES_BEHAVIOR", delta_id, "A rename cannot hide a behavior change."))

    if len(delta_ids) != len(set(delta_ids)):
        results.append(finding("DELTA_ID_DUPLICATE", change.get("id", "change"), "Delta IDs must be unique within a change."))

    state = change.get("state")
    if state not in KNOWN_STATES:
        results.append(finding("CHANGE_STATE_UNKNOWN", change.get("id", "change"), "The lifecycle state is not recognized."))
    actor_id = str(change.get("state_actor", ""))
    actor = principal(authority_map, actor_id)
    if not actor:
        results.append(finding("STATE_ACTOR_UNTRUSTED", change.get("id", "change"), "Lifecycle state actor is absent from the trusted authority registry."))
    if state in CONSEQUENTIAL_STATES:
        required_capability = {
            "APPROVED": "approve_change",
            "READY_FOR_INTEGRATION": "authorize_integration",
            "ARCHIVED": "authorize_archive",
        }[state]
        if actor and actor.get("type") == "coding_agent":
            results.append(finding("AGENT_SELF_TRANSITION", change.get("id", "change"), "A registry-identified coding agent cannot grant a consequential change state."))
        elif not principal_can(authority_map, actor_id, required_capability):
            results.append(finding("STATE_TRANSITION_UNAUTHORIZED", change.get("id", "change"), f"The trusted actor lacks {required_capability}."))

    for question in change.get("open_questions", []):
        if not question.get("owners"):
            results.append(finding("QUESTION_OWNER_MISSING", question.get("id", "question"), "Open questions need accountable owners."))
        if question.get("assumption_used") or (question.get("status") != "OPEN" and not question.get("decision_provenance")):
            results.append(finding("OPEN_QUESTION_COLLAPSED", question.get("id", "question"), "An unresolved owner decision was converted into an assumption."))
        for capability in question.get("blocks", []):
            if change.get("capability_readiness", {}).get(capability) != "BLOCKED":
                results.append(finding("BLOCKED_CAPABILITY_ENABLED", capability, "An open question's affected capability must remain blocked."))

    for proposal in change.get("design", {}).get("architecture_proposals", []):
        approved_by = proposal.get("approved_by")
        approver = principal(authority_map, approved_by)
        if proposal.get("status") in {"APPROVED", "OWNER_APPROVED"} and approver and approver.get("type") == "coding_agent":
            results.append(finding("ARCHITECTURE_SELF_APPROVED", proposal.get("id", "architecture"), "A registry-identified coding agent cannot approve architecture."))
        elif proposal.get("status") in {"APPROVED", "OWNER_APPROVED"} and not principal_can(authority_map, approved_by, "approve_architecture"):
            results.append(finding("ARCHITECTURE_APPROVER_UNAUTHORIZED", proposal.get("id", "architecture"), "The architecture approver lacks trusted authority."))
        elif proposal.get("status") not in {"PROPOSED", "OWNER_APPROVED"}:
            results.append(finding("ARCHITECTURE_PROPOSAL_UNROUTED", proposal.get("id", "architecture"), "Architecture changes need an explicit proposal route."))
    return results


def modified_targets(change: dict[str, Any]) -> set[str]:
    return {item["target"] for item in change.get("deltas", []) if item.get("operation") in {"MODIFIED", "REMOVED", "RENAMED"}}


def requirement_relationships(baseline: dict[str, Any]) -> set[frozenset[str]]:
    relationships: set[frozenset[str]] = set()
    for invariant in baseline.get("invariants", []):
        affected = invariant.get("affected_by", [])
        for index, left in enumerate(affected):
            for right in affected[index + 1 :]:
                relationships.add(frozenset({left, right}))
    return relationships


def validate_concurrency(package: dict[str, Any], baseline: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    changes = package.get("changes", [])
    identities = [change_identity(change) for change in changes]
    if len(identities) != len(set(identities)):
        results.append(finding("PORTFOLIO_CHANGE_IDENTITY_DUPLICATE", "portfolio", "Change identity pairs must be unique within the portfolio."))
    records = package.get("conflicts", [])
    baseline_requirements = requirement_index(baseline)
    related = requirement_relationships(baseline)
    for index, left in enumerate(changes):
        for right in changes[index + 1 :]:
            shared = modified_targets(left) & modified_targets(right)
            identities = {change_identity(left), change_identity(right)}
            matching = [
                record
                for record in records
                if record_change_identities(record) == identities
                and record.get("type") == "SHARED_REQUIREMENT_MODIFICATION"
            ]
            if shared:
                expected_subjects = {
                    (target, baseline_requirements.get(target, {}).get("revision"))
                    for target in shared
                }
                matching = [
                    record
                    for record in matching
                    if {
                        (str(subject.get("id", "")), subject.get("revision"))
                        for subject in record.get("subjects", [])
                        if isinstance(subject, dict)
                    } == expected_subjects
                ]
                if not matching:
                    results.append(finding("CONCURRENT_CHANGE_CONFLICT_UNRECORDED", ",".join(sorted(shared)), "Concurrent changes modify the same baseline requirement revision without an exact conflict record."))
                    continue
            else:
                left_targets = modified_targets(left)
                right_targets = modified_targets(right)
                related_pairs = {
                    pair
                    for pair in related
                    if pair & left_targets and pair & right_targets
                }
                if related_pairs:
                    candidate = [
                        record
                        for record in records
                        if record_change_identities(record) == identities
                        and record.get("type") == "POTENTIAL_CROSS_REQUIREMENT_CONFLICT"
                        and record.get("status") == "OWNER_REVIEW_REQUIRED"
                        and record.get("owner")
                    ]
                    if not candidate:
                        subjects = sorted({item for pair in related_pairs for item in pair})
                        results.append(finding("POTENTIAL_CROSS_REQUIREMENT_CONFLICT", ",".join(subjects), "Related requirements changed concurrently; semantic review by the recorded domain owner is required.", severity="REVIEW"))
                continue
            for record in matching:
                if record.get("agent_resolved"):
                    results.append(finding("CONFLICT_AGENT_RESOLVED", record.get("id", "conflict"), "An agent cannot resolve a consequential semantic conflict."))
                if not record.get("disposition") or not record.get("owner"):
                    results.append(finding("CONFLICT_DISPOSITION_MISSING", record.get("id", "conflict"), "The conflict lacks an accountable disposition."))
                blocked_ref = record.get("blocked_change", {})
                blocked = blocked_ref.get("id") if isinstance(blocked_ref, dict) else ""
                blocked_revision = blocked_ref.get("revision") if isinstance(blocked_ref, dict) else ""
                if blocked:
                    blocked_change = change_by_id(package, blocked)
                    if blocked_change.get("revision") != blocked_revision or blocked_change.get("state") != "BLOCKED_PENDING_REBASE":
                        results.append(finding("CONFLICTED_CHANGE_NOT_BLOCKED", blocked, "The disposition's exact blocked change revision is not held for rebase."))
    return results


def validate_tasks(package: dict[str, Any], baseline: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    invariant_ids = {item["id"] for item in baseline.get("invariants", [])}
    for change in package.get("changes", []):
        delta_ids = {item["id"] for item in change.get("deltas", [])}
        known_requirements = set(requirement_index(baseline)) | {
            item["target"] for item in change.get("deltas", []) if item.get("operation") == "ADDED"
        } | invariant_ids
        for task in change.get("tasks", []):
            task_id = task.get("id", "task")
            if task.get("change") != change.get("revision"):
                results.append(finding("TASK_CHANGE_ANCESTRY_MISSING", task_id, "The task is not bound to the exact change revision."))
            if not set(task.get("delta_ids", [])).issubset(delta_ids):
                results.append(finding("TASK_DELTA_UNKNOWN", task_id, "The task references an unknown delta."))
            if not set(task.get("requirements", [])).issubset(known_requirements):
                results.append(finding("TASK_REQUIREMENT_UNKNOWN", task_id, "The task references an unknown requirement or invariant."))
            if not task.get("required_evidence"):
                results.append(finding("TASK_EVIDENCE_MISSING", task_id, "The task has no claim-specific evidence obligation."))
    return results


def normalize_repo_pattern(value: str) -> str | None:
    normalized = value.replace("\\", "/").removeprefix("./").rstrip("/")
    parts = normalized.split("/")
    if not normalized or normalized.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        return None
    return normalized


def static_pattern_prefix(pattern: str) -> tuple[str, ...]:
    prefix = []
    for part in pattern.split("/"):
        if any(token in part for token in "*?["):
            break
        prefix.append(part)
    return tuple(prefix)


def path_patterns_overlap(left: str, right: str) -> bool:
    left_normalized = normalize_repo_pattern(left)
    right_normalized = normalize_repo_pattern(right)
    if left_normalized is None or right_normalized is None:
        return True
    left_prefix = static_pattern_prefix(left_normalized)
    right_prefix = static_pattern_prefix(right_normalized)
    common = min(len(left_prefix), len(right_prefix))
    if left_prefix[:common] != right_prefix[:common]:
        return False
    return True


def path_matches(pattern: str, path: str) -> bool:
    pattern_normalized = normalize_repo_pattern(pattern)
    path_normalized = normalize_repo_pattern(path)
    if pattern_normalized is None or path_normalized is None:
        return False
    if pattern_normalized.endswith("/**"):
        prefix = pattern_normalized[:-3].rstrip("/")
        return path_normalized == prefix or path_normalized.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path_normalized, pattern_normalized)


def validate_work_units(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    changes = {item.get("revision"): item for item in package.get("changes", [])}
    units_by_change: dict[str, list[dict[str, Any]]] = {revision: [] for revision in changes}
    for unit in package.get("work_units", []):
        units_by_change.setdefault(str(unit.get("change")), []).append(unit)

    for revision, units in units_by_change.items():
        change = changes.get(revision)
        if not change:
            for unit in units:
                results.append(finding("AWU_CHANGE_ANCESTRY_MISSING", unit.get("id", "awu"), "The work unit references no exact change revision in this portfolio."))
            continue
        tasks = {item["id"]: item for item in change.get("tasks", [])}
        seen_tasks: list[str] = []
        if change.get("state") == "BLOCKED_PENDING_REBASE" and units:
            results.append(finding("BLOCKED_CHANGE_HAS_EXECUTABLE_WORK", change.get("id", "change"), "A change held for rebase cannot dispatch executable work units."))
        for unit in units:
            unit_id = unit.get("id", "awu")
            writable = unit.get("writable_paths", [])
            protected = unit.get("protected_paths", [])
            changed = unit.get("observed_changed_paths", [])
            if not writable:
                results.append(finding("AWU_WRITABLE_SCOPE_MISSING", unit_id, "The work unit has no writable path boundary."))
            if not protected:
                results.append(finding("AWU_PROTECTED_SCOPE_MISSING", unit_id, "The work unit has no protected path boundary."))
            if any(path_patterns_overlap(left, right) for left in writable for right in protected):
                results.append(finding("AWU_SCOPE_OVERLAP", unit_id, "Writable and protected path patterns overlap."))
            if not changed:
                results.append(finding("AWU_DIFF_EVIDENCE_MISSING", unit_id, "The work unit lacks an authoritative changed-path observation."))
            for path in changed:
                if not any(path_matches(pattern, path) for pattern in writable):
                    results.append(finding("AWU_CHANGED_PATH_NOT_AUTHORIZED", unit_id, f"Observed changed path is outside writable scope: {path}"))
                if any(path_matches(pattern, path) for pattern in protected):
                    results.append(finding("AWU_PROTECTED_PATH_CHANGED", unit_id, f"Observed changed path intersects protected scope: {path}"))
            if not unit.get("stop_conditions"):
                results.append(finding("AWU_STOP_CONDITIONS_MISSING", unit_id, "The work unit has no explicit stop conditions."))
            required_evidence = set(unit.get("required_evidence", []))
            if not required_evidence:
                results.append(finding("AWU_EVIDENCE_MISSING", unit_id, "The work unit has no evidence obligation."))
            obligations = unit.get("evidence_obligations", [])
            if {item.get("kind") for item in obligations} != required_evidence:
                results.append(finding("AWU_EVIDENCE_OBLIGATION_DRIFT", unit_id, "Evidence kinds are not mapped one-to-one to explicit claim obligations."))
            for obligation in obligations:
                if obligation.get("requirement_id") not in unit.get("requirements", []) or not obligation.get("acceptance_criterion_id"):
                    results.append(finding("UNJUSTIFIED_EVIDENCE_INHERITANCE", unit_id, "An evidence obligation is not justified by this work unit's requirement and acceptance-criterion ancestry."))
            if "attest" in str(unit.get("evidence_role", "")) and "not_attest" not in str(unit.get("evidence_role", "")) and "never" not in str(unit.get("evidence_role", "")):
                results.append(finding("AWU_SELF_ATTESTATION", unit_id, "The implementation work unit cannot attest its own conformance."))
            for task_id in unit.get("task_ids", []):
                seen_tasks.append(task_id)
                task = tasks.get(task_id)
                if not task or task.get("requirements") != unit.get("requirements") or task.get("required_evidence") != unit.get("required_evidence"):
                    results.append(finding("AWU_ADAPTER_DRIFT", unit_id, "The work unit does not preserve task ancestry, requirements, and evidence."))
        if sorted(seen_tasks) != sorted(tasks):
            results.append(finding("AWU_TASK_COVERAGE_INVALID", str(revision), "Every task in each change must map to exactly one work unit."))
    return results


def evidence_key(record: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    return (
        str(record.get("requirement_id", "")),
        str(record.get("acceptance_criterion_id", "")),
        str(record.get("implementation_revision", "")),
        str(record.get("specification_revision", "")),
        str(record.get("kind", "")),
        str(record.get("population", "")),
        str(record.get("environment", "")),
    )


def validate_evidence(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    manifest = package.get("evidence_manifest", {})
    records = manifest.get("records", [])
    implementation_revision = str(manifest.get("implementation_revision", ""))
    specification_revision = str(manifest.get("specification_revision", ""))
    obligations = [
        {
            **obligation,
            "implementation_revision": implementation_revision,
            "specification_revision": specification_revision,
        }
        for unit in package.get("work_units", [])
        for obligation in unit.get("evidence_obligations", [])
    ]
    required_keys = {evidence_key(item) for item in obligations}
    passing_keys = {
        evidence_key(item)
        for item in records
        if item.get("independent") and item.get("result") == "PASS"
    }
    missing_keys = required_keys - passing_keys
    missing = {item[4] for item in missing_keys}
    if missing & DELTA_EVIDENCE:
        results.append(finding("DELTA_EVIDENCE_MISSING", "evidence", f"Changed claims lack exact, independent evidence: {sorted(missing & DELTA_EVIDENCE)}"))
    if missing & REGRESSION_EVIDENCE:
        results.append(finding("REGRESSION_EVIDENCE_MISSING", "evidence", f"Affected baseline invariants lack exact regression evidence: {sorted(missing & REGRESSION_EVIDENCE)}"))
    if missing - DELTA_EVIDENCE - REGRESSION_EVIDENCE:
        results.append(finding("EVIDENCE_OBLIGATION_MISSING", "evidence", f"Exact evidence obligations are unmet: {sorted(missing - DELTA_EVIDENCE - REGRESSION_EVIDENCE)}"))
    required_kinds = {item[4] for item in required_keys}
    for record in records:
        if record.get("kind") in required_kinds and not record.get("independent"):
            results.append(finding("EVIDENCE_NOT_INDEPENDENT", str(record.get("kind")), "Required conformance evidence is producer self-report."))
        if record.get("kind") in required_kinds and record.get("result") == "FAIL":
            results.append(finding("EVIDENCE_FAILED", str(record.get("kind")), "Required evidence failed."))
    for obligation in obligations:
        same_kind = [item for item in records if item.get("kind") == obligation.get("kind")]
        if same_kind and not any(evidence_key(item) == evidence_key(obligation) for item in same_kind):
            results.append(finding("EVIDENCE_SUBJECT_MISMATCH", str(obligation.get("kind")), "Evidence kind exists but its claim, acceptance criterion, implementation, specification, population, or environment binding is incompatible."))
    if manifest.get("production_ready"):
        results.append(finding("SYNTHETIC_PRODUCTION_CLAIM", "evidence", "Synthetic training evidence cannot claim production readiness."))
    if manifest.get("release_authority") != "delivery_control_plane":
        results.append(finding("RELEASE_AUTHORITY_BYPASSED", "evidence", "Release authority moved into the change package."))
    return results


def validate_multi_repository(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    model = package.get("multi_repository", {})
    canonical = set(model.get("canonical_requirement_ids", []))
    for child in model.get("children", []):
        if not set(child.get("requirement_ids", [])).issubset(canonical):
            results.append(finding("CHILD_REQUIREMENT_UNKNOWN", child.get("repository", "child"), "A child change invented a requirement outside the canonical parent."))
        if child.get("semantic_overrides"):
            results.append(finding("CHILD_WEAKENS_PARENT", child.get("repository", "child"), "A child repository cannot weaken parent change semantics."))
    return results


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def verify_integration_receipt(
    package: dict[str, Any],
    authority_map: dict[str, Any],
    control_plane: dict[str, Any],
) -> list[Finding]:
    results: list[Finding] = []
    integration = package.get("integration", {})
    receipt_id = integration.get("authorization_receipt_id")
    if not receipt_id:
        return results
    receipt = control_plane.get("integration_receipts", {}).get(receipt_id)
    if not receipt:
        return [finding("INTEGRATION_RECEIPT_UNKNOWN", "integration", "The receipt is absent from the trusted registry.")]
    change = primary_change(package)
    manifest = package.get("evidence_manifest", {})
    expected = {
        "baseline_digest": package.get("baseline", {}).get("digest"),
        "change_revision": change.get("revision"),
        "implementation_revision": manifest.get("implementation_revision"),
        "policy_context": package.get("context", {}).get("id"),
        "operation": integration.get("requested_operation", RECEIPT_OPERATION),
    }
    mismatches = [key for key, value in expected.items() if receipt.get(key) != value]
    if mismatches:
        results.append(finding("INTEGRATION_RECEIPT_BINDING_MISMATCH", "integration", f"Receipt values do not match the exact request: {sorted(mismatches)}"))
    issuer = receipt.get("issuer")
    if issuer not in control_plane.get("trusted_issuers", []) or not principal_can(authority_map, issuer, "issue_integration_receipt"):
        results.append(finding("INTEGRATION_RECEIPT_ISSUER_UNTRUSTED", "integration", "The receipt issuer is not a trusted integration authority."))
    if not principal_can(authority_map, receipt.get("approver_id"), "authorize_integration"):
        results.append(finding("INTEGRATION_APPROVER_UNAUTHORIZED", "integration", "The registered approver lacks integration authority."))
    evaluated_at = parse_timestamp(control_plane["evaluation_time"])
    if parse_timestamp(receipt.get("expires_at", "1970-01-01T00:00:00Z")) <= evaluated_at:
        results.append(finding("INTEGRATION_RECEIPT_EXPIRED", "integration", "The receipt expired before the fixed evaluation time."))
    if receipt.get("revoked"):
        results.append(finding("INTEGRATION_RECEIPT_REVOKED", "integration", "The receipt was revoked by the trusted control plane."))
    if receipt.get("state") != "UNUSED":
        results.append(finding("INTEGRATION_RECEIPT_REPLAYED", "integration", "The single-use receipt is not in UNUSED state."))
    if receipt.get("version") != integration.get("receipt_version"):
        results.append(finding("INTEGRATION_RECEIPT_VERSION_CONFLICT", "integration", "The requested receipt version is stale or mismatched."))
    return results


def consume_integration_receipt(
    package: dict[str, Any],
    authority_map: dict[str, Any],
    control_plane: dict[str, Any],
) -> dict[str, Any]:
    """Atomically consume a verified receipt in this in-memory training registry."""
    with _RECEIPT_LOCK:
        findings = verify_integration_receipt(package, authority_map, control_plane)
        if findings:
            raise ValueError(",".join(sorted(item.code for item in findings)))
        receipt_id = package["integration"]["authorization_receipt_id"]
        receipt = control_plane["integration_receipts"][receipt_id]
        expected_version = package["integration"].get("receipt_version")
        if receipt.get("version") != expected_version:
            raise ValueError("INTEGRATION_RECEIPT_VERSION_CONFLICT")
        receipt["state"] = "USED"
        receipt["consumed_at"] = control_plane["evaluation_time"]
        receipt["version"] += 1
        return copy.deepcopy(receipt)


def validate_integration(
    package: dict[str, Any],
    authority_map: dict[str, Any],
    control_plane: dict[str, Any],
) -> list[Finding]:
    results: list[Finding] = []
    integration = package.get("integration", {})
    change = primary_change(package)
    if package.get("baseline", {}).get("mutated") and not integration.get("eligible"):
        results.append(finding("BASELINE_MUTATED_EARLY", "baseline", "The baseline changed before the integration gate authorized it."))
    if integration.get("requested") and not integration.get("authorization_receipt_id"):
        results.append(finding("ARCHIVE_BEFORE_AUTHORIZATION", "integration", "Archive/integration was requested without external owner authorization."))
    results.extend(verify_integration_receipt(package, authority_map, control_plane))
    if change.get("state") == "ARCHIVED":
        if any(question.get("status") == "OPEN" and question.get("blocks") for question in change.get("open_questions", [])):
            results.append(finding("ARCHIVED_WITH_BLOCKING_QUESTION", change["id"], "A change was archived with a blocking open question."))
        if not integration.get("archive_destination"):
            results.append(finding("ARCHIVE_DESTINATION_MISSING", change["id"], "Archived history has no dated destination."))
    if integration.get("release_authorized"):
        results.append(finding("RELEASE_SELF_AUTHORIZED", "integration", "The training change package cannot authorize production release."))
    return results


def review_bundle(
    baseline: dict[str, Any],
    context: dict[str, Any],
    snapshot: dict[str, Any],
    package: dict[str, Any],
    authority_map: dict[str, Any] | None = None,
    control_plane: dict[str, Any] | None = None,
) -> list[Finding]:
    results: list[Finding] = []
    authority_map = authority_map or load_authority_map()
    control_plane = control_plane or load_control_plane()
    results.extend(validate_snapshot(snapshot))
    results.extend(validate_context(context, package, baseline))
    results.extend(validate_artifact_digests(package))
    for change in package.get("changes", []):
        results.extend(validate_delta(change, baseline, context, authority_map))
    results.extend(validate_concurrency(package, baseline))
    results.extend(validate_tasks(package, baseline))
    results.extend(validate_work_units(package))
    results.extend(validate_evidence(package))
    results.extend(validate_multi_repository(package))
    results.extend(validate_integration(package, authority_map, control_plane))
    return sorted(set(results))


def selection_state(findings: Iterable[Finding]) -> str:
    findings = list(findings)
    if any(item.severity == "BLOCK" for item in findings):
        return "BLOCKED"
    if findings:
        return "REVIEW"
    return "READY_FOR_OWNER_REVIEW"


def apply_change(baseline: dict[str, Any], change: dict[str, Any]) -> dict[str, Any]:
    """Return a candidate target. This does not authorize or persist integration."""
    target = copy.deepcopy(baseline)
    requirements = requirement_index(target)
    for delta in change.get("deltas", []):
        operation = delta["operation"]
        subject = delta["target"]
        if operation == "ADDED":
            requirements[subject] = {
                "id": subject,
                "revision": 1,
                "authority": "project",
                "text": delta["to_text"],
                "scenarios": delta["to_scenarios"],
            }
        elif operation == "MODIFIED":
            current = requirements[subject]
            requirements[subject] = {
                **current,
                "revision": current["revision"] + 1,
                "text": delta["to_text"],
                "scenarios": delta["to_scenarios"],
            }
        elif operation == "REMOVED":
            requirements.pop(subject)
        elif operation == "RENAMED":
            requirements[subject]["name"] = delta["to_name"]
    target["requirements"] = list(requirements.values())
    target["revision"] = "candidate-target-not-integrated"
    target["derived_from"] = {"baseline": baseline["revision"], "change": change["revision"]}
    return target


def classify_scenario(case: dict[str, Any]) -> str:
    signals = set(case.get("signals", []))
    if "protected_authority_mutation" in signals:
        return "BLOCK_PROTECTED_AUTHORITY"
    if "stale_baseline" in signals:
        return "REBASE_REQUIRED"
    if "shared_requirement" in signals:
        return "CONFLICT_REVIEW"
    if "semantic_contradiction" in signals:
        return "SEMANTIC_CONFLICT"
    if "unapproved_architecture" in signals:
        return "ARCHITECTURE_REVIEW"
    if "missing_change_ancestry" in signals:
        return "BLOCK_UNTRACEABLE_WORK"
    if "delta_pass_regression_fail" in signals:
        return "BLOCK_REGRESSION_FAILURE"
    if "archive_before_evidence" in signals:
        return "BLOCK_ARCHIVE"
    if "child_weakens_parent" in signals:
        return "BLOCK_CHILD_OVERRIDE"
    if "question_assumed" in signals:
        return "BLOCK_UNAUTHORIZED_ASSUMPTION"
    return "NO_LABEL"


def apply_mutation(
    name: str,
    package: dict[str, Any],
    snapshot: dict[str, Any],
    control_plane: dict[str, Any] | None = None,
) -> None:
    change = primary_change(package)
    baseline = package["baseline"]
    if name == "protected_authority_mutation":
        change["deltas"].append({"id": "M-POLICY", "operation": "MODIFIED", "target": "AI-030", "base_requirement_revision": 7, "from_text": "review required", "from_scenarios": [], "to_text": "review optional", "to_scenarios": ["bypass"]})
    elif name == "stale_baseline_revision":
        change["base_revision"] = "document-processing@3-training"
    elif name == "from_state_mismatch":
        change["deltas"][0]["from_text"] = "Broker documents MAY be manually classified."
    elif name == "concurrent_conflict_hidden":
        package["conflicts"] = []
    elif name == "architecture_self_approved":
        change["design"]["architecture_proposals"] = [{"id": "ARCH-PROP-019", "status": "OWNER_APPROVED", "approved_by": "agent-course14"}]
    elif name == "task_change_ancestry_missing":
        change["tasks"][0]["change"] = ""
    elif name == "delta_evidence_missing":
        package["evidence_manifest"]["records"] = [item for item in package["evidence_manifest"]["records"] if item["kind"] != "classification_evaluation"]
    elif name == "regression_evidence_missing":
        package["evidence_manifest"]["records"] = [item for item in package["evidence_manifest"]["records"] if item["kind"] != "manual_fallback_regression"]
    elif name == "archive_before_owner_review":
        package["integration"].update({"requested": True, "state": "ARCHIVE_REQUESTED", "authorization_receipt_id": None})
    elif name == "child_weakens_parent":
        package["multi_repository"]["children"][0]["semantic_overrides"] = ["human_review_optional"]
    elif name == "open_question_collapsed":
        change["open_questions"][0].update({"status": "ANSWERED", "assumption_used": True})
    elif name == "agent_self_transitions_archived":
        change.update({"state": "ARCHIVED", "state_actor": "agent-course14"})
    elif name == "evidence_subject_mismatch":
        binding = next(item for item in package["evidence_manifest"]["records"] if item["kind"] == "subject_binding_test")
        binding["implementation_revision"] = "impl-other@deadbeef"
    elif name == "baseline_mutated_early":
        baseline["mutated"] = True
    elif name == "context_digest_invalid":
        package["context"]["digest"] = "sha256:wrong"
    elif name == "baseline_digest_invalid":
        baseline["digest"] = "sha256:wrong"
        for item in package["changes"]:
            item["base_digest"] = "sha256:wrong"
    elif name == "delta_artifact_digest_invalid":
        change["delta_artifact"]["digest"] = "sha256:wrong"
    elif name == "duplicate_delta_id":
        change["deltas"][1]["id"] = change["deltas"][0]["id"]
    elif name == "added_existing_requirement":
        change["deltas"][1]["target"] = "REQ-DOC-010"
    elif name == "modified_missing_requirement":
        change["deltas"][0]["target"] = "REQ-DOC-999"
    elif name == "removed_without_migration":
        change["deltas"].append({"id": "M-REMOVE", "operation": "REMOVED", "target": "REQ-DOC-010"})
    elif name == "renamed_changes_behavior":
        change["deltas"].append({"id": "M-RENAME", "operation": "RENAMED", "target": "REQ-DOC-010", "from_name": "Approved extraction", "to_name": "Fast extraction", "to_text": "Use any extractor."})
    elif name == "capability_not_declared":
        change["proposal"]["modified_capabilities"] = []
    elif name == "question_owner_missing":
        change["open_questions"][0]["owners"] = []
    elif name == "blocked_capability_enabled":
        change["capability_readiness"]["automatic_classification_persistence"] = "READY_FOR_BOUNDED_IMPLEMENTATION"
    elif name == "task_delta_unknown":
        change["tasks"][0]["delta_ids"] = ["DELTA-UNKNOWN"]
    elif name == "task_requirement_unknown":
        change["tasks"][0]["requirements"] = ["REQ-UNKNOWN"]
    elif name == "task_evidence_missing":
        change["tasks"][0]["required_evidence"] = []
    elif name == "awu_mapping_drift":
        package["work_units"][0]["requirements"] = []
    elif name == "awu_writable_paths_missing":
        package["work_units"][0]["writable_paths"] = []
    elif name == "awu_protected_paths_missing":
        package["work_units"][0]["protected_paths"] = []
    elif name == "awu_stop_conditions_missing":
        package["work_units"][0]["stop_conditions"] = []
    elif name == "awu_evidence_missing":
        package["work_units"][0]["required_evidence"] = []
    elif name == "awu_self_attests":
        package["work_units"][0]["evidence_role"] = "attest_results"
    elif name == "blanket_evidence":
        inherited = copy.deepcopy(package["work_units"][0]["evidence_obligations"])
        for unit in package["work_units"]:
            unit["required_evidence"] = [item["kind"] for item in inherited]
            unit["evidence_obligations"] = copy.deepcopy(inherited)
    elif name == "evidence_not_independent":
        next(item for item in package["evidence_manifest"]["records"] if item["kind"] == "contract_test")["independent"] = False
    elif name == "evidence_fail":
        next(item for item in package["evidence_manifest"]["records"] if item["kind"] == "contract_test")["result"] = "FAIL"
    elif name == "conflict_agent_resolved":
        package["conflicts"][0]["agent_resolved"] = True
    elif name == "conflict_disposition_missing":
        package["conflicts"][0]["disposition"] = ""
    elif name == "blocked_change_not_blocked":
        change_by_id(package, "AI-2331")["state"] = "IMPLEMENTING"
    elif name == "production_ready_claim":
        package["evidence_manifest"]["production_ready"] = True
    elif name == "release_self_authorized":
        package["integration"]["release_authorized"] = True
    elif name == "integration_receipt_unbound":
        package["integration"].update({"requested": True, "requested_operation": RECEIPT_OPERATION, "authorization_receipt_id": "RCP-AI2310-001", "receipt_version": 1})
        if control_plane is None:
            raise ValueError("integration receipt mutation requires the trusted control plane")
        control_plane["integration_receipts"]["RCP-AI2310-001"]["baseline_digest"] = "sha256:wrong"
    elif name == "archived_with_active_question":
        change.update({"state": "ARCHIVED", "state_actor": "baseline-owner-01"})
        package["integration"]["archive_destination"] = "archive/2026-10-12-ai-2310"
    elif name == "archive_destination_missing":
        change.update({"state": "ARCHIVED", "state_actor": "baseline-owner-01"})
        change["open_questions"] = []
        package["integration"]["archive_destination"] = None
    elif name == "child_unknown_requirement":
        package["multi_repository"]["children"][0]["requirement_ids"].append("REQ-LOCAL-999")
    elif name == "snapshot_unpinned":
        snapshot["resolved_commit"] = "main"
    elif name == "snapshot_semantic_drift":
        snapshot["semantic_contracts"]["archive"] = ["move_folder"]
    elif name == "baseline_requirement_duplicate":
        # The package cannot mutate the external baseline fixture, so mark a synthetic duplicate for review.
        package["_baseline_duplicate"] = True
    elif name == "state_unknown":
        change["state"] = "DONE"
    elif name == "awu_scope_overlap":
        package["work_units"][0]["writable_paths"] = ["src/**"]
        package["work_units"][0]["protected_paths"] = ["src/auth/**"]
    elif name == "context_source_missing":
        package["context"]["source_ids"] = package["context"]["source_ids"][:-1]
    elif name == "change_context_drift":
        change["context_id"] = "CTX-OTHER@1"
    elif name == "evidence_wrong_claim_same_kind":
        record = next(item for item in package["evidence_manifest"]["records"] if item["kind"] == "classification_evaluation")
        record["requirement_id"] = "REQ-DOC-999"
    elif name == "conflict_change_identity_mismatch":
        package["conflicts"][0]["changes"][0]["id"] = "AI-9999"
    elif name == "cross_requirement_semantic_candidate":
        other = change_by_id(package, "AI-2331")
        current = load_baseline()["requirements"][2]
        other["deltas"][0].update({
            "target": current["id"],
            "base_requirement_revision": current["revision"],
            "from_text": current["text"],
            "from_scenarios": current["scenarios"],
        })
        package["conflicts"] = []
    elif name == "actor_name_bypass_attempt":
        change.update({"state": "ARCHIVED", "state_actor": "automation-service"})
    elif name == "awu_changed_path_outside_scope":
        package["work_units"][0]["observed_changed_paths"] = ["src/auth/policy.py"]
    elif name == "second_change_task_invalid":
        other = change_by_id(package, "AI-2331")
        other["tasks"] = [{"id": "T-AI2331-001", "change": "AI-OTHER@1", "delta_ids": ["UNKNOWN"], "requirements": ["REQ-UNKNOWN"], "required_evidence": []}]
    elif name == "integration_receipt_expired":
        package["integration"].update({"requested": True, "requested_operation": RECEIPT_OPERATION, "authorization_receipt_id": "RCP-AI2310-001", "receipt_version": 1})
        if control_plane is None:
            raise ValueError("integration receipt mutation requires the trusted control plane")
        control_plane["integration_receipts"]["RCP-AI2310-001"]["expires_at"] = "2026-10-01T00:00:00Z"
    elif name == "integration_receipt_replayed":
        package["integration"].update({"requested": True, "requested_operation": RECEIPT_OPERATION, "authorization_receipt_id": "RCP-AI2310-001", "receipt_version": 1})
        if control_plane is None:
            raise ValueError("integration receipt mutation requires the trusted control plane")
        control_plane["integration_receipts"]["RCP-AI2310-001"]["state"] = "USED"
    else:
        raise KeyError(f"unknown mutation: {name}")


def mutation_findings(name: str) -> set[str]:
    baseline = load_baseline()
    context = load_context()
    snapshot = copy.deepcopy(load_snapshot())
    package = copy.deepcopy(load_reference())
    control_plane = copy.deepcopy(load_control_plane())
    apply_mutation(name, package, snapshot, control_plane)
    results = review_bundle(baseline, context, snapshot, package, control_plane=control_plane)
    if package.get("_baseline_duplicate"):
        results.append(finding("BASELINE_REQUIREMENT_DUPLICATE", "baseline", "Injected duplicate baseline identity."))
    return {item.code for item in results}


def run_conformance_suite() -> dict[str, Any]:
    suite = read_json(ROOT / "conformance-suite.json")
    results = []
    for case in suite["cases"]:
        actual = classify_scenario(case)
        results.append({"id": case["id"], "expected": case["expected"], "actual": actual, "passed": actual == case["expected"]})
    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results, "claim": suite["claim"]}


def run_evaluation() -> dict[str, Any]:
    suite = read_json(ROOT / "evaluation-cases.json")
    results = []
    for case in suite["cases"]:
        observed = mutation_findings(case["mutation"])
        results.append({"id": case["id"], "expected": case["expected"], "observed": sorted(observed), "passed": case["expected"] in observed})
    return {"passed": sum(item["passed"] for item in results), "total": len(results), "results": results, "claim": suite["claim"]}


def run_demo() -> dict[str, Any]:
    baseline = load_baseline()
    context = load_context()
    snapshot = load_snapshot()
    reference = load_reference()
    candidate = load_candidate()
    candidate_snapshot = candidate.pop("_candidate_snapshot")
    reference_findings = review_bundle(baseline, context, snapshot, reference)
    candidate_findings = review_bundle(baseline, context, candidate_snapshot, candidate)
    target = apply_change(baseline, primary_change(reference))
    return {
        "snapshot": {"release": snapshot["release"], "commit": snapshot["resolved_commit"][:12]},
        "baseline": baseline["revision"],
        "candidate_target": target["revision"],
        "reference": {"state": selection_state(reference_findings), "findings": [item.code for item in reference_findings]},
        "unsafe_candidate": {"state": selection_state(candidate_findings), "findings": sorted({item.code for item in candidate_findings})},
        "concurrency": {"active_changes": 2, "recorded_conflicts": len(reference["conflicts"]), "blocked_change": "AI-2331@1-training"},
        "integration": reference["integration"]["state"],
        "authority_boundary": reference["authority_boundary"],
    }


def main() -> None:
    demo = run_demo()
    conformance = run_conformance_suite()
    evaluation = run_evaluation()
    demo["conformance"] = {"passed": conformance["passed"], "total": conformance["total"]}
    demo["evaluation"] = {"passed": evaluation["passed"], "total": evaluation["total"]}
    print(json.dumps(demo, indent=2))


if __name__ == "__main__":
    main()
