#!/usr/bin/env python3
"""Course 26 lab: executable enterprise architecture governance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from governance_app.simulation import run_reference  # noqa: E402


if __name__ == "__main__":
    print(json.dumps(run_reference(ROOT), indent=2, sort_keys=True))
