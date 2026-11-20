"""Command-line entry point: ``python -m dat_gov.cli <stage>``.

Stages: generate, bronze, silver, gold, quality, catalog, lineage, all, check.
``all`` runs the whole pipeline end to end and prints a stage summary
(row counts in/out, quarantined rows, duration) — the single command
a newcomer needs. ``check`` re-runs quality and exits 1 on failure,
so CI can gate on it.
"""

from __future__ import annotations

import argparse
import sys
import time

from .catalog import build_catalog
from .config import DATA_DIR, DOCS_DIR, ensure_dirs
from .generate import generate_all
from .ingest import ingest_all
from .lineage import write_lineage
from .quality import run_quality
from .transform_gold import transform_gold
from .transform_silver import transform_all


def _timed(label: str, fn):
    start = time.monotonic()
    result = fn()
    print(f"[{label}] done in {time.monotonic() - start:.1f}s")
    return result


def cmd_all() -> int:
    """Run generate -> bronze -> silver -> gold -> quality -> catalog -> lineage."""
    ensure_dirs()
    print("Northbridge University — data-governance pipeline")
    print("=" * 55)
    counts = _timed("generate", generate_all)
    print(f"[generate] rows (incl. dirty): {counts}")
    bronze = _timed("bronze", ingest_all)
    print(f"[bronze] rows: {bronze}")
    silver = _timed("silver", transform_all)
    for name, r in silver.items():
        print(f"[silver] {name}: bronze={r['bronze']} silver={r['silver']} quarantined={r['quarantined']}")
    gold = _timed("gold", transform_gold)
    print(f"[gold] rows: {gold}")
    report = _timed("quality", run_quality)
    print(f"[quality] passed={report['passed']} "
          f"quarantined={sum(d['quarantined'] for d in report['datasets'].values())}")
    _timed("catalog", build_catalog)
    _timed("lineage", lambda: write_lineage(DATA_DIR / "lineage.json", DOCS_DIR / "lineage.md"))
    print("=" * 55)
    verdict = "PASSED" if report["passed"] else "FAILED"
    print(f"Pipeline {verdict} — see data/quality_report.json, docs/catalog.md, docs/lineage.md")
    return 0 if report["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    """Parse args and dispatch. Returns a process exit code."""
    parser = argparse.ArgumentParser(prog="dat-gov", description="Northbridge University data-governance pipeline")
    stages = ["generate", "bronze", "silver", "gold", "quality", "catalog", "lineage", "all", "check"]
    parser.add_argument("stage", choices=stages)
    args = parser.parse_args(argv)
    ensure_dirs()
    if args.stage == "generate":
        print(generate_all())
    elif args.stage == "bronze":
        print(ingest_all())
    elif args.stage == "silver":
        print(transform_all())
    elif args.stage == "gold":
        print(transform_gold())
    elif args.stage == "quality":
        report = run_quality()
        print(f"quality passed={report['passed']}")
        return 0 if report["passed"] else 1
    elif args.stage == "catalog":
        print(f"wrote {build_catalog()}")
    elif args.stage == "lineage":
        write_lineage(DATA_DIR / "lineage.json", DOCS_DIR / "lineage.md")
        print("wrote data/lineage.json and docs/lineage.md")
    elif args.stage == "check":
        report = run_quality()
        print(f"quality passed={report['passed']}")
        return 0 if report["passed"] else 1
    elif args.stage == "all":
        return cmd_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
