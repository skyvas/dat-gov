"""Data quality: re-check Silver against its contract, reconcile layers.

Governance idea demonstrated here: quality is a *gate*, not a report
you read later. This module re-runs the contract checks on the Silver
files that were actually written, verifies Bronze = Silver +
Quarantine for every dataset, and reconciles Gold totals back to
Silver. The result is ``data/quality_report.json``; ``cli check``
exits non-zero when it fails, so CI can block a bad run.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .config import (
    BRONZE_DIR,
    DATA_DIR,
    GOLD_DIR,
    MAX_QUARANTINE_RATE,
    QUARANTINE_DIR,
    SILVER_DIR,
)
from .transform_silver import load_contract


def _count(con, path: Path) -> int:
    if not path.exists():
        return 0
    return int(con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0])


def run_quality(
    bronze_dir: Path = BRONZE_DIR,
    silver_dir: Path = SILVER_DIR,
    quarantine_dir: Path = QUARANTINE_DIR,
    gold_dir: Path = GOLD_DIR,
    out_path: Path | None = None,
) -> dict:
    """Run all quality checks. Returns the report dict (and writes JSON)."""
    con = duckdb.connect()
    report: dict = {"datasets": {}, "gold_checks": {}, "passed": True,
                    "thresholds": {"max_quarantine_rate": MAX_QUARANTINE_RATE}}
    try:
        for name in ("departments", "courses", "faculty", "sections", "applicants", "applications",
                     "students", "enrollments", "tuition_charges", "payments", "financial_aid"):
            contract = load_contract(name)
            pk = contract["primary_key"]
            bronze = _count(con, bronze_dir / f"{name}.parquet")
            silver = _count(con, silver_dir / f"{name}.parquet")
            quarantined = _count(con, quarantine_dir / f"{name}.parquet")
            checks: dict[str, bool] = {}
            checks["bronze_eq_silver_plus_quarantine"] = bronze == silver + quarantined
            if silver:
                dup = con.execute(
                    f"SELECT count(*) FROM (SELECT {pk}, count(*) c FROM read_parquet("
                    f"'{silver_dir / f'{name}.parquet'}') GROUP BY {pk} HAVING c > 1)"
                ).fetchone()[0]
                checks["pk_unique"] = dup == 0
                for col in contract["columns"]:
                    if not col["nullable"]:
                        nulls = con.execute(
                            f"SELECT count(*) FROM read_parquet('{silver_dir / f'{name}.parquet'}') "
                            f"WHERE {col['name']} IS NULL"
                        ).fetchone()[0]
                        checks[f"not_null:{col['name']}"] = nulls == 0
            q_rate = (quarantined / bronze) if bronze else 0.0
            checks["quarantine_rate_le_5pct"] = q_rate <= MAX_QUARANTINE_RATE
            passed = all(checks.values())
            report["datasets"][name] = {
                "bronze": bronze, "silver": silver, "quarantined": quarantined,
                "quarantine_rate": round(q_rate, 4), "checks": checks, "passed": passed,
            }
            report["passed"] = report["passed"] and passed
        # Gold reconciliation: Gold must agree with Silver.
        gold: dict[str, bool] = {}
        if (silver_dir / "enrollments.parquet").exists() and (gold_dir / "gold_enrollment.parquet").exists():
            silver_enr = _count(con, silver_dir / "enrollments.parquet")
            gold_enr = int(con.execute(
                "SELECT sum(enrollments) FROM read_parquet("
                f"'{gold_dir / 'gold_enrollment.parquet'}')").fetchone()[0] or 0)
            gold["gold_enrollment_eq_silver_enrollments"] = gold_enr == silver_enr
        if (silver_dir / "tuition_charges.parquet").exists() and (gold_dir / "gold_finance_summary.parquet").exists():
            silver_billed = float(con.execute(
                "SELECT sum(amount) FROM read_parquet("
                f"'{silver_dir / 'tuition_charges.parquet'}')").fetchone()[0] or 0)
            gold_billed = float(con.execute(
                "SELECT sum(billed) FROM read_parquet("
                f"'{gold_dir / 'gold_finance_summary.parquet'}')").fetchone()[0] or 0)
            gold["gold_finance_billed_eq_silver_charges"] = abs(gold_billed - silver_billed) < 0.01
        if (gold_dir / "gold_admissions_funnel.parquet").exists():
            funnel = con.execute(
                "SELECT sum(applied), sum(admitted), sum(enrolled) FROM read_parquet("
                f"'{gold_dir / 'gold_admissions_funnel.parquet'}')").fetchone()
            gold["funnel_applied_ge_admitted_ge_enrolled"] = bool(
                funnel and funnel[0] >= funnel[1] >= funnel[2] and funnel[0] > 0)
        report["gold_checks"] = gold
        report["passed"] = report["passed"] and all(gold.values())
        return report
    finally:
        con.close()
        out = out_path or (DATA_DIR / "quality_report.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
