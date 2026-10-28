"""Deterministic parent/child, dependency, rollout, and integration controls."""

from __future__ import annotations

import json
from collections import deque

from .contracts import Decision, Finding, TrustedContext
from .git_harness import canonical_digest


EXPECTED_CHILDREN = {
    "AI-2500-DOCUMENT",
    "AI-2500-AI",
    "AI-2500-REVIEW",
    "AI-2500-UNDERWRITING",
    "AI-2500-UI",
}
EXPECTED_DEPENDENCIES = {
    "AI-2500-CONTRACT": set(),
    "AI-2500-DOCUMENT": {"AI-2500-CONTRACT"},
    "AI-2500-AI": {"AI-2500-CONTRACT"},
    "AI-2500-REVIEW": {"AI-2500-CONTRACT"},
    "AI-2500-UNDERWRITING": {"AI-2500-CONTRACT"},
    "AI-2500-UI": {"AI-2500-UNDERWRITING"},
    "AI-2500-INTEGRATION": {
        "AI-2500-DOCUMENT",
        "AI-2500-AI",
        "AI-2500-REVIEW",
        "AI-2500-UNDERWRITING",
        "AI-2500-UI",
    },
}
EXPECTED_ROLLOUT = [
    "deploy-review-v2",
    "verify-review-v2-accepts-ai-v1",
    "deploy-ai-v2-disabled",
    "verify-ai-v2-review-v2",
    "enable-bounded-traffic",
]


def dependency_order(graph: dict[str, list[str]]) -> tuple[str, ...]:
    dependencies = {node: set(items) for node, items in graph.items()}
    unknown = {item for items in dependencies.values() for item in items} - dependencies.keys()
    if unknown:
        raise ValueError(f"unknown dependencies: {sorted(unknown)}")
    ready = deque(sorted(node for node, items in dependencies.items() if not items))
    order: list[str] = []
    while ready:
        node = ready.popleft()
        order.append(node)
        for candidate in sorted(dependencies):
            if node in dependencies[candidate]:
                dependencies[candidate].remove(node)
                if not dependencies[candidate] and candidate not in order and candidate not in ready:
                    ready.append(candidate)
    if len(order) != len(dependencies):
        raise ValueError("dependency graph contains a cycle")
    return tuple(order)


