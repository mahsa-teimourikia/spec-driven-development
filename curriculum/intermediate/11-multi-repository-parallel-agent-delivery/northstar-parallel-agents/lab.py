#!/usr/bin/env python3
"""Course 21 lab: governed parallel-agent delivery across real Git repositories."""

from __future__ import annotations

import json
from pathlib import Path

from parallel_app.simulation import (
    evaluation_checks,
    golden_scenarios,
    run_reference,
    scheduling_comparison,
)


ROOT = Path(__file__).resolve().parent


def build_report() -> dict[str, object]:
    plane, revisions, manifest, system_results, decision = run_reference(ROOT)
    conformance = golden_scenarios(ROOT)
    evaluation = evaluation_checks(ROOT)
    passed = (
        decision.state == "READY_FOR_INTEGRATION_REVIEW"
        and all(system_results.values())
        and all(conformance.values())
        and all(evaluation.values())
    )
    return {
        "course_validation": {
            "status": "PASS" if passed else "FAIL",
            "fixture_boundary": "credential-free deterministic teaching system",
        },
        "candidate_assessment": {
            "status": decision.state,
            "findings": list(decision.findings),
            "revision_set_digest": decision.revision_set_digest,
            "component_commits": dict(decision.component_commits),
            "contract_revision": decision.contract_revision,
            "merge_authorized": decision.merge_authorized,
            "deployment_authorized": decision.deployment_authorized,
            "release_authorized": decision.release_authorized,
        },
        "repository_observations": {
            repository: {
                "baseline_commit": revision.baseline_commit,
                "candidate_commit": revision.candidate_commit,
                "changed_paths": list(revision.changed_paths),
                "tests_passed": revision.tests_passed,
            }
            for repository, revision in revisions.items()
        },
        "integration_manifest": manifest,
        "system_scenarios": {
            "passed": sum(system_results.values()),
            "total": len(system_results),
            "results": system_results,
        },
        "conformance": {
            "passed": sum(conformance.values()),
            "total": len(conformance),
            "results": conformance,
        },
        "evaluation": {
            "passed": sum(evaluation.values()),
            "total": len(evaluation),
            "population": {
                "positive": 7,
                "negative": 15,
                "boundary": 5,
                "failure_recovery": 3,
            },
            "results": evaluation,
        },
        "scheduling_comparison": scheduling_comparison(ROOT),
        "observability": {
            "event_count": len(plane.events),
            "recorded_fields": [
                "work_unit_id",
                "workload_identity",
                "lease_generation",
                "base_commit",
                "candidate_commit",
                "contract_revision",
                "evidence_id",
                "terminal_state",
            ],
            "private_reasoning_recorded": False,
        },
        "limitations": [
            "Elapsed hours are deterministic event-simulation values, not production benchmarks.",
            "In-memory locking demonstrates semantics but is not a distributed consensus implementation.",
            "Production adoption requires authenticated workload identity, durable transactional storage, signed provenance, and enforced repository and release controls.",
        ],
    }


def main() -> None:
    print(json.dumps(build_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
