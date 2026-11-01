#!/usr/bin/env python3
"""Course 23 lab: trusted human approval gates and delegated authority."""
from __future__ import annotations

import json
from pathlib import Path

from approval_app.simulation import run_reference

ROOT = Path(__file__).resolve().parent


def build_report():
    return run_reference(ROOT)


if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2, sort_keys=True))
