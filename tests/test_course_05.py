"""Tests for Course 05 requirements engineering and runtime boundaries."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "beginner" / "05-requirements-engineering-for-agents"
SPEC = importlib.util.spec_from_file_location("course05_lab", LESSON / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course05RequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.package = lab.load_package()
        cls.plan = (
            lab.MissingItem("MI-001", "REQ-FU-001", "Loss history", ("EV-LOSS-EMPTY",)),
            lab.MissingItem("MI-002", "REQ-FU-001", "Signed application", ("EV-SIGNED-ABSENT",)),
        )
        cls.draft = lab.Draft(
            "BROKER-204",
            "Information required for SUB-4815",
            "Please provide loss history and the signed application.",
            ("MI-001", "MI-002"),
        )
        cls.context = lab.SendContext(
            "SUB-4815",
            "sub-rev-7",
            cls.package["specification"]["revision"],
            "BROKER-204",
            True,
            True,
            "SEND-SUB-4815-DRAFT-001",
        )
        cls.receipt = lab.ApprovalReceipt(
            "UW-118",
            "approved",
            "The draft corresponds to the validated missing-item plan.",
            lab.draft_digest(cls.draft),
            "BROKER-204",
            "SUB-4815",
            "sub-rev-7",
            cls.package["specification"]["revision"],
            "2026-09-20T17:00:00Z",
            "2026-09-21T00:00:00Z",
        )
        cls.now = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)

    def test_reference_package_is_clean(self) -> None:
        self.assertEqual(lab.package_findings(self.package), ())

    def test_open_question_blocks_only_send_capability(self) -> None:
        statuses = {item.capability: item for item in lab.capability_readiness(self.package)}
        self.assertTrue(statuses["analyze_missing_items"].ready)
        self.assertTrue(statuses["draft_message"].ready)
        self.assertFalse(statuses["send_message"].ready)
        self.assertEqual(statuses["send_message"].blocking_question_ids, ("OQ-017",))

    def test_missing_item_requires_current_rule_and_observed_evidence(self) -> None:
        unsafe = lab.MissingItem("MI-X", "REQ-OLD", "Bank statements", ("EV-UNKNOWN",))
        findings = lab.validate_missing_items(
            (unsafe,),
            current_requirement_ids={"REQ-FU-001"},
            observed_evidence_ids={"EV-LOSS-EMPTY"},
        )
        self.assertEqual(
            {item.code for item in findings},
            {"UNSUPPORTED_MISSING_ITEM", "MISSING_ITEM_EVIDENCE_INVALID"},
        )

    def test_draft_rejects_unsupported_addition_and_omission(self) -> None:
        changed = replace(self.draft, missing_item_ids=("MI-001", "MI-999"))
        findings = lab.validate_draft(self.plan, changed)
        self.assertEqual(
            {item.code for item in findings},
            {"DRAFT_UNSUPPORTED_ADDITION", "DRAFT_OMISSION"},
        )
        metrics = lab.correspondence_metrics(("MI-001", "MI-002"), changed.missing_item_ids)
        self.assertEqual(metrics["precision"].value, 0.5)
        self.assertEqual(metrics["recall"].value, 0.5)

    def test_valid_receipt_authorizes_the_simulated_attempt(self) -> None:
        decision = lab.authorize_send(self.draft, self.receipt, self.context, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.PROCEED)
        self.assertEqual(decision.reason_codes, ())

    def test_edit_after_approval_invalidates_receipt(self) -> None:
        changed = replace(self.draft, body=self.draft.body + " Provide bank statements.")
        decision = lab.authorize_send(changed, self.receipt, self.context, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.ABSTAIN)
        self.assertIn("DRAFT_CHANGED_AFTER_APPROVAL", decision.reason_codes)

    def test_stale_context_and_wrong_broker_fail_closed(self) -> None:
        stale = replace(
            self.context,
            requirements_revision="new-revision",
            broker_id="BROKER-WRONG",
            broker_authorized=False,
        )
        decision = lab.authorize_send(self.draft, self.receipt, stale, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.ESCALATE)
        self.assertTrue(
            {"BROKER_NOT_AUTHORIZED", "APPROVAL_BROKER_MISMATCH", "REQUIREMENTS_CONTEXT_STALE"}.issubset(
                decision.reason_codes
            )
        )

    def test_replay_duplicate_and_unknown_outcome_are_blocked(self) -> None:
        receipt = replace(self.receipt, consumed=True)
        delivered = replace(self.context, prior_delivery_state="delivered")
        decision = lab.authorize_send(self.draft, receipt, delivered, now=self.now)
        self.assertIn("APPROVAL_ALREADY_USED", decision.reason_codes)
        self.assertIn("DUPLICATE_OPERATION", decision.reason_codes)
        unknown = lab.authorize_send(
            self.draft,
            self.receipt,
            replace(self.context, prior_delivery_state="unknown"),
            now=self.now,
        )
        self.assertIn("DELIVERY_OUTCOME_UNKNOWN", unknown.reason_codes)

    def test_only_declared_transient_failure_is_retryable(self) -> None:
        retry = lab.failure_decision(self.package, "transport", attempts=0)
        exhausted = lab.failure_decision(self.package, "transport", attempts=2)
        safety = lab.failure_decision(self.package, "safety", attempts=0)
        self.assertEqual(retry.reason_codes, ("BOUNDED_RETRY_ALLOWED",))
        self.assertEqual(exhausted.outcome, lab.Outcome.ESCALATE)
        self.assertEqual(safety.reason_codes, ("SAFETY_POLICY_DENIED",))

    def test_traceability_detects_orphan_task(self) -> None:
        changed = dict(self.package)
        changed["tasks"] = list(self.package["tasks"]) + [
            {"id": "TASK-099", "title": "Add Redis caching", "requirement_ids": []}
        ]
        self.assertIn("ORPHAN_TASK", {item.code for item in lab.traceability_findings(changed)})

    def test_stale_spec_context_is_review_not_automatic_rework(self) -> None:
        findings = lab.spec_context_findings(self.package, "old-revision")
        self.assertEqual([item.code for item in findings], ["SPEC_CONTEXT_STALE"])
        self.assertEqual(findings[0].severity, lab.Severity.REVIEW)

    def test_semantic_diff_names_changed_obligation_fields(self) -> None:
        before = self.package["requirements"][3]
        after = dict(before)
        after["postconditions"] = list(before["postconditions"]) + [
            "approval rationale is present"
        ]
        diff = lab.semantic_requirement_diff(before, after)
        self.assertEqual(diff["changed_fields"], ("postconditions",))

    def test_evaluation_preserves_population_and_error_counts(self) -> None:
        result = lab.evaluate_cases()
        self.assertEqual(result["population"], 8)
        self.assertEqual(result["labelled_findings"], 5)
        self.assertEqual(result["evidence_aware"]["false_negative"], 0)
        self.assertGreaterEqual(
            result["evidence_aware"]["recall"], result["keyword_baseline"]["recall"]
        )


if __name__ == "__main__":
    unittest.main()
