"""Fictional Document Service boundary used by the training fixture."""


def extract(document_id: str, tenant_id: str) -> dict[str, str]:
    if not document_id or not tenant_id:
        raise ValueError("document and tenant identity are required")
    return {"document_id": document_id, "tenant_id": tenant_id, "text_ref": f"evidence:{document_id}"}
