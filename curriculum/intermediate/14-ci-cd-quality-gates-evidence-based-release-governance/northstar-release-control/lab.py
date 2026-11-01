#!/usr/bin/env python3
"""Course 24 lab: trusted CI/CD release governance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from release_app.simulation import run_reference  # noqa: E402


def main() -> None:
    print(json.dumps(run_reference(ROOT), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
