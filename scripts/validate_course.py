"""Validate local links, lesson structure, notebooks, labs, and Hub assets."""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PAGES_BASE = "https://mahsa-teimourikia.github.io/spec-driven-development"


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def markdown_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.md") if ".git" not in path.parts)


def check_local_links() -> list[str]:
    errors: list[str] = []
    for document in markdown_files():
        for raw_target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = target.split("#", maxsplit=1)[0]
            if path_part and not (document.parent / path_part).resolve().exists():
                errors.append(f"broken local link in {document.relative_to(ROOT)}: {target}")
    return errors


def lesson_directories() -> list[Path]:
    return sorted(path.parent for path in (ROOT / "curriculum").glob("**/lab.py"))


def check_lesson_structure() -> list[str]:
    errors: list[str] = []
    lessons = lesson_directories()
    if not lessons:
        return ["no complete lesson directories found"]
    for lesson in lessons:
        notebooks = list(lesson.glob("*.ipynb"))
        if not (lesson / "README.md").exists():
            errors.append(f"missing README.md: {lesson.relative_to(ROOT)}")
        if len(notebooks) != 1:
            errors.append(
                f"expected exactly one notebook in {lesson.relative_to(ROOT)}, "
                f"found {len(notebooks)}"
            )
    return errors


def validate_and_execute_notebooks() -> list[str]:
    errors: list[str] = []
    for lesson in lesson_directories():
        notebooks = list(lesson.glob("*.ipynb"))
        if len(notebooks) != 1:
            continue
        notebook_path = notebooks[0]
        try:
            notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
            assert notebook.get("nbformat") == 4
            assert notebook.get("cells")
            namespace: dict[str, object] = {"__name__": "__notebook__"}
            with working_directory(lesson):
                for index, cell in enumerate(notebook["cells"]):
                    if cell.get("cell_type") != "code":
                        continue
                    source = "".join(cell.get("source", []))
                    exec(compile(source, f"{notebook_path.name}:cell-{index}", "exec"), namespace)
        except Exception as exc:  # validation should report the exact artifact
            errors.append(f"notebook failed {notebook_path.relative_to(ROOT)}: {exc}")
    return errors


