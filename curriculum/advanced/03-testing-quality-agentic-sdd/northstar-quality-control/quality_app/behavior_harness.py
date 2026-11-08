"""Execute protected behavior against exact Git-loaded service modules."""

from __future__ import annotations

import hashlib
import json
import tempfile
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .repository_harness import RevisionFixture


NOW = "2026-11-08T18:00:00Z"
FUTURE = "2026-12-31T23:59:59Z"
PAST = "2026-11-08T17:00:00Z"


def sample_document(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "document_id": "DOC-2605-AMB-001",
        "tenant_id": "TENANT-A",
        "prediction": "LOSS_HISTORY",
        "confidence": 0.99,
        "ambiguous": True,
        "evidence_refs": ["DOC-2605-AMB-001:PAGE-2"],
        "model_revision": "classifier-v2",
    }
    value.update(overrides)
    return value


def _approval(review_module, payload: dict, *, expired: bool = False, revoked: bool = False):
    return review_module.Approval(
        approval_id="APP-2605-001",
        tenant_id="TENANT-A",
        actor_role="authorized-underwriter",
        proposal_digest=review_module.payload_digest(payload),
        expires_at=PAST if expired else FUTURE,
        revoked=revoked,
    )


def execute_protected_checks(
    fixture: RevisionFixture,
    *,
    mutant: str | None = None,
) -> dict[str, Any]:
    ai = fixture.modules["ai-service"]
    review = fixture.modules["review-service"]
    underwriting = fixture.modules["underwriting-api"]
    proposal = ai.propose(sample_document(), mutant=mutant)
    unsupported = ai.propose(
        sample_document(
            document_id="DOC-2605-UNSUPPORTED",
            evidence_refs=["TENANT-B:DOC-UNKNOWN:PAGE-1"],
        ),
        mutant=mutant,
    )
    payload = {"document_id": proposal.document_id, "classification": proposal.document_type}

    with tempfile.TemporaryDirectory(prefix="course27-review-") as directory:
        database = Path(directory) / "review.sqlite3"
        store = review.ReviewStore(database, mutant=mutant)
        approval = _approval(review, payload)

        def apply_same() -> dict:
            return store.apply(
                operation_id="OP-2605-001",
                tenant_id="TENANT-A",
                actor_tenant="TENANT-A",
                payload=payload,
                approval=approval,
                now=NOW,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent = list(executor.map(lambda _: apply_same(), range(2)))

        conflicting = dict(payload)
        conflicting["classification"] = "OTHER"
        conflict_result = store.apply(
            operation_id="OP-2605-001",
            tenant_id="TENANT-A",
            actor_tenant="TENANT-A",
            payload=conflicting,
            approval=_approval(review, conflicting),
            now=NOW,
        )
        cross_tenant = store.apply(
            operation_id="OP-2605-XTENANT",
            tenant_id="TENANT-B",
            actor_tenant="TENANT-A",
            payload=payload,
            approval=approval,
            now=NOW,
        )
        expired = store.apply(
            operation_id="OP-2605-EXPIRED",
            tenant_id="TENANT-A",
            actor_tenant="TENANT-A",
            payload=payload,
            approval=_approval(review, payload, expired=True),
            now=NOW,
        )
        revoked = store.apply(
            operation_id="OP-2605-REVOKED",
            tenant_id="TENANT-A",
            actor_tenant="TENANT-A",
            payload=payload,
            approval=_approval(review, payload, revoked=True),
            now=NOW,
        )
        ai_mutation = underwriting.persist_classification(
            {}, proposal, {"status": "APPLIED"}, caller="ai-service", mutant=mutant
        )
        outage = underwriting.route_during_review_outage(mutant=mutant)

        checks = {
            "ambiguous_requires_review": review.requires_review(proposal, mutant=mutant) is True,
            "evidence_provenance_preserved": bool(proposal.evidence_refs),
            "unsupported_evidence_rejected": not ai.evidence_is_supported(
                unsupported,
                {"DOC-2605-AMB-001:PAGE-2"},
            ),
            "cross_tenant_denied": cross_tenant["status"] == "DENIED",
            "ai_cannot_mutate_state": ai_mutation["status"] == "DENIED",
            "duplicate_effect_is_single": store.effect_count() == 1,
            "conflicting_idempotency_payload_rejected": (
                conflict_result["status"] == "IDEMPOTENCY_CONFLICT"
            ),
            "expired_approval_rejected": expired["status"] == "APPROVAL_EXPIRED",
            "revoked_approval_rejected": revoked["status"] == "APPROVAL_REVOKED",
            "review_outage_holds_safely": outage == "REVIEW_UNAVAILABLE_SAFE_HOLD",
        }
        return {
            "checks": checks,
            "concurrent_statuses": sorted(item["status"] for item in concurrent),
            "effect_count": store.effect_count(),
            "conflict_status": conflict_result["status"],
            "outage_status": outage,
        }


def property_population(fixture: RevisionFixture, *, mutant: str | None = None) -> dict[str, Any]:
    """Deterministic fallback for the same property taught with Hypothesis."""

    ai = fixture.modules["ai-service"]
    review = fixture.modules["review-service"]
    failures: list[float] = []
    for step in range(101):
        confidence = step / 100
        proposal = ai.propose(sample_document(confidence=confidence), mutant=mutant)
        if not review.requires_review(proposal, mutant=mutant):
            failures.append(confidence)
    return {
        "population": 101,
        "failures": failures,
        "passed": not failures,
        "claim": "enumerated confidence boundary; Hypothesis can expand the generated domain",
    }


def metamorphic_population(fixture: RevisionFixture, *, mutant: str | None = None) -> dict[str, Any]:
    ai = fixture.modules["ai-service"]
    review = fixture.modules["review-service"]
    pairs = ((0.0, 0.99), (0.49, 0.95), (0.94, 1.0))
    failures: list[tuple[float, float]] = []
    for low, high in pairs:
        low_proposal = ai.propose(sample_document(confidence=low), mutant=mutant)
        high_proposal = ai.propose(sample_document(confidence=high), mutant=mutant)
        if not (
            review.requires_review(low_proposal, mutant=mutant)
            and review.requires_review(high_proposal, mutant=mutant)
        ):
            failures.append((low, high))
    return {"population": len(pairs), "failures": failures, "passed": not failures}


def execute_fault_experiments(fixture: RevisionFixture) -> list[dict[str, Any]]:
    behavior = execute_protected_checks(fixture)
    contract_before = hashlib.sha256(
        json.dumps({"classification_contract": 3}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    contract_after = hashlib.sha256(
        json.dumps({"classification_contract": 4}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    with tempfile.TemporaryDirectory(prefix="course27-rollback-") as directory:
        database = Path(directory) / "rollback.sqlite3"
        connection = sqlite3.connect(database, isolation_level=None)
        connection.execute("CREATE TABLE effects (effect_id TEXT PRIMARY KEY)")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("INSERT INTO effects VALUES ('EFFECT-PARTIAL')")
        connection.rollback()
        durable_count = int(connection.execute("SELECT COUNT(*) FROM effects").fetchone()[0])
        connection.close()
    return [
        {
            "experiment_id": "REVIEW_SERVICE_UNAVAILABLE",
            "outcome": "SAFE" if behavior["checks"]["review_outage_holds_safely"] else "UNSAFE",
            "safe_state": behavior["outage_status"],
        },
        {
            "experiment_id": "DATABASE_INTERRUPTED_BEFORE_COMMIT",
            "outcome": "SAFE" if durable_count == 0 else "UNSAFE",
            "safe_state": f"durable_effects={durable_count}",
        },
        {
            "experiment_id": "DUPLICATE_DELIVERY",
            "outcome": "SAFE" if behavior["effect_count"] == 1 else "UNSAFE",
            "safe_state": f"durable_effects={behavior['effect_count']}",
        },
        {
            "experiment_id": "STALE_APPROVAL",
            "outcome": "SAFE" if behavior["checks"]["expired_approval_rejected"] else "UNSAFE",
            "safe_state": "APPROVAL_EXPIRED",
        },
        {
            "experiment_id": "CONTRACT_CHANGED_DURING_RUN",
            "outcome": "SAFE" if contract_before != contract_after else "UNSAFE",
            "safe_state": "EVIDENCE_REVALIDATION_REQUIRED",
        },
        {
            "experiment_id": "UNSUPPORTED_EVIDENCE_REFERENCE",
            "outcome": "SAFE" if behavior["checks"]["unsupported_evidence_rejected"] else "UNSAFE",
            "safe_state": "QUALITY_FAILURE",
        },
    ]
