"""CLI: generate, bronze, silver, gold, quality, catalog, all, check.

Governance concept demonstrated: one entry point runs the whole governed
pipeline end to end, logging row counts in/out and quarantined rows at
every stage so a run can be audited from its printed summary alone.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .catalog import build_catalog
from .config import PROJECT_ROOT
from .generate import generate_all
from .ingest import ingest_all
from .quality import run_quality
from .transform_gold import transform_gold
from .transform_silver import transform_silver


def _root() -> Path:
    return PROJECT_ROOT


def cmd_all(root: Path) -> int:
    counts = generate_all(root)
    print(f"generate: {sum(counts.values())} raw rows across {len(counts)} datasets")
    bronze = ingest_all(root)
    silver = transform_silver(root)
    gold = transform_gold(root)
    quality = run_quality(root)
    build_catalog(root)
    print("--- summary ---")
    print(f"raw={sum(counts.values())} bronze={sum(v['in'] for v in bronze.values())} "
          f"silver={sum(v['silver'] for v in silver.values())} "
          f"quarantined={sum(v['quarantined'] for v in silver.values())}")
    print(f"gold marts: {gold}")
    print(f"quality: {'PASSED' if quality['overall']['passed'] else 'FAILED'}")
    return 0 if quality["overall"]["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dat_gov")
    parser.add_argument("command", choices=["generate", "bronze", "silver", "gold", "quality", "catalog", "all", "check"])
    args = parser.parse_args(argv)
    root = _root()
    if args.command == "generate":
        counts = generate_all(root)
        print(f"generate: {sum(counts.values())} raw rows across {len(counts)} datasets")
        return 0
    if args.command == "bronze":
        ingest_all(root)
        return 0
    if args.command == "silver":
        transform_silver(root)
        return 0
    if args.command == "gold":
        transform_gold(root)
        return 0
    if args.command == "quality":
        return 0 if run_quality(root)["overall"]["passed"] else 1
    if args.command == "catalog":
        build_catalog(root)
        return 0
    if args.command == "check":
        # check = quality gate only, on existing outputs
        return 0 if run_quality(root)["overall"]["passed"] else 1
    return cmd_all(root)


if __name__ == "__main__":
    sys.exit(main())
