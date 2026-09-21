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


def check_course_05_discovery() -> list[str]:
    lesson = ROOT / "curriculum" / "beginner" / "05-requirements-engineering-for-agents"
    scenario = lesson / "northstar-broker-follow-up"
    required = [
        "README.md",
        "evaluation-cases.json",
        "ticket/AI-2176.md",
        "sources/operating-baseline.json",
        "sources/stakeholder-decisions.md",
        "sources/underwriting-requirements.json",
        "workshop/starter/README.md",
        "workshop/starter/ambiguity-register.md",
        "workshop/starter/requirements-package.json",
        "reference/requirements-package.json",
    ]
    errors = [
        f"missing Course 05 artifact: {item}"
        for item in required
        if not (scenario / item).exists()
    ]
    if errors:
        return errors

    for relative_path in (
        "workshop/starter/requirements-package.json",
        "reference/requirements-package.json",
        "evaluation-cases.json",
        "sources/operating-baseline.json",
        "sources/underwriting-requirements.json",
    ):
        path = scenario / relative_path
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid Course 05 JSON {relative_path}: {exc}")

    reference_path = scenario / "reference" / "requirements-package.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    required_sections = {
        "specification", "problem", "scope", "glossary", "sources", "release", "capabilities",
        "requirements", "invariants", "questions", "failure_matrix", "tasks", "agent_authority",
    }
    missing_sections = required_sections - reference.keys()
    if missing_sections:
        errors.append(f"Course 05 reference is missing sections: {sorted(missing_sections)}")
    capability_ids = {item["id"] for item in reference.get("capabilities", [])}
    if capability_ids != {"analyze_missing_items", "draft_message", "send_message"}:
        errors.append("Course 05 reference must declare analysis, drafting, and sending capabilities")
    send_questions = {
        item["id"] for item in reference.get("questions", [])
        if item.get("status") == "open" and "send_message" in item.get("blocks_capabilities", [])
    }
    if send_questions != {"OQ-017"}:
        errors.append("Course 05 automatic send must remain blocked only by open question OQ-017")
    release = reference.get("release", {})
    if set(release.get("included_capabilities", [])) != {"analyze_missing_items", "draft_message"}:
        errors.append("Course 05 Release 1 must include only analysis and drafting")
    if release.get("deferred_capabilities") != ["send_message"] or release.get("blocked_by") != ["OQ-017"]:
        errors.append("Course 05 send capability must be explicitly deferred by OQ-017")
    send_requirements = [
        item for item in reference.get("requirements", []) if item.get("capability") == "send_message"
    ]
    if not send_requirements or any(item.get("status") != "approved" for item in send_requirements):
        errors.append("Course 05 send controls must remain approved durable requirements")
    if any(
        item.get("release_applicability")
        != {"release_id": "release-1-draft-only", "status": "deferred", "blocked_by": ["OQ-017"]}
        for item in send_requirements
    ):
        errors.append("Course 05 approved send requirements must be deferred from Release 1")
    analysis_requirement = next(
        (item for item in reference.get("requirements", []) if item.get("id") == "REQ-FU-001"),
        {},
    )
    required_gap_fields = {
        "id", "requirement_id", "field", "label", "status", "reason_code",
        "requirement_evidence_ids", "observation",
    }
    if analysis_requirement.get("behavior", {}).get("output") != "RequirementGap[]":
        errors.append("Course 05 analysis output must use typed RequirementGap records")
    if set(analysis_requirement.get("behavior", {}).get("required_fields", [])) != required_gap_fields:
        errors.append("Course 05 RequirementGap contract is missing typed status or evidence fields")
    if "send a message" not in reference.get("agent_authority", {}).get("forbidden", []):
        errors.append("Course 05 agent boundary must forbid sending a message")
    requirement_ids = {item["id"] for item in reference.get("requirements", [])}
    task_links = {
        requirement_id
        for task in reference.get("tasks", [])
        for requirement_id in task.get("requirement_ids", [])
    }
    if requirement_ids - task_links:
        errors.append("Course 05 reference contains approved requirements without task links")
    task_04 = next((item for item in reference.get("tasks", []) if item.get("id") == "TASK-04"), {})
    if task_04.get("release_status") != "deferred" or task_04.get("blocked_by") != ["OQ-017"]:
        errors.append("Course 05 TASK-04 must remain deferred until OQ-017 closes")

    evaluation = json.loads((scenario / "evaluation-cases.json").read_text(encoding="utf-8"))
    cases = evaluation.get("cases", [])
    if len(cases) != 8 or sum(bool(item.get("expected_finding")) for item in cases) != 5:
        errors.append("Course 05 evaluation must contain eight cases with five labelled findings")

    reference_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (scenario / "reference").glob("*")
        if path.is_file()
    )
    if "TODO" in reference_text:
        errors.append("Course 05 reference artifacts contain unresolved TODOs")
    starter_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (scenario / "workshop" / "starter").glob("*")
        if path.is_file()
    )
    if "TODO" not in starter_text:
        errors.append("Course 05 starter workspace has no editable TODO prompts")
    return errors


