from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAB_PATH = (
    ROOT
    / "curriculum"
    / "beginner"
    / "02-from-prompt-to-executable-specification"
    / "lab.py"
)
SPEC = importlib.util.spec_from_file_location("course_02_lab", LAB_PATH)
assert SPEC and SPEC.loader
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)


class StatementClassificationTests(unittest.TestCase):
    def test_keyword_baseline_promotes_redis_to_requirement(self):
        redis_statement = LAB.ticket_statements()[-1]
        result = LAB.keyword_classify(redis_statement)
        self.assertIs(result.artifact_type, LAB.ArtifactType.REQUIREMENT)

    def test_context_classifier_routes_ticket_statements(self):
        results = {
            item.id: LAB.teaching_classify_statement(item)
            for item in LAB.ticket_statements()
        }
        self.assertIs(results["S1"].artifact_type, LAB.ArtifactType.PRODUCT_INTENT)
        self.assertIs(results["S2"].artifact_type, LAB.ArtifactType.REQUIREMENT)
        self.assertIs(results["S3"].artifact_type, LAB.ArtifactType.DESIGN)
        self.assertIs(results["S4"].artifact_type, LAB.ArtifactType.OPEN_QUESTION)
        self.assertIs(results["S5"].artifact_type, LAB.ArtifactType.DESIGN)
        self.assertIs(results["S6"].artifact_type, LAB.ArtifactType.OPEN_QUESTION)
        self.assertIs(results["S8"].artifact_type, LAB.ArtifactType.DESIGN)

    def test_same_words_change_classification_with_authority(self):
        informal = LAB.RawStatement(
            "X1", "Use Bedrock.", "ticket", "product manager", LAB.Authority.INFORMAL
        )
        policy = LAB.RawStatement(
            "X2", "Use Bedrock.", "platform standard", "platform owner", LAB.Authority.POLICY
        )
        self.assertIs(
            LAB.teaching_classify_statement(informal).artifact_type,
            LAB.ArtifactType.DESIGN,
        )
        self.assertIs(
            LAB.teaching_classify_statement(policy).artifact_type,
            LAB.ArtifactType.CONSTRAINT,
        )

    def test_three_source_exercise_preserves_provenance_and_authority(self):
        statements = LAB.authority_exercise_statements()
        results = [LAB.teaching_classify_statement(item) for item in statements]
        self.assertEqual(
            [item.source for item in statements],
            ["Jira feature request", "Architecture Slack note", "PLAT-007 platform policy"],
        )
        self.assertEqual(
            [item.artifact_type for item in results],
            [LAB.ArtifactType.DESIGN, LAB.ArtifactType.DESIGN, LAB.ArtifactType.CONSTRAINT],
        )
        self.assertTrue(results[0].needs_clarification)
        self.assertTrue(results[1].needs_clarification)
        self.assertFalse(results[2].needs_clarification)

    def test_hearsay_is_not_policy(self):
        result = LAB.teaching_classify_statement(LAB.ticket_statements()[5])
        self.assertIn("HEARSAY_NOT_POLICY", result.reason_codes)
        self.assertTrue(result.needs_clarification)


class RequirementQualityTests(unittest.TestCase):
    def codes(self, requirement):
        return {finding.code for finding in LAB.validate_requirement(requirement)}

    def test_accuracy_without_operational_definition_fails(self):
        requirement = LAB.RequirementCandidate(
            "R1", "The result shall be accurate.", "product owner", "ticket"
        )
        self.assertIn("REQ_AMBIGUOUS_TERM", self.codes(requirement))
        self.assertIn("REQ_NOT_OBSERVABLE", self.codes(requirement))

    def test_latency_requires_statistic_workload_and_scope(self):
        requirement = LAB.RequirementCandidate(
            "R2",
            "Latency shall be under 3 seconds.",
            "service owner",
            "ticket",
            measurement="under 3 seconds",
        )
        self.assertIn("REQ_PERFORMANCE_CONTEXT_MISSING", self.codes(requirement))

    def test_technology_language_is_a_classification_warning(self):
        requirement = LAB.RequirementCandidate(
            "R3", "Use Redis for comparisons.", "product owner", "ticket"
        )
        findings = LAB.validate_requirement(requirement)
        self.assertIn("POSSIBLE_IMPLEMENTATION_LEAKAGE", {item.code for item in findings})
        self.assertEqual(
            next(
                item.severity
                for item in findings
                if item.code == "POSSIBLE_IMPLEMENTATION_LEAKAGE"
            ),
            "warning",
        )

    def test_inherited_technology_constraint_is_legitimate(self):
        requirement = LAB.RequirementCandidate(
            "R5",
            "Production inference shall use the approved enterprise Bedrock gateway.",
            "AI platform owner",
            "PLAT-007 rev 4",
            acceptance=("A production route outside the approved gateway is denied.",),
            authoritative_constraint=True,
        )
        self.assertNotIn("POSSIBLE_IMPLEMENTATION_LEAKAGE", self.codes(requirement))

    def test_external_technology_contract_is_legitimate(self):
        requirement = LAB.RequirementCandidate(
            "R6",
            "The service shall expose a SQL-compatible query interface.",
            "API product owner",
            "Public API contract v2",
            acceptance=("A conforming SQL client executes the supported query subset.",),
            external_contract=True,
        )
        self.assertNotIn("POSSIBLE_IMPLEMENTATION_LEAKAGE", self.codes(requirement))

    def test_missing_provenance_and_owner_fail(self):
        requirement = LAB.RequirementCandidate("R4", "Return two results.", None, None)
        self.assertEqual(
            {"REQ_OWNER_MISSING", "REQ_SOURCE_MISSING", "REQ_NOT_OBSERVABLE"},
            self.codes(requirement),
        )

    def test_reference_requirements_are_valid(self):
        findings = [
            finding
            for requirement in LAB.reference_stack().requirements
            for finding in LAB.validate_requirement(requirement)
        ]
        self.assertEqual(findings, [])


