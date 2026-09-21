"""Tests for Course 06 executable requirements and trusted boundaries."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "beginner" / "06-writing-executable-requirements"
SPEC = importlib.util.spec_from_file_location("course06_lab", LESSON / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course06ExecutableRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.digest = "sha256:" + "a" * 64
        cls.evidence = (lab.SourceEvidence("SPAN-12", "MSG-882", "constructed in 2001"),)
        cls.proposal = lab.ModelProposal(
            "PROP-991",
            "SUB-42",
            "S17",
            cls.digest,
            ("construction_year",),
            2001,
            "MSG-882",
            cls.evidence,
            "UW-018",
            "offline-fixture-v1",
            model_status="applied",
        )
        cls.context = lab.DecisionContext(
            "S17",
            cls.digest,
            True,
            True,
            frozenset({"construction_year", "occupancy", "building_value"}),
            frozenset({"construction_year", "occupancy", "building_value"}),
            frozenset({"construction_year"}),
            {"construction_year": lab.ExistingField(1998, True)},
            response_sequence=8,
            latest_applied_sequence=7,
        )
        cls.now = datetime(2026, 9, 20, 21, 0, tzinfo=timezone.utc)

    def test_reference_artifacts_are_consistent_and_requirements_ready(self) -> None:
        self.assertEqual(lab.requirement_findings(lab.load_contract()), ())
        self.assertEqual(lab.artifact_consistency_findings(), ())

    def test_normative_table_mutation_stops_instead_of_adjudicating(self) -> None:
        findings = lab.artifact_consistency_findings(table=lab.mutated_table())
        self.assertIn("NORMATIVE_ARTIFACT_CONFLICT", {item.code for item in findings})
        self.assertTrue(all(item.severity == lab.Severity.STOP for item in findings))

    def test_normative_elaboration_requires_an_explicit_reverse_link(self) -> None:
        contract = json.loads(json.dumps(lab.load_contract()))
        requirement = next(item for item in contract["requirements"] if item["id"] == "REQ-BR-002")
        requirement["elaboration_ids"] = []
        findings = lab.artifact_consistency_findings(contract=contract)
        unlinked = [item for item in findings if item.code == "NORMATIVE_ELABORATION_UNLINKED"]
        self.assertTrue(any(item.subject_id == "CONTRACT-BR-001" for item in unlinked))

    def test_normative_example_cannot_override_decision_table(self) -> None:
        scenarios = lab.load_scenarios()
        changed = json.loads(json.dumps(scenarios))
        changed["scenarios"][0]["then"]["outcome"] = "auto_apply_eligible"
        findings = lab.artifact_consistency_findings(scenarios=changed)
        self.assertIn("SCENARIO_CONTRADICTS_REQUIREMENT", {item.code for item in findings})

    def test_linter_is_diagnostic_about_undefined_language(self) -> None:
        requirement = {
            "id": "REQ-BAD",
            "statement": "The system SHALL quickly notify and/or escalate it, etc.",
            "check_pronouns": True,
        }
        codes = {item.code for item in lab.writing_findings(requirement)}
        self.assertEqual(
            codes,
            {"AND_OR_AMBIGUOUS", "OPEN_ENDED_LIST", "UNDEFINED_MODIFIER", "AMBIGUOUS_REFERENT"},
        )

    def test_universal_quantifier_needs_a_defined_population(self) -> None:
        incomplete = {"id": "REQ-Q", "statement": "Every proposal SHALL retain its source."}
        complete = incomplete | {"population": "ProposedUpdate records created by AI-2219"}
        self.assertEqual([item.code for item in lab.writing_findings(incomplete)], ["UNBOUNDED_QUANTIFIER"])
        self.assertEqual(lab.writing_findings(complete), ())

    def test_decision_table_has_one_match_for_representative_boundaries(self) -> None:
        cases = lab.load_json(lab.EVALUATION_PATH)["cases"]
        for case in cases[:5]:
            proposal, context = lab._case_objects(case)
            decision = lab.classify_proposal(proposal, context)
            self.assertNotIn("DECISION_TABLE_NONDETERMINISTIC", decision.reason_codes)

    def test_model_status_is_untrusted_and_conflict_is_recomputed(self) -> None:
        decision = lab.classify_proposal(self.proposal, self.context)
        self.assertEqual(self.proposal.model_status, "applied")
        self.assertEqual(decision.status, lab.ProposalStatus.CONFLICTING)
        self.assertEqual(decision.disposition, lab.Disposition.CONFLICT)

    def test_unauthorized_response_is_blocked_before_domain_decision(self) -> None:
        context = replace(self.context, broker_authorized=False)
        decision = lab.classify_proposal(self.proposal, context)
        self.assertEqual(decision.outcome, lab.Outcome.BLOCK)
        self.assertEqual(decision.reason_codes, ("BROKER_NOT_AUTHORIZED",))

    def test_unknown_and_ambiguous_fields_do_not_expand_schema(self) -> None:
        unknown = replace(self.proposal, field_candidates=("roof_membrane_year",))
        unknown_decision = lab.classify_proposal(unknown, self.context)
        self.assertEqual(unknown_decision.status, lab.ProposalStatus.UNMAPPED)
        ambiguous = replace(self.proposal, field_candidates=("building_value", "replacement_cost"))
        ambiguous_decision = lab.classify_proposal(ambiguous, self.context)
        self.assertEqual(ambiguous_decision.status, lab.ProposalStatus.MAPPING_AMBIGUOUS)

    def test_source_conflict_and_attachment_only_require_intervention(self) -> None:
        conflict = replace(self.proposal, candidate_values=(1998, 2001))
        self.assertEqual(lab.classify_proposal(conflict, self.context).status, lab.ProposalStatus.SOURCE_CONFLICT)
        attachment = replace(self.proposal, field_candidates=(), attachment_only=True)
        decision = lab.classify_proposal(attachment, self.context)
        self.assertEqual(decision.status, lab.ProposalStatus.ATTACHMENT_REVIEW_REQUIRED)
        self.assertEqual(decision.outcome, lab.Outcome.CLARIFY)

    def test_stale_duplicate_and_reordered_responses_are_blocked(self) -> None:
        stale = replace(self.proposal, submission_revision="S16")
        self.assertEqual(lab.classify_proposal(stale, self.context).status, lab.ProposalStatus.STALE)
        duplicate_context = replace(self.context, processed_response_ids=frozenset({"MSG-882"}))
        self.assertIn("DUPLICATE_RESPONSE", lab.classify_proposal(self.proposal, duplicate_context).reason_codes)
        reordered_context = replace(self.context, response_sequence=7)
        self.assertIn("OUT_OF_ORDER_RESPONSE", lab.classify_proposal(self.proposal, reordered_context).reason_codes)

    def test_schema_shape_does_not_replace_domain_validation(self) -> None:
        invalid = replace(self.proposal, proposed_value=-900000)
        decision = lab.classify_proposal(invalid, replace(self.context, existing_fields={}))
        self.assertEqual(decision.status, lab.ProposalStatus.REJECTED)
        self.assertEqual(decision.disposition, lab.Disposition.REJECT)

    def test_conflict_property_explores_more_than_one_example(self) -> None:
        result = lab.conflict_property(range(1990, 2000))
        self.assertEqual(result["checked_pairs"], 90)
        self.assertEqual(result["violations"], 0)

    def test_invalid_state_transitions_are_absent(self) -> None:
        self.assertIsNone(lab.transition_status(lab.ProposalStatus.CONFLICTING, "apply", "always"))
        self.assertEqual(
            lab.transition_status(lab.ProposalStatus.APPROVED, "apply", "valid_receipt_and_current"),
            lab.ProposalStatus.APPLIED,
        )

    def test_conflicting_proposal_cannot_reach_mutation_boundary(self) -> None:
        decision = lab.classify_proposal(self.proposal, self.context)
        update = lab.materialize_update(self.proposal, decision)
        assert update
        authorization = lab.authorize_application(update, self.context)
        changed, fields = lab.apply_in_memory({"construction_year": 1998, "occupancy": "office"}, update, authorization)
        self.assertEqual(authorization.outcome, lab.Outcome.BLOCK)
        self.assertEqual(changed["construction_year"], 1998)
        self.assertEqual(fields, ())

    def test_applied_proposal_cannot_reenter_mutation_boundary(self) -> None:
        context = replace(self.context, existing_fields={})
        decision = lab.classify_proposal(self.proposal, context)
        update = lab.materialize_update(self.proposal, decision)
        assert update
        replay = replace(update, status=lab.ProposalStatus.APPLIED)
        authorization = lab.authorize_application(replay, context)
        self.assertEqual(authorization.outcome, lab.Outcome.BLOCK)
        self.assertIn("STATE_NOT_APPLICABLE", authorization.reason_codes)

    def test_authorized_auto_apply_changes_only_the_target_field(self) -> None:
        context = replace(self.context, existing_fields={})
        decision = lab.classify_proposal(self.proposal, context)
        update = lab.materialize_update(self.proposal, decision)
        assert update
        authorization = lab.authorize_application(update, context)
        changed, fields = lab.apply_in_memory({"occupancy": "office", "broker_id": "BROKER-19"}, update, authorization)
        self.assertEqual(authorization.outcome, lab.Outcome.PROCEED)
        self.assertEqual(fields, ("construction_year",))
        self.assertEqual(changed["occupancy"], "office")
        self.assertEqual(changed["broker_id"], "BROKER-19")

    def test_approval_receipt_is_exact_current_expiring_and_single_use(self) -> None:
        context = replace(self.context, existing_fields={}, automatic_acceptance_fields=frozenset())
        decision = lab.classify_proposal(self.proposal, context)
        update = lab.materialize_update(self.proposal, decision)
        assert update
        approved = replace(update, status=lab.ProposalStatus.APPROVED)
        receipt = lab.ApprovalReceipt(
            "UW-22",
            "approved",
            "Proposal and provenance reviewed.",
            lab.proposal_digest(approved),
            "SUB-42",
            "S17",
            self.digest,
            "2026-09-20T20:00:00Z",
            "2026-09-20T22:00:00Z",
        )
        self.assertEqual(lab.authorize_application(approved, context, receipt, now=self.now).outcome, lab.Outcome.PROCEED)
        changed = replace(approved, proposed_value=2002)
        rejected = lab.authorize_application(changed, context, receipt, now=self.now)
        self.assertIn("PROPOSAL_CHANGED_AFTER_APPROVAL", rejected.reason_codes)
        replay = lab.authorize_application(approved, context, replace(receipt, consumed=True), now=self.now)
        self.assertIn("APPROVAL_ALREADY_USED", replay.reason_codes)

    def test_capability_readiness_is_not_a_percentage(self) -> None:
        statuses = {item.capability: item for item in lab.capability_readiness()}
        self.assertTrue(statuses["extract_response"].implementation_ready)
        self.assertFalse(statuses["apply_unverified_value"].implementation_ready)
        self.assertIn("OQ-BR-001", statuses["apply_unverified_value"].blocking_ids)
        self.assertFalse(statuses["overwrite_verified_value"].implementation_ready)
        self.assertIn("CAPABILITY_PROHIBITED", statuses["overwrite_verified_value"].reason_codes)

    def test_evaluation_separates_baseline_from_governed_decisions(self) -> None:
        result = lab.evaluate_cases()
        self.assertEqual(result["population"], 10)
        self.assertLess(result["baseline"]["accuracy"], result["governed"]["accuracy"])
        self.assertGreater(result["baseline"]["unsafe_auto_apply"], 0)
        self.assertEqual(result["governed"]["unsafe_auto_apply"], 0)

    def test_requirement_change_classifies_obligation_addition(self) -> None:
        before = {"id": "REQ-BR-030", "required_fields": ["source_response_id"]}
        after = {
            "id": "REQ-BR-030",
            "required_fields": ["source_response_id", "source_span", "model_version"],
        }
        change = lab.requirement_change(before, after)
        self.assertIn("obligation_added", change["change_kinds"])
        self.assertEqual(change["added_obligations"], ("model_version", "source_span"))

    def test_impact_analysis_separates_direct_and_transitive_consumers(self) -> None:
        impact = lab.impact_analysis("REQ-BR-030")
        self.assertEqual(impact["direct"], ("CONTRACT-BR-001",))
        self.assertEqual(
            impact["transitive"],
            ("API-CLIENT-BR", "API-SCHEMA-BR", "ExtractionAdapter"),
        )


if __name__ == "__main__":
    unittest.main()
