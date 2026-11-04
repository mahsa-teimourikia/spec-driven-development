"""Exact-scope, signed, expiring architecture-exception validation."""

from __future__ import annotations

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


def validate_exception(
    record: dict[str, Any],
    finding: Finding,
    observation: Observation,
    now: str,
    authority_keys: dict[str, str],
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
    if not controls or not all(item.get("evidence_id") for item in controls):
        return False, "COMPENSATING_CONTROL_EVIDENCE_MISSING"
    return True, str(payload["exception_id"])
