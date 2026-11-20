"""Thin wrapper: ``python scripts/run_pipeline.py`` runs the full pipeline.

Prefer ``python -m dat_gov.cli all``; this file exists so the pipeline
can be run from a checkout without installing the package.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dat_gov.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["all"]))
