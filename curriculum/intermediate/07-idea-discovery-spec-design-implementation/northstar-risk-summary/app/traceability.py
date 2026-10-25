"""Semantic checks for requirement-to-evidence traceability."""

from __future__ import annotations

from collections.abc import Collection


def validate_traceability(
    traceability: dict[str, object],
    requirements: dict[str, object],
    acceptance: dict[str, object],
    work_units: dict[str, object],
    evidence_manifest: dict[str, object],
    known_tests: Collection[str],
) -> tuple[str, ...]:
    findings: set[str] = set()
    requirement_rows = {item["id"]: item for item in requirements["requirements"]}
    acceptance_rows = {item["id"]: item for item in acceptance["acceptance"]}
    work_unit_rows = {item["id"]: item for item in work_units["work_units"]}
    evidence_rows = {item["id"]: item for item in evidence_manifest["evidence"]}
    links = {item["requirement"]: item for item in traceability["links"]}

    if traceability.get("specification_revision") != requirements.get("revision"):
        findings.add("STALE_REQUIREMENT_REVISION")
    if evidence_manifest.get("subject", {}).get("specification_revision") != requirements.get("revision"):
        findings.add("STALE_EVIDENCE_REVISION")
    if set(links) != set(requirement_rows):
        findings.add("REQUIREMENT_COVERAGE_INCOMPLETE")

    for requirement_id, link in links.items():
        if requirement_id not in requirement_rows:
            findings.add("UNKNOWN_REQUIREMENT_ID")
            continue
        for test_id in link.get("tests", []):
            if test_id not in known_tests:
                findings.add("UNKNOWN_TEST_ID")
        for acceptance_id in link.get("acceptance", []):
            criterion = acceptance_rows.get(acceptance_id)
            if criterion is None:
                findings.add("UNKNOWN_ACCEPTANCE_CRITERION")
            elif requirement_id not in criterion.get("requirements", []):
                findings.add("UNRELATED_ACCEPTANCE_CRITERION")
        for work_unit_id in link.get("work_units", []):
            work_unit = work_unit_rows.get(work_unit_id)
            if work_unit is None:
                findings.add("UNKNOWN_WORK_UNIT")
            elif requirement_id not in work_unit.get("requirements", []):
                findings.add("WORK_UNIT_REQUIREMENT_MISMATCH")
        for evidence_id in link.get("evidence", []):
            record = evidence_rows.get(evidence_id)
            if record is None:
                findings.add("UNKNOWN_EVIDENCE_ID")
            elif requirement_id not in record.get("criterion_ids", []):
                findings.add("EVIDENCE_SUBJECT_MISMATCH")

    return tuple(sorted(findings))

