"""Run the credential-free Course 27 quality control lab."""

from __future__ import annotations

import json
from pathlib import Path

from quality_app.simulation import run_reference


if __name__ == "__main__":
    result = run_reference(Path(__file__).resolve().parent)
    holdout = result["model_comparison"]["holdout"]
    summary = {
        "course": result["course"],
        "change_id": result["change_id"],
        "quality_decision": result["quality_decision"],
        "delivery_state": result["delivery_state"],
        "release_authorized": result["release_authorized"],
        "revision_set": result["revision_set"],
        "coverage": result["quality_report"]["coverage"],
        "quality_metrics": result["quality_report"]["metrics"],
        "model_comparison": {
            "selection": result["model_comparison"]["selection"],
            "v1_holdout": holdout["v1"],
            "v2_holdout": holdout["v2"],
            "overfit_holdout": holdout["overfit"],
        },
        "golden": {
            "passed": sum(item["passed"] for item in result["golden"]),
            "total": len(result["golden"]),
        },
        "adversarial": result["adversarial_evaluation"]["metrics"],
        "subject_tamper_result": result["subject_tamper_result"],
        "limitations": result["limitations"],
    }
    print(json.dumps(summary, indent=2))
