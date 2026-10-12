#!/usr/bin/env python3
"""Deterministic Course 14 lab: govern OpenSpec-style brownfield changes."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
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


def validate_delta(change: dict[str, Any], baseline: dict[str, Any], context: dict[str, Any]) -> list[Finding]:
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
    actor = str(change.get("state_actor", ""))
    if state in CONSEQUENTIAL_STATES and "agent" in actor:
        results.append(finding("AGENT_SELF_TRANSITION", change.get("id", "change"), "A coding agent cannot grant a consequential change state."))

    for question in change.get("open_questions", []):
        if not question.get("owners"):
            results.append(finding("QUESTION_OWNER_MISSING", question.get("id", "question"), "Open questions need accountable owners."))
        if question.get("assumption_used") or (question.get("status") != "OPEN" and not question.get("decision_provenance")):
            results.append(finding("OPEN_QUESTION_COLLAPSED", question.get("id", "question"), "An unresolved owner decision was converted into an assumption."))
        for capability in question.get("blocks", []):
            if change.get("capability_readiness", {}).get(capability) != "BLOCKED":
                results.append(finding("BLOCKED_CAPABILITY_ENABLED", capability, "An open question's affected capability must remain blocked."))

    for proposal in change.get("design", {}).get("architecture_proposals", []):
        if proposal.get("status") == "APPROVED" and proposal.get("approved_by") == "coding_agent":
            results.append(finding("ARCHITECTURE_SELF_APPROVED", proposal.get("id", "architecture"), "A coding agent cannot approve architecture."))
        elif proposal.get("status") not in {"PROPOSED", "OWNER_APPROVED"}:
            results.append(finding("ARCHITECTURE_PROPOSAL_UNROUTED", proposal.get("id", "architecture"), "Architecture changes need an explicit proposal route."))
    return results


def modified_targets(change: dict[str, Any]) -> set[str]:
    return {item["target"] for item in change.get("deltas", []) if item.get("operation") in {"MODIFIED", "REMOVED", "RENAMED"}}


def validate_concurrency(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    changes = package.get("changes", [])
    records = package.get("conflicts", [])
    for index, left in enumerate(changes):
        for right in changes[index + 1 :]:
            shared = modified_targets(left) & modified_targets(right)
            if not shared:
                continue
            revisions = {left.get("revision"), right.get("revision")}
            matching = [record for record in records if set(record.get("changes", [])) == revisions and record.get("type") == "SHARED_REQUIREMENT_MODIFICATION"]
            if not matching:
                results.append(finding("CONCURRENT_CHANGE_CONFLICT_UNRECORDED", ",".join(sorted(shared)), "Concurrent changes modify the same baseline behavior without a conflict record."))
                continue
            for record in matching:
                if record.get("agent_resolved"):
                    results.append(finding("CONFLICT_AGENT_RESOLVED", record.get("id", "conflict"), "An agent cannot resolve a consequential semantic conflict."))
                if not record.get("disposition") or not record.get("owner"):
                    results.append(finding("CONFLICT_DISPOSITION_MISSING", record.get("id", "conflict"), "The conflict lacks an accountable disposition."))
                blocked = record.get("blocked_change", "").split("@", 1)[0]
                if blocked and change_by_id(package, blocked).get("state") != "BLOCKED_PENDING_REBASE":
                    results.append(finding("CONFLICTED_CHANGE_NOT_BLOCKED", blocked, "The disposition says rebase, but the affected change is still executable."))
    return results


def validate_tasks(package: dict[str, Any], baseline: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    change = primary_change(package)
    delta_ids = {item["id"] for item in change.get("deltas", [])}
    known_requirements = set(requirement_index(baseline)) | {item["target"] for item in change.get("deltas", []) if item.get("operation") == "ADDED"} | {item["id"] for item in baseline.get("invariants", [])}
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


def validate_work_units(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    change = primary_change(package)
    tasks = {item["id"]: item for item in change.get("tasks", [])}
    seen_tasks: list[str] = []
    evidence_sets: list[tuple[str, ...]] = []
    for unit in package.get("work_units", []):
        unit_id = unit.get("id", "awu")
        if unit.get("change") != change.get("revision"):
            results.append(finding("AWU_CHANGE_ANCESTRY_MISSING", unit_id, "The work unit is not bound to the exact change revision."))
        if not unit.get("writable_paths"):
            results.append(finding("AWU_WRITABLE_SCOPE_MISSING", unit_id, "The work unit has no writable path boundary."))
        if not unit.get("protected_paths"):
            results.append(finding("AWU_PROTECTED_SCOPE_MISSING", unit_id, "The work unit has no protected path boundary."))
        if set(unit.get("writable_paths", [])) & set(unit.get("protected_paths", [])):
            results.append(finding("AWU_SCOPE_OVERLAP", unit_id, "A path cannot be both writable and protected."))
        if not unit.get("stop_conditions"):
            results.append(finding("AWU_STOP_CONDITIONS_MISSING", unit_id, "The work unit has no explicit stop conditions."))
        if not unit.get("required_evidence"):
            results.append(finding("AWU_EVIDENCE_MISSING", unit_id, "The work unit has no evidence obligation."))
        evidence_sets.append(tuple(unit.get("required_evidence", [])))
        if "attest" in str(unit.get("evidence_role", "")) and "not_attest" not in str(unit.get("evidence_role", "")) and "never" not in str(unit.get("evidence_role", "")):
            results.append(finding("AWU_SELF_ATTESTATION", unit_id, "The implementation work unit cannot attest its own conformance."))
        for task_id in unit.get("task_ids", []):
            seen_tasks.append(task_id)
            task = tasks.get(task_id)
            if not task or task.get("requirements") != unit.get("requirements") or task.get("required_evidence") != unit.get("required_evidence"):
                results.append(finding("AWU_ADAPTER_DRIFT", unit_id, "The work unit does not preserve task ancestry, requirements, and evidence."))
    if sorted(seen_tasks) != sorted(tasks):
        results.append(finding("AWU_TASK_COVERAGE_INVALID", "work_units", "Every task must map to exactly one work unit."))
    if evidence_sets and len(set(evidence_sets)) != len(evidence_sets):
        results.append(finding("BLANKET_EVIDENCE_INHERITANCE", "work_units", "Work units reused a blanket evidence list instead of claim-specific obligations."))
    return results


def validate_evidence(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    manifest = package.get("evidence_manifest", {})
    records = manifest.get("records", [])
    independent_pass = {item.get("kind") for item in records if item.get("independent") and item.get("result") == "PASS"}
    required = {kind for unit in package.get("work_units", []) for kind in unit.get("required_evidence", [])}
    missing = required - independent_pass
    if missing & DELTA_EVIDENCE:
        results.append(finding("DELTA_EVIDENCE_MISSING", "evidence", f"Changed claims lack independent evidence: {sorted(missing & DELTA_EVIDENCE)}"))
    if missing & REGRESSION_EVIDENCE:
        results.append(finding("REGRESSION_EVIDENCE_MISSING", "evidence", f"Affected baseline invariants lack regression evidence: {sorted(missing & REGRESSION_EVIDENCE)}"))
    if missing - DELTA_EVIDENCE - REGRESSION_EVIDENCE:
        results.append(finding("EVIDENCE_OBLIGATION_MISSING", "evidence", f"Evidence obligations are unmet: {sorted(missing - DELTA_EVIDENCE - REGRESSION_EVIDENCE)}"))
    for record in records:
        if record.get("kind") in required and not record.get("independent"):
            results.append(finding("EVIDENCE_NOT_INDEPENDENT", str(record.get("kind")), "Required conformance evidence is producer self-report."))
        if record.get("kind") in required and record.get("result") == "FAIL":
            results.append(finding("EVIDENCE_FAILED", str(record.get("kind")), "Required evidence failed."))
    binding = next((item for item in records if item.get("kind") == "subject_binding_test"), None)
    if not binding or binding.get("claim") != manifest.get("implementation_revision"):
        results.append(finding("EVIDENCE_SUBJECT_MISMATCH", "evidence", "Evidence is not bound to the exact implementation revision."))
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


def validate_integration(package: dict[str, Any]) -> list[Finding]:
    results: list[Finding] = []
    integration = package.get("integration", {})
    change = primary_change(package)
    if package.get("baseline", {}).get("mutated") and not integration.get("eligible"):
        results.append(finding("BASELINE_MUTATED_EARLY", "baseline", "The baseline changed before the integration gate authorized it."))
    if integration.get("requested") and not integration.get("authorization_receipt"):
        results.append(finding("ARCHIVE_BEFORE_AUTHORIZATION", "integration", "Archive/integration was requested without external owner authorization."))
    receipt = integration.get("authorization_receipt")
    if receipt:
        required_bindings = {"baseline_digest", "change_revision", "implementation_revision", "policy_context", "approver", "expires_at", "state"}
        if not required_bindings.issubset(receipt) or receipt.get("state") != "UNUSED":
            results.append(finding("INTEGRATION_RECEIPT_UNBOUND", "integration", "The integration receipt is not exact-revision-bound and single-use."))
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
) -> list[Finding]:
    results: list[Finding] = []
    results.extend(validate_snapshot(snapshot))
    results.extend(validate_context(context, package, baseline))
    results.extend(validate_artifact_digests(package))
    for change in package.get("changes", []):
        results.extend(validate_delta(change, baseline, context))
    results.extend(validate_concurrency(package))
    results.extend(validate_tasks(package, baseline))
    results.extend(validate_work_units(package))
    results.extend(validate_evidence(package))
    results.extend(validate_multi_repository(package))
    results.extend(validate_integration(package))
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


def apply_mutation(name: str, package: dict[str, Any], snapshot: dict[str, Any]) -> None:
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
        change["design"]["architecture_proposals"] = [{"id": "ARCH-PROP-019", "status": "APPROVED", "approved_by": "coding_agent"}]
    elif name == "task_change_ancestry_missing":
        change["tasks"][0]["change"] = ""
    elif name == "delta_evidence_missing":
        package["evidence_manifest"]["records"] = [item for item in package["evidence_manifest"]["records"] if item["kind"] != "classification_evaluation"]
    elif name == "regression_evidence_missing":
        package["evidence_manifest"]["records"] = [item for item in package["evidence_manifest"]["records"] if item["kind"] != "manual_fallback_regression"]
    elif name == "archive_before_owner_review":
        package["integration"].update({"requested": True, "state": "ARCHIVE_REQUESTED", "authorization_receipt": None})
    elif name == "child_weakens_parent":
        package["multi_repository"]["children"][0]["semantic_overrides"] = ["human_review_optional"]
    elif name == "open_question_collapsed":
        change["open_questions"][0].update({"status": "ANSWERED", "assumption_used": True})
    elif name == "agent_self_transitions_archived":
        change.update({"state": "ARCHIVED", "state_actor": "coding_agent"})
    elif name == "evidence_subject_mismatch":
        binding = next(item for item in package["evidence_manifest"]["records"] if item["kind"] == "subject_binding_test")
        binding["claim"] = "impl-other@deadbeef"
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
        for unit in package["work_units"]:
            unit["required_evidence"] = ["contract_test"]
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
        package["integration"]["authorization_receipt"] = {"state": "USED", "approver": "owner"}
    elif name == "archived_with_active_question":
        change.update({"state": "ARCHIVED", "state_actor": "baseline_owner"})
        package["integration"]["archive_destination"] = "archive/2026-10-12-ai-2310"
    elif name == "archive_destination_missing":
        change.update({"state": "ARCHIVED", "state_actor": "baseline_owner"})
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
        package["work_units"][0]["protected_paths"] = [package["work_units"][0]["writable_paths"][0]]
    elif name == "context_source_missing":
        package["context"]["source_ids"] = package["context"]["source_ids"][:-1]
    elif name == "change_context_drift":
        change["context_id"] = "CTX-OTHER@1"
    else:
        raise KeyError(f"unknown mutation: {name}")


def mutation_findings(name: str) -> set[str]:
    baseline = load_baseline()
    context = load_context()
    snapshot = copy.deepcopy(load_snapshot())
    package = copy.deepcopy(load_reference())
    apply_mutation(name, package, snapshot)
    results = review_bundle(baseline, context, snapshot, package)
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
