"""Silver transform: Bronze -> cleaned, typed, contract-validated Silver.

Governance idea demonstrated here: a *data contract* (YAML) is the
law for each dataset. Every row is checked against it — types, not-null,
ranges, formats, allowed values, future dates, foreign keys, primary-key
uniqueness. A row that fails any check is *quarantined* (written to
``data/quarantine/<dataset>.parquet`` with ``_quarantine_reason``) and
counted in the quality report. Nothing is silently dropped, and a
quarantined row can be inspected, fixed at source, and re-run.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from .config import (
    BRONZE_DIR,
    CONTRACTS_DIR,
    DATASETS,
    QUARANTINE_DIR,
    SILVER_DIR,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TODAY = date(2026, 6, 1)  # "today" for the synthetic universe (latest term is 2026-Spring)


def load_contract(name: str) -> dict:
    """Load the YAML contract for a dataset."""
    return yaml.safe_load((CONTRACTS_DIR / f"{name}.yaml").read_text(encoding="utf-8"))


def _cast(value: str | None, col_type: str):
    """Cast a raw (all-varchar) Bronze value to its contract type."""
    if value is None or str(value).strip() == "":
        return None
    v = str(value).strip()
    if col_type == "INTEGER":
        return int(float(v))
    if col_type == "DOUBLE":
        return float(v)
    if col_type == "DATE":
        return date.fromisoformat(v[:10])
    return v


def _validate(row: dict, contract: dict, refs: dict[str, set]) -> list[str]:
    """Return the list of contract violations for one (already cast) row."""
    reasons: list[str] = []
    cols = {c["name"]: c for c in contract["columns"]}
    for col in contract["columns"]:
        if not col["nullable"] and row.get(col["name"]) is None:
            reasons.append(f"null:{col['name']}")
    for check in contract.get("checks", []):
        kind, col = check["type"], check["column"]
        val = row.get(col)
        if val is None:
            continue
        if kind == "range":
            if "min" in check and val < check["min"]:
                reasons.append(f"range:{col}<{check['min']}")
            if "max" in check and val > check["max"]:
                reasons.append(f"range:{col}>{check['max']}")
        elif kind == "format" and check.get("pattern") == "email":
            if not EMAIL_RE.match(str(val)):
                reasons.append(f"format:email:{col}")
        elif kind == "date_not_future":
            if isinstance(val, date) and val > TODAY:
                reasons.append(f"future_date:{col}")
        elif kind == "allowed_values":
            if val not in check["values"]:
                reasons.append(f"not_allowed:{col}={val}")
        elif kind == "foreign_key":
            ref_dataset, _ref_col = check["references"].split(".")
            if ref_dataset in refs and val not in refs[ref_dataset]:
                reasons.append(f"unknown_fk:{col}={val}")
    _ = cols
    return reasons


def _read_bronze(name: str, bronze_dir: Path) -> tuple[list[str], list[dict]]:
    con = duckdb.connect()
    try:
        rel = con.execute(f"SELECT * FROM read_parquet('{bronze_dir / f'{name}.parquet'}')")
        cols = [d[0] for d in rel.description]
        rows = [dict(zip(cols, r)) for r in rel.fetchall()]
        return cols, rows
    finally:
        con.close()


def transform_dataset(
    name: str,
    bronze_dir: Path = BRONZE_DIR,
    silver_dir: Path = SILVER_DIR,
    quarantine_dir: Path = QUARANTINE_DIR,
    refs: dict[str, set] | None = None,
) -> dict[str, int]:
    """Transform one dataset. Returns {bronze, silver, quarantined} counts."""
    contract = load_contract(name)
    pk = contract["primary_key"]
    raw_cols, raw_rows = _read_bronze(name, bronze_dir)
    data_cols = [c for c in raw_cols if not c.startswith("_")]
    col_types = {c["name"]: c["type"] for c in contract["columns"]}
    refs = refs if refs is not None else {}
    seen: set = set()
    clean, quarantined = [], []
    for raw in raw_rows:
        row: dict = {}
        cast_errors: list[str] = []
        for col in data_cols:
            try:
                row[col] = _cast(raw.get(col), col_types.get(col, "VARCHAR"))
            except (ValueError, TypeError):
                row[col] = None
                cast_errors.append(f"bad_type:{col}")
        reasons = list(cast_errors)
        if row.get(pk) in seen:
            reasons.append(f"duplicate_pk:{pk}={row.get(pk)}")
        else:
            seen.add(row.get(pk))
        reasons += _validate(row, contract, refs)
        if reasons:
            q = {c: ("" if raw.get(c) is None else str(raw.get(c))) for c in data_cols}
            q["_quarantine_reason"] = "; ".join(sorted(set(reasons)))
            quarantined.append(q)
        else:
            clean.append(row)
    silver_dir.mkdir(parents=True, exist_ok=True)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    # Silver: typed via the contract column order.
    silver_table = pa.Table.from_pylist(clean, schema=_arrow_schema(contract)) if clean else pa.Table.from_pylist(
        [], schema=_arrow_schema(contract)
    )
    pq.write_table(silver_table, silver_dir / f"{name}.parquet")
    q_cols = data_cols + ["_quarantine_reason"]
    q_schema = pa.schema([(c, pa.string()) for c in q_cols])
    if quarantined:
        q_table = pa.Table.from_pylist(quarantined, schema=q_schema)
    else:
        q_table = pa.Table.from_pylist([], schema=q_schema)
    pq.write_table(q_table, quarantine_dir / f"{name}.parquet")
    return {"bronze": len(raw_rows), "silver": len(clean), "quarantined": len(quarantined)}


def _arrow_schema(contract: dict) -> pa.Schema:
    type_map = {"VARCHAR": pa.string(), "INTEGER": pa.int64(), "DOUBLE": pa.float64(), "DATE": pa.date32()}
    fields = []
    for col in contract["columns"]:
        fields.append(pa.field(col["name"], type_map[col["type"]], nullable=col["nullable"]))
    return pa.schema(fields)


def transform_all(
    bronze_dir: Path = BRONZE_DIR,
    silver_dir: Path = SILVER_DIR,
    quarantine_dir: Path = QUARANTINE_DIR,
) -> dict[str, dict[str, int]]:
    """Transform every dataset in dependency order (FK targets first)."""
    refs: dict[str, set] = {}
    results: dict[str, dict[str, int]] = {}
    for name in DATASETS:
        result = transform_dataset(name, bronze_dir, silver_dir, quarantine_dir, refs=refs)
        results[name] = result
        # Reference set for later FK checks = Silver primary keys.
        contract = load_contract(name)
        con = duckdb.connect()
        try:
            pk = contract["primary_key"]
            vals = con.execute(f"SELECT {pk} FROM read_parquet('{silver_dir / f'{name}.parquet'}')").fetchall()
            refs[name] = {v[0] for v in vals if v[0] is not None}
        finally:
            con.close()
    return results