def check_course_06_executable_requirements() -> list[str]:
    lesson = ROOT / "curriculum" / "beginner" / "06-writing-executable-requirements"
    scenario = lesson / "northstar-broker-response"
    required = [
        "README.md",
        "evaluation-cases.json",
        "ticket/AI-2219.md",
        "sources/stakeholder-decisions.md",
        "sources/field-rules.json",
        "sources/authorization-policy.json",
        "workshop/starter/README.md",
        "workshop/starter/glossary.md",
        "workshop/starter/requirements.md",
        "workshop/starter/scenarios.md",
        "workshop/starter/decision-table.csv",
        "workshop/starter/state-machine.json",
        "workshop/starter/contracts/proposed-update.schema.json",
        "reference/behavior-contract.json",
        "reference/requirements.md",
        "reference/scenarios.json",
        "reference/scenarios.md",
        "reference/decision-table.json",
        "reference/decision-table.csv",
        "reference/state-machine.json",
        "reference/traceability.csv",
        "reference/contracts/proposed-update.schema.json",
    ]
    errors = [
        f"missing Course 06 artifact: {item}"
        for item in required
        if not (scenario / item).exists()
    ]
    if errors:
        return errors

    json_paths = [
        scenario / "evaluation-cases.json",
        scenario / "sources" / "field-rules.json",
        scenario / "sources" / "authorization-policy.json",
        scenario / "workshop" / "starter" / "state-machine.json",
        scenario / "workshop" / "starter" / "contracts" / "proposed-update.schema.json",
        scenario / "reference" / "behavior-contract.json",
        scenario / "reference" / "scenarios.json",
        scenario / "reference" / "decision-table.json",
        scenario / "reference" / "state-machine.json",
        scenario / "reference" / "contracts" / "proposed-update.schema.json",
    ]
    payloads: dict[Path, dict] = {}
    for path in json_paths:
        try:
            payloads[path] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid Course 06 JSON {path.relative_to(ROOT)}: {exc}")
    if errors:
        return errors

    reference = scenario / "reference"
    contract_path = reference / "behavior-contract.json"
    contract = payloads[contract_path]
    required_sections = {
        "specification", "scope", "sources", "artifact_authority", "controlled_vocabulary",
        "capabilities", "requirements", "contracts", "invariants", "state_requirements",
        "questions", "agent_authority",
    }
    missing_sections = required_sections - contract.keys()
    if missing_sections:
        errors.append(f"Course 06 behavior contract is missing sections: {sorted(missing_sections)}")

    authority = contract.get("artifact_authority", {})
    expected_roles = {
        "normative_requirement", "normative_elaboration", "normative_example", "informative", "evidence",
    }
    if not expected_roles.issubset(authority):
        errors.append("Course 06 must declare authority for every representation role")
    if authority.get("conflict_outcome") != "SPEC_CONTRADICTION_STOP":
        errors.append("Course 06 normative contradictions must stop for owner resolution")

    capability_status = {
        item.get("id"): item.get("status") for item in contract.get("capabilities", [])
    }
    expected_capabilities = {
        "extract_response": "ready",
        "classify_proposal": "ready",
        "create_proposal": "ready",
        "apply_unverified_value": "review_required",
        "apply_reviewed_conflict": "review_required",
        "automatically_overwrite_verified_value": "prohibited",
    }
    if capability_status != expected_capabilities:
        errors.append("Course 06 capability readiness boundary changed unexpectedly")

    questions = contract.get("questions", [])
    open_application_questions = {
        item.get("id")
        for item in questions
        if item.get("status") == "open"
        and "apply_unverified_value" in item.get("blocks_capabilities", [])
    }
    if open_application_questions != {"OQ-BR-001"}:
        errors.append("Course 06 unverified application must remain blocked by OQ-BR-001")

    requirements = {item.get("id"): item for item in contract.get("requirements", [])}
    expected_patterns = {
        "REQ-BR-001": "ubiquitous",
        "REQ-BR-003": "event_driven",
        "REQ-BR-004": "state_driven",
        "REQ-BR-005": "unwanted_behavior",
        "REQ-BR-006": "optional_feature",
        "REQ-BR-007": "complex",
        "REQ-BR-021": "unwanted_behavior",
        "REQ-BR-037": "event_driven",
    }
    for identifier, pattern in expected_patterns.items():
        if requirements.get(identifier, {}).get("ears_pattern") != pattern:
            errors.append(f"Course 06 {identifier} must demonstrate {pattern} EARS")
    readiness_fields = {
        "id", "revision", "status", "role", "ears_pattern", "capability", "owner",
        "source_ids", "statement", "actor", "trigger", "inputs", "preconditions", "behavior",
        "prohibited", "postconditions", "frame_conditions", "failure_behavior", "evidence_ids",
    }
    for identifier, requirement in requirements.items():
        missing = sorted(field for field in readiness_fields if not requirement.get(field))
        if missing:
            errors.append(f"Course 06 requirement {identifier} lacks fields: {', '.join(missing)}")

    table = payloads[reference / "decision-table.json"]
    conflict_row = next((row for row in table.get("rows", []) if row.get("id") == "DT-07"), {})
    if conflict_row.get("outcome") != "conflict" or conflict_row.get("existing_verified") is not True:
        errors.append("Course 06 verified-conflict table row must remain conflict")
    if len(table.get("rows", [])) != 8:
        errors.append("Course 06 decision table must retain eight non-overlapping teaching rows")
    if "existing_verification_known_when_value_present" not in table.get("preconditions", []):
        errors.append("Course 06 decision table must require known existing verification state")

    state_machine = payloads[reference / "state-machine.json"]
    forbidden = {
        ("extracted", "apply", "applied"),
        ("conflicting", "apply", "applied"),
        ("rejected", "apply", "applied"),
        ("stale", "apply", "applied"),
    }
    declared_valid = {
        (item.get("current"), item.get("event"), item.get("next"))
        for item in state_machine.get("transitions", [])
    }
    declared_invalid = {
        (item.get("current"), item.get("event"), item.get("next"))
        for item in state_machine.get("critical_invalid_transitions", [])
    }
    if forbidden & declared_valid or not forbidden.issubset(declared_invalid):
        errors.append("Course 06 state model must declare and prohibit all critical apply transitions")
    expected_conflict_path = {
        ("conflicting", "request_review", "awaiting_review"),
        ("awaiting_review", "approve_replacement", "approved"),
        ("approved", "apply", "applied"),
    }
    if not expected_conflict_path.issubset(declared_valid):
        errors.append("Course 06 state model must preserve the explicit reviewed-conflict path")
    guards = state_machine.get("guards", {})
    required_guard_conditions = {
        "approval proposal digest equals the current ProposedUpdate digest",
        "submission revision is current",
        "requirement-context digest is current",
        "approval is unexpired",
        "approval is unused",
    }
    receipt_conditions = set(guards.get("valid_receipt_and_current", {}).get("conditions", []))
    if not required_guard_conditions.issubset(receipt_conditions):
        errors.append("Course 06 approval guard must define exact proposal and current-context semantics")
    conflict_conditions = set(guards.get("valid_conflict_replacement_receipt", {}).get("conditions", []))
    if "approval resolution is replace_verified_value" not in conflict_conditions:
        errors.append("Course 06 conflict replacement guard must bind the selected resolution")
    if {"source": "conflicting", "target": "applied", "via": "approved"} not in state_machine.get("required_waypoints", []):
        errors.append("Course 06 conflict application must pass through the approved waypoint")

    schema = payloads[reference / "contracts" / "proposed-update.schema.json"]
    required_proposal_fields = {
        "proposal_id", "submission_id", "submission_revision", "requirement_context_digest",
        "field", "proposed_value", "source_response_id", "source_span", "requirement_id",
        "model_version", "evidence_ids", "origin_disposition", "status",
    }
    if set(schema.get("required", [])) != required_proposal_fields:
        errors.append("Course 06 ProposedUpdate schema lost a required trust-boundary field")
    if schema.get("additionalProperties") is not False:
        errors.append("Course 06 ProposedUpdate schema must reject undeclared fields")

    agent_forbidden = set(contract.get("agent_authority", {}).get("forbidden", []))
    if not {"apply production updates", "adjudicate normative contradictions", "widen supported fields"}.issubset(agent_forbidden):
        errors.append("Course 06 agent boundary grants consequential authority")

    evaluation = payloads[scenario / "evaluation-cases.json"]
    if len(evaluation.get("cases", [])) != 11 or not evaluation.get("limitations"):
        errors.append("Course 06 evaluation must contain eleven labelled cases and limitations")

    with (reference / "traceability.csv").open(newline="", encoding="utf-8") as handle:
        trace_rows = list(csv.DictReader(handle))
    relations = {row.get("relationship") for row in trace_rows}
    if not {"elaborated_by", "illustrated_by", "evidenced_by", "implemented_by"}.issubset(relations):
        errors.append("Course 06 traceability must connect specification, examples, tests, and work")
    declared_trace_sources = {
        item.get("id")
        for section in ("requirements", "invariants", "state_requirements")
        for item in contract.get(section, [])
    }
    traced_sources = {row.get("source_id") for row in trace_rows}
    if contract.get("specification", {}).get("traceability_scope") != "complete_reference":
        errors.append("Course 06 reference must declare its traceability scope")
    untraced = sorted(declared_trace_sources - traced_sources)
    if untraced:
        errors.append(f"Course 06 reference has untraced normative records: {untraced}")

    reference_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in reference.rglob("*")
        if path.is_file()
    )
    if "TODO" in reference_text:
        errors.append("Course 06 reference artifacts contain unresolved TODOs")
    starter = scenario / "workshop" / "starter"
    starter_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in starter.rglob("*")
        if path.is_file()
    )
    if "TODO" not in starter_text:
        errors.append("Course 06 starter workspace has no editable TODO prompts")

    result = subprocess.run(
        [sys.executable, str(lesson / "lab.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(result.stdout) if result.returncode == 0 else {}
    except json.JSONDecodeError:
        report = {}
    if report.get("requirement_findings") or report.get("consistency_findings"):
        errors.append("Course 06 reference contract must pass requirement and consistency checks")
    if report.get("table_shape", {}).get("declared_fact_combinations") != 20 or report.get("table_shape", {}).get("findings"):
        errors.append("Course 06 decision table must match exactly once across its declared fact space")
    if report.get("state_graph", {}).get("findings"):
        errors.append("Course 06 state graph must preserve reachability, terminality, and required waypoints")
    governed = report.get("evaluation", {}).get("governed", {})
    if governed.get("correct") != 11 or governed.get("unsafe_auto_apply") != 0:
        errors.append("Course 06 governed evaluation must classify all eleven cases without unsafe apply")
    property_check = report.get("property_check", {})
    if property_check.get("checked_pairs", 0) < 2 or property_check.get("violations") != 0:
        errors.append("Course 06 verified-conflict property must explore multiple pairs without violation")
    return errors


def check_course_07_acceptance_evidence() -> list[str]:
    lesson = ROOT / "curriculum" / "beginner" / "07-acceptance-criteria-invariants-evidence"
    scenario = lesson / "northstar-broker-evidence"
    required = [
        "README.md",
        "acceptance_evidence.ipynb",
        "lab.py",
        "assets/diagram-spec.json",
        "assets/render_diagram.py",
        "assets/requirement-to-runtime-evidence.svg",
        "northstar-broker-evidence/README.md",
        "northstar-broker-evidence/evaluation-cases.json",
        "northstar-broker-evidence/ticket/AI-2219-verification.md",
        "northstar-broker-evidence/reference/acceptance-contract.json",
        "northstar-broker-evidence/reference/decision-table-cases.json",
        "northstar-broker-evidence/reference/evaluation-contract.json",
        "northstar-broker-evidence/reference/gate-policy.json",
        "northstar-broker-evidence/reference/human-rubric.json",
        "northstar-broker-evidence/reference/invalidation-matrix.json",
        "northstar-broker-evidence/reference/runtime-events.json",
        "northstar-broker-evidence/reference/tool-manifest.json",
        "northstar-broker-evidence/reference/traceability.csv",
        "northstar-broker-evidence/reference/evidence/manifest.json",
        "northstar-broker-evidence/reference/evidence/deterministic.json",
        "northstar-broker-evidence/reference/evidence/properties.json",
        "northstar-broker-evidence/reference/evidence/mutation.json",
        "northstar-broker-evidence/reference/evidence/statistical.json",
        "northstar-broker-evidence/reference/evidence/human.json",
        "northstar-broker-evidence/reference/evidence/runtime.json",
        "northstar-broker-evidence/workshop/starter/README.md",
        "northstar-broker-evidence/workshop/starter/acceptance-contract.json",
        "northstar-broker-evidence/workshop/starter/evaluation-contract.json",
        "northstar-broker-evidence/workshop/starter/gate-policy.json",
        "northstar-broker-evidence/workshop/starter/human-rubric.json",
        "northstar-broker-evidence/workshop/starter/traceability.csv",
        "northstar-broker-evidence/workshop/starter/evidence/manifest.json",
    ]
    errors = [f"missing Course 07 artifact: {item}" for item in required if not (lesson / item).exists()]
    if errors:
        return errors

    json_paths = [
        scenario / "evaluation-cases.json",
        scenario / "reference" / "acceptance-contract.json",
        scenario / "reference" / "decision-table-cases.json",
        scenario / "reference" / "evaluation-contract.json",
        scenario / "reference" / "gate-policy.json",
        scenario / "reference" / "human-rubric.json",
        scenario / "reference" / "invalidation-matrix.json",
        scenario / "reference" / "runtime-events.json",
        scenario / "reference" / "tool-manifest.json",
        scenario / "reference" / "evidence" / "manifest.json",
        lesson / "assets" / "diagram-spec.json",
    ]
    evidence_files = sorted((scenario / "reference" / "evidence").glob("*.json"))
    json_paths.extend(path for path in evidence_files if path.name != "manifest.json")
    payloads: dict[Path, dict] = {}
    for path in json_paths:
        try:
            payloads[path] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid Course 07 JSON {path.relative_to(ROOT)}: {exc}")
    if errors:
        return errors

    reference = scenario / "reference"
    contract = payloads[reference / "acceptance-contract.json"]
    criteria = contract.get("acceptance_criteria", [])
    kinds = {item.get("kind") for item in criteria}
    required_kinds = {"positive", "negative", "boundary", "failure", "staleness", "security", "contract"}
    if len(contract.get("scope", {}).get("requirement_ids", [])) != 10:
        errors.append("Course 07 high-risk scope must retain ten Course 06 requirements")
    if len(criteria) != 14 or not required_kinds.issubset(kinds):
        errors.append("Course 07 must retain fourteen diverse observable acceptance criteria")
    if len(contract.get("invariants", [])) != 6:
        errors.append("Course 07 must retain five invariants and one frame condition")
    stale_criterion = next((item for item in criteria if item.get("id") == "AC-BR-036-A"), {})
    if stale_criterion.get("requirement_ids") != ["REQ-BR-036"] or stale_criterion.get("invariant_ids") != ["INV-BR-005"]:
        errors.append("Course 07 stale-context criterion must not reuse replay/idempotency traceability")
    rubric = payloads[reference / "human-rubric.json"]
    protocol = rubric.get("review_protocol", {})
    if rubric.get("status") != "template_only_not_run" or rubric.get("release_threshold") is not None:
        errors.append("Course 07 human rubric must remain unexecuted and must not invent a release threshold")
    if protocol.get("reviewers_per_case", 0) < 2 or not protocol.get("independent_before_adjudication"):
        errors.append("Course 07 human rubric must require independent ratings before adjudication")

    records = [
        record
        for path in evidence_files
        if path.name != "manifest.json"
        for record in payloads[path].get("records", [])
    ]
    expected_classes = {"deterministic_conformance", "statistical_quality", "human_judgment", "runtime_operational"}
    if len(records) != 14 or {item.get("evidence_class") for item in records} != expected_classes:
        errors.append("Course 07 evidence bundle must retain fourteen records across all four evidence classes")
    if any(not item.get("limitations") for item in records):
        errors.append("Course 07 evidence records must declare limitations")
    record_map = {item.get("evidence_id"): item for item in records}
    if record_map.get("EVID-PROP-PROVENANCE", {}).get("invariant_ids") != ["INV-BR-003"]:
        errors.append("Course 07 provenance invariant needs direct behavioral property evidence")
    if record_map.get("EVID-HUMAN-RUBRIC", {}).get("lifecycle_state") != "planned":
        errors.append("Course 07 unexecuted human rubric must remain planned evidence")
    if any(item.get("lifecycle_state") != "executed" for item in records if item.get("evidence_id") != "EVID-HUMAN-RUBRIC"):
        errors.append("Course 07 executed evidence records must declare their lifecycle state")

    reference_text = "\n".join(path.read_text(encoding="utf-8") for path in reference.rglob("*") if path.is_file())
    if "TODO" in reference_text:
        errors.append("Course 07 reference artifacts contain unresolved TODOs")
    starter = scenario / "workshop" / "starter"
    starter_text = "\n".join(path.read_text(encoding="utf-8") for path in starter.rglob("*") if path.is_file())
    if "TODO" not in starter_text:
        errors.append("Course 07 starter workspace has no editable TODO prompts")

    result = subprocess.run(
        [sys.executable, str(lesson / "lab.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(result.stdout) if result.returncode == 0 else {}
    except json.JSONDecodeError:
        report = {}
    if report.get("contract_findings") or report.get("evidence_findings") or report.get("traceability_findings"):
        errors.append("Course 07 reference contracts, evidence, and traceability must validate cleanly")
    if report.get("acceptance", {}).get("passed") != 14 or report.get("acceptance", {}).get("total") != 14:
        errors.append("Course 07 acceptance suite must pass all fourteen declared criteria")
    properties = report.get("properties", [])
    if len(properties) != 5 or any(item.get("violations") != 0 or item.get("checked", 0) == 0 for item in properties):
        errors.append("Course 07 must exercise five non-empty bounded properties without reference violations")
    coverage = report.get("decision_table_coverage", {})
    if (coverage.get("covered"), coverage.get("total")) != (8, 8) or coverage.get("failed_case_ids"):
        errors.append("Course 07 must retain complete decision-table row coverage with no reference failures")
    mutation = report.get("mutation_evidence", {})
    if (mutation.get("killed"), mutation.get("total")) != (3, 3):
        errors.append("Course 07 evidence must detect all three seeded mutants")
    governed = report.get("evaluation", {}).get("governed", {}).get("overall", {})
    baseline = report.get("evaluation", {}).get("baseline", {}).get("overall", {})
    if (governed.get("numerator"), governed.get("denominator")) != (12, 12) or baseline.get("value", 1) >= governed.get("value", 0):
        errors.append("Course 07 evaluation fixtures must preserve twelve labelled cases and a weaker baseline")
    gates = {item.get("gate_id"): item for item in report.get("gates", [])}
    if gates.get("GATE-BR-CONFLICT-EVAL", {}).get("decision") != "blocked" or gates.get("GATE-BR-CONFLICT-EVAL", {}).get("reason_codes") != ["THRESHOLD_NOT_AUTHORIZED"]:
        errors.append("Course 07 statistical gate must remain blocked until an owner authorizes its threshold")
    runtime = report.get("runtime", {})
    if (runtime.get("violations"), runtime.get("applicable_events")) != (0, 5):
        errors.append("Course 07 runtime fixture must retain an explicit non-zero applicable population")
    if runtime.get("production_evidence") is not False or runtime.get("evidence_status") != "simulated_not_production":
        errors.append("Course 07 runtime output must be visibly labelled simulated and non-production")
    release = report.get("release_assessment", {})
    scope = release.get("scope", {})
    if release.get("production_ready") is not False or release.get("claim") != "bounded_high_risk_slice_conformance_only":
        errors.append("Course 07 green bounded evidence must not claim production readiness")
    if (scope.get("course06_requirement_count"), scope.get("assurance_requirement_count"), scope.get("excluded_normative_requirement_count")) != (10, 3, 8):
        errors.append("Course 07 release assessment must expose included and excluded scope")
    populations = report.get("population_eligibility", {})
    if populations.get("french", {}).get("disposition") != "manual_review" or populations.get("attachment", {}).get("disposition") != "manual_review":
        errors.append("Course 07 out-of-population inputs must route to manual review")
    field_coverage = report.get("evaluation_field_coverage", {})
    if field_coverage.get("missing_supported_fields") != ["sprinkler_system"] or field_coverage.get("prior_evidence_wholly_invalid") is not False:
        errors.append("Course 07 must report new-field evaluation gaps as partial invalidation")
    freshness = report.get("freshness", [])
    if len(freshness) != 14 or any(not item.get("current") for item in freshness):
        errors.append("Course 07 reference evidence must be current for the declared fixture revisions")
    return errors


def check_course_08_non_functional_requirements() -> list[str]:
    lesson = ROOT / "curriculum" / "beginner" / "08-non-functional-requirements-agentic-systems"
    scenario = lesson / "northstar-broker-nfrs"
    required = [
        "README.md",
        "nfr_engineering.ipynb",
        "lab.py",
        "northstar-broker-nfrs/README.md",
        "northstar-broker-nfrs/workload-profiles.json",
        "northstar-broker-nfrs/synthetic-runtime-events.json",
        "northstar-broker-nfrs/synthetic-quality-cases.json",
        "northstar-broker-nfrs/ticket/AI-2219-rollout.md",
        "northstar-broker-nfrs/reference/nfr-contract.json",
        "northstar-broker-nfrs/reference/target-decisions.json",
        "northstar-broker-nfrs/reference/measurement-plan.json",
        "northstar-broker-nfrs/reference/degradation-policy.json",
        "northstar-broker-nfrs/reference/agent-budget.json",
        "northstar-broker-nfrs/reference/traceability.csv",
        "northstar-broker-nfrs/workshop/starter/README.md",
        "northstar-broker-nfrs/workshop/starter/nfr-contract.json",
        "northstar-broker-nfrs/workshop/starter/target-decisions.json",
        "northstar-broker-nfrs/workshop/starter/measurement-plan.json",
        "northstar-broker-nfrs/workshop/starter/degradation-policy.json",
        "northstar-broker-nfrs/workshop/starter/agent-budget.json",
        "northstar-broker-nfrs/workshop/starter/traceability.csv",
    ]
    errors = [f"missing Course 08 artifact: {item}" for item in required if not (lesson / item).exists()]
    if errors:
        return errors

    json_paths = [
        scenario / "workload-profiles.json",
        scenario / "synthetic-runtime-events.json",
        scenario / "synthetic-quality-cases.json",
        scenario / "reference" / "nfr-contract.json",
        scenario / "reference" / "target-decisions.json",
        scenario / "reference" / "measurement-plan.json",
        scenario / "reference" / "degradation-policy.json",
        scenario / "reference" / "agent-budget.json",
    ]
    payloads: dict[Path, dict] = {}
    for path in json_paths:
        try:
            payloads[path] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"invalid Course 08 JSON {path.relative_to(ROOT)}: {exc}")
    if errors:
        return errors

    reference = scenario / "reference"
    reference_text = "\n".join(path.read_text(encoding="utf-8") for path in reference.rglob("*") if path.is_file())
    if "TODO" in reference_text:
        errors.append("Course 08 reference artifacts contain unresolved TODOs")
    starter = scenario / "workshop" / "starter"
    starter_text = "\n".join(path.read_text(encoding="utf-8") for path in starter.rglob("*") if path.is_file())
    if "TODO" not in starter_text:
        errors.append("Course 08 starter workspace has no editable TODO prompts")

    contract = payloads[reference / "nfr-contract.json"]
    requirements = contract.get("requirements", [])
    expected_ids = {
        "PERF-BR-001", "REL-BR-001", "RES-BR-001", "AGENT-NFR-001", "COST-BR-001",
        "OBS-BR-001", "AIQ-BR-001", "SEC-NFR-001", "PRIV-NFR-001", "CAP-BR-001",
        "SEC-NFR-002",
    }
    if {item.get("id") for item in requirements} != expected_ids:
        errors.append("Course 08 must retain eleven atomic production-quality requirements")
    unresolved = {item.get("id") for item in requirements if item.get("target", {}).get("status") == "target_unresolved"}
    if unresolved != {"COST-BR-001", "AIQ-BR-001"}:
        errors.append("Course 08 cost and AI-quality targets must remain explicitly unresolved")
    if any(
        item.get("target", {}).get("value") is not None or item.get("target", {}).get("decision_id") is not None
        for item in requirements
        if item.get("id") in unresolved
    ):
        errors.append("Course 08 unresolved targets must not contain invented values or decisions")

    profiles = payloads[scenario / "workload-profiles.json"].get("profiles", [])
    profile_status = {item.get("id"): item.get("status") for item in profiles}
    if profile_status != {"W1": "owner_approved_training_fixture", "W2": "target_unresolved", "W3": "target_unresolved"}:
        errors.append("Course 08 workload profiles must distinguish approved W1 from unresolved W2/W3 hypotheses")
    events = payloads[scenario / "synthetic-runtime-events.json"]
    quality = payloads[scenario / "synthetic-quality-cases.json"]
    if events.get("fixture_status") != "synthetic_training_fixture_not_production_evidence" or len(events.get("events", [])) != 12:
        errors.append("Course 08 runtime fixture must retain twelve explicitly synthetic events")
    if quality.get("fixture_status") != "fixed_prediction_pipeline_exercise_not_model_quality_evidence" or len(quality.get("cases", [])) != 8:
        errors.append("Course 08 quality fixture must retain eight fixed-prediction cases without model-quality claims")

    with (reference / "traceability.csv").open(encoding="utf-8", newline="") as handle:
        trace_rows = list(csv.DictReader(handle))
    if {row.get("nfr_id") for row in trace_rows} != expected_ids or any(row.get("status") != "planned" for row in trace_rows):
        errors.append("Course 08 traceability must cover every NFR without fabricating executed production evidence")

    result = subprocess.run(
        [sys.executable, str(lesson / "lab.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(result.stdout) if result.returncode == 0 else {}
    except json.JSONDecodeError:
        report = {}
    if report.get("contract_findings") or report.get("workload_findings") or report.get("measurement_plan_findings"):
        errors.append("Course 08 reference contract, workloads, and measurement plan must validate cleanly")
    runtime_report = report.get("runtime_measurements", {})
    latency = runtime_report.get("end_to_end_latency_ms", {})
    reliability = runtime_report.get("semantic_service_success_ratio", {})
    compliant = runtime_report.get("compliant_workflow_success_ratio", {})
    if (latency.get("p50"), latency.get("p95"), latency.get("p99"), latency.get("denominator")) != (1850.0, 4800.0, 4800.0, 12):
        errors.append("Course 08 must preserve boundary-labelled p50/p95/p99 latency with denominator")
    if (reliability.get("numerator"), reliability.get("denominator")) != (11, 12):
        errors.append("Course 08 semantic service-success ratio must retain its numerator and denominator")
    if (compliant.get("numerator"), compliant.get("denominator")) != (11, 12):
        errors.append("Course 08 compliant workflow success must remain a separately labelled metric")
    if latency.get("sample_size") != 12 or "not_statistically_representative" not in latency.get("representativeness", ""):
        errors.append("Course 08 small-sample percentiles must disclose sample size and representativeness")
    if runtime_report.get("evidence_status") != "synthetic_training_fixture_not_production_evidence":
        errors.append("Course 08 runtime output must be visibly synthetic and non-production")
    quality_report = report.get("quality_measurements", {})
    if quality_report.get("claim") != "pipeline_mechanics_only_not_model_quality" or quality_report.get("slices", {}).get("unsupported_field", {}).get("value") != 0.5:
        errors.append("Course 08 quality results must expose the unsupported-field slice without a model-quality claim")
    resilience = report.get("resilience_experiment", {})
    if resilience.get("unsafe", {}).get("provider_attempts") != 600 or resilience.get("governed", {}).get("provider_attempts") != 8:
        errors.append("Course 08 must contrast retry amplification with bounded circuit-breaker behavior")
    if resilience.get("governed", {}).get("work_items_preserved") != 100:
        errors.append("Course 08 governed degradation must preserve every work item")
    degradation = report.get("degradation", {})
    if any(degradation.get(name, {}).get("automatic_mutation") is not False for name in ("authorization", "model_provider", "policy_service")):
        errors.append("Course 08 critical dependency degradation must reduce automation")
    if any(not degradation.get(name, {}).get("recovery_condition") for name in ("authorization", "model_provider", "policy_service", "analytics_export")):
        errors.append("Course 08 degradation modes must include explicit recovery and exit criteria")
    budget_findings = report.get("budget_policy_findings", [])
    if sum(item.get("code") == "AGENT_BUDGET_TARGET_UNRESOLVED" for item in budget_findings) != 6:
        errors.append("Course 08 must surface six unresolved agent-budget decisions instead of inventing limits")
    gates = {item.get("requirement_id"): item for item in report.get("target_gates", [])}
    if sum(item.get("decision") == "pass" for item in gates.values()) != 8:
        errors.append("Course 08 reference fixture must retain eight bounded target passes")
    if gates.get("COST-BR-001", {}).get("decision") != "blocked" or gates.get("AIQ-BR-001", {}).get("decision") != "blocked":
        errors.append("Course 08 measured but unauthorized cost and quality targets must remain blocked")
    if gates.get("CAP-BR-001", {}).get("decision") != "not_measured":
        errors.append("Course 08 static events must not be presented as capacity evidence")
    if gates.get("PRIV-NFR-001", {}).get("numerator") != 0 or gates.get("PRIV-NFR-001", {}).get("denominator") != 12:
        errors.append("Course 08 privacy gate must retain numerator and denominator")
    release = report.get("release_assessment", {})
    if release.get("production_ready") is not False or release.get("claim") != "nfr_contract_and_measurement_pipeline_exercised_only":
        errors.append("Course 08 synthetic NFR exercise must not claim production readiness")
    if "AGENT_BUDGET_TARGETS_UNRESOLVED" not in release.get("blockers", []):
        errors.append("Course 08 unresolved agent budgets must block bounded production autonomy")
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
        "Course 05 requirements engineering": check_course_05_discovery,
        "Course 06 executable requirements": check_course_06_executable_requirements,
        "Course 07 acceptance evidence": check_course_07_acceptance_evidence,
        "Course 08 non-functional requirements": check_course_08_non_functional_requirements,
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
