"""Bronze ingestion: raw CSV -> immutable Bronze Parquet.

Governance concept demonstrated: Bronze is append-only raw-as-received.
It adds audit columns only — never fixes, drops or rewrites a value —
so every downstream decision can be traced back to exactly what arrived,
including whether it was captured offline on a vessel and its sync state.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb

from .config import BRONZE_COLUMNS, DATASETS, REFERENCE_DATE, VESSEL_ORIGINATED, columns_of

BATCH_ID = "batch-20261120-seed42"


def _source_system(dataset: str, row_vessel_id: str | None) -> str:
    if dataset in VESSEL_ORIGINATED:
        return f"vessel-{row_vessel_id}" if row_vessel_id else "warehouse-erp"
    if DATASETS[dataset]["source"] == "onshore":
        return "warehouse-erp"
    if DATASETS[dataset]["source"] == "vessel":
        return f"vessel-{row_vessel_id}" if row_vessel_id else "warehouse-erp"
    # mixed: vessel-linked rows come from the vessel, the rest from the ERP
    return f"vessel-{row_vessel_id}" if row_vessel_id else "warehouse-erp"


def ingest_all(root: Path) -> dict[str, dict[str, int]]:
    """Read data/raw/*.csv, write data/bronze/*.parquet. Returns per-dataset counts."""
    raw_dir, bronze_dir = root / "data" / "raw", root / "data" / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, int]] = {}
    con = duckdb.connect()
    try:
        for name in DATASETS:
            csv_path = raw_dir / f"{name}.csv"
            cols = columns_of(name)
            # Build bronze rows in Python so audit columns are explicit and auditable.
            import csv as _csv
            with open(csv_path, newline="", encoding="utf-8") as fh:
                reader = list(_csv.DictReader(fh))
            vessel_col = "vessel_id" if "vessel_id" in cols else None
            offline = 0
            pending = conflict = 0
            # Deterministic offline/sync assignment from the row hash.
            import random as _random
            rng = _random.Random(42)
            bronze_rows = []
            for row in reader:
                raw = "|".join(row.get(c, "") or "" for c in cols)
                row_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                vid = (row.get(vessel_col) or "") if vessel_col else ""
                source = _source_system(name, vid or None)
                is_vessel = source.startswith("vessel-")
                captured_offline = bool(is_vessel and rng.random() < 0.35)
                if captured_offline:
                    offline += 1
                if captured_offline and rng.random() < 0.25:
                    sync_status = "pending"
                    pending += 1
                elif captured_offline and name in ("documents", "incidents", "audits", "conformance_reports") and rng.random() < 0.03 or is_vessel and rng.random() < 0.005:
                    sync_status = "conflict"
                    conflict += 1
                else:
                    sync_status = "synced"
                bronze_rows.append({**row, "_ingested_at": REFERENCE_DATE, "_source_file": f"{name}.csv",
                                    "_source_system": source, "_captured_offline": str(captured_offline).lower(),
                                    "_sync_status": sync_status, "_batch_id": BATCH_ID, "_row_hash": row_hash})
            out = bronze_dir / f"{name}.parquet"
            if out.exists():
                out.unlink()
            # Write via DuckDB from a temp CSV to avoid a pandas dependency.
            tmp = bronze_dir / f"_{name}.tmp.csv"
            with open(tmp, "w", newline="", encoding="utf-8") as fh:
                w = _csv.DictWriter(fh, fieldnames=cols + BRONZE_COLUMNS)
                w.writeheader()
                w.writerows(bronze_rows)
            con.execute(f"COPY (SELECT * FROM read_csv('{tmp}', header=true, all_varchar=true)) TO '{out}' (FORMAT PARQUET)")
            tmp.unlink()
            results[name] = {"in": len(reader), "out": len(bronze_rows), "offline": offline,
                             "pending": pending, "conflict": conflict}
            print(f"bronze {name}: in={len(reader)} out={len(bronze_rows)} offline={offline} pending={pending} conflict={conflict}")
    finally:
        con.close()
    return results
