"""Independent, specification-traceable quality evidence evaluation."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import QualityError, QualityFinding, QualityReport, SubjectObservation
from .registry import digest_payload, load_json, parse_time, verify_signature


VALID_ORACLES = {"specification", "independent_reference", "contract", "protected_dataset"}


class QualityControlPlane:
    """Evaluate evidence without accepting candidate self-certification."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.policy = load_json(root / "quality-policy.json")
        keys = load_json(root / "trusted-harness" / "verification-keys.json")["training_keys"]
        self.policy_version = self.policy["policy_version"]
        self.observation_producer = self.policy["observation_producer"]
        self.observation_key = keys[self.policy["observation_key_id"]]
        self.evidence_producer = self.policy["evidence_producer"]
        self.evidence_key = keys[self.policy["evidence_key_id"]]

    def evaluate(
        self,
        subject: SubjectObservation,
        evidence_records: Iterable[dict[str, Any]],
        now: str,
    ) -> QualityReport:
        self._validate_subject(subject)
        requirements = {item["id"]: item for item in self.policy["requirements"]}
        required_obligations = {
            (requirement_id, kind)
            for requirement_id, requirement in requirements.items()
            for kind in requirement["required_kinds"]
        }
        covered: set[tuple[str, str]] = set()
        findings: list[QualityFinding] = []
        accepted_ids: list[str] = []
        accepted_evidence_digests: dict[str, str] = {}
        mutation_outcomes: dict[str, str] = {}
        fault_outcomes: dict[str, str] = {}

        for record in evidence_records:
            payload = record.get("payload")
            if not isinstance(payload, dict):
                findings.append(self._evidence_finding("EVIDENCE_PAYLOAD_INVALID"))
                continue
            if payload.get("producer") != self.evidence_producer:
                findings.append(
                    QualityFinding(
                        code="CANDIDATE_EVIDENCE_NOT_ATTESTATION",
                        requirement_id="QUALITY-AUTHORITY",
                        resource=str(payload.get("evidence_id", "unknown")),
                        disposition="INFO",
                        message="Candidate-produced tests are useful diagnostics but not independent attestation.",
                    )
                )
                continue
            if not verify_signature(payload, str(record.get("signature", "")), self.evidence_key):
                findings.append(self._evidence_finding("EVIDENCE_AUTHENTICITY_UNVERIFIED"))
                continue
            validity_code = self._validate_evidence_binding(payload, subject, now)
            if validity_code:
                findings.append(self._evidence_finding(validity_code, str(payload.get("evidence_id", "unknown"))))
                continue
            evidence_id = str(payload["evidence_id"])
            payload_digest = digest_payload(payload)
            if evidence_id in accepted_evidence_digests and accepted_evidence_digests[evidence_id] != payload_digest:
                findings.append(
                    QualityFinding(
                        code="EVIDENCE_ID_COLLISION",
                        requirement_id="QUALITY-EVIDENCE",
                        resource=evidence_id,
                        disposition="BLOCK",
                        message="One evidence ID identifies conflicting authenticated payloads.",
                    )
                )
                continue
            accepted_evidence_digests[evidence_id] = payload_digest
            if evidence_id not in accepted_ids:
                accepted_ids.append(evidence_id)

            if not all(isinstance(payload.get(field, []), list) for field in ("cases", "mutations", "fault_experiments")):
                findings.append(self._evidence_finding("EVIDENCE_SCHEMA_INVALID", evidence_id))
                continue
            for case in payload.get("cases", []):
                if not isinstance(case, dict):
                    findings.append(self._evidence_finding("EVIDENCE_SCHEMA_INVALID", evidence_id))
                    continue
                self._evaluate_case(case, evidence_id, requirements, covered, findings)
            for mutation in payload.get("mutations", []):
                if not isinstance(mutation, dict):
                    findings.append(self._evidence_finding("EVIDENCE_SCHEMA_INVALID", evidence_id))
                    continue
                mutation_id = str(mutation.get("mutation_id", ""))
                outcome = str(mutation.get("outcome", ""))
                if mutation_id in self.policy["required_mutations"]:
                    previous = mutation_outcomes.get(mutation_id)
                    if previous is not None and previous != outcome:
                        findings.append(
                            QualityFinding(
                                code="MUTATION_OUTCOME_CONFLICT",
                                requirement_id="QUALITY-MUTATION",
                                resource=mutation_id,
                                disposition="BLOCK",
                                message="Authenticated evidence contains conflicting mutation outcomes.",
                            )
                        )
                    else:
                        mutation_outcomes[mutation_id] = outcome
                else:
                    findings.append(
                        QualityFinding(
                            code="UNREGISTERED_MUTATION",
                            requirement_id="QUALITY-MUTATION",
                            resource=mutation_id or "unknown",
                            disposition="INFO",
                            message="Unregistered mutations do not affect the governed mutation denominator.",
                            evidence=(evidence_id,),
                        )
                    )
            for experiment in payload.get("fault_experiments", []):
                if not isinstance(experiment, dict):
                    findings.append(self._evidence_finding("EVIDENCE_SCHEMA_INVALID", evidence_id))
                    continue
                experiment_id = str(experiment.get("experiment_id", ""))
                if experiment_id in self.policy["required_fault_experiments"]:
                    outcome = str(experiment.get("outcome", ""))
                    previous = fault_outcomes.get(experiment_id)
                    if previous is not None and previous != outcome:
                        findings.append(
                            QualityFinding(
                                code="FAULT_OUTCOME_CONFLICT",
                                requirement_id="REQ-QUALITY-003",
                                resource=experiment_id,
                                disposition="BLOCK",
                                message="Authenticated evidence contains conflicting fault outcomes.",
                            )
                        )
                    else:
                        fault_outcomes[experiment_id] = outcome

        for requirement_id, kind in sorted(required_obligations - covered):
            findings.append(
                QualityFinding(
                    code="REQUIRED_TEST_EVIDENCE_MISSING",
                    requirement_id=requirement_id,
                    resource=kind,
                    disposition="EVIDENCE",
                    message=f"No independent passing {kind} evidence covers {requirement_id}.",
                )
            )

        for mutation_id in self.policy["required_mutations"]:
            outcome = mutation_outcomes.get(mutation_id)
            if outcome is None:
                findings.append(
                    QualityFinding(
                        code="REQUIRED_MUTATION_NOT_EXECUTED",
                        requirement_id="QUALITY-MUTATION",
                        resource=mutation_id,
                        disposition="EVIDENCE",
                        message="A policy-selected mutation was absent from trusted evidence.",
                    )
                )
            elif outcome != "KILLED":
                findings.append(
                    QualityFinding(
                        code="CRITICAL_MUTANT_SURVIVED",
                        requirement_id="QUALITY-MUTATION",
                        resource=mutation_id,
                        disposition="BLOCK",
                        message="The test portfolio did not detect a specified critical defect.",
                    )
                )

        for experiment_id in self.policy["required_fault_experiments"]:
            outcome = fault_outcomes.get(experiment_id)
            if outcome is None:
                findings.append(
                    QualityFinding(
                        code="REQUIRED_FAILURE_EXPERIMENT_MISSING",
                        requirement_id="REQ-QUALITY-003",
                        resource=experiment_id,
                        disposition="EVIDENCE",
                        message="Required failure behavior has not been independently exercised.",
                    )
                )
            elif outcome != "SAFE":
                findings.append(
                    QualityFinding(
                        code="FAILURE_EXPERIMENT_UNSAFE",
                        requirement_id="REQ-QUALITY-003",
                        resource=experiment_id,
                        disposition="BLOCK",
                        message="The observed failure path violated the safe-state oracle.",
                    )
                )

        findings = self._deduplicate(findings)
        decision = self._decision(findings)
        killed = sum(outcome == "KILLED" for outcome in mutation_outcomes.values())
        required_mutations = len(self.policy["required_mutations"])
        passed_faults = sum(outcome == "SAFE" for outcome in fault_outcomes.values())
        report_seed = {
            "subject": subject.payload(),
            "decision": decision,
            "findings": [item.payload() for item in findings],
            "evidence_ids": sorted(accepted_ids),
        }
        return QualityReport(
            report_id="QUALITY-REPORT-" + digest_payload(report_seed).split(":", 1)[1][:16].upper(),
            change_id=subject.change_id,
            revision=subject.revision,
            specification_revision=subject.specification_revision,
            policy_version=subject.policy_version,
            decision=decision,
            findings=tuple(findings),
            evidence_ids=tuple(sorted(accepted_ids)),
            coverage={
                "covered_obligations": len(covered),
                "required_obligations": len(required_obligations),
                "value": len(covered) / len(required_obligations),
            },
            metrics={
                "mutation": {
                    "killed": killed,
                    "required": required_mutations,
                    "value": killed / required_mutations,
                    "excluded_from_denominator": 0,
                },
                "fault_experiments": {
                    "safe": passed_faults,
                    "required": len(self.policy["required_fault_experiments"]),
                },
                "claim": "deterministic labelled-fixture evidence, not production defect-detection accuracy",
            },
            limitations=(
                "Passing evidence covers only registered requirements, test kinds, mutations, and failure experiments.",
                "Mutation score measures the selected mutation set; it is not a universal test-quality metric.",
                "This quality decision is evidence for a protected release workflow and does not authorize release.",
            ),
            generated_at=now,
            release_authorized=False,
            merge_authorized=False,
            deployment_authorized=False,
            activation_authorized=False,
            delivery_state="READY_FOR_INTEGRATION_REVIEW",
        )

    def _validate_subject(self, subject: SubjectObservation) -> None:
        if subject.policy_version != self.policy_version:
            raise QualityError("QUALITY_POLICY_STALE")
        if subject.producer != self.observation_producer:
            raise QualityError("SUBJECT_PRODUCER_UNTRUSTED")
        if not verify_signature(subject.payload(), subject.signature, self.observation_key):
            raise QualityError("SUBJECT_AUTHENTICITY_UNVERIFIED")

    def _validate_evidence_binding(
        self,
        payload: dict[str, Any],
        subject: SubjectObservation,
        now: str,
    ) -> str | None:
        if not payload.get("evidence_id"):
            return "EVIDENCE_ID_MISSING"
        if payload.get("subject_digest") != digest_payload(subject.payload()):
            return "EVIDENCE_SUBJECT_MISMATCH"
        if payload.get("policy_version") != self.policy_version:
            return "EVIDENCE_POLICY_STALE"
        if payload.get("suite_revision") != self.policy["suite_revision"]:
            return "EVIDENCE_SUITE_STALE"
        try:
            issued = parse_time(str(payload["issued_at"]))
            expires = parse_time(str(payload["expires_at"]))
            moment = parse_time(now)
        except (KeyError, QualityError):
            return "EVIDENCE_TIME_INVALID"
        if not issued < expires:
            return "EVIDENCE_INTERVAL_INVALID"
        if not issued <= moment < expires:
            return "EVIDENCE_EXPIRED"
        return None

    def _evaluate_case(
        self,
        case: dict[str, Any],
        evidence_id: str,
        requirements: dict[str, dict[str, Any]],
        covered: set[tuple[str, str]],
        findings: list[QualityFinding],
    ) -> None:
        case_id = str(case.get("case_id", "unknown"))
        kind = str(case.get("kind", "unknown"))
        requirement_ids = tuple(str(item) for item in case.get("requirement_ids", []))
        unknown = sorted(set(requirement_ids) - set(requirements))
        if unknown:
            findings.append(
                QualityFinding(
                    code="UNKNOWN_REQUIREMENT_REFERENCE",
                    requirement_id="QUALITY-TRACEABILITY",
                    resource=case_id,
                    disposition="BLOCK",
                    message="Test evidence cites requirements outside the governed specification.",
                    evidence=tuple(unknown),
                )
            )
            return
        runs = tuple(str(item) for item in case.get("runs", []))
        if not runs or len(set(runs)) > 1:
            findings.append(
                QualityFinding(
                    code="FLAKY_TEST_NOT_EVIDENCE",
                    requirement_id="QUALITY-RELIABILITY",
                    resource=case_id,
                    disposition="REVIEW",
                    message="A nondeterministic result cannot satisfy a release-quality obligation.",
                    evidence=(evidence_id, *runs),
                )
            )
            return
        if case.get("oracle_source") not in VALID_ORACLES:
            findings.append(
                QualityFinding(
                    code="ORACLE_INDEPENDENCE_UNPROVEN",
                    requirement_id="QUALITY-ORACLE",
                    resource=case_id,
                    disposition="EVIDENCE",
                    message="The expected result is not grounded in a registered independent oracle.",
                    evidence=(evidence_id,),
                )
            )
            return
        if case.get("result") != "PASS" or any(run != "PASS" for run in runs):
            findings.append(
                QualityFinding(
                    code="INDEPENDENT_TEST_FAILED",
                    requirement_id=requirement_ids[0] if requirement_ids else "QUALITY-TRACEABILITY",
                    resource=case_id,
                    disposition="BLOCK",
                    message="Independent evidence contradicts the expected specification behavior.",
                    evidence=(evidence_id,),
                )
            )
            return
        for requirement_id in requirement_ids:
            if kind in requirements[requirement_id]["required_kinds"]:
                covered.add((requirement_id, kind))

    @staticmethod
    def _evidence_finding(code: str, resource: str = "quality-evidence") -> QualityFinding:
        disposition = "STALE" if code in {
            "EVIDENCE_SUBJECT_MISMATCH",
            "EVIDENCE_POLICY_STALE",
            "EVIDENCE_SUITE_STALE",
            "EVIDENCE_EXPIRED",
        } else "EVIDENCE"
        return QualityFinding(
            code=code,
            requirement_id="QUALITY-EVIDENCE",
            resource=resource,
            disposition=disposition,
            message="The supplied record cannot establish independent quality evidence.",
        )

    @staticmethod
    def _deduplicate(findings: list[QualityFinding]) -> list[QualityFinding]:
        unique = {
            (item.code, item.requirement_id, item.resource): item
            for item in findings
        }
        return [unique[key] for key in sorted(unique)]

    @staticmethod
    def _decision(findings: list[QualityFinding]) -> str:
        dispositions = {item.disposition for item in findings}
        if "BLOCK" in dispositions:
            return "BLOCKED"
        if "REVIEW" in dispositions:
            return "REVIEW_REQUIRED"
        if "STALE" in dispositions:
            return "STALE_EVIDENCE"
        if "EVIDENCE" in dispositions:
            return "INSUFFICIENT_EVIDENCE"
        return "CONFORMANT"
