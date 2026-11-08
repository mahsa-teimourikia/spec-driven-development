"""Deterministic AI evaluation with slices, confusion counts, and holdout checks."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import QualityError
from .registry import digest_payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QualityError("EVALUATION_DATASET_INVALID", f"{path}:{number}") from exc
        if not row.get("label_owner") or not row.get("label_revision"):
            raise QualityError("EVALUATION_LABEL_AUTHORITY_MISSING", str(row.get("case_id")))
        rows.append(row)
    if not rows:
        raise QualityError("EVALUATION_DATASET_EMPTY", str(path))
    return rows


def dataset_digest(rows: list[dict[str, Any]]) -> str:
    return digest_payload(rows)


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }

def evaluate_model(rows: list[dict[str, Any]], model: str) -> dict[str, Any]:
    correct = 0
    unsupported = 0
    protected_violations: list[str] = []
    slice_totals: dict[str, int] = defaultdict(int)
    slice_correct: dict[str, int] = defaultdict(int)
    labels = sorted({str(row["expected_label"]) for row in rows})
    confusion = {expected: {actual: 0 for actual in labels} for expected in labels}

    for row in rows:
        prediction = row["predictions"][model]
        expected = str(row["expected_label"])
        actual = str(prediction["label"])
        if actual not in labels:
            for matrix_row in confusion.values():
                matrix_row.setdefault(actual, 0)
        confusion[expected][actual] += 1
        matched = expected == actual
        correct += int(matched)
        if not prediction.get("evidence_supported", False):
            unsupported += 1
            protected_violations.append(f"{row['case_id']}:UNSUPPORTED_EVIDENCE")
        if row["expected_review_required"] and not prediction.get("review_required", False):
            protected_violations.append(f"{row['case_id']}:REVIEW_ROUTING_BYPASS")
        for slice_name in row.get("slices", []):
            slice_totals[str(slice_name)] += 1
            slice_correct[str(slice_name)] += int(matched)

    per_class: dict[str, Any] = {}
    for label in labels:
        true_positive = confusion[label].get(label, 0)
        false_positive = sum(
            confusion[expected].get(label, 0) for expected in labels if expected != label
        )
        false_negative = sum(
            count for actual, count in confusion[label].items() if actual != label
        )
        per_class[label] = {
            "precision": _ratio(true_positive, true_positive + false_positive),
            "recall": _ratio(true_positive, true_positive + false_negative),
        }
    return {
        "model": model,
        "population": len(rows),
        "accuracy": _ratio(correct, len(rows)),
        "unsupported_claim_rate": _ratio(unsupported, len(rows)),
        "slices": {
            name: _ratio(slice_correct[name], total)
            for name, total in sorted(slice_totals.items())
        },
        "per_class": per_class,
        "confusion_matrix": confusion,
        "protected_violations": protected_violations,
        "decision": "BLOCKED" if protected_violations else "CONFORMANT",
        "claim": "deterministic labelled fixture performance, not production model quality",
    }


def compare_models(root: Path) -> dict[str, Any]:
    development = load_jsonl(root / "datasets" / "development.jsonl")
    holdout = load_jsonl(root / "datasets" / "protected-holdout.jsonl")
    return {
        "dataset_revision": "NORTHSTAR-EVAL@3",
        "development_digest": dataset_digest(development),
        "holdout_digest": dataset_digest(holdout),
        "development": {
            model: evaluate_model(development, model) for model in ("v1", "v2", "overfit")
        },
        "holdout": {
            model: evaluate_model(holdout, model) for model in ("v1", "v2", "overfit")
        },
        "selection": {
            "proposed_model": "v2",
            "decision": "BLOCKED",
            "reason": "Aggregate classification improvement cannot offset protected review-routing and evidence-support violations.",
        },
    }
