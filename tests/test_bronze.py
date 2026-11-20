"""Bronze: raw values preserved (including dirty rows) + audit metadata."""

from __future__ import annotations

import duckdb

from dat_gov.config import BRONZE_DIR, DATASETS


def _con():
    return duckdb.connect()


def test_bronze_preserves_raw_counts_and_dirty_rows():
    con = _con()
    try:
        for name in DATASETS:
            n = con.execute(f"SELECT count(*) FROM read_parquet('{BRONZE_DIR / f'{name}.parquet'}')").fetchone()[0]
            assert n > 0, name
        assert con.execute(
            "SELECT count(*) FROM read_parquet('" + str(BRONZE_DIR / "applicants.parquet") + "') "
            "WHERE email = 'not-an-email'").fetchone()[0] >= 20
        assert con.execute(
            "SELECT count(*) FROM read_parquet('" + str(BRONZE_DIR / "tuition_charges.parquet") + "') "
            "WHERE CAST(amount AS DOUBLE) < 0").fetchone()[0] >= 50
    finally:
        con.close()


def test_bronze_has_audit_metadata():
    con = _con()
    try:
        cols = [d[0] for d in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{BRONZE_DIR / 'students.parquet'}')").fetchall()]
        for meta in ("_ingested_at", "_source_file", "_batch_id", "_row_hash"):
            assert meta in cols, meta
        assert con.execute(
            f"SELECT count(*) FROM read_parquet('{BRONZE_DIR / 'students.parquet'}') "
            "WHERE _row_hash IS NULL OR _batch_id IS NULL").fetchone()[0] == 0
    finally:
        con.close()
