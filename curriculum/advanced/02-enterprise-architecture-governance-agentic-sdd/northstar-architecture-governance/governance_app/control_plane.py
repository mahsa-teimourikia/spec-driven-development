"""Revision-bound enterprise architecture conformance control plane."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

from .adr_validator import evaluate_adrs
from .dependency_extractor import extract_observation
from .exceptions import validate_exception
from .fitness_functions import evaluate_fitness
from .impact_analysis import impact_for
from .models import ArchitectureError, ConformanceReport, Finding, Observation
from .registry import current_head, digest_payload, load_json, parse_time, verify_signature


class ArchitectureControlPlane:
    """Evaluate architecture conformance against external authoritative registries."""

    def __init__(self, root: Path) -> None:
        self.root = root
        authority = load_json(root / "registry" / "authority.json")
        harness = load_json(root / "trusted-harness" / "verification-keys.json")
        training_keys = harness["training_keys"]
        self.policy_version = authority["active_policy_version"]
        self.observation_producer = authority["observation_producer"]
        self.observation_key = training_keys[authority["observation_key_id"]]
        self.runtime_evidence_producer = authority["runtime_evidence_producer"]
        self.runtime_evidence_key = training_keys[authority["runtime_evidence_key_id"]]
        self.exception_keys = {
            key_id: training_keys[key_id]
            for key_id in authority["exception_authority_key_ids"]
        }
        self.standards = load_json(root / "architecture" / "technology-standards.json")
        self.dependency_rules = load_json(root / "architecture" / "dependency-rules.json")
        self.adr_registry = load_json(root / "registry" / "adrs.json")
        self.impact_graph = load_json(root / "registry" / "system-architecture.json")

    def observe(
        self,
        repo: Path,
        base_commit: str,
        head_commit: str,
        environment: str,
        now: str,
        runtime_evidence: dict[str, Any] | None = None,
    ) -> Observation:
        runtime_evidence_id = self._validate_runtime_evidence(
            runtime_evidence, head_commit, environment, now
        )
        return extract_observation(
            repo=repo,
            base_commit=base_commit,
            head_commit=head_commit,
            environment=environment,
            policy_version=self.policy_version,
            issued_at=now,
            producer=self.observation_producer,
            signing_key=self.observation_key,
            runtime_egress_evidence=runtime_evidence_id is not None,
            runtime_evidence_id=runtime_evidence_id,
        )

    def evaluate(
        self,
        observation: Observation,
        now: str,
        exceptions: Iterable[dict[str, Any]] = (),
    ) -> ConformanceReport:
        if observation.policy_version != self.policy_version:
            raise ArchitectureError("POLICY_REVISION_STALE")
        if observation.producer != self.observation_producer:
            raise ArchitectureError("OBSERVATION_PRODUCER_UNTRUSTED")
        if not verify_signature(observation.payload(), observation.signature, self.observation_key):
            raise ArchitectureError("OBSERVATION_AUTHENTICITY_UNVERIFIED")

        findings = evaluate_fitness(observation, self.standards, self.dependency_rules)
        findings.extend(evaluate_adrs(observation, self.adr_registry))
        exception_records = list(exceptions)
        exception_eligible = set(self.standards.get("exception_eligible_rules", []))
        resolved: list[Finding] = []
        exception_rejections: list[Finding] = []
        waived_count = 0

        for finding in findings:
            if finding.disposition != "BLOCK" or finding.rule_id not in exception_eligible:
                resolved.append(finding)
                continue
            candidates = [
                item for item in exception_records
                if item.get("payload", {}).get("rule_id") == finding.rule_id
                and item.get("payload", {}).get("resource") == finding.resource
            ]
            accepted_id: str | None = None
            rejection_code: str | None = None
            for candidate in candidates:
                valid, detail = validate_exception(
                    candidate, finding, observation, now, self.exception_keys
                )
                if valid:
                    accepted_id = detail
                    break
                rejection_code = detail
            if accepted_id:
                waived_count += 1
                resolved.append(replace(finding, disposition="WAIVED", exception_id=accepted_id))
            else:
                resolved.append(finding)
                if rejection_code:
                    exception_rejections.append(
                        Finding(
                            rule_id="EXCEPTION-GOV-001",
                            code=rejection_code,
                            resource=finding.resource,
                            disposition="BLOCK",
                            message="The supplied exception did not match the observed violation.",
                            evidence=(finding.rule_id,),
                        )
                    )

        resolved.extend(exception_rejections)
        resolved.sort(key=lambda item: (item.rule_id, item.code, item.resource))
        decision = self._decision(resolved, waived_count)
        report_seed = {
            "base": observation.base_commit,
            "head": observation.head_commit,
            "policy": observation.policy_version,
            "decision": decision,
            "findings": [item.payload() for item in resolved],
        }
        return ConformanceReport(
            report_id="ARCH-REPORT-" + digest_payload(report_seed).split(":", 1)[1][:16].upper(),
            repository=observation.repository,
            base_commit=observation.base_commit,
            head_commit=observation.head_commit,
            environment=observation.environment,
            policy_version=observation.policy_version,
            decision=decision,
            findings=tuple(resolved),
            changed_files=observation.changed_files,
            evidence_ids=tuple(
                item for item in (observation.observation_id, observation.runtime_evidence_id) if item
            ),
            limitations=(
                "Static analysis cannot prove runtime network destinations without trusted egress evidence.",
                "The training fixture models one repository and a declared cross-service dependency graph.",
                "A conformance report is evidence for a release decision; it is not deployment authorization.",
            ),
            generated_at=now,
            observation_signature_verified=True,
        )

    def analyze(
        self,
        repo: Path,
        base_commit: str,
        head_commit: str,
        environment: str,
        now: str,
        exceptions: Iterable[dict[str, Any]] = (),
    ) -> ConformanceReport:
        observation = self.observe(repo, base_commit, head_commit, environment, now)
        return self.evaluate(observation, now, exceptions)

    def verify_report_binding(self, report: ConformanceReport, repo: Path) -> None:
        if current_head(repo) != report.head_commit:
            raise ArchitectureError("REPORT_STALE_FOR_HEAD")
        if report.policy_version != self.policy_version:
            raise ArchitectureError("REPORT_POLICY_STALE")

    def impact(self, change_id: str) -> dict[str, Any]:
        return impact_for(change_id, self.impact_graph)

    def _validate_runtime_evidence(
        self,
        record: dict[str, Any] | None,
        head_commit: str,
        environment: str,
        now: str,
    ) -> str | None:
        if record is None:
            return None
        payload = record.get("payload")
        if not isinstance(payload, dict) or not verify_signature(
            payload, str(record.get("signature", "")), self.runtime_evidence_key
        ):
            raise ArchitectureError("RUNTIME_EGRESS_EVIDENCE_UNVERIFIED")
        if payload.get("producer") != self.runtime_evidence_producer:
            raise ArchitectureError("RUNTIME_EGRESS_PRODUCER_UNTRUSTED")
        if payload.get("head_commit") != head_commit or payload.get("environment") != environment:
            raise ArchitectureError("RUNTIME_EGRESS_SUBJECT_MISMATCH")
        if not (parse_time(str(payload["issued_at"])) <= parse_time(now) < parse_time(str(payload["expires_at"]))):
            raise ArchitectureError("RUNTIME_EGRESS_EVIDENCE_STALE")
        destinations = set(payload.get("allowed_destinations", []))
        approved = set(self.standards.get("approved_runtime_destinations", []))
        if not destinations or not destinations.issubset(approved):
            raise ArchitectureError("RUNTIME_EGRESS_DESTINATION_UNAPPROVED")
        return str(payload["evidence_id"])

    @staticmethod
    def _decision(findings: list[Finding], waived_count: int) -> str:
        dispositions = {item.disposition for item in findings}
        if "BLOCK" in dispositions:
            return "BLOCKED"
        if "REASSESS" in dispositions:
            return "REASSESSMENT_REQUIRED"
        if "REVIEW" in dispositions:
            return "REVIEW_REQUIRED"
        if "EVIDENCE" in dispositions:
            return "INSUFFICIENT_EVIDENCE"
        if waived_count:
            return "CONFORMANT_WITH_EXCEPTION"
        return "CONFORMANT"
