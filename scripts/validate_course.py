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


def main() -> None:
    checks = {
        "local links": check_local_links,
        "lesson structure": check_lesson_structure,
        "site assets": check_site_assets,
        "published navigation": check_published_navigation,
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