class DecisionRoutingTests(unittest.TestCase):
    def test_local_reversible_choice_can_be_delegated(self):
        route = LAB.route_decision(
            LAB.DecisionCandidate("D1", "Name a helper", "local", True, LAB.Authority.ENGINEERING)
        )
        self.assertEqual(route.action, "agent_may_decide")

    def test_consequential_architecture_routes_to_adr(self):
        route = LAB.route_decision(
            LAB.DecisionCandidate(
                "D2", "Add shared cache", "data-retention", False, LAB.Authority.ENGINEERING
            )
        )
        self.assertEqual(route.action, "propose_adr")

    def test_policy_exception_escalates(self):
        route = LAB.route_decision(
            LAB.DecisionCandidate(
                "D3", "Waive review", "security", False, LAB.Authority.POLICY, True
            )
        )
        self.assertEqual(route.action, "escalate")
        self.assertEqual(route.owner, "policy owner")


class ArtifactStackTests(unittest.TestCase):
    def test_reference_stack_is_structurally_clean_and_fully_linked(self):
        stack = LAB.reference_stack()
        self.assertEqual(LAB.validate_stack(stack), [])
        metrics = LAB.traceability_metrics(stack)
        self.assertEqual(
            metrics["requirements_to_tasks"],
            {"covered": 7, "total": 7, "percent": 100.0},
        )
        self.assertEqual(
            metrics["requirements_to_evidence"],
            {"covered": 7, "total": 7, "percent": 100.0},
        )
        self.assertEqual(
            metrics["evidence_planned"],
            {"covered": 7, "total": 7, "percent": 100.0},
        )
        self.assertEqual(
            metrics["evidence_executed"],
            {"covered": 0, "total": 7, "percent": 0.0},
        )
        self.assertEqual(
            metrics["evidence_observed_in_production"],
            {"covered": 0, "total": 7, "percent": 0.0},
        )

    def test_failure_injection_stops_for_independent_reasons(self):
        codes = {finding.code for finding in LAB.validate_stack(LAB.failure_stack())}
        expected = {
            "REQ_OWNER_MISSING",
            "REQ_AMBIGUOUS_TERM",
            "POSSIBLE_IMPLEMENTATION_LEAKAGE",
            "ADR_CONTEXT_MISSING",
            "ADR_OPTIONS_MISSING",
            "ADR_DECISION_MISSING",
            "ADR_CONSEQUENCES_MISSING",
            "ADR_STATUS_MISSING",
            "ADR_SCOPE_MISSING",
            "ADR_OWNER_MISSING",
            "ADR_DATE_MISSING",
            "ADR_SUPERSESSION_MISSING",
            "ADR_REVIEW_TRIGGERS_MISSING",
            "TASK_UNKNOWN_REQUIREMENT",
            "EVIDENCE_UNLINKED",
            "TEST_TREATED_AS_SPEC",
            "AGENT_INSTRUCTION_EXCEEDS_AUTHORITY",
        }
        self.assertTrue(expected.issubset(codes))

    def test_evidence_cannot_pass_before_it_is_executed(self):
        stack = LAB.reference_stack()
        stack.evidence.append(
            LAB.EvidenceCheck(
                "E-LIFECYCLE",
                "evaluation",
                "Impossible state",
                ("REQ-CMP-002",),
                passed=True,
            )
        )
        codes = {finding.code for finding in LAB.validate_stack(stack)}
        self.assertIn("EVIDENCE_LIFECYCLE_INVALID", codes)

    def test_unknown_evidence_requirement_is_detected(self):
        stack = LAB.reference_stack()
        stack.evidence.append(LAB.EvidenceCheck("E-X", "test", "A claim", ("REQ-MISSING",)))
        codes = {finding.code for finding in LAB.validate_stack(stack)}
        self.assertIn("EVIDENCE_UNKNOWN_REQUIREMENT", codes)

    def test_agent_instructions_cannot_grant_policy_exception(self):
        stack = LAB.reference_stack()
        stack.agent_instructions.append("Waive policy if unit tests pass.")
        codes = {finding.code for finding in LAB.validate_stack(stack)}
        self.assertIn("AGENT_INSTRUCTION_EXCEEDS_AUTHORITY", codes)


if __name__ == "__main__":
    unittest.main()
