"""Silver: contracts enforced, dirty rows quarantined, never silently dropped."""

from __future__ import annotations

import duckdb

from dat_gov.config import BRONZE_DIR, QUARANTINE_DIR, SILVER_DIR


def _q(sql: str):
    con = duckdb.connect()
    try:
        return con.execute(sql).fetchone()[0]
    finally:
        con.close()


def test_silver_counts_equal_clean_counts():
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'applicants.parquet'}')") == 5000
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'students.parquet'}')") == 3000
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'enrollments.parquet'}')") == 12000
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'departments.parquet'}')") == 8
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'courses.parquet'}')") == 40


def test_bronze_equals_silver_plus_quarantine():
    for name in ("applicants", "students", "enrollments", "tuition_charges", "payments", "financial_aid"):
        b = _q(f"SELECT count(*) FROM read_parquet('{BRONZE_DIR / f'{name}.parquet'}')")
        s = _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / f'{name}.parquet'}')")
        q = _q(f"SELECT count(*) FROM read_parquet('{QUARANTINE_DIR / f'{name}.parquet'}')")
        assert b == s + q, name
        assert q > 0, f"expected quarantined rows for {name}"


def test_no_future_dob_no_negative_tuition_no_duplicates():
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'applicants.parquet'}') "
              "WHERE date_of_birth > DATE '2026-06-01'") == 0
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'tuition_charges.parquet'}') "
              "WHERE amount < 0") == 0
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'payments.parquet'}') WHERE amount < 0") == 0
    assert _q(f"SELECT count(*) FROM (SELECT applicant_id, count(*) c FROM read_parquet("
              f"'{SILVER_DIR / 'applicants.parquet'}') GROUP BY applicant_id HAVING c > 1)") == 0
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'enrollments.parquet'}') "
              "WHERE course_id = 'XX999'") == 0
    assert _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'enrollments.parquet'}') "
              "WHERE term NOT IN ('2024-Fall','2025-Spring','2025-Fall','2026-Spring')") == 0


def test_quarantine_rows_carry_a_reason():
    assert _q(f"SELECT count(*) FROM read_parquet('{QUARANTINE_DIR / 'applicants.parquet'}') "
              "WHERE _quarantine_reason IS NULL OR _quarantine_reason = ''") == 0
