"""Validate local links, lesson structure, notebooks, labs, and Hub assets."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


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
                f"expected exactly one notebook in {lesson.relative_to(ROOT)}, found {len(notebooks)}"
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
    errors = [f"missing enterprise fixture artifact: {item}" for item in required if not (fixture / item).exists()]
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
    return errors


def main() -> None:
    checks = {
        "local links": check_local_links,
        "lesson structure": check_lesson_structure,
        "site assets": check_site_assets,
        "published navigation": check_published_navigation,
        "enterprise fixture": check_enterprise_fixture,
        "Course 02 artifact stack": check_course_02_artifact_stack,
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
