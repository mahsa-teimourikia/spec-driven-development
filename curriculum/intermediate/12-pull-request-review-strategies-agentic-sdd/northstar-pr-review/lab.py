#!/usr/bin/env python3
"""Course 22 lab: trustworthy PR review over exact Git revisions."""

from __future__ import annotations

import json
from pathlib import Path

from review_app.simulation import run_reference


ROOT = Path(__file__).resolve().parent


def build_report() -> dict[str, object]:
    return run_reference(ROOT)


def main() -> None:
    print(json.dumps(build_report(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
