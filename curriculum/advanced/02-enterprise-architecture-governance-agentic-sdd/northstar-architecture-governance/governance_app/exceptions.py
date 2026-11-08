"""Exact-scope, signed, expiring architecture-exception validation."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import ArchitectureError, Finding, Observation
from .registry import digest_payload, parse_time, verify_signature


def exception_subject_digest(observation: Observation, finding: Finding) -> str:
    resource_digest = observation.file_digests.get(finding.resource, "missing")
    return digest_payload(
        {
            "environment": observation.environment,
            "policy_version": observation.policy_version,
            "resource": finding.resource,
            "resource_digest": resource_digest,
            "rule_id": finding.rule_id,
        }
    )


def _control_evidence_valid(
    control: dict[str, Any],
    records: Iterable[dict[str, Any]],
    exception_payload: dict[str, Any],
    observation: Observation,
    now: str,
    producer: str,
    verification_key: str,
) -> bool:
    expected = {
        "evidence_id": control.get("evidence_id"),
        "producer": producer,
        "control": control.get("control"),
        "exception_id": exception_payload.get("exception_id"),
        "rule_id": exception_payload.get("rule_id"),
        "resource": exception_payload.get("resource"),
        "environment": observation.environment,
        "approved_subject_digest": exception_payload.get("approved_subject_digest"),
        "result": "PASS",
    }
    for record in records:
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        if any(payload.get(field) != value for field, value in expected.items()):
            continue
        if not verify_signature(payload, str(record.get("signature", "")), verification_key):
            continue
        try:
            issued = parse_time(str(payload["issued_at"]))
            expires = parse_time(str(payload["expires_at"]))
            moment = parse_time(now)
        except (KeyError, ArchitectureError):
            continue
        if issued < expires and issued <= moment < expires:
            return True
    return False


def validate_exception(
    record: dict[str, Any],
    finding: Finding,
    observation: Observation,
    now: str,
    authority_keys: dict[str, str],
    control_evidence_records: Iterable[dict[str, Any]] = (),
    control_evidence_producer: str = "",
    control_evidence_key: str = "",
) -> tuple[bool, str]:
    payload = record.get("payload")
    signature = record.get("signature", "")
    if not isinstance(payload, dict):
        return False, "EXCEPTION_PAYLOAD_INVALID"
    key = authority_keys.get(str(payload.get("authority_key_id")))
    if key is None or not verify_signature(payload, signature, key):
        return False, "EXCEPTION_AUTHENTICITY_UNVERIFIED"
    if payload.get("status") != "APPROVED":
        return False, "EXCEPTION_NOT_APPROVED"
    if payload.get("rule_id") != finding.rule_id:
        return False, "EXCEPTION_RULE_MISMATCH"
    if payload.get("resource") != finding.resource:
        return False, "EXCEPTION_RESOURCE_MISMATCH"
    if payload.get("environment") != observation.environment:
        return False, "EXCEPTION_ENVIRONMENT_MISMATCH"
    if payload.get("approved_subject_digest") != exception_subject_digest(observation, finding):
        return False, "EXCEPTION_SUBJECT_MISMATCH"
    try:
        moment = parse_time(now)
        issued = parse_time(str(payload["issued_at"]))
        expires = parse_time(str(payload["expires_at"]))
    except (KeyError, ArchitectureError):
        return False, "EXCEPTION_TIME_INVALID"
    if issued >= expires:
        return False, "EXCEPTION_INTERVAL_INVALID"
    if moment < issued:
        return False, "EXCEPTION_NOT_YET_VALID"
    if moment >= expires:
        return False, "EXCEPTION_EXPIRED"
    controls = payload.get("compensating_controls", [])
    if not controls or not all(isinstance(item, dict) and item.get("evidence_id") for item in controls):
        return False, "COMPENSATING_CONTROL_EVIDENCE_MISSING"
    records = tuple(control_evidence_records)
    if not control_evidence_producer or not control_evidence_key:
        return False, "COMPENSATING_CONTROL_EVIDENCE_UNVERIFIED"
    if not all(
        _control_evidence_valid(
            control,
            records,
            payload,
            observation,
            now,
            control_evidence_producer,
            control_evidence_key,
        )
        for control in controls
    ):
        return False, "COMPENSATING_CONTROL_EVIDENCE_UNVERIFIED"
    return True, str(payload["exception_id"])
