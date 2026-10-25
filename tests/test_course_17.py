import copy
import importlib.util
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LESSON = ROOT / "curriculum" / "intermediate" / "07-idea-discovery-spec-design-implementation"
SCENARIO = LESSON / "northstar-risk-summary"
SPEC = importlib.util.spec_from_file_location("course17_lab", SCENARIO / "lab.py")
lab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lab
SPEC.loader.exec_module(lab)


class Course17EndToEndPDLCTests(unittest.TestCase):
    def setUp(self):
        self.context, self.documents = lab.reference_context()

    def findings(self, mode):
        _, trace = lab.run_pipeline(mode=mode)
        return set(trace["validation_findings"])

    def test_context_selects_only_authorized_submission_evidence(self):
        self.assertEqual(
            set(self.documents),
            {"DOC-APP-001", "DOC-LOSS-001", "DOC-INJECT-001", "DOC-FLOOD-PENDING-001"},
        )
        self.assertNotIn("DOC-OTHER-001", self.documents)
        self.assertNotIn("DOC-RESTRICTED-001", self.documents)

    def test_context_digest_is_canonical(self):
        from app.context_builder import context_is_canonical
        self.assertTrue(context_is_canonical(self.context))

    def test_reference_stops_at_integration_review(self):
        result, trace = lab.run_pipeline()
        self.assertEqual(result.state, "READY_FOR_INTEGRATION_REVIEW")
        self.assertFalse(result.release_authorized)
        self.assertFalse(trace["release_authorized"])

    def test_valid_claim_retains_evidence_identity(self):
        result, _ = lab.run_pipeline()
        self.assertEqual(result.evidence_ids, ("DOC-APP-001",))

    def test_missing_source_blocks(self):
        self.assertIn("CITATION_NOT_FOUND", self.findings("missing_source"))

    def test_unsupported_claim_blocks(self):
        self.assertIn("EVIDENCE_DOES_NOT_SUPPORT_CLAIM", self.findings("unsupported_claim"))

    def test_topic_relevance_is_not_exact_claim_support(self):
        findings = self.findings("unsupported_claim")
        self.assertIn("EVIDENCE_INSUFFICIENT_FOR_CLAIM", findings)
        self.assertNotIn("CITATION_NOT_RELEVANT", findings)

    def test_adversarial_document_attempt_is_blocked_before_effect_gateway(self):
        result, trace = lab.run_pipeline(mode="prompt_injection")
        self.assertEqual(result.state, "BLOCKED")
        self.assertEqual(trace["attempted_actions"], ["send_broker_email"])
        self.assertIn("UNAUTHORIZED_SIDE_EFFECT", trace["validation_findings"])
        self.assertEqual(trace["effect_invocations"], [])

    def test_stale_context_blocks(self):
        self.assertIn("STALE_CONTEXT", self.findings("stale_context"))

    def test_stale_specification_blocks(self):
        self.assertIn("STALE_SPECIFICATION", self.findings("stale_specification"))

    def test_stale_architecture_blocks(self):
        self.assertIn("STALE_ARCHITECTURE", self.findings("stale_architecture"))

    def test_wrong_submission_blocks(self):
        self.assertIn("SUBMISSION_SCOPE_MISMATCH", self.findings("wrong_submission"))

    def test_model_cannot_mutate_underwriting_state(self):
        self.assertIn("UNAUTHORIZED_SIDE_EFFECT", self.findings("unauthorized_mutation"))

    def test_model_cannot_send_broker_message(self):
        self.assertIn("UNAUTHORIZED_SIDE_EFFECT", self.findings("unauthorized_send"))

    def test_evidence_revision_change_invalidates_proposal(self):
        from app.generator import DeterministicRiskGenerator
        from app.validator import validate_proposal
        proposal = DeterministicRiskGenerator().generate(self.context, self.documents)
        changed = copy.deepcopy(self.documents)
        changed["DOC-APP-001"] = replace(changed["DOC-APP-001"], revision=4)
        codes = {item.code for item in validate_proposal(proposal, self.context, changed).findings}
        self.assertIn("EVIDENCE_REVISION_MISMATCH", codes)

    def test_cited_evidence_is_reauthorized_during_validation(self):
        from app.generator import DeterministicRiskGenerator
        from app.validator import validate_proposal
        proposal = DeterministicRiskGenerator().generate(self.context, self.documents)
        changed = copy.deepcopy(self.documents)
        changed["DOC-APP-001"] = replace(
            changed["DOC-APP-001"],
            submission_id="SUB-OTHER",
            authorized=False,
        )
        codes = {item.code for item in validate_proposal(proposal, self.context, changed).findings}
        self.assertTrue({"EVIDENCE_NOT_AUTHORIZED", "EVIDENCE_SUBMISSION_MISMATCH"}.issubset(codes))

    def test_cited_evidence_outside_approved_context_is_blocked(self):
        from app.generator import DeterministicRiskGenerator
        from app.validator import validate_proposal
        proposal = DeterministicRiskGenerator().generate(self.context, self.documents)
        all_documents = {item.document_id: item for item in lab.load_documents()}
        restricted = all_documents["DOC-RESTRICTED-001"]
        claim = replace(proposal.claims[0], risk_code="FLOOD", evidence_ids=(restricted.document_id,))
        proposal = replace(proposal, claims=(claim,))
        codes = {item.code for item in validate_proposal(proposal, self.context, all_documents).findings}
        self.assertTrue({"EVIDENCE_NOT_AUTHORIZED", "EVIDENCE_OUTSIDE_APPROVED_CONTEXT"}.issubset(codes))

    def test_empty_evidence_abstains_without_exception(self):
        from app.generator import DeterministicRiskGenerator
        from app.validator import validate_proposal
        proposal = DeterministicRiskGenerator().generate(self.context, {})
        self.assertEqual(proposal.generation_outcome, "INSUFFICIENT_EVIDENCE")
        codes = {item.code for item in validate_proposal(proposal, self.context, {}).findings}
        self.assertIn("INSUFFICIENT_EVIDENCE", codes)

    def test_empty_risk_facts_abstain_without_exception(self):
        from app.context_builder import build_context
        from app.contracts import EvidenceDocument
        from app.generator import DeterministicRiskGenerator
        document = EvidenceDocument("DOC-EMPTY", "SUB-EMPTY", 1, "No risk facts.", (), (), True)
        context, documents = build_context(
            "SUB-EMPTY",
            [document],
            specification_revision=3,
            architecture_revision=lab.ARCHITECTURE_REVISION,
            repository_base=lab.REPOSITORY_BASE,
        )
        proposal = DeterministicRiskGenerator().generate(context, documents)
        self.assertEqual(proposal.generation_outcome, "NO_SUPPORTED_RISK_FACTORS")

    def test_missing_review_receipt_waits_for_human(self):
        result, _ = lab.run_pipeline(include_receipt=False)
        self.assertEqual(result.state, "READY_FOR_HUMAN_REVIEW")
        self.assertEqual(result.reason_codes, ("HUMAN_REVIEW_REQUIRED",))

    def test_review_receipt_binds_exact_proposal(self):
        result, _ = lab.run_pipeline(receipt_mutation="wrong_subject")
        self.assertEqual(result.state, "BLOCKED")
        self.assertIn("REVIEW_SUBJECT_MISMATCH", result.reason_codes)

    def test_expired_review_receipt_blocks(self):
        result, _ = lab.run_pipeline(receipt_mutation="expired")
        self.assertIn("REVIEW_RECEIPT_EXPIRED", result.reason_codes)

    def test_unverified_review_identity_blocks(self):
        result, _ = lab.run_pipeline(receipt_mutation="unverified")
        self.assertIn("REVIEW_IDENTITY_UNVERIFIED", result.reason_codes)

    def test_review_role_label_cannot_replace_authorized_principal(self):
        result, _ = lab.run_pipeline(receipt_mutation="unauthorized_principal")
        self.assertIn("REVIEW_PRINCIPAL_UNAUTHORIZED", result.reason_codes)

    def test_future_review_receipt_blocks(self):
        result, _ = lab.run_pipeline(receipt_mutation="future")
        self.assertIn("REVIEW_TIME_INVALID", result.reason_codes)

    def test_caller_cannot_self_assert_a_verified_receipt(self):
        from app.contracts import ApprovalReceipt
        from app.generator import DeterministicRiskGenerator
        from app.review import ReceiptStore, TrustedReceiptRegistry, review_for_integration
        from app.validator import validate_proposal
        proposal = DeterministicRiskGenerator().generate(self.context, self.documents)
        report = validate_proposal(proposal, self.context, self.documents)
        result = review_for_integration(
            report,
            ApprovalReceipt("CALLER-FORGED"),
            registry=TrustedReceiptRegistry(),
            evaluation_time=lab.EVALUATION_TIME,
            store=ReceiptStore(),
        )
        self.assertEqual(result.reason_codes, ("REVIEW_RECEIPT_NOT_FOUND",))

    def test_review_receipt_is_single_use(self):
        result, _ = lab.run_pipeline(replay=True)
        self.assertEqual(result.reason_codes, ("REVIEW_RECEIPT_REPLAYED",))

    def test_durable_receipt_consumption_survives_restart(self):
        exercise = lab.run_restart_replay_exercise()
        self.assertEqual(exercise["first_state"], "READY_FOR_INTEGRATION_REVIEW")
        self.assertTrue(exercise["atomic_uniqueness_enforced"])

    def test_specification_change_preserves_authority_and_invalidates_context(self):
        result, trace = lab.run_specification_change()
        self.assertEqual(result.state, "BLOCKED")
        self.assertTrue(trace["specification_authority_preserved"])
        self.assertNotEqual(trace["old_context_digest"], trace["new_context_digest"])
        self.assertTrue({"STALE_CONTEXT", "STALE_SPECIFICATION"}.issubset(trace["validation_findings"]))

    def test_all_seven_required_experiments_pass(self):
        report = lab.build_report()["experiments"]
        self.assertEqual((report["passed"], report["total"]), (7, 7))
        self.assertEqual(set(report["results"]), set(lab.EXPECTED_EXPERIMENTS))

    def test_direct_baseline_is_not_misrepresented_as_validated(self):
        report = lab.compare_baseline()
        self.assertEqual(report["direct_baseline_validated"], 0)
        self.assertEqual(report["governed_accuracy"], {"numerator": 7, "denominator": 7, "value": 1.0})
        self.assertIn("not a model-quality", report["claim"])

    def test_all_twelve_golden_scenarios_match(self):
        result = lab.run_conformance()
        self.assertEqual((result["passed"], result["total"]), (12, 12))

    def test_all_thirty_nine_labelled_mutations_are_detected(self):
        result = lab.run_mutation_evaluation()
        self.assertEqual((result["passed"], result["total"]), (39, 39))

    def test_requirements_and_acceptance_are_parseable_json_yaml(self):
        requirements = json.loads((SCENARIO / "specs" / "AI-2410" / "requirements.yaml").read_text())
        acceptance = json.loads((SCENARIO / "specs" / "AI-2410" / "acceptance.yaml").read_text())
        self.assertEqual(requirements["revision"], 3)
        self.assertEqual(len(requirements["requirements"]), 5)
        self.assertEqual(len(acceptance["acceptance"]), 5)

    def test_work_units_form_dependency_ordered_graph(self):
        payload = json.loads((SCENARIO / "specs" / "AI-2410" / "work-units.yaml").read_text())
        units = {item["id"]: item for item in payload["work_units"]}
        self.assertEqual(set(units), {"AWU-RISK-CONTRACT", "AWU-RISK-GENERATION", "AWU-RISK-VALIDATION", "AWU-RISK-INTEGRATION"})
        self.assertEqual(set(units["AWU-RISK-INTEGRATION"]["depends_on"]), {"AWU-RISK-GENERATION", "AWU-RISK-VALIDATION"})

    def test_pr_sequence_is_dependency_ordered_and_never_authorizes_release(self):
        payload = json.loads((SCENARIO / "specs" / "AI-2410" / "pr-sequence.yaml").read_text())
        sequence = payload["sequence"]
        self.assertEqual([item["id"] for item in sequence], ["PR-AI2410-01-CONTRACT", "PR-AI2410-02-IMPLEMENTATION", "PR-AI2410-03-INTEGRATION"])
        self.assertEqual(sequence[1]["depends_on"], [sequence[0]["id"]])
        self.assertEqual(sequence[2]["depends_on"], [sequence[1]["id"]])
        self.assertTrue(all("production_deployment" in item["excludes"] or "production_release" in item["excludes"] for item in sequence))

    def test_three_real_commits_preserve_dependency_order_and_invalidate_on_change(self):
        result = lab.run_three_commit_exercise()
        self.assertEqual(len(set(result["commits"].values())), 3)
        self.assertTrue(result["dependency_order_valid"])
        self.assertFalse(result["integration_valid_after_change"])
        self.assertEqual(result["invalidation_code"], "STALE_CONTRACT_REVISION")

    def test_traceability_covers_every_requirement_with_code_test_and_evidence(self):
        requirements = json.loads((SCENARIO / "specs" / "AI-2410" / "requirements.yaml").read_text())
        traceability = json.loads((SCENARIO / "specs" / "AI-2410" / "traceability.json").read_text())
        required_ids = {item["id"] for item in requirements["requirements"]}
        links = {item["requirement"]: item for item in traceability["links"]}
        self.assertEqual(set(links), required_ids)
        for item in links.values():
            self.assertTrue(item["design"])
            self.assertTrue(item["work_units"])
            self.assertTrue(item["code"])
            self.assertTrue(item["tests"])
            self.assertTrue(item["evidence"])

    def test_semantic_traceability_reference_is_clean(self):
        result = lab.run_traceability_evaluation()
        self.assertEqual(result["reference_findings"], [])

    def test_semantic_traceability_mutations_are_detected(self):
        result = lab.run_traceability_evaluation()
        self.assertEqual((result["passed"], result["total"]), (4, 4))
        self.assertEqual(
            {item["expected_code"] for item in result["results"]},
            {
                "UNKNOWN_TEST_ID",
                "UNRELATED_ACCEPTANCE_CRITERION",
                "STALE_REQUIREMENT_REVISION",
                "EVIDENCE_SUBJECT_MISMATCH",
            },
        )

    def test_evidence_manifest_is_bounded_and_revision_bound(self):
        manifest = json.loads((SCENARIO / "evidence" / "manifest.json").read_text())
        self.assertEqual(manifest["subject"]["specification_revision"], 3)
        self.assertEqual(len(manifest["evidence"]), 6)
        self.assertIn("no merge or release authorization", manifest["limitations"])
        self.assertTrue(manifest["run"]["implementation_digest"].startswith("sha256:"))
        self.assertTrue(manifest["run"]["dataset_digest"].startswith("sha256:"))
        for item in manifest["evidence"]:
            self.assertTrue(item["criterion_ids"])
            self.assertTrue(item["result_artifact_digest"].startswith("sha256:"))

    def test_evidence_manifest_is_reproduced_by_executed_results(self):
        stored = json.loads((SCENARIO / "evidence" / "manifest.json").read_text())
        self.assertEqual(stored, lab.build_evidence_manifest())

    def test_reference_lifecycle_does_not_self_authorize_release(self):
        package = json.loads((SCENARIO / "reference" / "lifecycle-package.json").read_text())
        self.assertEqual(package["integration"]["state"], "READY_FOR_INTEGRATION_REVIEW")
        self.assertEqual(package["merge"]["state"], "NOT_AUTHORIZED")
        self.assertEqual(package["release"]["state"], "NOT_AUTHORIZED")

    def test_starter_retains_exactly_four_learner_decisions(self):
        source = (SCENARIO / "workshop" / "starter" / "lifecycle-package.json").read_text()
        self.assertEqual(source.count("TODO"), 4)

    def test_notebook_has_no_stored_outputs(self):
        notebook = json.loads((SCENARIO / "end_to_end_agentic_pdlc.ipynb").read_text())
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell.get("outputs"), [])
                self.assertIsNone(cell.get("execution_count"))

    def test_diagram_spec_validates_and_render_is_reproducible(self):
        renderer_spec = importlib.util.spec_from_file_location("course17_diagram", SCENARIO / "assets" / "render_diagram.py")
        renderer = importlib.util.module_from_spec(renderer_spec)
        renderer_spec.loader.exec_module(renderer)
        payload = json.loads((SCENARIO / "assets" / "end-to-end-pdlc-spec.json").read_text())
        renderer.validate(payload)
        self.assertEqual((SCENARIO / "assets" / "end-to-end-pdlc.svg").read_text(), renderer.render(payload))

    def test_candidate_is_explicitly_an_anti_pattern(self):
        candidate = json.loads((SCENARIO / "candidate" / "direct-coding-output.json").read_text())
        self.assertEqual(candidate["label"], "EDUCATIONAL_ANTI_PATTERN")
        self.assertEqual(candidate["state"], "NOT_ELIGIBLE_FOR_INTEGRATION")


if __name__ == "__main__":
    unittest.main()
