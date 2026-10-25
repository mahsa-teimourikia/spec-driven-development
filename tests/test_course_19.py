"""Focused verification for Course 19 bug fixes and small changes."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "09-bug-fixes-and-small-changes-with-agentic-coding-agents"
SCENARIO = LESSON / "northstar-bugfix"
SPEC = importlib.util.spec_from_file_location("course19_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
sys.path.insert(0, str(SCENARIO))
SPEC.loader.exec_module(lab)

from bugfix_app.api import off_by_one_normalizer, risk_response  # noqa: E402
from bugfix_app.contracts import ChangeRisk, DiffEntry  # noqa: E402
from bugfix_app.risk_engine import classify_risk_buggy, classify_risk_fixed, validate_score  # noqa: E402
from bugfix_app.workflow import (  # noqa: E402
    canonical_digest,
    evaluate_candidate,
    select_workflow_mode,
    validate_diff,
    validate_repository_path,
    verify_acceptance_oracle,
)


class Course19Tests(unittest.TestCase):
    def codes(self, mutations):
        return {finding.code for finding in evaluate_candidate(lab.build_candidate(mutations)).findings}

    def test_original_defect_is_exactly_reproduced(self):
        self.assertEqual(classify_risk_buggy(80), "MEDIUM")

    def test_minimal_fix_repairs_exact_boundary(self):
        self.assertEqual(classify_risk_fixed(80), "HIGH")

    def test_adjacent_approved_boundaries_are_preserved(self):
        self.assertEqual(
            [classify_risk_fixed(score) for score in (0, 49, 50, 79, 80, 81, 100)],
            ["LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH", "HIGH"],
        )

    def test_invalid_scores_are_rejected(self):
        for value in (-1, 101, 80.0, True):
            with self.assertRaises(ValueError):
                validate_score(value)

    def test_production_path_preserves_identity_and_review(self):
        response = risk_response("SUB-2415", 80)
        self.assertEqual(response["submission_id"], "SUB-2415")
        self.assertIs(response["review_required"], True)

    def test_root_cause_mismatch_is_exercised_through_production_path(self):
        self.assertEqual(risk_response("SUB-2415", 80, normalizer=off_by_one_normalizer)["normalized_score"], 79)
        self.assertIn("ROOT_CAUSE_MISMATCH", self.codes(["root_cause_mismatch"]))

    def test_risk_not_diff_size_selects_workflow(self):
        self.assertEqual(select_workflow_mode(ChangeRisk(0, 0, 0, 0, 0, 0)), "LIGHTWEIGHT")
        self.assertEqual(select_workflow_mode(ChangeRisk(1, 1, 1, 1, 1, 1)), "STRUCTURED")
        self.assertEqual(select_workflow_mode(ChangeRisk(3, 3, 0, 0, 0, 0)), "GOVERNED")

    def test_mandatory_mode_is_a_floor_owned_by_policy(self):
        risk = ChangeRisk(0, 0, 0, 0, 0, 0)
        self.assertEqual(select_workflow_mode(risk, mandatory_mode="GOVERNED"), "GOVERNED")

    def test_oracle_weakening_is_detected_by_content(self):
        self.assertIn("TEST_ORACLE_CHANGED", self.codes(["weaken_oracle"]))

    def test_oracle_digest_is_canonical(self):
        left = {"b": 2, "a": 1}
        right = {"a": 1, "b": 2}
        self.assertEqual(canonical_digest(left), canonical_digest(right))

    def test_scope_expansion_is_detected_from_actual_diff(self):
        self.assertIn("SCOPE_EXPANSION", self.codes(["scope_expansion"]))

    def test_rename_checks_old_and_new_paths(self):
        decision = validate_diff(
            [DiffEntry("R", "app/risk_engine.py", "app/authorization.py", "correct_boundary_condition")],
            writable_paths={"app/risk_engine.py"},
            protected_paths={"app/authorization.py"},
            allowed_purposes={"correct_boundary_condition"},
        )
        self.assertIn("PROTECTED_PATH_CHANGE", {item.code for item in decision.findings})

    def test_path_traversal_is_rejected(self):
        self.assertIsNone(validate_repository_path("../secrets.txt"))
        self.assertIsNone(validate_repository_path("/absolute/path"))
        self.assertIsNone(validate_repository_path("app/./risk_engine.py"))
        self.assertIsNone(validate_repository_path(r"app\risk_engine.py"))

    def test_protected_path_change_is_detected(self):
        self.assertIn("PROTECTED_PATH_CHANGE", self.codes(["protected_path_change"]))

    def test_opportunistic_refactor_is_not_justified(self):
        self.assertIn("UNJUSTIFIED_CHANGE", self.codes(["opportunistic_refactor"]))

    def test_conflicting_requirement_stops_execution(self):
        self.assertIn("NORMATIVE_CONFLICT", self.codes(["requirement_conflict"]))

    def test_red_green_requires_a_real_baseline_failure(self):
        codes = self.codes(["missing_reproduction"])
        self.assertIn("DEFECT_NOT_REPRODUCED", codes)
        self.assertIn("RED_GREEN_NOT_PROVEN", codes)

    def test_replayed_evidence_is_revision_mismatched(self):
        self.assertIn("STALE_EVIDENCE", self.codes(["replay_old_evidence"]))

    def test_red_green_receipt_uses_the_same_regression_identity(self):
        candidate = lab.build_candidate()
        receipt = candidate["evidence_receipt"]
        candidate["evidence_receipt"] = replace(receipt, after=replace(receipt.after, test_id="OTHER-TEST"))
        codes = {finding.code for finding in evaluate_candidate(candidate).findings}
        self.assertIn("WRONG_REGRESSION_EVIDENCE", codes)
        self.assertIn("EVIDENCE_OBSERVATION_MISMATCH", codes)

    def test_self_report_is_not_trusted_evidence(self):
        self.assertIn("UNTRUSTED_EVIDENCE_PRODUCER", self.codes(["untrusted_evidence"]))

    def test_evaluator_does_not_trust_mutation_labels(self):
        candidate = lab.build_candidate()
        candidate["mutation_labels"] = ["protected_path_change", "weaken_oracle"]
        self.assertEqual(evaluate_candidate(candidate).state, "PASS")

    def test_reference_package_grants_no_release_authority(self):
        package = json.loads((SCENARIO / "reference" / "bugfix-package.json").read_text())
        self.assertTrue(all(value is False for value in package["non_authorities"].values()))

    def test_starter_contains_five_decisions(self):
        starter = (SCENARIO / "workshop" / "starter" / "bugfix-package.json").read_text()
        self.assertEqual(starter.count("TODO:"), 5)

    def test_diagram_is_reproducible(self):
        before = (SCENARIO / "assets" / "bugfix-workflow.svg").read_text()
        subprocess.run([sys.executable, "assets/render_diagram.py"], cwd=SCENARIO, check=True, capture_output=True, text=True)
        after = (SCENARIO / "assets" / "bugfix-workflow.svg").read_text()
        self.assertEqual(before, after)
        self.assertIn("aria-labelledby", after)

    def test_notebook_is_clean_and_has_no_saved_outputs(self):
        notebook = json.loads((SCENARIO / "bugfix_small_changes.ipynb").read_text())
        self.assertTrue(all(cell.get("outputs", []) == [] for cell in notebook["cells"] if cell["cell_type"] == "code"))
        self.assertTrue(all(cell.get("execution_count") is None for cell in notebook["cells"] if cell["cell_type"] == "code"))

    def test_lab_report_is_complete(self):
        result = subprocess.run([sys.executable, str(SCENARIO / "lab.py")], cwd=SCENARIO, text=True, capture_output=True, check=True)
        report = json.loads(result.stdout)
        self.assertEqual(report["state"], "READY_FOR_INTEGRATION_REVIEW")
        self.assertEqual((report["conformance"]["passed"], report["conformance"]["total"]), (12, 12))
        self.assertEqual((report["evaluation"]["passed"], report["evaluation"]["total"]), (30, 30))
        self.assertEqual((report["experiments"]["passed"], report["experiments"]["total"]), (10, 10))
        self.assertEqual(report["comparison"]["baseline_cases_accepted"], 12)


if __name__ == "__main__":
    unittest.main()
