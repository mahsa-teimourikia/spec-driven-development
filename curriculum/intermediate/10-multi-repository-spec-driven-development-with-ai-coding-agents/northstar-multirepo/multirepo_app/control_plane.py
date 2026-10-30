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
ALLOWED_DISPOSITIONS = {
    "CHANGED",
    "UNCHANGED_DEPENDENCY",
    "EXTERNAL_DEPENDENCY",
    "NOT_APPLICABLE",
}


def _evidence_passes(reference: str, trusted: TrustedContext) -> bool:
    category, separator, identifier = reference.partition(":")
    if not separator:
        return False
    if category == "scenario":
        return trusted.scenario_results.get(identifier) is True
    if category == "compatibility":
        return trusted.compatibility_matrix.get(identifier) is True
    if category == "local-ci":
        return trusted.local_ci_results.get(identifier) is True
    return False


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

    candidate_dispositions = candidate.get("repository_dispositions", {})
    dispositions = dict(trusted.repository_dispositions)
    if candidate_dispositions != dispositions:
        findings.append(Finding("REPOSITORY_DISPOSITION_DRIFT", "Repository dispositions differ from the protected impact analysis."))
    if set(candidate_dispositions) != set(trusted.repositories):
        findings.append(Finding("REPOSITORY_DISPOSITION_INCOMPLETE", "Every repository requires an explicit change disposition."))
    work_units = candidate["work_units"]
    for repository, revision in trusted.repositories.items():
        disposition = dispositions.get(repository, {})
        disposition_name = disposition.get("disposition")
        if disposition_name not in ALLOWED_DISPOSITIONS:
            findings.append(Finding("REPOSITORY_DISPOSITION_INVALID", f"{repository} has no valid disposition."))
            continue
        changed = set(revision.changed_paths)
        if disposition_name == "CHANGED" and repository not in trusted.trusted_work_units:
            findings.append(Finding("CHANGED_REPOSITORY_WITHOUT_WORK_UNIT", f"{repository} is changed without a trusted work unit."))
        if disposition_name != "CHANGED" and changed:
            findings.append(Finding("DISPOSITION_DIFF_CONFLICT", f"{repository} is declared unchanged but has an executable diff."))
        if disposition_name == "UNCHANGED_DEPENDENCY":
            evidence = disposition.get("compatibility_evidence", [])
            if not evidence or not all(trusted.scenario_results.get(item) is True for item in evidence):
                findings.append(Finding("UNCHANGED_DEPENDENCY_UNVERIFIED", f"{repository} lacks passing compatibility evidence."))

    for repository in sorted(trusted.trusted_work_units):
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

    if candidate.get("local_ci") != dict(trusted.local_ci_results):
        findings.append(Finding("LOCAL_CI_REPORT_MISMATCH", "Repository CI claims differ from executed repository tests."))
    failed_local = sorted(name for name, passed in trusted.local_ci_results.items() if not passed)
    if failed_local:
        findings.append(Finding("REPOSITORY_LOCAL_CI_FAILED", f"Failed repository tests: {', '.join(failed_local)}."))

    if candidate["declared_compatibility"] != dict(trusted.compatibility_matrix):
        findings.append(Finding("COMPATIBILITY_OVERCLAIM", "Declared compatibility differs from executed producer-consumer checks."))
    if candidate["rollout_order"] != EXPECTED_ROLLOUT:
        findings.append(Finding("UNSAFE_DEPLOYMENT_ORDER", "The rollout does not upgrade and verify the tolerant consumer first."))
    rollout = candidate.get("rollout_transitions", {})
    transitions = rollout.get("transitions", [])
    protected_transitions = trusted.rollout_policy.get("transitions", [])
    if [item.get("id") for item in transitions] != EXPECTED_ROLLOUT:
        findings.append(Finding("ROLLOUT_TRANSITIONS_INCOMPLETE", "Observed rollout transitions do not match the approved sequence."))
    completed: set[str] = set()
    for index, transition in enumerate(transitions):
        transition_id = transition.get("id", "unknown")
        if index >= len(protected_transitions):
            findings.append(Finding("ROLLOUT_POLICY_DRIFT", f"{transition_id} is not an approved transition."))
            continue
        protected_transition = protected_transitions[index]
        for field in ("id", "prerequisites", "evidence"):
            if transition.get(field) != protected_transition.get(field):
                findings.append(Finding("ROLLOUT_POLICY_DRIFT", f"{transition_id} changes protected {field}."))
        prerequisites = set(transition.get("prerequisites", []))
        if not prerequisites <= completed:
            findings.append(Finding("ROLLOUT_PREREQUISITE_MISSING", f"{transition_id} ran before its prerequisites completed."))
        evidence = transition.get("evidence", [])
        if not evidence or not all(_evidence_passes(item, trusted) for item in evidence):
            findings.append(Finding("ROLLOUT_EVIDENCE_FAILED", f"{transition_id} lacks passing observed evidence."))
        expected_status = (
            "READY_FOR_ACCOUNTABLE_APPROVAL"
            if transition_id == "enable-bounded-traffic"
            else "SUCCEEDED"
        )
        if transition.get("observed_status") != expected_status:
            findings.append(Finding("ROLLOUT_TRANSITION_FAILED", f"{transition_id} did not succeed."))
        if not any(
            finding.message.startswith(transition_id)
            for finding in findings
            if finding.code.startswith("ROLLOUT_")
        ):
            completed.add(transition_id)
    activation = rollout.get("activation_controls", {})
    protected_activation = trusted.rollout_policy.get("activation_controls", {})
    if set(activation) != set(protected_activation):
        findings.append(Finding("ROLLOUT_POLICY_DRIFT", "Activation controls differ from the protected rollout policy."))
    if (
        not activation.get("new_behavior_disable_control_verified")
        or not activation.get("queued_work_compatible_or_quarantined")
    ):
        findings.append(Finding("ACTIVATION_PREREQUISITE_MISSING", "Bounded traffic cannot start without disable and queued-work controls."))
    if activation.get("activation_authorized") is True:
        findings.append(Finding("SELF_AUTHORIZED_ACTIVATION", "The integration package cannot authorize traffic activation."))
    if (
        not candidate.get("rollback_compatibility_verified")
        or not trusted.compatibility_matrix["ai-v1/review-v2"]
    ):
        findings.append(Finding("ROLLBACK_COMPATIBILITY_UNVERIFIED", "The recovery path has not proved Review v2 accepts AI v1."))

    manifest = candidate["integration_manifest"]
    if manifest.get("change_id") != "AI-2500" or manifest.get("contract_revision") != 2:
        findings.append(Finding("INTEGRATION_SUBJECT_MISMATCH", "Integration evidence targets a different change or contract."))
    expected_contract_digest = canonical_digest(dict(trusted.canonical_contract))
    if manifest.get("contract_digest") != expected_contract_digest:
        findings.append(Finding("INTEGRATION_CONTRACT_DIGEST_MISMATCH", "The manifest is not bound to the executed canonical contract."))
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

    requirement_evidence = trusted.requirement_evidence
    if set(requirement_evidence) != required_ids:
        findings.append(Finding("REQUIREMENT_EVIDENCE_INCOMPLETE", "Every parent requirement requires an executable verification obligation."))
    failed_requirements = sorted(
        requirement_id
        for requirement_id, evidence in requirement_evidence.items()
        if evidence.get("passed") is not True
    )
    if failed_requirements:
        findings.append(Finding("REQUIREMENT_CONFORMANCE_FAILED", f"Failed requirements: {', '.join(failed_requirements)}."))
    for requirement_id, evidence in requirement_evidence.items():
        allocated_boundaries = {
            str(child.get("repository", "")).rsplit("/", 1)[-1]
            for child in child_specs.values()
            if requirement_id in child.get("implements", [])
        }
        if set(evidence.get("implementation_boundaries", [])) != allocated_boundaries:
            findings.append(Finding("REQUIREMENT_BOUNDARY_MISMATCH", f"{requirement_id} evidence does not cover its allocated implementation boundaries."))

    valid_evidence = False
    for evidence_reference in candidate["evidence_references"]:
        receipt = trusted.evidence_registry.get(evidence_reference)
        if receipt is None:
            findings.append(Finding("UNTRUSTED_INTEGRATION_EVIDENCE", f"Unknown evidence reference {evidence_reference}."))
            continue
        if receipt.contract_revision != 2:
            findings.append(Finding("STALE_CONTRACT_EVIDENCE", "Integration evidence targets an obsolete contract."))
        if receipt.contract_digest != expected_contract_digest:
            findings.append(Finding("STALE_CONTRACT_EVIDENCE", "Integration evidence has a different contract digest."))
        if dict(receipt.component_commits) != expected_commits:
            findings.append(Finding("STALE_COMPONENT_EVIDENCE", "Integration evidence targets other repository commits."))
        if dict(receipt.scenario_results) != dict(trusted.scenario_results):
            findings.append(Finding("INTEGRATION_REPORT_MISMATCH", "Registry evidence differs from trusted execution."))
        if dict(receipt.compatibility_results) != dict(trusted.compatibility_matrix):
            findings.append(Finding("INTEGRATION_REPORT_MISMATCH", "Registry compatibility evidence differs from trusted execution."))
        expected_claim_coverage = {
            requirement_id: tuple(evidence["test_ids"])
            for requirement_id, evidence in requirement_evidence.items()
        }
        if dict(receipt.claim_coverage) != expected_claim_coverage:
            findings.append(Finding("REQUIREMENT_EVIDENCE_INCOMPLETE", "The receipt does not bind parent requirements to executed tests."))
        if manifest.get("result_artifact_digest") != receipt.result_artifact_digest:
            findings.append(Finding("RESULT_ARTIFACT_DIGEST_MISMATCH", "The manifest does not identify the executed result artifact."))
        if (
            receipt.contract_revision == 2
            and receipt.contract_digest == expected_contract_digest
            and dict(receipt.component_commits) == expected_commits
            and dict(receipt.scenario_results) == dict(trusted.scenario_results)
            and dict(receipt.compatibility_results) == dict(trusted.compatibility_matrix)
            and dict(receipt.claim_coverage) == expected_claim_coverage
            and manifest.get("result_artifact_digest") == receipt.result_artifact_digest
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
