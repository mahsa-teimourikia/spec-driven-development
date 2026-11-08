"""Optional pytest/Hypothesis expansion of the credential-free property population."""

from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def load_service(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


ai_service = load_service("course27_hypothesis_ai", ROOT / "repositories/ai-service/service.py")
review_service = load_service(
    "course27_hypothesis_review", ROOT / "repositories/review-service/service.py"
)


@given(confidence=st.floats(min_value=0, max_value=1, allow_nan=False))
def test_ambiguity_always_requires_review(confidence: float) -> None:
    proposal = ai_service.propose(
        {
            "document_id": "DOC-HYPOTHESIS",
            "tenant_id": "TENANT-A",
            "prediction": "LOSS_HISTORY",
            "confidence": confidence,
            "ambiguous": True,
            "evidence_refs": ["DOC-HYPOTHESIS:PAGE-1"],
            "model_revision": "classifier-v2",
        }
    )
    assert review_service.requires_review(proposal)
