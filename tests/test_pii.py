"""PII: Gold contains no raw identifiers; masking is deterministic."""

from __future__ import annotations

import duckdb

from dat_gov.config import GOLD_DIR, GOLD_TABLES, SILVER_DIR
from dat_gov.masking import hash_value, mask_email, mask_phone


def test_gold_has_no_raw_pii_columns():
    con = duckdb.connect()
    try:
        for table in GOLD_TABLES:
            cols = [d[0] for d in con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{GOLD_DIR / f'{table}.parquet'}')").fetchall()]
            for banned in ("email", "phone", "gov_id", "first_name", "last_name", "date_of_birth"):
                assert banned not in cols, f"{table} exposes {banned}"
    finally:
        con.close()


def test_gold_values_do_not_leak_raw_identifiers():
    # Spot-check: no Silver email/phone appears anywhere in any Gold file.
    con = duckdb.connect()
    try:
        emails = {r[0] for r in con.execute(
            f"SELECT DISTINCT email FROM read_parquet('{SILVER_DIR / 'students.parquet'}') LIMIT 200").fetchall()}
        for table in GOLD_TABLES:
            cols = [d[0] for d in con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{GOLD_DIR / f'{table}.parquet'}')").fetchall()]
            for col in cols:
                vals = {str(r[0]) for r in con.execute(
                    f"SELECT DISTINCT {col} FROM read_parquet('{GOLD_DIR / f'{table}.parquet'}') LIMIT 500").fetchall()}
                assert not (vals & emails), f"{table}.{col} leaks an email"
    finally:
        con.close()


def test_masking_is_deterministic_and_hides_raw_value():
    assert hash_value("NB-100001") == hash_value("NB-100001")
    assert hash_value("NB-100001") != hash_value("NB-100002")
    assert hash_value("NB-100001") != "NB-100001"
    assert mask_email("maya.patel1@example.edu") == "m***@example.edu"
    assert mask_phone("+1-555-123-4567") == "***-***-4567"
    assert mask_email(None) is None and mask_phone(None) is None