def run_labs() -> list[str]:
    errors: list[str] = []
    for lesson in lesson_directories():
        lab = lesson / "lab.py"
        result = subprocess.run(
            [sys.executable, str(lab)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            errors.append(f"lab failed {lab.relative_to(ROOT)}:\n{result.stderr or result.stdout}")
    return errors


def run_repository_labs() -> list[str]:
    errors: list[str] = []
    for lab in sorted((ROOT / "curriculum").glob("**/repo_lab.py")):
        with tempfile.TemporaryDirectory(prefix="course-repo-lab-") as output:
            result = subprocess.run(
                [sys.executable, str(lab), "--candidate", "all", "--output", output],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        if result.returncode:
            errors.append(
                f"repository lab failed {lab.relative_to(ROOT)}:\n{result.stderr or result.stdout}"
            )
    return errors


def render_and_validate_diagrams() -> list[str]:
    errors: list[str] = []
    renderers = sorted((ROOT / "curriculum").glob("**/assets/render_diagram.py"))
    for renderer in renderers:
        result = subprocess.run(
            [sys.executable, str(renderer)],
            cwd=renderer.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            errors.append(
                f"diagram failed {renderer.relative_to(ROOT)}:\n{result.stderr or result.stdout}"
            )
    return errors


def check_site_assets() -> list[str]:
    required = [
        "index.html",
        "hub/index.html",
        "hub/styles.css",
        "hub/lessons.js",
        "hub/app.js",
        "quiz/index.html",
        "quiz/questions.js",
        "assets/one-plus-i.png",
    ]
    return [f"missing site asset: {item}" for item in required if not (ROOT / item).exists()]


def check_published_navigation() -> list[str]:
    """Keep entry-point links independent of GitHub's source-file renderer."""
    expected_links = {
        "README.md": [f"{PAGES_BASE}/hub/", f"{PAGES_BASE}/quiz/"],
        "curriculum/README.md": [f"{PAGES_BASE}/hub/"],
        "index.html": [f"{PAGES_BASE}/hub/"],
        "hub/index.html": [f"{PAGES_BASE}/quiz/"],
        "hub/app.js": [f"{PAGES_BASE}/quiz/"],
        "quiz/index.html": [f"{PAGES_BASE}/hub/"],
    }
    errors: list[str] = []
    for relative_path, urls in expected_links.items():
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        for url in urls:
            if url not in content:
                errors.append(f"missing published navigation URL in {relative_path}: {url}")

    hub = (ROOT / "hub/index.html").read_text(encoding="utf-8")
    for stale_target in ("../README.md", "../COURSE_PLAN.md", "../curriculum/README.md"):
        if stale_target in hub:
            errors.append(f"Hub links to a file absent from the Pages artifact: {stale_target}")
    return errors


def check_enterprise_fixture() -> list[str]:
    fixture = (
        ROOT
        / "curriculum"
        / "beginner"
        / "01-why-agentic-coding-changes-pdlc"
        / "northstar-underwriter"
    )
    required = [
        "ticket/JIRA-4821.md",
        "enterprise/privacy/PRIV-003-pii.md",
        "enterprise/ai-governance/AI-004-approved-models.md",
        "enterprise/ai-governance/AI-012-evaluation.md",
        "enterprise/ai-governance/AI-021-human-oversight.md",
        "enterprise/ai-governance/AI-021-GUIDANCE.md",
        "enterprise/payments/PCI-002-tokenization.md",
        "changes/policy-document-qa/clarifications.md",
        "changes/policy-document-qa/applicability.md",
        "changes/policy-document-qa/conflict-record.md",
        "changes/policy-document-qa/proposal.md",
        "changes/policy-document-qa/requirements.md",
        "changes/policy-document-qa/design.md",
        "changes/policy-document-qa/tasks.md",
        "changes/policy-document-qa/traceability.csv",
        "changes/unsafe/tests/test_candidate_claims.py",
        "changes/governed/tests/test_candidate_claims.py",
        "evals/cases.json",
        "evals/run_evals.py",
        "approvals/training-receipts.json",
    ]
    errors = [
        f"missing enterprise fixture artifact: {item}"
        for item in required
        if not (fixture / item).exists()
    ]
    reference = fixture / "changes" / "policy-document-qa"
    for path in reference.glob("*"):
        if path.is_file() and "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"unresolved TODO in reference artifact: {path.relative_to(ROOT)}")
    starter = fixture / "workshop" / "starter" / "policy-document-qa"
    if not starter.exists() or not any(
        "TODO" in path.read_text(encoding="utf-8")
        for path in starter.glob("*")
        if path.is_file()
    ):
        errors.append("learner starter workspace is missing editable TODO prompts")
    return errors


def check_course_02_artifact_stack() -> list[str]:
    scenario = (
        ROOT
        / "curriculum"
        / "beginner"
        / "02-from-prompt-to-executable-specification"
        / "northstar-policy-comparison"
    )
    required = [
        "ticket/AI-1842.md",
        "sources/AI-021-human-oversight.md",
        "sources/SEC-014-authorization-boundary.md",
        "sources/OBS-008-trace-data.md",
        "sources/SLO-CMP-001.md",
        "authority-exercise/README.md",
        "authority-exercise/01-jira.md",
        "authority-exercise/02-architecture-slack-note.md",
        "authority-exercise/03-platform-policy.md",
        "authority-exercise/reference-answer.md",
        "workshop/starter/classification.md",
        "workshop/starter/spec.md",
        "workshop/starter/design-and-decisions.md",
        "workshop/starter/traceability.csv",
        "reference/classification.md",
        "reference/clarifications.md",
        "reference/spec.md",
        "reference/design.md",
        "reference/ADR-007-comparison-caching.md",
        "reference/tasks.md",
        "reference/evidence-plan.md",
        "reference/AGENTS.md",
        "reference/traceability.csv",
    ]
    errors = [
        f"missing Course 02 artifact: {item}"
        for item in required
        if not (scenario / item).exists()
    ]
    for path in (scenario / "reference").glob("*"):
        if path.is_file() and "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"unresolved TODO in Course 02 reference: {path.relative_to(ROOT)}")
    starter = scenario / "workshop" / "starter"
    if not any(
        "TODO" in path.read_text(encoding="utf-8")
        for path in starter.glob("*")
        if path.is_file()
    ):
        errors.append("Course 02 starter workspace has no editable TODO prompts")

    lifecycle_columns = {
        "planned",
        "implemented",
        "executed",
        "passed",
        "approved",
        "observed_in_production",
        "dataset_or_case_set",
        "threshold",
        "evidence_version",
        "threshold_owner",
        "environment",
        "implementation_sha",
    }
    for relative_path in ("workshop/starter/traceability.csv", "reference/traceability.csv"):
        path = scenario / relative_path
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
            columns = set(rows[0]) if rows else set()
        missing = sorted(lifecycle_columns - columns)
        if missing:
            errors.append(
                f"Course 02 traceability lifecycle columns missing in {relative_path}: "
                f"{', '.join(missing)}"
            )

    reference_traceability = scenario / "reference" / "traceability.csv"
    with reference_traceability.open(newline="", encoding="utf-8") as handle:
        reference_rows = list(csv.DictReader(handle))
    for row in reference_rows:
        if row["planned"] != "yes" or any(
            row[stage] != "no"
            for stage in (
                "implemented",
                "executed",
                "passed",
                "approved",
                "observed_in_production",
            )
        ):
            errors.append(
                "Course 02 reference evidence must remain honestly staged as planned-only: "
                f"{row['requirement_id']}"
            )
        for field in ("dataset_or_case_set", "threshold", "evidence_version", "threshold_owner"):
            if not row[field].strip():
                errors.append(
                    f"Course 02 reference traceability lacks {field}: {row['requirement_id']}"
                )
    return errors


def check_course_03_hierarchy() -> list[str]:
    scenario = (
        ROOT
        / "curriculum"
        / "beginner"
        / "03-the-specification-hierarchy"
        / "northstar-broker-export"
    )
    required = [
        "README.md",
        "ticket/AI-1937.md",
        "ticket/change-context.json",
        "exceptions/EXC-009.json",
        "workshop/starter/README.md",
        "workshop/starter/applicability.csv",
        "workshop/starter/conflict-and-precedence.md",
        "workshop/starter/exception-review.md",
        "workshop/starter/effective-context.md",
        "reference/applicability.csv",
        "reference/conflict-and-precedence.md",
        "reference/exception-review.md",
        "reference/effective-context.md",
        "reference/provenance-manifest.csv",
    ]
    errors = [
        f"missing Course 03 artifact: {item}"
        for item in required
        if not (scenario / item).exists()
    ]

    catalog_paths = sorted((scenario / "catalog").glob("**/*.json"))
    if len(catalog_paths) != 14:
        errors.append(
            f"Course 03 catalog must contain 14 requirements, found {len(catalog_paths)}"
        )
    json_paths = catalog_paths + sorted((scenario / "exceptions").glob("*.json"))
    context_path = scenario / "ticket" / "change-context.json"
    if context_path.exists():
        json_paths.append(context_path)
    for path in json_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid Course 03 JSON {path.relative_to(ROOT)}: {exc}")
            continue
        if path in catalog_paths:
            for field in (
                "authority_domain",
                "scope_operator",
                "resource",
                "effective_until",
                "review_due",
            ):
                if field not in payload:
                    errors.append(
                        f"Course 03 requirement lacks {field}: {path.relative_to(ROOT)}"
                    )
            if payload.get("scope_operator") != "all":
                errors.append(
                    f"Course 03 requirement must declare ALL scope: {path.relative_to(ROOT)}"
                )

    reference = scenario / "reference"
    for path in reference.glob("*"):
        if path.is_file() and "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"unresolved TODO in Course 03 reference: {path.relative_to(ROOT)}")
    starter = scenario / "workshop" / "starter"
    if not any(
        "TODO" in path.read_text(encoding="utf-8")
        for path in starter.glob("*")
        if path.is_file()
    ):
        errors.append("Course 03 starter workspace has no editable TODO prompts")

    applicability_path = reference / "applicability.csv"
    if applicability_path.exists():
        with applicability_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        required_columns = {
            "requirement_id",
            "decision",
            "reason_codes",
            "evidence_ids",
        }
        columns = set(rows[0]) if rows else set()
        missing = sorted(required_columns - columns)
        if missing:
            errors.append(
                "Course 03 applicability matrix is missing columns: "
                + ", ".join(missing)
            )
        if len(rows) != 14:
            errors.append(
                f"Course 03 applicability matrix must cover 14 candidates, found {len(rows)}"
            )
        results = {row.get("decision") for row in rows}
        if not {"applicable", "not_applicable"}.issubset(results):
            errors.append("Course 03 reference must demonstrate applicable and N/A decisions")

    provenance_path = reference / "provenance-manifest.csv"
    if provenance_path.exists():
        with provenance_path.open(newline="", encoding="utf-8") as handle:
            provenance_rows = list(csv.DictReader(handle))
        provenance_columns = set(provenance_rows[0]) if provenance_rows else set()
        required_provenance_columns = {
            "requirement_id",
            "source_repository",
            "source_path",
            "version",
            "revision",
            "effective_until",
            "review_due",
        }
        missing = sorted(required_provenance_columns - provenance_columns)
        if missing:
            errors.append(
                "Course 03 provenance manifest is missing columns: "
                + ", ".join(missing)
            )
        if len(provenance_rows) != 14:
            errors.append(
                "Course 03 provenance manifest must cover all 14 candidates, "
                f"found {len(provenance_rows)}"
            )

    exception_path = scenario / "exceptions" / "EXC-009.json"
    if exception_path.exists():
        try:
            exception = json.loads(exception_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            exception = {}
        if exception:
            for field in (
                "requirement_id",
                "scope",
                "modification",
                "conditions",
                "approver",
                "approval_record",
                "expires_on",
                "source",
            ):
                if not exception.get(field):
                    errors.append(f"Course 03 exception lacks required field: {field}")
            scope = exception.get("scope", {})
            modification = exception.get("modification", {})
            if not scope.get("change_ids") or not scope.get("resources"):
                errors.append("Course 03 exception has incomplete change/resource scope")
            if not modification.get("control") or not modification.get(
                "permitted_expected"
            ):
                errors.append("Course 03 exception has incomplete modification")
            related = exception.get("related_unaffected_obligation_ids", [])
            if not isinstance(related, list) or not all(
                isinstance(item, str) and item.strip() for item in related
            ):
                errors.append(
                    "Course 03 exception has invalid related unaffected obligations"
                )
    return errors


def check_course_04_ownership() -> list[str]:
    lesson = ROOT / "curriculum" / "beginner" / "04-company-project-feature-requirements"
    scenario = lesson / "northstar-renewal"
    required = [
        "README.md",
        "ticket/AI-2048.md",
        "ticket/change-context.json",
        "project/policy-manifest.json",
        "project/agent-boundary.json",
        "project/AGENTS.md",
        "project/architecture/ARCH-031.json",
        "project/architecture/ARCH-032-weakening.json",
        "project/copied-policy/AI-030.json",
        "exceptions/EXC-014.json",
        "updates/AI-030-v4.json",
        "workshop/starter/README.md",
        "workshop/starter/requirement-location.csv",
        "workshop/starter/ownership-raci.csv",
        "workshop/starter/requirement-graph.csv",
        "workshop/starter/enforcement-map.csv",
        "workshop/starter/exception-review.md",
        "workshop/starter/impact-analysis.md",
        "workshop/starter/effective-context.md",
        "reference/requirement-location.csv",
        "reference/ownership-raci.csv",
        "reference/requirement-graph.csv",
        "reference/workshop-relationship-graph.csv",
        "reference/enforcement-map.csv",
        "reference/exception-review.md",
        "reference/impact-analysis.md",
        "reference/effective-context.md",
        "reference/release-context.json",
        "reference/runtime-evidence.json",
    ]
    errors = [
        f"missing Course 04 artifact: {item}"
        for item in required
        if not (scenario / item).exists()
    ]

    requirement_paths = sorted((scenario / "catalog").glob("**/*.json"))
    if len(requirement_paths) != 6:
        errors.append(
            f"Course 04 catalog must contain 6 candidate requirements, found {len(requirement_paths)}"
        )
    required_fields = {
        "id",
        "layer",
        "meaning_owner",
        "source_domain",
        "fixed_controls",
        "delegated_controls",
        "enforcement",
        "evidence_ids",
        "source",
    }
    ids: set[str] = set()
    for path in requirement_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid Course 04 JSON {path.relative_to(ROOT)}: {exc}")
            continue
        missing = sorted(required_fields - set(payload))
        if missing:
            errors.append(
                f"Course 04 requirement lacks fields {', '.join(missing)}: "
                f"{path.relative_to(ROOT)}"
            )
        requirement_id = payload.get("id")
        if requirement_id in ids:
            errors.append(f"duplicate Course 04 requirement ID: {requirement_id}")
        ids.add(requirement_id)
        source = payload.get("source", {})
        if not all(source.get(field) for field in ("repository", "path", "version", "revision")):
            errors.append(f"incomplete Course 04 provenance: {path.relative_to(ROOT)}")

    exception_path = scenario / "exceptions" / "EXC-014.json"
    if exception_path.exists():
        exception = json.loads(exception_path.read_text(encoding="utf-8"))
        for field in (
            "requirement_id",
            "requirement_revision",
            "scope",
            "requester",
            "approver",
            "approval_record",
            "modification",
            "rationale",
            "conditions",
            "expires_on",
            "source",
        ):
            if not exception.get(field):
                errors.append(f"Course 04 exception lacks required field: {field}")
        if exception.get("requester") == exception.get("approver"):
            errors.append(
                "Course 04 exception must keep separate requester and approver records"
            )
        modification = exception.get("modification", {})
        if not modification.get("field") or not modification.get("expected"):
            errors.append("Course 04 exception must name its modified control and value")
        if not isinstance(exception.get("conditions"), list) or not exception["conditions"]:
            errors.append("Course 04 exception must include compensating conditions")

    manifest_path = scenario / "project" / "policy-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("specialization_ids") != ["ARCH-031"]:
            errors.append("Course 04 manifest must select the valid specialization only")
        if manifest.get("exception_ids") != ["EXC-014"]:
            errors.append("Course 04 manifest must select the governed exception")

    boundary_path = scenario / "project" / "agent-boundary.json"
    if boundary_path.exists():
        boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
        authority = boundary.get("decision_authority", {})
        if not authority.get("permitted") or not authority.get("prohibited"):
            errors.append(
                "Course 04 agent boundary must separate path access from decision authority"
            )
        if "approve_exception" not in authority.get("prohibited", []):
            errors.append("Course 04 coding agent must not approve exceptions")

    specialization_path = scenario / "project" / "architecture" / "ARCH-031.json"
    parent_path = scenario / "catalog" / "enterprise" / "ai-governance" / "AI-030.json"
    if specialization_path.exists() and parent_path.exists():
        specialization = json.loads(specialization_path.read_text(encoding="utf-8"))
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
        rebound = set(specialization.get("bindings", {})) & set(
            parent.get("fixed_controls", {})
        )
        if rebound:
            errors.append(
                "Course 04 valid specialization rebinds fixed controls: "
                + ", ".join(sorted(rebound))
            )

    impact_path = scenario / "reference" / "impact-analysis.json"
    if impact_path.exists():
        impact = json.loads(impact_path.read_text(encoding="utf-8"))
        if impact.get("impact_detected") is not True:
            errors.append("Course 04 reference must identify the upstream impact")
        if impact.get("conformance_reevaluation_required") is not True:
            errors.append("Course 04 reference must require conformance re-evaluation")
        if impact.get("migration_required") is not None:
            errors.append(
                "Course 04 dependency traversal must not pre-judge code migration"
            )

    runtime_path = scenario / "reference" / "runtime-evidence.json"
    if runtime_path.exists():
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        required_runtime_fields = {
            "requirement_id",
            "control",
            "control_version",
            "observed_window",
            "consequential_recommendations",
            "review_receipts",
            "authorized_review_receipts",
            "legacy_endpoint_bypasses",
            "limitations",
        }
        missing = sorted(required_runtime_fields - set(runtime))
        if missing:
            errors.append(
                "Course 04 runtime evidence lacks fields: " + ", ".join(missing)
            )
        counts = [
            runtime.get("consequential_recommendations"),
            runtime.get("review_receipts"),
            runtime.get("authorized_review_receipts"),
            runtime.get("legacy_endpoint_bypasses"),
        ]
        if not all(isinstance(item, int) and item >= 0 for item in counts):
            errors.append("Course 04 runtime evidence counts must be non-negative integers")
        elif counts[1] > counts[0] or counts[2] > counts[1]:
            errors.append("Course 04 runtime evidence violates its denominators")

    reference = scenario / "reference"
    for path in reference.glob("*"):
        if path.is_file() and "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"unresolved TODO in Course 04 reference: {path.relative_to(ROOT)}")
    starter = scenario / "workshop" / "starter"
    if not any(
        "TODO" in path.read_text(encoding="utf-8")
        for path in starter.glob("*")
        if path.is_file()
    ):
        errors.append("Course 04 starter workspace has no editable TODO prompts")

    relationship_path = reference / "workshop-relationship-graph.csv"
    if relationship_path.exists():
        with relationship_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        required_relationships = {"specializes", "derived_from", "implements", "excepts"}
        if not required_relationships.issubset({row.get("relation") for row in rows}):
            errors.append("Course 04 reference does not demonstrate core relationship types")
        if any(not row.get("parent_revision") for row in rows):
            errors.append("Course 04 relationship graph has an unversioned parent binding")
    return errors


def main() -> None:
    checks = {
        "local links": check_local_links,
        "lesson structure": check_lesson_structure,
        "site assets": check_site_assets,
        "published navigation": check_published_navigation,
        "enterprise fixture": check_enterprise_fixture,
        "Course 02 artifact stack": check_course_02_artifact_stack,
        "Course 03 hierarchy": check_course_03_hierarchy,
        "Course 04 ownership": check_course_04_ownership,
        "diagrams": render_and_validate_diagrams,
        "labs": run_labs,
        "repository labs": run_repository_labs,
        "notebooks": validate_and_execute_notebooks,
    }
    errors: list[str] = []
    for name, check in checks.items():
        findings = check()
        if findings:
            errors.extend(findings)
            print(f"FAIL: {name}")
        else:
            print(f"PASS: {name}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: course scaffold is internally consistent")


if __name__ == "__main__":
    main()
