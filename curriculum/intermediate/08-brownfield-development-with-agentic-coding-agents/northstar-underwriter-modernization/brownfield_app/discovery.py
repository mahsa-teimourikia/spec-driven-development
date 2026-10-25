"""Repository/runtime discovery and behavior-disposition validation."""

from __future__ import annotations

from .contracts import BehaviorRecord, Decision, Finding, RegressionPlan


REQUIRED_DISCOVERY_EVIDENCE = {"STATIC", "RUNTIME", "CONTRACT", "OWNER"}


def validate_discovery_manifest(
    manifest: dict[str, object],
    *,
    actual_repository_revision: str,
    trusted_dependency_evidence: dict[str, object] | None = None,
) -> Decision:
    findings: list[Finding] = []
    revision = manifest.get("repository_revision")
    if revision != actual_repository_revision:
        findings.append(Finding("STALE_REPOSITORY_REVISION", "Discovery is not bound to the current commit."))

    inspected = manifest.get("inspected_paths", [])
    if not isinstance(inspected, list) or not inspected:
        findings.append(Finding("NO_INSPECTED_PATHS", "Discovery must name inspected paths."))

    for item in manifest.get("findings", []):
        if not isinstance(item, dict):
            findings.append(Finding("INVALID_FINDING", "Discovery finding is not structured."))
            continue
        if item.get("confidence") not in {"CONFIRMED", "PARTIAL", "UNKNOWN"}:
            findings.append(Finding("INVALID_CONFIDENCE", f"{item.get('id')} lacks calibrated confidence."))
        provenance = set(item.get("provenance", []))
        if not provenance:
            findings.append(Finding("MISSING_PROVENANCE", f"{item.get('id')} has no evidence provenance."))

    if trusted_dependency_evidence is not None:
        claimed_consumers: set[str] = set()
        for item in manifest.get("findings", []):
            if not isinstance(item, dict):
                continue
            consumers = item.get("consumers", [])
            if isinstance(consumers, list):
                claimed_consumers.update(str(consumer) for consumer in consumers)
            if item.get("type") == "EXTERNAL_CONSUMER" and item.get("subject"):
                claimed_consumers.add(str(item["subject"]))

        independently_observed: dict[str, set[str]] = {}
        for observation in trusted_dependency_evidence.get("observations", []):
            if not isinstance(observation, dict):
                continue
            source = str(observation.get("source", ""))
            for consumer in observation.get("consumers", []):
                independently_observed.setdefault(str(consumer), set()).add(source)

        for consumer, sources in independently_observed.items():
            if consumer not in claimed_consumers:
                findings.append(
                    Finding(
                        "INCOMPLETE_IMPACT_GRAPH",
                        f"{consumer} exists in independent dependency evidence but not the discovery manifest.",
                    )
                )
            elif len(sources) < 2:
                findings.append(
                    Finding(
                        "UNVERIFIED_RELATIONSHIP",
                        f"{consumer} has only one independent evidence source and remains UNKNOWN.",
                        "REVIEW",
                    )
                )

    if manifest.get("unverified_external_consumer") and "Q-DISC-001" not in manifest.get("open_questions", []):
        findings.append(Finding("HIDDEN_UNKNOWN", "Unverified consumer must remain an open question."))
    if any(item.severity == "BLOCK" for item in findings):
        return Decision("BLOCKED", tuple(findings))
    return Decision("REVIEW_REQUIRED" if findings else "PASS", tuple(findings))


def validate_behavior_records(records: list[BehaviorRecord]) -> Decision:
    findings: list[Finding] = []
    for record in records:
        if record.disposition == "UNKNOWN":
            findings.append(Finding("UNKNOWN_BEHAVIOR", f"{record.behavior_id} needs an owner decision."))
        if record.disposition in {"PRESERVE", "MODIFY", "RETIRE", "DEFECT"} and not record.owner:
            findings.append(Finding("MISSING_OWNER", f"{record.behavior_id} has no accountable owner."))
        if record.disposition in {"PRESERVE", "MODIFY", "RETIRE"} and not record.requirement_id:
            findings.append(Finding("MISSING_REQUIREMENT", f"{record.behavior_id} has no normative basis."))
        if not record.evidence:
            findings.append(Finding("MISSING_BEHAVIOR_EVIDENCE", f"{record.behavior_id} has no evidence."))
    return Decision("BLOCKED" if findings else "PASS", tuple(findings))


def required_regression_tests(
    *,
    impacted_consumers: set[str],
    mapped_tests: dict[str, set[str]],
    protected_tests: set[str],
    critical_consumers: set[str] | None = None,
) -> RegressionPlan:
    """Select tests and expose every consumer without a verification path."""
    selected = set(protected_tests)
    selected.update(mapped_tests.get("CHANGED_COMPONENT", set()))
    unmapped: set[str] = set()
    for consumer in impacted_consumers:
        tests = mapped_tests.get(consumer, set())
        if tests:
            selected.update(tests)
        else:
            unmapped.add(consumer)
    critical = impacted_consumers if critical_consumers is None else critical_consumers
    if unmapped & critical:
        state = "BLOCKED"
    elif unmapped:
        state = "REVIEW_REQUIRED"
    else:
        state = "PASS"
    return RegressionPlan(frozenset(selected), frozenset(unmapped), state)
