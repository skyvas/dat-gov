"""Bronze ingestion: raw CSV -> immutable Bronze Parquet.

Governance idea demonstrated here: Bronze is *raw as received*. It
adds only audit metadata — ``_ingested_at``, ``_source_file``,
``_batch_id`` (a hash of the source file, so re-ingesting the same
file is recognisable) and ``_row_hash`` (a fingerprint of the raw
values) — and never fixes, drops or rewrites a value. Dirty rows are
preserved here on purpose: if Bronze cleaned them, Silver could never
prove what arrived.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .config import BRONZE_DIR, DATASETS, RAW_DIR


def _batch_id(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def ingest_dataset(name: str, raw_dir: Path = RAW_DIR, bronze_dir: Path = BRONZE_DIR) -> int:
    """Ingest one raw CSV into Bronze Parquet. Returns the row count."""
    src = raw_dir / f"{name}.csv"
    out = bronze_dir / f"{name}.parquet"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        rel = con.read_csv(str(src), header=True, all_varchar=True)
        cols = rel.columns
        hash_expr = "md5(concat_ws('||', " + ", ".join(f'"{c}"' for c in cols) + "))"
        ingested_at = datetime.now(timezone.utc).isoformat()
        con.execute(
            f"COPY (SELECT *, '{ingested_at}' AS _ingested_at, "
            f"'{src.name}' AS _source_file, '{_batch_id(src)}' AS _batch_id, "
            f"{hash_expr} AS _row_hash FROM read_csv('{src}', header=true, all_varchar=true))"
            f" TO '{out}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE)"
        )
        return int(con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0])
    finally:
        con.close()


def ingest_all(raw_dir: Path = RAW_DIR, bronze_dir: Path = BRONZE_DIR) -> dict[str, int]:
    """Ingest every dataset. Returns {dataset: bronze_row_count}."""
    return {name: ingest_dataset(name, raw_dir, bronze_dir) for name in DATASETS}
