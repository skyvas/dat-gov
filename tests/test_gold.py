"""Gold: marts reconcile to Silver; funnel is monotonic."""

from __future__ import annotations

import duckdb

from dat_gov.config import GOLD_DIR, SILVER_DIR


def _q(sql: str):
    con = duckdb.connect()
    try:
        return con.execute(sql).fetchone()
    finally:
        con.close()


def test_gold_enrollment_reconciles_to_silver():
    silver = _q(f"SELECT count(*) FROM read_parquet('{SILVER_DIR / 'enrollments.parquet'}')")[0]
    gold = _q(f"SELECT sum(enrollments) FROM read_parquet('{GOLD_DIR / 'gold_enrollment.parquet'}')")[0]
    assert gold == silver


def test_gold_finance_billed_reconciles_to_silver():
    silver = _q(f"SELECT sum(amount) FROM read_parquet('{SILVER_DIR / 'tuition_charges.parquet'}')")[0]
    gold = _q(f"SELECT sum(billed) FROM read_parquet('{GOLD_DIR / 'gold_finance_summary.parquet'}')")[0]
    assert abs(gold - silver) < 0.01


def test_funnel_is_monotonic():
    funnel = GOLD_DIR / "gold_admissions_funnel.parquet"
    applied, admitted, enrolled = _q(
        f"SELECT sum(applied), sum(admitted), sum(enrolled) FROM read_parquet('{funnel}')")
    assert applied >= admitted >= enrolled
    assert applied == 5200  # clean applications (one per applicant + 200 second applications)
    assert enrolled == 3000


def test_retention_cohorts_sum_to_students():
    total = _q(f"SELECT sum(cohort_size) FROM read_parquet('{GOLD_DIR / 'gold_student_retention.parquet'}')")[0]
    assert total == 3000
    retention = GOLD_DIR / "gold_student_retention.parquet"
    rate = _q(f"SELECT min(retention_rate_pct), max(retention_rate_pct) FROM read_parquet('{retention}')")
    assert 0 <= rate[0] <= rate[1] <= 100


def test_faculty_load_has_no_pii_columns():
    con = duckdb.connect()
    try:
        cols = [d[0] for d in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{GOLD_DIR / 'gold_faculty_teaching_load.parquet'}')").fetchall()]
        assert "email" not in cols and "phone" not in cols and "gov_id" not in cols
    finally:
        con.close()
