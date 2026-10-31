"""Execute Course 20-compatible flows from the exact candidate repositories.

Results come from loaded component methods and observed side effects, never from
documentation strings, fixture flags, or a second copy of the service behavior.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _raises(code: str, action: object) -> bool:
    try:
        action()  # type: ignore[operator]
    except Exception as error:
        return code in str(error)
    return False


def _load_component(workspace: Path, repository: str) -> object:
    path = workspace / repository / "src/component.py"
    module_name = "course21_" + repository.replace("-", "_")
    specification = importlib.util.spec_from_file_location(module_name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"COMPONENT_LOAD_FAILED:{repository}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def execute_repository_system_scenarios(workspace: Path) -> dict[str, bool]:
    """Load and execute the component modules from the exact Git workspaces."""

    document_service = _load_component(workspace, "document-service")
    ai_service = _load_component(workspace, "ai-service")
    review_service = _load_component(workspace, "review-service")
    underwriting_api = _load_component(workspace, "underwriting-api")
    underwriter_ui = _load_component(workspace, "underwriter-ui")
    now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)

    document = document_service.extract_document("DOC-1", "TENANT-A")
    ambiguous = ai_service.propose_classification(
        document,
        ambiguity_status="AMBIGUOUS",
        model_confidence=0.999,
    )
    review = review_service.ReviewService()
    approval = review_service.issue_approval(
        ambiguous,
        receipt_id="APPROVAL-1",
        tenant_id="TENANT-A",
        expires_at=now + timedelta(minutes=5),
    )
    routed = review.process(
        ambiguous,
        submission_id="SUBMISSION-1",
        authorized_tenant="TENANT-A",
        evidence_tenants={document["evidence_ref"]: "TENANT-A"},
        approval_receipt=approval,
        now=now,
    )

    cross_tenant = {**ambiguous, "proposal_id": "proposal:TENANT-B:DOC-1", "tenant_id": "TENANT-B"}
    tenant_isolation = _raises(
        "CROSS_TENANT_PROPOSAL",
        lambda: review_service.ReviewService().process(
            cross_tenant,
            submission_id="SUBMISSION-XTENANT",
            authorized_tenant="TENANT-A",
            evidence_tenants={document["evidence_ref"]: "TENANT-A"},
            approval_receipt=None,
            now=now,
        ),
    )

    supported_document = document_service.extract_document("DOC-2", "TENANT-A")
    supported = ai_service.propose_classification(
        supported_document,
        ambiguity_status="SUPPORTED",
        model_confidence=0.98,
    )
    duplicate_review = review_service.ReviewService()
    first = duplicate_review.process(
        supported,
        submission_id="SUBMISSION-DUPLICATE",
        authorized_tenant="TENANT-A",
        evidence_tenants={supported_document["evidence_ref"]: "TENANT-A"},
        approval_receipt=None,
        now=now,
    )
    second = duplicate_review.process(
        supported,
        submission_id="SUBMISSION-DUPLICATE",
        authorized_tenant="TENANT-A",
        evidence_tenants={supported_document["evidence_ref"]: "TENANT-A"},
        approval_receipt=None,
        now=now,
    )

    expired = review_service.issue_approval(
        ambiguous,
        receipt_id="APPROVAL-EXPIRED",
        tenant_id="TENANT-A",
        expires_at=now - timedelta(seconds=1),
    )
    expired_rejected = _raises(
        "APPROVAL_EXPIRED",
        lambda: review_service.ReviewService().process(
            ambiguous,
            submission_id="SUBMISSION-EXPIRED",
            authorized_tenant="TENANT-A",
            evidence_tenants={document["evidence_ref"]: "TENANT-A"},
            approval_receipt=expired,
            now=now,
        ),
    )

    api = underwriting_api.UnderwritingAPI()
    unauthorized_mutation = _raises(
        "AUTHORITATIVE_WRITER_DENIED",
        lambda: api.apply_review_result(
            routed,
            authenticated_identity="agent-ai-a",
            authorized_tenant="TENANT-A",
        ),
    )
    rendered = underwriter_ui.render(ambiguous, authoritative_state="PENDING_REVIEW")
    return {
        "ambiguity_routes_to_review": (
            ambiguous["review_required"] is True
            and routed["status"] == "REVIEW_COMPLETED"
            and routed["authoritative_mutation_count"] == 0
        ),
        "tenant_isolation": tenant_isolation,
        "duplicate_operation_reconciled": (
            first["duplicate"] is False
            and second["duplicate"] is True
            and duplicate_review.side_effect_count == 1
        ),
        "expired_approval_rejected": expired_rejected,
        "proposal_not_authoritative": unauthorized_mutation and api.mutation_count == 0,
        "provenance_preserved": (
            ambiguous["evidence_refs"] == ["evidence:DOC-1"]
            and ambiguous["model_provenance"]["model_revision"] == "2026-02"
            and "not authoritative" in rendered["proposal_label"]
        ),
    }
