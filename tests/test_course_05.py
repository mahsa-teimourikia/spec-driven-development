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
            lab.RequirementGap(
                "GAP-001",
                "REQ-FU-001",
                "loss_history",
                "Loss history",
                lab.GapStatus.INVALID,
                "LOSS_HISTORY_EMPTY",
                ("SRC-UW-REQ-12",),
                lab.ObservationEvidence(
                    "EV-LOSS-EMPTY", "sub-rev-7", "loss_history", "value_invalid"
                ),
            ),
            lab.RequirementGap(
                "GAP-002",
                "REQ-FU-001",
                "signed_application",
                "Signed application",
                lab.GapStatus.MISSING,
                "SIGNED_APPLICATION_ABSENT",
                ("SRC-UW-REQ-12",),
                lab.ObservationEvidence(
                    "EV-SIGNED-ABSENT", "sub-rev-7", "signed_application", "field_absent"
                ),
            ),
        )
        cls.draft = lab.Draft(
            "BROKER-204",
            "Information required for SUB-4815",
            "Please provide loss history and the signed application.",
            ("GAP-001", "GAP-002"),
        )
        cls.context_digest = lab.effective_context_digest(cls.package)
        cls.context = lab.SendContext(
            "SUB-4815",
            "sub-rev-7",
            cls.context_digest,
            "BROKER-204",
            True,
            True,
            "SEND-SUB-4815-DRAFT-001",
        )
        cls.receipt = lab.ApprovalReceipt(
            "UW-118",
            "approved",
            "The draft corresponds to the validated requirement-gap plan.",
            lab.draft_digest(cls.draft),
            "BROKER-204",
            "SUB-4815",
            "sub-rev-7",
            cls.context_digest,
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
        self.assertEqual(statuses["send_message"].release_status, "deferred")
        self.assertEqual(statuses["send_message"].active_requirement_ids, ())
        self.assertEqual(
            statuses["send_message"].deferred_requirement_ids,
            ("REL-FU-002", "SEC-FU-003"),
        )

    def test_requirement_lifecycle_release_scope_and_readiness_are_independent(self) -> None:
        send_requirements = [
            item for item in self.package["requirements"] if item["capability"] == "send_message"
        ]
        self.assertTrue(all(item["status"] == "approved" for item in send_requirements))
        self.assertTrue(
            all(item["release_applicability"]["status"] == "deferred" for item in send_requirements)
        )
        task = next(item for item in self.package["tasks"] if item["id"] == "TASK-04")
        self.assertEqual(task["release_status"], "deferred")
        self.assertEqual(task["blocked_by"], ["OQ-017"])

    def test_requirement_gap_requires_rule_and_current_observation_evidence(self) -> None:
        unsafe = lab.RequirementGap(
            "GAP-X",
            "REQ-OLD",
            "bank_statements",
            "Bank statements",
            lab.GapStatus.MISSING,
            "BANK_STATEMENTS_ABSENT",
            (),
            lab.ObservationEvidence(
                "EV-UNKNOWN", "sub-rev-6", "other_field", "value_invalid"
            ),
        )
        findings = lab.validate_requirement_gaps(
            (unsafe,),
            current_requirement_ids={"REQ-FU-001"},
            trusted_requirement_evidence_ids={"SRC-UW-REQ-12"},
            current_submission_revision="sub-rev-7",
            observed_evidence_ids={"EV-LOSS-EMPTY"},
        )
        self.assertEqual(
            {item.code for item in findings},
            {
                "UNSUPPORTED_REQUIREMENT_GAP",
                "REQUIREMENT_EVIDENCE_MISSING",
                "OBSERVATION_EVIDENCE_UNKNOWN",
                "OBSERVATION_CONTEXT_STALE",
                "OBSERVATION_FIELD_MISMATCH",
                "GAP_STATUS_EVIDENCE_MISMATCH",
            },
        )

    def test_requirement_gap_ids_are_unique(self) -> None:
        duplicate = replace(self.plan[1], id="GAP-001")
        findings = lab.validate_requirement_gaps(
            (self.plan[0], duplicate),
            current_requirement_ids={"REQ-FU-001"},
            trusted_requirement_evidence_ids={"SRC-UW-REQ-12"},
            current_submission_revision="sub-rev-7",
            observed_evidence_ids={"EV-LOSS-EMPTY", "EV-SIGNED-ABSENT"},
        )
        self.assertIn("DUPLICATE_REQUIREMENT_GAP", {item.code for item in findings})

    def test_missing_and_invalid_are_distinct_typed_states(self) -> None:
        self.assertEqual(self.plan[0].status, lab.GapStatus.INVALID)
        self.assertEqual(self.plan[0].observation.observation, "value_invalid")
        self.assertEqual(self.plan[1].status, lab.GapStatus.MISSING)
        self.assertEqual(self.plan[1].observation.observation, "field_absent")
        mismatched = replace(self.plan[1], status=lab.GapStatus.INVALID)
        findings = lab.validate_requirement_gaps(
            (mismatched,),
            current_requirement_ids={"REQ-FU-001"},
            trusted_requirement_evidence_ids={"SRC-UW-REQ-12"},
            current_submission_revision="sub-rev-7",
            observed_evidence_ids={"EV-SIGNED-ABSENT"},
        )
        self.assertEqual([item.code for item in findings], ["GAP_STATUS_EVIDENCE_MISMATCH"])

    def test_draft_rejects_unsupported_addition_and_omission(self) -> None:
        changed = replace(self.draft, gap_ids=("GAP-001", "GAP-999"))
        findings = lab.validate_draft(self.plan, changed)
        self.assertEqual(
            {item.code for item in findings},
            {"DRAFT_UNSUPPORTED_ADDITION", "DRAFT_OMISSION"},
        )
        metrics = lab.correspondence_metrics(("GAP-001", "GAP-002"), changed.gap_ids)
        self.assertEqual(metrics["precision"].value, 0.5)
        self.assertEqual(metrics["recall"].value, 0.5)

    def test_valid_receipt_authorizes_the_simulated_attempt(self) -> None:
        decision = lab.authorize_send(self.draft, self.receipt, self.context, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.PROCEED)
        self.assertEqual(decision.reason_codes, ())

    def test_edit_after_approval_invalidates_receipt(self) -> None:
        changed = replace(self.draft, body=self.draft.body + " Provide bank statements.")
        decision = lab.authorize_send(changed, self.receipt, self.context, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.BLOCK)
        self.assertIn("DRAFT_CHANGED_AFTER_APPROVAL", decision.reason_codes)

    def test_stale_context_and_wrong_broker_fail_closed(self) -> None:
        stale = replace(
            self.context,
            effective_context_digest="sha256:" + "0" * 64,
            broker_id="BROKER-WRONG",
            broker_authorized=False,
        )
        decision = lab.authorize_send(self.draft, self.receipt, stale, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.BLOCK)
        self.assertTrue(
            {"BROKER_NOT_AUTHORIZED", "APPROVAL_BROKER_MISMATCH", "EFFECTIVE_CONTEXT_STALE"}.issubset(
                decision.reason_codes
            )
        )

    def test_replay_duplicate_and_unknown_outcome_are_blocked(self) -> None:
        receipt = replace(self.receipt, consumed=True)
        delivered = replace(self.context, prior_delivery_state="delivered")
        decision = lab.authorize_send(self.draft, receipt, delivered, now=self.now)
        self.assertEqual(decision.outcome, lab.Outcome.BLOCK)
        self.assertIn("APPROVAL_ALREADY_USED", decision.reason_codes)
        self.assertIn("DUPLICATE_OPERATION", decision.reason_codes)
        unknown = lab.authorize_send(
            self.draft,
            self.receipt,
            replace(self.context, prior_delivery_state="unknown"),
            now=self.now,
        )
        self.assertEqual(unknown.outcome, lab.Outcome.ESCALATE)
        self.assertIn("DELIVERY_OUTCOME_UNKNOWN", unknown.reason_codes)

    def test_abstain_is_reserved_for_epistemic_or_model_quality_failure(self) -> None:
        schema = lab.failure_decision(self.package, "schema", attempts=0)
        quality = lab.failure_decision(self.package, "quality", attempts=0)
        self.assertEqual(schema.outcome, lab.Outcome.BLOCK)
        self.assertEqual(quality.outcome, lab.Outcome.ABSTAIN)

    def test_invalid_or_future_approval_time_fails_closed(self) -> None:
        malformed = replace(self.receipt, expires_at="not-a-time")
        malformed_result = lab.authorize_send(
            self.draft, malformed, self.context, now=self.now
        )
        self.assertIn("APPROVAL_TIME_INVALID", malformed_result.reason_codes)
        naive = replace(self.receipt, issued_at="2026-09-20T16:00:00")
        naive_result = lab.authorize_send(self.draft, naive, self.context, now=self.now)
        self.assertIn("APPROVAL_TIME_INVALID", naive_result.reason_codes)
        future = replace(self.receipt, issued_at="2026-09-20T19:00:00Z")
        future_result = lab.authorize_send(self.draft, future, self.context, now=self.now)
        self.assertIn("APPROVAL_NOT_YET_VALID", future_result.reason_codes)

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

    def test_universal_quantifiers_are_reviewed_not_declared_vague(self) -> None:
        findings = lab.lexical_findings(
            {"id": "REQ-X", "statement": "The system SHALL process every supported submission."}
        )
        self.assertEqual([item.code for item in findings], ["UNIVERSAL_QUANTIFIER_REVIEW"])
        self.assertIn("population", findings[0].message)


if __name__ == "__main__":
    unittest.main()
