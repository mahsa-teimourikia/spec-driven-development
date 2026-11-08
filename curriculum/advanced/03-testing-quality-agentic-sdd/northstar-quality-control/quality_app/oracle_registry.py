"""Protected requirement and oracle registry for Course 27."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import QualityError
from .registry import digest_payload, load_json


class OracleRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.change = load_json(root / "requirements" / "AI-2605.json")
        self.invariants = load_json(root / "requirements" / "protected-invariants.json")
        self.obligations = load_json(root / "requirements" / "verification-obligations.json")
        self._validate()

    def _validate(self) -> None:
        invariants = {item["id"] for item in self.invariants.get("invariants", [])}
        obligations = self.obligations.get("obligations", [])
        if not invariants or len(invariants) != 5:
            raise QualityError("PROTECTED_INVARIANT_REGISTRY_INVALID")
        for obligation in obligations:
            if obligation.get("requirement_id") not in invariants:
                raise QualityError("OBLIGATION_REQUIREMENT_UNKNOWN", str(obligation))
            oracle = obligation.get("oracle", {})
            if not oracle.get("owner") or not oracle.get("revision"):
                raise QualityError("PROTECTED_ORACLE_INCOMPLETE", str(obligation))

    @property
    def digest(self) -> str:
        return digest_payload(
            {
                "change": self.change,
                "invariants": self.invariants,
                "obligations": self.obligations,
            }
        )

    @property
    def requirement_ids(self) -> set[str]:
        return {item["id"] for item in self.invariants["invariants"]}

    def required_pairs(self) -> set[tuple[str, str]]:
        return {
            (item["requirement_id"], kind)
            for item in self.obligations["obligations"]
            for kind in item["required_kinds"]
        }

    def as_policy_requirements(self) -> list[dict[str, Any]]:
        criticality = {
            item["id"]: item["criticality"] for item in self.invariants["invariants"]
        }
        return [
            {
                "id": item["requirement_id"],
                "criticality": criticality[item["requirement_id"]],
                "required_kinds": item["required_kinds"],
                "statement": item["claim"],
            }
            for item in self.obligations["obligations"]
        ]
