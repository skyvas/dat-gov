"""Gold transforms: Silver -> business marts.

Governance idea demonstrated here: Gold is *derived, aggregated and
PII-free*. No Gold query selects email, phone, gov_id or a name — the
marts answer business questions (funnel, enrolment, retention, money,
teaching load) without ever exposing a person. Because Gold is built
only from Silver, its totals must reconcile to Silver totals; the
quality step checks exactly that.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from .config import GOLD_DIR, GOLD_TABLES, SILVER_DIR

QUERIES: dict[str, str] = {
    "gold_admissions_funnel": """
        SELECT term, program,
               count(*) AS applied,
               sum(CASE WHEN status IN ('admitted', 'enrolled') THEN 1 ELSE 0 END) AS admitted,
               sum(CASE WHEN status = 'enrolled' THEN 1 ELSE 0 END) AS enrolled,
               round(100.0 * sum(CASE WHEN status IN ('admitted', 'enrolled') THEN 1 ELSE 0 END)
                     / count(*), 2) AS admit_rate_pct,
               round(100.0 * sum(CASE WHEN status = 'enrolled' THEN 1 ELSE 0 END)
                     / nullif(sum(CASE WHEN status IN ('admitted', 'enrolled')
                     THEN 1 ELSE 0 END), 0), 2) AS yield_rate_pct
        FROM applications GROUP BY term, program ORDER BY term, program
    """,
    "gold_enrollment": """
        SELECT e.term, c.department_id, s.program,
               count(*) AS enrollments,
               count(DISTINCT e.student_id) AS students,
               round(avg(e.credits), 2) AS avg_credits,
               sum(CASE WHEN e.status = 'completed' THEN 1 ELSE 0 END) AS completed,
               sum(CASE WHEN e.status = 'withdrawn' THEN 1 ELSE 0 END) AS withdrawn
        FROM enrollments e
        JOIN students s ON s.student_id = e.student_id
        JOIN courses c ON c.course_id = e.course_id
        GROUP BY e.term, c.department_id, s.program ORDER BY e.term, c.department_id, s.program
    """,
    "gold_student_retention": """
        SELECT enrollment_year AS cohort_year, program,
               count(*) AS cohort_size,
               sum(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active,
               sum(CASE WHEN status = 'graduated' THEN 1 ELSE 0 END) AS graduated,
               sum(CASE WHEN status = 'withdrawn' THEN 1 ELSE 0 END) AS withdrawn,
               round(100.0 * sum(CASE WHEN status IN ('active', 'graduated') THEN 1 ELSE 0 END)
                     / count(*), 2) AS retention_rate_pct
        FROM students GROUP BY enrollment_year, program ORDER BY enrollment_year, program
    """,
    "gold_finance_summary": """
        WITH billed AS (
            SELECT term, sum(amount) AS billed FROM tuition_charges GROUP BY term),
        collected AS (
            SELECT term, sum(amount) AS collected FROM payments WHERE status = 'completed' GROUP BY term),
        aid AS (
            SELECT term, sum(amount) AS aid_disbursed FROM financial_aid WHERE status = 'disbursed' GROUP BY term)
        SELECT b.term,
               round(b.billed, 2) AS billed,
               round(coalesce(c.collected, 0), 2) AS collected,
               round(coalesce(a.aid_disbursed, 0), 2) AS aid_disbursed,
               round(b.billed - coalesce(c.collected, 0) - coalesce(a.aid_disbursed, 0), 2) AS net_due
        FROM billed b
        LEFT JOIN collected c ON c.term = b.term
        LEFT JOIN aid a ON a.term = b.term
        ORDER BY b.term
    """,
    "gold_faculty_teaching_load": """
        SELECT sec.faculty_id, sec.term,
               count(DISTINCT sec.section_id) AS sections_taught,
               sum(sec.capacity) AS total_capacity,
               count(e.enrollment_id) AS total_enrolled,
               round(avg(c.credits), 2) AS avg_credits_per_section,
               sum(c.credits) AS credits_taught
        FROM sections sec
        JOIN courses c ON c.course_id = sec.course_id
        LEFT JOIN enrollments e ON e.section_id = sec.section_id AND e.status <> 'withdrawn'
        GROUP BY sec.faculty_id, sec.term ORDER BY sec.faculty_id, sec.term
    """,
}


def transform_gold(silver_dir: Path = SILVER_DIR, gold_dir: Path = GOLD_DIR) -> dict[str, int]:
    """Build every Gold mart from Silver Parquet. Returns {table: rows}."""
    gold_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        # Register Silver as views first; Gold queries reference bare table names.
        for dataset in ("applications", "enrollments", "students", "courses", "sections",
                        "tuition_charges", "payments", "financial_aid", "faculty"):
            con.execute(
                f"CREATE OR REPLACE VIEW {dataset} AS "
                f"SELECT * FROM read_parquet('{silver_dir / f'{dataset}.parquet'}')"
            )
        counts: dict[str, int] = {}
        for name in GOLD_TABLES:
            out = gold_dir / f"{name}.parquet"
            con.execute(f"COPY ({QUERIES[name]}) TO '{out}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE)")
            counts[name] = int(con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0])
        return counts
    finally:
        con.close()
