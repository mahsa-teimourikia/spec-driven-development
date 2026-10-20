"""Deterministic Course 16 enterprise governance-control-plane lab.

The fixtures are educational. They model trust boundaries and exact identity but
do not authenticate real providers, enforce a sandbox, or authorize production.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REQUIRED_GATES = (
    "registry_integrity",
    "context_resolution",
    "authority_compatibility",
    "instruction_adapter_conformance",
    "execution_authorization",
    "delegation_attenuation",
    "audit_handoff_integrity",
)


class Applicability(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Finding:
    code: str
    subject: str
    message: str
    severity: str = "BLOCK"


@dataclass(frozen=True)
class GateResult:
    gate: str
    status: str
    findings: tuple[Finding, ...]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def finding(code: str, subject: str, message: str, severity: str = "BLOCK") -> Finding:
    return Finding(code=code, subject=subject, message=message, severity=severity)


def _resolve_pointer(document: Any, pointer: str) -> tuple[Any, str]:
    parts = [part.replace("~1", "/").replace("~0", "~") for part in pointer.strip("/").split("/") if part]
    if not parts:
        raise ValueError("patch path must identify a child value")
    current = document
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current, parts[-1]


def apply_patch(document: dict[str, Any], patch: dict[str, Any]) -> None:
    parent, leaf = _resolve_pointer(document, patch["path"])
    operation = patch.get("op", "replace")
    key: str | int = int(leaf) if isinstance(parent, list) else leaf
    if operation == "delete":
        del parent[key]
    elif operation == "append":
        parent[key].append(copy.deepcopy(patch["value"]))
    elif operation == "replace_text":
        parent[key] = parent[key].replace(patch["old"], patch["new"])
    else:
        parent[key] = copy.deepcopy(patch["value"])


def load_control_plane() -> dict[str, Any]:
    return read_json(ROOT / "policy" / "trusted-governance-plane.json")


def _load_adapter_bundle(reference_dir: Path) -> tuple[dict[str, Any], dict[str, str]]:
    manifest = read_json(reference_dir / "instruction-manifest.json")
    adapters = {
        target: (reference_dir / output["path"]).read_text(encoding="utf-8")
        for target, output in manifest["outputs"].items()
    }
    return manifest, adapters


def load_reference() -> dict[str, Any]:
    package = read_json(ROOT / "reference" / "governance-package.json")
    manifest, adapters = _load_adapter_bundle(ROOT / "reference")
    package["_adapter_manifest"] = manifest
    package["_adapters"] = adapters
    return package


def load_candidate() -> dict[str, Any]:
    package = load_reference()
    mutations = read_json(ROOT / "candidate" / "package-patches.json")
    for patch in mutations["patches"]:
        if patch.get("target") == "adapter":
            content_patch = {**patch, "path": f"/_adapters/{patch['adapter']}"}
            content_patch.pop("target", None)
            content_patch.pop("adapter", None)
            apply_patch(package, content_patch)
        else:
            apply_patch(package, patch)
    return package


def load_candidate_control() -> dict[str, Any]:
    control = load_control_plane()
    observations = read_json(ROOT / "candidate" / "trusted-observations.json")
    for patch in observations["control_patches"]:
        apply_patch(control, patch)
    return control


def policy_ref(policy: dict[str, Any]) -> str:
    return f"{policy['id']}@{policy['revision']}"


def policy_payload(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in policy.items()
        if key not in {"digest"}
    }


def registry_payload(control: dict[str, Any]) -> list[dict[str, Any]]:
    return [policy_payload(policy) for policy in control.get("policy_registry", [])]


def validate_registry_integrity(control: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if canonical_digest(registry_payload(control)) != control.get("policy_registry_digest"):
        findings.append(finding("POLICY_REGISTRY_INTEGRITY_FAILURE", "policy-registry", "The protected policy registry digest does not match its canonical records."))
    if canonical_digest(control.get("canonical_agent_rules", [])) != control.get("canonical_agent_rules_digest"):
        findings.append(finding("CANONICAL_RULE_REGISTRY_INTEGRITY_FAILURE", "agent-rule-registry", "The canonical agent-rule digest does not match its records."))
    attestation = control.get("control_plane_attestation", {})
    resolver = control.get("resolver", {})
    compiler = control.get("instruction_compiler", {})
    if (
        not attestation.get("attestation_verified")
        or not attestation.get("protected_workflow")
        or attestation.get("resolver_version") != resolver.get("version")
        or attestation.get("instruction_compiler_version") != compiler.get("version")
    ):
        findings.append(finding("CONTROL_PLANE_ATTESTATION_INVALID", "control-plane", "Trusted execution did not authenticate the protected resolver and instruction compiler revisions."))
    return findings


def _predicate_state(predicate: dict[str, Any], facts: dict[str, Any]) -> Applicability:
    fact_name = predicate["fact"]
    if fact_name not in facts or facts[fact_name] is None:
        return Applicability.UNKNOWN
    observed = facts[fact_name]
    operator = predicate["operator"]
    expected = predicate["value"]
    if operator == "equals":
        if isinstance(expected, bool) and not isinstance(observed, bool):
            return Applicability.UNKNOWN
        if isinstance(expected, str) and not isinstance(observed, str):
            return Applicability.UNKNOWN
        return Applicability.APPLICABLE if observed == expected else Applicability.NOT_APPLICABLE
    if operator == "in":
        if not isinstance(expected, list):
            return Applicability.UNKNOWN
        if expected and all(isinstance(item, str) for item in expected) and not isinstance(observed, str):
            return Applicability.UNKNOWN
        return Applicability.APPLICABLE if observed in expected else Applicability.NOT_APPLICABLE
    return Applicability.UNKNOWN


def resolve_applicability(policy: dict[str, Any], facts: dict[str, Any]) -> Applicability:
    states = [_predicate_state(predicate, facts) for predicate in policy.get("applicability", [])]
    if any(state is Applicability.NOT_APPLICABLE for state in states):
        return Applicability.NOT_APPLICABLE
    if any(state is Applicability.UNKNOWN for state in states):
        return Applicability.UNKNOWN
    return Applicability.APPLICABLE


def resolve_policies(control: dict[str, Any]) -> list[dict[str, Any]]:
    facts = control.get("trusted_subject_facts", {})
    policies = control.get("policy_registry", [])
    by_ref = {policy_ref(policy): policy for policy in policies}
    resolutions: list[dict[str, Any]] = []
    for policy in policies:
        lifecycle = policy.get("status")
        lifecycle_issue: str | None = None
        if lifecycle == "ACTIVE":
            applicability = resolve_applicability(policy, facts)
        elif lifecycle == "SUPERSEDED":
            replacement = by_ref.get(policy.get("superseded_by"))
            if replacement and replacement.get("status") == "ACTIVE":
                applicability = Applicability.NOT_APPLICABLE
            else:
                applicability = Applicability.UNKNOWN
                lifecycle_issue = "POLICY_SUPERSESSION_INVALID"
        elif lifecycle == "WITHDRAWN":
            applicability = Applicability.UNKNOWN
            lifecycle_issue = "POLICY_WITHDRAWN"
        else:
            applicability = Applicability.UNKNOWN
            lifecycle_issue = "POLICY_LIFECYCLE_UNKNOWN"
        resolutions.append({
            "policy_ref": policy_ref(policy),
            "status": applicability.value,
            "lifecycle_status": lifecycle,
            "lifecycle_issue": lifecycle_issue,
            "superseded_by": policy.get("superseded_by"),
            "digest": canonical_digest(policy_payload(policy)),
            "authority_domain": policy["authority_domain"],
            "obligations": copy.deepcopy(policy.get("obligations", [])) if lifecycle == "ACTIVE" else [],
            "protected_decisions": copy.deepcopy(policy.get("protected_decisions", [])) if lifecycle == "ACTIVE" else [],
        })
    return resolutions


def validate_subject(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    trusted = control.get("trusted_subject_facts", {})
    expected = {key: trusted.get(key) for key in ("repository", "change_id", "base_commit")}
    if package.get("subject") != expected:
        return [finding("SOURCE_SUBJECT_MISMATCH", "subject", "The package is not bound to the trusted repository, change, and base commit facts.")]
    source = control.get("source_control", {})
    if (
        not source.get("attestation_verified")
        or source.get("repository") != trusted.get("repository")
        or source.get("base_commit") != trusted.get("base_commit")
    ):
        return [finding("SOURCE_CONTROL_ATTESTATION_INVALID", "source-control", "The source-control provider did not attest the exact repository and base revision.")]
    return []


def _valid_exception_ids(package: dict[str, Any], control: dict[str, Any]) -> tuple[set[str], list[Finding]]:
    findings: list[Finding] = []
    valid: set[str] = set()
    if "exception_assertion" in package:
        findings.append(finding("UNTRUSTED_EXCEPTION_ASSERTION", "exception-assertion", "A change package may reference an exception but cannot assert its approval or validity."))
    facts = control.get("trusted_subject_facts", {})
    policies = {policy_ref(policy): policy for policy in control.get("policy_registry", [])}
    registry = control.get("exception_registry", {})
    condition_evidence = control.get("exception_condition_evidence", {})
    authority = control.get("authority_registry", {}).get("exception_approvers", {})
    for exception_id in package.get("exception_references", []):
        record = registry.get(exception_id)
        if not record:
            findings.append(finding("EXCEPTION_NOT_FOUND", str(exception_id), "The referenced exception is absent from the trusted exception registry."))
            continue
        policy = policies.get(record.get("policy_ref"))
        if not policy:
            findings.append(finding("EXCEPTION_POLICY_UNKNOWN", exception_id, "The exception targets an unknown policy revision."))
            continue
        if record.get("state") != "ACTIVE" or _parse_time(record["expires_at"]) <= _parse_time(control["evaluation_time"]):
            findings.append(finding("EXCEPTION_EXPIRED", exception_id, "The exception is inactive or expired."))
            continue
        scope = record.get("scope", {})
        if scope.get("repository") != facts.get("repository") or scope.get("change_id") != facts.get("change_id"):
            findings.append(finding("EXCEPTION_SCOPE_MISMATCH", exception_id, "The exception does not cover this repository and change."))
            continue
        allowed = set(authority.get(policy["authority_domain"], []))
        approvals = record.get("approvals", [])
        if not approvals or any(
            approval.get("principal") not in allowed
            or not approval.get("identity_verified")
            or not approval.get("attestation_verified")
            for approval in approvals
        ):
            findings.append(finding("EXCEPTION_APPROVAL_INVALID", exception_id, "The exception lacks authenticated approval from the governing authority."))
            continue
        unmet_conditions = []
        for condition in record.get("conditions", []):
            evidence = condition_evidence.get(condition)
            if (
                not evidence
                or evidence.get("exception_id") != exception_id
                or evidence.get("result") != "PASS"
                or not evidence.get("producer_identity_verified")
                or not evidence.get("attestation_verified")
                or _parse_time(evidence.get("valid_until", "1970-01-01T00:00:00Z")) <= _parse_time(control["evaluation_time"])
            ):
                unmet_conditions.append(condition)
        if unmet_conditions:
            findings.append(finding("EXCEPTION_CONDITION_UNSATISFIED", exception_id, "Trusted evidence does not establish current exception conditions: " + ", ".join(sorted(unmet_conditions))))
            continue
        valid.add(exception_id)
    return valid, findings


def _authorized_deviation(
    requirement_id: str,
    key: str,
    project_value: Any,
    policy_ref_value: str,
    policy_value: Any,
    package: dict[str, Any],
    control: dict[str, Any],
    valid_exception_ids: set[str],
) -> bool:
    requested = package.get("requested_policy_deviations", [])
    registry = control.get("exception_registry", {})
    for deviation in requested:
        exception_id = deviation.get("exception_id")
        if (
            exception_id not in valid_exception_ids
            or deviation.get("requirement_id") != requirement_id
            or deviation.get("policy_ref") != policy_ref_value
            or deviation.get("semantic_key") != key
            or deviation.get("from") != policy_value
            or deviation.get("to") != project_value
        ):
            continue
        allowed = registry[exception_id].get("authorized_deviations", [])
        if any(
            item.get("policy_ref") == policy_ref_value
            and item.get("semantic_key") == key
            and item.get("from") == policy_value
            and item.get("to") == project_value
            for item in allowed
        ):
            return True
    return False


def validate_authority_compatibility(
    package: dict[str, Any], control: dict[str, Any], resolutions: list[dict[str, Any]]
) -> list[Finding]:
    valid_exceptions, findings = _valid_exception_ids(package, control)
    relationships = [
        (requirement.get("id", "unknown-requirement"), key, value)
        for requirement in package.get("project_requirements", [])
        for key, value in requirement.get("semantics", {}).items()
    ]
    by_key: dict[str, list[tuple[str, Any]]] = {}
    for requirement_id, key, value in relationships:
        by_key.setdefault(key, []).append((requirement_id, value))
    for key, entries in by_key.items():
        distinct_values = {canonical_digest(value) for _, value in entries}
        if len(distinct_values) > 1:
            subjects = ", ".join(requirement_id for requirement_id, _ in entries)
            findings.append(finding("PROJECT_REQUIREMENT_CONFLICT", key, f"Project requirements {subjects} assign incompatible values to the same semantic key."))
    for resolution in resolutions:
        if resolution["status"] != Applicability.APPLICABLE.value:
            continue
        for obligation in resolution["obligations"]:
            key = obligation["key"]
            for requirement_id, project_key, project_value in relationships:
                if project_key != key or project_value == obligation["value"]:
                    continue
                if not _authorized_deviation(
                    requirement_id,
                    key,
                    project_value,
                    resolution["policy_ref"],
                    obligation["value"],
                    package,
                    control,
                    valid_exceptions,
                ):
                    findings.append(finding("NORMATIVE_AUTHORITY_CONFLICT", requirement_id, f"Project semantic {key}={project_value!r} weakens or contradicts {resolution['policy_ref']} rather than specializing it compatibly."))
    for deviation in package.get("requested_policy_deviations", []):
        exception_id = deviation.get("exception_id")
        matched = _authorized_deviation(
            deviation.get("requirement_id", ""),
            deviation.get("semantic_key", ""),
            deviation.get("to"),
            deviation.get("policy_ref", ""),
            deviation.get("from"),
            package,
            control,
            valid_exceptions,
        )
        if not matched:
            findings.append(finding("EXCEPTION_DEVIATION_NOT_AUTHORIZED", str(exception_id), "A valid exception reference does not authorize an undeclared or mismatched policy deviation."))
    return findings


def compile_effective_context(package: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    resolutions = resolve_policies(control)
    applicable = [item for item in resolutions if item["status"] == Applicability.APPLICABLE.value]
    not_applicable = [item["policy_ref"] for item in resolutions if item["status"] == Applicability.NOT_APPLICABLE.value]
    unresolved = [item["policy_ref"] for item in resolutions if item["status"] == Applicability.UNKNOWN.value]
    protected_decisions = sorted({decision for item in applicable for decision in item["protected_decisions"]})
    core = {
        "id": "CTX-AI-2310@4-training",
        "subject": copy.deepcopy(package.get("subject", {})),
        "sources": [
            {"policy_ref": item["policy_ref"], "digest": item["digest"], "authority_domain": item["authority_domain"]}
            for item in applicable
        ],
        "not_applicable": not_applicable,
        "unresolved": unresolved,
        "protected_decisions": protected_decisions,
        "resolver": copy.deepcopy(control.get("resolver", {})),
    }
    return {**core, "digest": canonical_digest(core), "status": "VALIDATED" if not unresolved else "UNRESOLVED"}


def validate_context_resolution(
    package: dict[str, Any], control: dict[str, Any], context: dict[str, Any]
) -> list[Finding]:
    findings = validate_subject(package, control)
    for unresolved in context.get("unresolved", []):
        findings.append(finding("APPLICABILITY_UNKNOWN", unresolved, "Required applicability facts are missing or unsupported; unknown cannot become not applicable."))
    work_unit = package.get("work_unit", {})
    by_ref = {item["policy_ref"]: item for item in resolve_policies(control)}
    for item in by_ref.values():
        if item.get("lifecycle_issue"):
            findings.append(finding(item["lifecycle_issue"], item["policy_ref"], "Policy lifecycle state cannot safely contribute to the effective context."))
    inactive_dependencies = [
        dependency
        for dependency in work_unit.get("policy_dependencies", [])
        if dependency in by_ref and by_ref[dependency].get("lifecycle_status") != "ACTIVE"
    ]
    if inactive_dependencies:
        findings.append(finding("WORK_UNIT_POLICY_DEPENDENCY_INACTIVE", work_unit.get("id", "work-unit"), "The work unit depends on an inactive policy revision: " + ", ".join(sorted(inactive_dependencies))))
    resolved_refs = {source["policy_ref"] for source in context.get("sources", [])} | set(context.get("not_applicable", [])) | set(context.get("unresolved", []))
    missing = set(work_unit.get("policy_dependencies", [])) - resolved_refs
    if missing:
        findings.append(finding("WORK_UNIT_POLICY_DEPENDENCY_UNRESOLVED", work_unit.get("id", "work-unit"), "The work unit names a policy revision absent from the resolved context: " + ", ".join(sorted(missing))))
    return findings


def _adapter_loading_note(target: str, snapshot: dict[str, Any]) -> str:
    return f"- Target behavior snapshot ({snapshot['verified_on']}): {snapshot['discovery_contract']}."


def compile_adapter(target: str, context: dict[str, Any], control: dict[str, Any]) -> str:
    snapshot = control["compatibility_snapshots"][target]
    compiler = control["instruction_compiler"]
    header = [
        "<!-- GENERATED: do not edit manually.",
        f"compiler: {compiler['id']}@{compiler['version']}",
        f"target: {target}",
        f"effective-context: {context['id']}",
        f"context-digest: {context['digest']}",
        f"canonical-rules-digest: {control['canonical_agent_rules_digest']}",
        f"compatibility-verified-on: {snapshot['verified_on']}",
        "-->",
        "",
        "# Repository agent instructions",
        "",
        "## Source of truth",
        "",
        "- Read the active specification and the effective-context manifest; this file does not own feature semantics or enterprise policy.",
        f"- Effective context: `{context['id']}` with digest `{context['digest']}`.",
        "- Instruction text guides agent behavior. Authenticated identity, sandbox permissions, source-control facts, and trusted gates enforce authority.",
        "",
        "## Canonical operating rules",
        "",
    ]
    rules = [
        f"- [{rule['modality']}][{rule['id']}@{rule['revision']}] {rule['text']}"
        for rule in control.get("canonical_agent_rules", [])
    ]
    footer = [
        "",
        "## Target compatibility",
        "",
        _adapter_loading_note(target, snapshot),
        f"- Enforcement boundary: {snapshot['enforcement_boundary']}.",
        "- Regenerate and review this adapter when the effective context, canonical rules, compiler, or supported tool behavior changes.",
        "",
    ]
    return "\n".join(header + rules + footer)


def compile_all_adapters(context: dict[str, Any], control: dict[str, Any], targets: list[str]) -> dict[str, str]:
    return {target: compile_adapter(target, context, control) for target in targets}


def expected_adapter_manifest(context: dict[str, Any], control: dict[str, Any], adapters: dict[str, str]) -> dict[str, Any]:
    outputs = {
        target: {
            "path": control["compatibility_snapshots"][target]["target_file"],
            "output_digest": canonical_digest(content),
        }
        for target, content in adapters.items()
    }
    core = {
        "fixture_status": "GENERATED_REFERENCE_NOT_RUNTIME_ENFORCEMENT",
        "context_id": context["id"],
        "context_digest": context["digest"],
        "canonical_rules_digest": control["canonical_agent_rules_digest"],
        "compiler": copy.deepcopy(control["instruction_compiler"]),
        "outputs": outputs,
    }
    return {**core, "manifest_digest": canonical_digest(core)}


def validate_instruction_adapters(
    package: dict[str, Any], control: dict[str, Any], context: dict[str, Any]
) -> list[Finding]:
    findings: list[Finding] = []
    request = package.get("instruction_request", {})
    allowed_sources = {"canonical_agent_rules", "effective_context"}
    unexpected_sources = set(request.get("sources", [])) - allowed_sources
    if unexpected_sources:
        findings.append(finding("UNTRUSTED_INSTRUCTION_SOURCE", "instruction-request", "Repository content cannot be promoted into governance authority: " + ", ".join(sorted(unexpected_sources))))
    targets = request.get("targets", [])
    snapshots = control.get("compatibility_snapshots", {})
    required_targets = set(control.get("required_instruction_targets", []))
    missing_targets = required_targets - set(targets)
    if missing_targets:
        findings.append(finding("REQUIRED_INSTRUCTION_TARGET_MISSING", "instruction-request", "Trusted work-unit configuration requires adapters for: " + ", ".join(sorted(missing_targets))))
    if len(targets) != len(set(targets)):
        findings.append(finding("INSTRUCTION_TARGET_DUPLICATE", "instruction-request", "Instruction targets must be unique."))
    unknown_targets = set(targets) - set(snapshots)
    if unknown_targets:
        findings.append(finding("INSTRUCTION_TARGET_UNSUPPORTED", "instruction-request", "No tested adapter contract exists for: " + ", ".join(sorted(unknown_targets))))
        return findings
    actual_adapters = package.get("_adapters", {})
    manifest = package.get("_adapter_manifest", {})
    if set(actual_adapters) != set(targets) or set(manifest.get("outputs", {})) != set(targets):
        findings.append(finding("ADAPTER_TARGET_SET_MISMATCH", "instruction-request", "Requested targets, generated outputs, and manifest outputs must identify the same set."))
    expected_adapters = compile_all_adapters(context, control, targets)
    expected_manifest = expected_adapter_manifest(context, control, expected_adapters)
    if manifest.get("context_digest") != context.get("digest") or manifest.get("canonical_rules_digest") != control.get("canonical_agent_rules_digest"):
        findings.append(finding("AGENT_INSTRUCTION_ADAPTER_STALE", "instruction-manifest", "Generated instructions are bound to stale context or canonical-rule revisions."))
    for target in targets:
        output = manifest.get("outputs", {}).get(target, {})
        actual = actual_adapters.get(target)
        expected = expected_adapters[target]
        if output.get("path") != snapshots[target]["target_file"]:
            findings.append(finding("ADAPTER_TARGET_INVALID", target, "The generated instruction is stored at the wrong target-specific path."))
        if actual is None:
            findings.append(finding("ADAPTER_OUTPUT_MISSING", target, "The requested generated adapter is absent."))
            continue
        if output.get("output_digest") != canonical_digest(actual):
            findings.append(finding("ADAPTER_OUTPUT_DIGEST_INVALID", target, "The manifest digest does not match the checked-in adapter bytes."))
        if actual != expected:
            missing_rules = [
                rule["id"]
                for rule in control.get("canonical_agent_rules", [])
                if f"[{rule['modality']}][{rule['id']}@{rule['revision']}] {rule['text']}" not in actual
            ]
            code = "INSTRUCTION_SEMANTIC_WEAKENING" if missing_rules else "ADAPTER_OUTPUT_MISMATCH"
            findings.append(finding(code, target, "The adapter is not the exact output of the protected compiler" + (f"; missing or weakened rules: {', '.join(missing_rules)}" if missing_rules else ".")))
    manifest_core = {key: copy.deepcopy(value) for key, value in manifest.items() if key != "manifest_digest"}
    if manifest.get("manifest_digest") != canonical_digest(manifest_core) or manifest.get("manifest_digest") != expected_manifest.get("manifest_digest"):
        findings.append(finding("ADAPTER_MANIFEST_DIGEST_INVALID", "instruction-manifest", "The adapter manifest is not canonically bound to the expected compiler output."))
    return findings


def _parse_path_scope(pattern: Any) -> tuple[str, tuple[str, ...]] | None:
    if not isinstance(pattern, str) or not pattern or pattern.startswith(("/", "\\")) or "\\" in pattern:
        return None
    kind = "tree" if pattern.endswith("/**") else "file"
    raw = pattern[:-3] if kind == "tree" else pattern
    if not raw or any(token in raw for token in ("*", "?", "[", "]")):
        return None
    parts = tuple(raw.split("/"))
    if any(not part or part in {".", ".."} for part in parts):
        return None
    return kind, parts


def path_scope_contains(parent: str, child: str) -> bool:
    parent_scope = _parse_path_scope(parent)
    child_scope = _parse_path_scope(child)
    if not parent_scope or not child_scope:
        return False
    parent_kind, parent_parts = parent_scope
    child_kind, child_parts = child_scope
    if parent_kind == "file":
        return child_kind == "file" and child_parts == parent_parts
    return child_parts[:len(parent_parts)] == parent_parts


def _path_allowed(path: str, patterns: list[str]) -> bool:
    return any(path_scope_contains(pattern, path) for pattern in patterns)


def _invalid_path_scopes(patterns: list[Any]) -> list[str]:
    return [str(pattern) for pattern in patterns if _parse_path_scope(pattern) is None]


def _scopes_outside(child_patterns: list[str], parent_patterns: list[str]) -> list[str]:
    return [child for child in child_patterns if not any(path_scope_contains(parent, child) for parent in parent_patterns)]


def validate_execution_authorization(
    package: dict[str, Any], control: dict[str, Any], context: dict[str, Any]
) -> list[Finding]:
    findings: list[Finding] = []
    request = package.get("authorization", {})
    principal = request.get("principal")
    identity = control.get("identity_registry", {}).get(principal)
    if not identity or not identity.get("attestation_verified"):
        findings.append(finding("AGENT_IDENTITY_UNVERIFIED", str(principal), "A role label or package claim is not an authenticated workload identity."))
    grant_id = request.get("grant_id")
    grant = control.get("authorization_grants", {}).get(grant_id)
    if not grant or not grant.get("issuer_identity_verified") or grant.get("state") != "ACTIVE":
        findings.append(finding("AUTHORIZATION_GRANT_INVALID", str(grant_id), "The trusted grant is missing, inactive, or unauthenticated."))
        return findings
    expected_subject = control.get("trusted_subject_facts", {})
    if grant.get("principal") != principal:
        findings.append(finding("AUTHORIZATION_PRINCIPAL_MISMATCH", str(grant_id), "The grant belongs to a different authenticated workload identity."))
    if (
        grant.get("repository") != expected_subject.get("repository")
        or grant.get("change_id") != expected_subject.get("change_id")
        or grant.get("base_commit") != expected_subject.get("base_commit")
        or grant.get("work_unit_id") != package.get("work_unit", {}).get("id")
    ):
        findings.append(finding("AUTHORIZATION_SUBJECT_MISMATCH", str(grant_id), "The grant is not bound to the exact repository, change, base, and work unit."))
    if grant.get("context_digest") != context.get("digest"):
        findings.append(finding("AUTHORIZATION_CONTEXT_MISMATCH", str(grant_id), "The grant is bound to a different effective governance context."))
    if _parse_time(grant["expires_at"]) <= _parse_time(control["evaluation_time"]):
        findings.append(finding("AUTHORIZATION_GRANT_EXPIRED", str(grant_id), "The work-unit grant expired before evaluation."))
    grant_read_paths = grant.get("readable_paths", [])
    grant_write_paths = grant.get("writable_paths", [])
    invalid_grant_paths = _invalid_path_scopes(grant_read_paths + grant_write_paths)
    if invalid_grant_paths:
        findings.append(finding("AUTHORIZATION_PATH_SCOPE_INVALID", str(grant_id), "The trusted grant contains unsupported or ambiguous path scopes: " + ", ".join(invalid_grant_paths)))
    requested = request.get("requested_permissions")
    if not isinstance(requested, dict):
        findings.append(finding("EXECUTION_PERMISSION_REQUEST_MISSING", str(grant_id), "Dispatch must declare requested capabilities plus read and write resource scopes."))
        requested = {}
    requested_capabilities = set(requested.get("capabilities", []))
    requested_read_paths = requested.get("read_paths", [])
    requested_write_paths = requested.get("write_paths", [])
    invalid_requested_paths = _invalid_path_scopes(requested_read_paths + requested_write_paths)
    if invalid_requested_paths:
        findings.append(finding("EXECUTION_PATH_SCOPE_INVALID", str(grant_id), "The dispatch request contains unsupported or ambiguous path scopes: " + ", ".join(invalid_requested_paths)))
    outside_capabilities = requested_capabilities - set(grant.get("capabilities", []))
    outside_read = _scopes_outside(requested_read_paths, grant_read_paths)
    outside_write = _scopes_outside(requested_write_paths, grant_write_paths)
    if outside_capabilities or outside_read or outside_write:
        findings.append(finding("REQUESTED_AUTHORITY_EXCEEDS_GRANT", str(grant_id), "Requested execution capabilities or resources exceed the trusted grant."))
    source = control.get("source_control", {})
    if not source.get("attestation_verified"):
        findings.append(finding("SOURCE_CONTROL_ATTESTATION_INVALID", "source-control", "Changed paths were not attested by the Git provider."))
    outside = [path for path in source.get("changed_paths", []) if not _path_allowed(path, grant_write_paths)]
    if outside:
        findings.append(finding("WORK_UNIT_SCOPE_VIOLATION", str(grant_id), "The authoritative diff crosses the enforced work-unit boundary: " + ", ".join(outside)))
    outside_request = [path for path in source.get("changed_paths", []) if not _path_allowed(path, requested_write_paths)]
    if outside_request:
        findings.append(finding("REQUESTED_WRITE_SCOPE_MISMATCH", str(grant_id), "The authoritative diff crosses the dispatch request's declared write scope: " + ", ".join(outside_request)))
    return findings


def validate_delegation(package: dict[str, Any], control: dict[str, Any]) -> list[Finding]:
    delegation = package.get("delegation")
    if not delegation:
        return []
    findings: list[Finding] = []
    parent_principal = delegation.get("parent_principal")
    child_principal = delegation.get("child_principal")
    child_identity = control.get("identity_registry", {}).get(child_principal)
    if not child_identity or not child_identity.get("attestation_verified"):
        findings.append(finding("DELEGATE_IDENTITY_UNVERIFIED", str(child_principal), "The delegated worker lacks an authenticated workload identity."))
    grant_id = package.get("authorization", {}).get("grant_id")
    grant = control.get("authorization_grants", {}).get(grant_id, {})
    if parent_principal != grant.get("principal") or not grant.get("may_delegate"):
        findings.append(finding("DELEGATION_NOT_AUTHORIZED", str(grant_id), "The parent identity or grant does not authorize delegation."))
    permissions = delegation.get("permissions", {})
    parent_capabilities = set(grant.get("capabilities", []))
    child_capabilities = set(permissions.get("capabilities", []))
    child_read_paths = permissions.get("read_paths", [])
    child_write_paths = permissions.get("write_paths", [])
    parent_read_paths = grant.get("readable_paths", [])
    parent_write_paths = grant.get("writable_paths", [])
    invalid_paths = _invalid_path_scopes(parent_read_paths + parent_write_paths + child_read_paths + child_write_paths)
    if invalid_paths:
        findings.append(finding("DELEGATION_PATH_SCOPE_INVALID", str(child_principal), "Delegation uses unsupported or ambiguous path patterns: " + ", ".join(invalid_paths)))
    expanded_read = _scopes_outside(child_read_paths, parent_read_paths)
    expanded_write = _scopes_outside(child_write_paths, parent_write_paths)
    if not child_capabilities.issubset(parent_capabilities) or expanded_read or expanded_write:
        findings.append(finding("DELEGATION_AUTHORITY_AMPLIFICATION", str(child_principal), "Delegation may attenuate authority but cannot add capabilities, readable paths, or writable paths."))
    if delegation.get("depth", 0) > grant.get("max_delegation_depth", 0):
        findings.append(finding("DELEGATION_DEPTH_EXCEEDED", str(child_principal), "Delegation exceeds the authorized depth."))
    if _parse_time(delegation["expires_at"]) > _parse_time(grant["expires_at"]):
        findings.append(finding("DELEGATION_EXPIRY_EXCEEDS_PARENT", str(child_principal), "A child grant cannot outlive its parent grant."))
    return findings


def _gate(name: str, findings: list[Finding]) -> GateResult:
    return GateResult(name, "BLOCK" if any(item.severity == "BLOCK" for item in findings) else "PASS", tuple(findings))


def adapter_manifest_digest(package: dict[str, Any]) -> str | None:
    return package.get("_adapter_manifest", {}).get("manifest_digest")


def validate_audit_handoff(
    package: dict[str, Any], control: dict[str, Any], context: dict[str, Any], upstream: list[GateResult]
) -> list[Finding]:
    findings: list[Finding] = []
    attestation = control.get("control_plane_attestation", {})
    contract = control.get("delivery_handoff_contract", {})
    if not attestation.get("attestation_verified") or attestation.get("workload_identity") != contract.get("producer"):
        findings.append(finding("AUDIT_PRODUCER_UNTRUSTED", "audit", "The policy decision producer is not the authenticated control-plane workload."))
    handoff = package.get("delivery_handoff", {})
    if handoff.get("requested"):
        failed = [gate.gate for gate in upstream if gate.status != "PASS"]
        if failed:
            findings.append(finding("HANDOFF_PREREQUISITE_FAILED", "delivery-handoff", "A delivery handoff cannot bypass failed governance gates: " + ", ".join(failed)))
        if handoff.get("context_digest") != context.get("digest") or handoff.get("adapter_manifest_digest") != adapter_manifest_digest(package):
            findings.append(finding("DELIVERY_HANDOFF_SUBJECT_MISMATCH", "delivery-handoff", "The handoff is not bound to the exact context and adapter manifest."))
    return findings


def evaluate_governance(package: dict[str, Any], control: dict[str, Any] | None = None) -> tuple[list[GateResult], dict[str, Any]]:
    trusted = control or load_control_plane()
    context = compile_effective_context(package, trusted)
    resolutions = resolve_policies(trusted)
    gates = [
        _gate("registry_integrity", validate_registry_integrity(trusted)),
        _gate("context_resolution", validate_context_resolution(package, trusted, context)),
        _gate("authority_compatibility", validate_authority_compatibility(package, trusted, resolutions)),
        _gate("instruction_adapter_conformance", validate_instruction_adapters(package, trusted, context)),
        _gate("execution_authorization", validate_execution_authorization(package, trusted, context)),
        _gate("delegation_attenuation", validate_delegation(package, trusted)),
    ]
    gates.append(_gate("audit_handoff_integrity", validate_audit_handoff(package, trusted, context, gates)))
    if tuple(gate.gate for gate in gates) != REQUIRED_GATES:
        raise AssertionError("gate inventory changed")
    context["status"] = "VALIDATED" if all(gate.status == "PASS" for gate in gates[:3]) else "BLOCKED"
    return gates, context


def aggregate(gates: list[GateResult]) -> str:
    if tuple(gate.gate for gate in gates) != REQUIRED_GATES:
        return "BLOCKED_INCOMPLETE_GATE_SET"
    return "ELIGIBLE_FOR_AGENT_DISPATCH" if all(gate.status == "PASS" for gate in gates) else "BLOCKED"


def finding_codes(gates: list[GateResult]) -> set[str]:
    return {item.code for gate in gates for item in gate.findings}


def build_policy_decision(package: dict[str, Any], control: dict[str, Any] | None = None) -> dict[str, Any]:
    trusted = control or load_control_plane()
    gates, context = evaluate_governance(package, trusted)
    result = aggregate(gates)
    core = {
        "decision_id": "PDP-AI2310-017-training",
        "subject": {
            **copy.deepcopy(package.get("subject", {})),
            "head_commit": trusted.get("source_control", {}).get("head_commit"),
            "context_digest": context["digest"],
            "adapter_manifest_digest": adapter_manifest_digest(package),
        },
        "action": "agent_dispatch",
        "policy": {"id": "SDD-AGENT-DISPATCH", "revision": 3},
        "result": result,
        "reason_codes": sorted(finding_codes(gates)),
        "producer": trusted.get("control_plane_attestation", {}).get("workload_identity"),
        "evaluated_at": trusted.get("evaluation_time"),
    }
    return {**core, "decision_digest": canonical_digest(core)}


def build_delivery_handoff(package: dict[str, Any], control: dict[str, Any] | None = None) -> dict[str, Any]:
    trusted = control or load_control_plane()
    decision = build_policy_decision(package, trusted)
    if decision["result"] != "ELIGIBLE_FOR_AGENT_DISPATCH":
        raise ValueError("HANDOFF_PREREQUISITE_FAILED")
    core = {
        "target": trusted["delivery_handoff_contract"]["target"],
        "state": "ELIGIBLE_FOR_DELIVERY_REVIEW",
        "governance_decision_digest": decision["decision_digest"],
        "context_digest": decision["subject"]["context_digest"],
        "adapter_manifest_digest": decision["subject"]["adapter_manifest_digest"],
        "source_commit": trusted["source_control"]["head_commit"],
        "producer": decision["producer"],
    }
    return {**core, "handoff_digest": canonical_digest(core)}


def assess_policy_change(
    old_policy: dict[str, Any], new_policy: dict[str, Any], work_unit: dict[str, Any]
) -> dict[str, Any]:
    old_ref = policy_ref(old_policy)
    dependencies = set(work_unit.get("policy_dependencies", []))
    if old_ref not in dependencies:
        return {"decision": "CONTINUE", "reason": "policy_not_in_work_unit_dependency_set"}
    if new_policy.get("status") != "ACTIVE":
        return {"decision": "CANCEL", "reason": "governing_policy_no_longer_authorizes_current_work"}
    authority_fields = (
        "id",
        "authority_domain",
        "owner",
        "applicability",
        "obligations",
        "protected_decisions",
        "scope",
        "exception_policy",
    )
    changed_fields = [field for field in authority_fields if old_policy.get(field) != new_policy.get(field)]
    if changed_fields:
        return {"decision": "PAUSE_AND_REVALIDATE", "reason": "authority_context_changed", "changed_fields": changed_fields}
    if old_policy.get("revision") != new_policy.get("revision"):
        return {"decision": "PAUSE_AND_REVALIDATE", "reason": "governing_policy_revision_changed", "changed_fields": ["revision"]}
    return {"decision": "CONTINUE", "reason": "revision_does_not_change_relevant_semantics"}


def _case_state(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    package = load_reference()
    control = load_control_plane()
    for patch in case.get("patches", []):
        target = patch.get("target", "package")
        if target == "control":
            apply_patch(control, patch)
        elif target == "adapter":
            adapter_patch = {**patch, "path": f"/_adapters/{patch['adapter']}"}
            adapter_patch.pop("target", None)
            adapter_patch.pop("adapter", None)
            apply_patch(package, adapter_patch)
        else:
            apply_patch(package, patch)
    return package, control


def classify_scenario(case: dict[str, Any]) -> str:
    package, control = _case_state(case)
    gates, _ = evaluate_governance(package, control)
    codes = finding_codes(gates)
    return case["expected"] if case["expected"] in codes else "UNDETECTED"


def run_conformance_suite() -> dict[str, Any]:
    suite = read_json(ROOT / "conformance-suite.json")
    passed = sum(classify_scenario(case) == case["expected"] for case in suite["cases"])
    return {"passed": passed, "total": len(suite["cases"]), "claim": suite["claim"]}


def _expanded_evaluation_cases() -> list[dict[str, Any]]:
    specification = read_json(ROOT / "evaluation-cases.json")
    cases: list[dict[str, Any]] = []
    for family in specification["families"]:
        for index, variant in enumerate(family["variants"], start=1):
            patch = copy.deepcopy(family["patch"])
            for key in ("path", "op", "old", "new", "value"):
                if key in variant:
                    patch[key] = copy.deepcopy(variant[key])
            cases.append({
                "id": f"{family['id']}-{index}",
                "patches": copy.deepcopy(family.get("setup_patches", [])) + [patch],
                "expected": family["expected"],
            })
    return cases


def mutation_findings(case: dict[str, Any]) -> set[str]:
    package, control = _case_state(case)
    gates, _ = evaluate_governance(package, control)
    return finding_codes(gates)


def run_evaluation() -> dict[str, Any]:
    cases = _expanded_evaluation_cases()
    passed = sum(case["expected"] in mutation_findings(case) for case in cases)
    return {
        "passed": passed,
        "total": len(cases),
        "claim": "labelled fixture mutation coverage, not general policy-engine or agent-compliance accuracy",
    }


def serialize_gates(gates: list[GateResult]) -> list[dict[str, Any]]:
    return [
        {"gate": gate.gate, "status": gate.status, "findings": [asdict(item) for item in gate.findings]}
        for gate in gates
    ]


def main() -> None:
    reference = load_reference()
    reference_control = load_control_plane()
    reference_gates, reference_context = evaluate_governance(reference, reference_control)
    unsafe = load_candidate()
    unsafe_gates, _ = evaluate_governance(unsafe, load_candidate_control())
    old_policy = reference_control["policy_registry"][0]
    changed_policy = copy.deepcopy(old_policy)
    changed_policy["revision"] = 8
    changed_policy["obligations"][0]["value"] = "required_with_reason_code"
    report = {
        "thesis": "Agents consume governed context and propose work; trusted systems resolve, authorize, enforce, and audit.",
        "reference": {
            "decision": aggregate(reference_gates),
            "context": reference_context,
            "gates": serialize_gates(reference_gates),
            "policy_decision": build_policy_decision(reference, reference_control),
        },
        "unsafe_candidate": {
            "decision": aggregate(unsafe_gates),
            "findings": sorted(finding_codes(unsafe_gates)),
        },
        "policy_change": assess_policy_change(old_policy, changed_policy, reference["work_unit"]),
        "conformance": run_conformance_suite(),
        "evaluation": run_evaluation(),
        "evidence_boundary": "deterministic trusted fixtures demonstrate control relationships; they are not authenticated production services or proof of future agent behavior",
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