def evaluate_candidate(candidate: dict[str, object], trusted: TrustedContext) -> Decision:
    findings: list[Finding] = []
    parent_revision = int(trusted.parent_change["revision"])
    child_specs = candidate["child_specs"]
    if set(child_specs) != EXPECTED_CHILDREN:
        findings.append(Finding("CHILD_SET_INCOMPLETE", "The parent change is missing repository child specifications."))
    for child_id, child in child_specs.items():
        if child.get("parent_change") != "AI-2500" or child.get("parent_revision") != parent_revision:
            findings.append(Finding("STALE_PARENT_REVISION", f"{child_id} is not bound to AI-2500@{parent_revision}."))
        if child.get("allows_review_bypass") is True:
            findings.append(Finding("PARENT_CHILD_SEMANTIC_CONFLICT", f"{child_id} introduces an unauthorized review bypass."))
    required_ids = {item["id"] for item in trusted.parent_change["requirements"]}
    allocated_ids = {
        requirement
        for child in child_specs.values()
        for requirement in child.get("implements", [])
    }
    if not required_ids <= allocated_ids:
        findings.append(Finding("REQUIREMENT_ALLOCATION_INCOMPLETE", "A parent requirement has no repository implementation owner."))

    registry = candidate["contract_registry"]
    if registry.get("owner") != "Enterprise Integration Architecture":
        findings.append(Finding("CONTRACT_OWNER_MISMATCH", "Canonical contract ownership is not the approved owner."))
    if registry.get("revision") != 2 or registry.get("digest") != canonical_digest(dict(trusted.canonical_contract)):
        findings.append(Finding("CONTRACT_REVISION_MISMATCH", "The contract record is not bound to the protected revision."))
    if candidate["contract_proposal"] != dict(trusted.canonical_contract):
        findings.append(Finding("CANONICAL_CONTRACT_DRIFT", "The candidate contract differs from the protected canonical artifact."))

    graph = candidate["dependency_graph"]
    try:
        order = dependency_order(graph)
    except ValueError as error:
        findings.append(Finding("CHANGE_GRAPH_INVALID", str(error)))
        order = ()
    if {key: set(value) for key, value in graph.items()} != EXPECTED_DEPENDENCIES:
        findings.append(Finding("DEPENDENCY_PLAN_INCOMPLETE", "The change graph omits or reorders a required dependency."))
    if order and order.index("AI-2500-CONTRACT") > order.index("AI-2500-AI"):
        findings.append(Finding("CONTRACT_NOT_FIRST", "Implementation begins before contract approval."))

    work_units = candidate["work_units"]
    for repository in ("ai-service", "review-service"):
        work_unit = work_units.get(repository, {})
        trusted_work_unit = trusted.trusted_work_units[repository]
        revision = trusted.repositories[repository]
        if work_unit.get("base_commit") != trusted_work_unit["base_commit"]:
            findings.append(Finding("STALE_REPOSITORY_CONTEXT", f"{repository} work is not bound to its baseline commit."))
        if work_unit.get("contract_revision") != trusted_work_unit["contract_revision"]:
            findings.append(Finding("WORK_UNIT_CONTRACT_STALE", f"{repository} does not target contract revision 2."))
        forbidden = set(trusted_work_unit["may_not_decide"])
        if not forbidden <= set(work_unit.get("may_not_decide", [])):
            findings.append(Finding("WORK_UNIT_AUTHORITY_WIDENED", f"{repository} omits protected decisions."))
        changed = set(revision.changed_paths)
        writable = set(trusted_work_unit["writable_paths"])
        if not changed <= writable:
            findings.append(Finding("CROSS_REPOSITORY_SCOPE_EXPANSION", f"{repository} changed paths outside its work unit."))

    if candidate["declared_compatibility"] != dict(trusted.compatibility_matrix):
        findings.append(Finding("COMPATIBILITY_OVERCLAIM", "Declared compatibility differs from executed producer-consumer checks."))
    if candidate["rollout_order"] != EXPECTED_ROLLOUT:
        findings.append(Finding("UNSAFE_DEPLOYMENT_ORDER", "The rollout does not upgrade and verify the tolerant consumer first."))
    if (
        not candidate.get("rollback_compatibility_verified")
        or not trusted.compatibility_matrix["ai-v1/review-v2"]
    ):
        findings.append(Finding("ROLLBACK_COMPATIBILITY_UNVERIFIED", "The recovery path has not proved Review v2 accepts AI v1."))

    manifest = candidate["integration_manifest"]
    if manifest.get("change_id") != "AI-2500" or manifest.get("contract_revision") != 2:
        findings.append(Finding("INTEGRATION_SUBJECT_MISMATCH", "Integration evidence targets a different change or contract."))
    expected_commits = {
        repository: revision.candidate_commit
        for repository, revision in trusted.repositories.items()
    }
    if manifest.get("component_commits") != expected_commits:
        findings.append(Finding("INTEGRATION_MANIFEST_STALE", "The manifest does not pin the exact executed repository commits."))
    if any(len(commit) != 40 for commit in manifest.get("component_commits", {}).values()):
        findings.append(Finding("UNPINNED_COMPONENT_REVISION", "Every integrated repository requires a full Git commit."))

    if candidate["submitted_scenario_results"] != dict(trusted.scenario_results):
        findings.append(Finding("INTEGRATION_REPORT_MISMATCH", "Candidate-reported results differ from trusted execution."))
    failed_scenarios = sorted(name for name, passed in trusted.scenario_results.items() if not passed)
    if failed_scenarios:
        findings.append(Finding("SYSTEM_INTEGRATION_FAILED", f"Failed scenarios: {', '.join(failed_scenarios)}."))

    valid_evidence = False
    for evidence_reference in candidate["evidence_references"]:
        receipt = trusted.evidence_registry.get(evidence_reference)
        if receipt is None:
            findings.append(Finding("UNTRUSTED_INTEGRATION_EVIDENCE", f"Unknown evidence reference {evidence_reference}."))
            continue
        if receipt.contract_revision != 2:
            findings.append(Finding("STALE_CONTRACT_EVIDENCE", "Integration evidence targets an obsolete contract."))
        if dict(receipt.component_commits) != expected_commits:
            findings.append(Finding("STALE_COMPONENT_EVIDENCE", "Integration evidence targets other repository commits."))
        if dict(receipt.scenario_results) != dict(trusted.scenario_results):
            findings.append(Finding("INTEGRATION_REPORT_MISMATCH", "Registry evidence differs from trusted execution."))
        if (
            receipt.contract_revision == 2
            and dict(receipt.component_commits) == expected_commits
            and dict(receipt.scenario_results) == dict(trusted.scenario_results)
        ):
            valid_evidence = True
    if not valid_evidence:
        findings.append(Finding("INTEGRATION_EVIDENCE_MISSING", "No current trusted receipt covers this integration subject."))

    if candidate.get("contract_change_status") == "DIRECTLY_APPLIED":
        findings.append(Finding("CONTRACT_CHANGE_NOT_APPROVED", "A repository agent directly changed the canonical contract."))
    if candidate.get("affected_work_units_invalidated") is not True:
        findings.append(Finding("AFFECTED_WORK_UNITS_NOT_INVALIDATED", "A shared-contract change requires replanning affected work."))
    if candidate.get("local_ci_is_system_evidence") is True:
        findings.append(Finding("LOCAL_CI_TREATED_AS_SYSTEM_EVIDENCE", "Repository-local CI cannot prove the integrated revision set."))
    if candidate.get("release_authorized") is True:
        findings.append(Finding("SELF_AUTHORIZED_RELEASE", "The change package cannot grant production release authority."))

    unique: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (finding.code, finding.message)
        if key not in seen:
            seen.add(key)
            unique.append(finding)
    return Decision("BLOCKED" if unique else "READY_FOR_INTEGRATION_REVIEW", tuple(unique))


def direct_agent_baseline(candidate: dict[str, object]) -> Decision:
    """Unsafe comparison: trust green local-CI declarations as system assurance."""
    return Decision(
        "READY_FOR_INTEGRATION_REVIEW"
        if all(candidate.get("local_ci", {}).values())
        else "BLOCKED"
    )


def evidence_digest(candidate: dict[str, object], trusted: TrustedContext) -> str:
    return canonical_digest(
        {
            "manifest": candidate["integration_manifest"],
            "compatibility": dict(trusted.compatibility_matrix),
            "scenarios": dict(trusted.scenario_results),
        }
    )


def load_json(path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
