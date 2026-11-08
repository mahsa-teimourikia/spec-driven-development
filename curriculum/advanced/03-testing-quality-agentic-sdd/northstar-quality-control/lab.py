"""Run the credential-free Course 27 quality control lab."""

from __future__ import annotations

import json
from pathlib import Path

from quality_app.simulation import run_reference


if __name__ == "__main__":
    print(json.dumps(run_reference(Path(__file__).resolve().parent), indent=2))

