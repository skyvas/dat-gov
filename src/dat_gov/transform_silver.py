"""Silver transform: typed, deduped, contract-validated, FK-checked.

Governance concept demonstrated: a contract is enforced, not documented
and ignored. Every row that fails a not-null / range / format / FK /
exactly-one-location / date-order rule is quarantined with a reason in
data/quarantine/<dataset>.parquet — never silently dropped. Sync rule:
last-write-wins, EXCEPT conflict-flagged safety/compliance rows, which are
quarantined for steward review (see docs/OFFLINE_SYNC.md).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import duckdb

from .config import FOREIGN_KEYS, REFERENCE_DATE, SAFETY_COMPLIANCE, SCHEMAS, columns_of, pk_of

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
REF = REFERENCE_DATE

# Extra date-order rules: (earlier column, later column)
DATE_ORDER = {
    "voyages": [("departure_date", "arrival_date")],
    "crew_assignments": [("embark_date", "disembark_date")],
    "certifications": [("issue_date", "expiry_date")],
    "documents": [("issue_date", "expiry_date")],
    "work_orders": [("created_date", "due_date")],
    "purchase_orders": [("order_date", "required_date")],
}
# Numeric columns that must be >= 0.
NON_NEGATIVE = {"gross_tonnage", "year_built", "cargo_tonnes", "fuel_consumed_tonnes", "unit_cost",
                "reorder_level", "current_qty", "quantity", "rating", "total_amount", "received_qty",
                "delivered_amount", "estimated_cost", "actual_cost", "estimated_hours", "actual_hours",
                "capacity_sqm", "findings_count", "quantity_tonnes", "cost_amount"}


def _validate(name: str, row: dict, fk_sets: dict[str, set[str]]) -> list[str]:
    """Return a list of quarantine reasons for one row (empty = valid)."""
    reasons: list[str] = []
    for c in SCHEMAS[name]:
        v = row.get(c["name"], "")
        if v in ("", None):
            if not c["nullable"]:
                reasons.append(f"null_required:{c['name']}")
            continue
        if c["type"] in ("BIGINT", "DOUBLE"):
            try:
                num = float(v)
            except ValueError:
                reasons.append(f"bad_number:{c['name']}")
                continue
            if c["name"] in NON_NEGATIVE and num < 0:
                reasons.append(f"negative_value:{c['name']}")
            if c["name"] == "rating" and not (0 <= num <= 5):
                reasons.append(f"out_of_range:{c['name']}")
            if c["name"] == "year_built" and not (1900 <= num <= 2026):
                reasons.append(f"out_of_range:{c['name']}")
        if c["type"] == "DATE":
            if v > REF and c["name"] not in ("expiry_date", "required_date", "due_date"):
                reasons.append(f"future_date:{c['name']}")
            if c["name"] == "date_of_birth" and v > "2008-01-01":
                reasons.append(f"future_date:{c['name']}")
        if c["name"] in ("email", "contact_email") and not EMAIL_RE.match(v):
            reasons.append(f"bad_email:{c['name']}")
    for earlier, later in DATE_ORDER.get(name, []):
        if row.get(earlier) and row.get(later) and row[later] < row[earlier]:
            reasons.append(f"date_order:{earlier}_after_{later}")
    for col_name, ref_ds, _ref_col in FOREIGN_KEYS.get(name, []):
        v = row.get(col_name, "")
        if v and v not in fk_sets.get(ref_ds, set()):
            reasons.append(f"invalid_fk:{col_name}->{ref_ds}")
    if name in ("assets", "documents") and bool(row.get("vessel_id")) == bool(row.get("warehouse_id")):
        reasons.append("exactly_one_location:vessel_or_warehouse")
    if name == "conformance_reports" and not row.get("audit_id") and not row.get("document_id"):
        reasons.append("missing_link:audit_or_document")
    if name == "certifications" and row.get("expiry_date") and row.get("expiry_date") < REF and row.get("cert_status") == "valid":
        reasons.append("inconsistent_status:expired_cert_marked_valid")
    if name == "documents" and row.get("expiry_date") and row.get("expiry_date") < REF and row.get("doc_status") == "valid":
        reasons.append("inconsistent_status:expired_doc_marked_valid")
    return reasons


def transform_silver(root: Path) -> dict[str, dict[str, int]]:
    """Bronze -> Silver + quarantine. Returns per-dataset counts."""
    bronze_dir, silver_dir, q_dir = root / "data" / "bronze", root / "data" / "silver", root / "data" / "quarantine"
    silver_dir.mkdir(parents=True, exist_ok=True)
    q_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    results: dict[str, dict[str, int]] = {}
    try:
        # Load Bronze as plain dicts, in FK-safe order (dimensions first).
        order = ["ports", "warehouses", "vessels", "crew_members", "suppliers", "inventory_items",
                 "assets", "purchase_orders", "documents", "audits", "voyages", "crew_assignments",
                 "certifications", "stock_movements", "deliveries", "work_orders", "inspections",
                 "conformance_reports", "incidents", "fuel_bunkering"]
        bronze: dict[str, list[dict]] = {}
        for name in order:
            path = bronze_dir / f"{name}.parquet"
            rel = con.execute(f"SELECT * FROM read_parquet('{path}')")
            cols = [d[0] for d in rel.description]
            bronze[name] = [dict(zip(cols, ["" if v is None else str(v) for v in r])) for r in rel.fetchall()]
        # FK reference sets are built from Bronze PKs as received: a dimension
        # row quarantined for its own defect (e.g. a supplier's bad email) must
        # not cascade-quarantine every fact that references it. An FK is invalid
        # only if the referenced key never arrived at all (e.g. VES-999).
        fk_sets: dict[str, set[str]] = {n: {r[pk_of(n)] for r in rows} for n, rows in bronze.items()}
        silver: dict[str, list[dict]] = {}
        for name in order:
            pk = pk_of(name)
            seen: set[str] = set()
            good: list[dict] = []
            bad: list[dict] = []
            for row in bronze[name]:
                reasons: list[str] = []
                if row[pk] in seen:
                    reasons.append("duplicate_pk")
                else:
                    seen.add(row[pk])
                # Sync-conflict steward review for safety/compliance rows.
                if name in SAFETY_COMPLIANCE and row.get("_sync_status") == "conflict":
                    reasons.append("sync_conflict_steward_review")
                reasons += _validate(name, row, fk_sets)
                if reasons:
                    bad.append({**row, "_quarantine_reason": ";".join(sorted(set(reasons)))})
                else:
                    good.append(row)
            silver[name] = good
            # Write Silver + quarantine as Parquet via temp CSV (no pandas).
            for rows, out_dir, extra in ((good, silver_dir, []), (bad, q_dir, ["_quarantine_reason"])):
                out = out_dir / f"{name}.parquet"
                if out.exists():
                    out.unlink()
                fields = columns_of(name) + ["_ingested_at", "_source_file", "_source_system",
                                              "_captured_offline", "_sync_status", "_batch_id", "_row_hash"] + extra
                tmp = out_dir / f"_{name}.tmp.csv"
                with open(tmp, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=fields)
                    w.writeheader()
                    w.writerows(rows)
                con.execute(f"COPY (SELECT * FROM read_csv('{tmp}', header=true, all_varchar=true)) TO '{out}' (FORMAT PARQUET)")
                tmp.unlink()
            results[name] = {"in": len(bronze[name]), "silver": len(good), "quarantined": len(bad)}
            print(f"silver {name}: in={len(bronze[name])} silver={len(good)} quarantined={len(bad)}")
    finally:
        con.close()
    return results
