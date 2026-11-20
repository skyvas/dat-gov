"""Generation, Bronze, Silver, Gold and quality tests."""

from __future__ import annotations

import hashlib
import json

import duckdb

from dat_gov.config import DATASETS, GOLD_MARTS, SCHEMAS, columns_of, pii_columns_of, pk_of
from dat_gov.generate import generate_all
from dat_gov.masking import hash_value, mask_email, mask_passport, mask_phone


def _count(con, root, layer, name):
    return con.execute(f"SELECT COUNT(*) FROM read_parquet('{root / 'data' / layer / name}.parquet')").fetchone()[0]


def _cols(con, root, layer, name):
    rel = con.execute(f"SELECT * FROM read_parquet('{root / 'data' / layer / name}.parquet') LIMIT 0")
    return [d[0] for d in rel.description]


# --- generation ---
def test_generation_counts_match_registry(tmp_path):
    counts = generate_all(tmp_path)
    assert counts == {name: meta["count"] for name, meta in DATASETS.items()}
    assert sum(counts.values()) == 88960


def test_generation_deterministic(tmp_path, tmp_path_factory):
    other = tmp_path_factory.mktemp("det")
    a = generate_all(tmp_path)
    b = generate_all(other)
    assert a == b
    for name in ("vessels", "ports", "crew_members"):
        ha = hashlib.sha256((tmp_path / "data" / "raw" / f"{name}.csv").read_bytes()).hexdigest()
        hb = hashlib.sha256((other / "data" / "raw" / f"{name}.csv").read_bytes()).hexdigest()
        assert ha == hb


def test_reference_tables_clean(pipeline_root):
    con = duckdb.connect()
    for name in ("ports", "warehouses"):
        assert _count(con, pipeline_root, "quarantine", name) == 0


# --- bronze ---
def test_bronze_row_counts_equal_raw(pipeline_root):
    con = duckdb.connect()
    for name, meta in DATASETS.items():
        assert _count(con, pipeline_root, "bronze", name) == meta["count"]


def test_bronze_has_audit_columns(pipeline_root):
    con = duckdb.connect()
    cols = _cols(con, pipeline_root, "bronze", "voyages")
    for c in ("_ingested_at", "_source_file", "_source_system", "_captured_offline",
              "_sync_status", "_batch_id", "_row_hash"):
        assert c in cols


def test_bronze_offline_rows_preserved(pipeline_root):
    con = duckdb.connect()
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/bronze/voyages.parquet') "
                    "WHERE _captured_offline = 'true'").fetchone()[0]
    assert n > 500  # ~35% of 3200 vessel-originated voyages
    n_onshore = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/bronze/ports.parquet') "
                            "WHERE _captured_offline = 'true'").fetchone()[0]
    assert n_onshore == 0


def test_bronze_sync_status_values_valid(pipeline_root):
    con = duckdb.connect()
    for name in DATASETS:
        vals = con.execute(f"SELECT DISTINCT _sync_status FROM read_parquet('{pipeline_root}/data/bronze/{name}.parquet')").fetchall()
        assert {v[0] for v in vals} <= {"synced", "pending", "conflict"}


def test_bronze_source_system_vessel_prefixed(pipeline_root):
    con = duckdb.connect()
    vals = con.execute(f"SELECT DISTINCT _source_system FROM read_parquet('{pipeline_root}/data/bronze/voyages.parquet')").fetchall()
    assert all(v[0].startswith("vessel-") for v in vals)
    vals = con.execute(f"SELECT DISTINCT _source_system FROM read_parquet('{pipeline_root}/data/bronze/ports.parquet')").fetchall()
    assert vals == [("warehouse-erp",)]


# --- silver ---
def test_silver_plus_quarantine_equals_bronze(pipeline_root):
    con = duckdb.connect()
    for name in DATASETS:
        b, s = _count(con, pipeline_root, "bronze", name), _count(con, pipeline_root, "silver", name)
        q = _count(con, pipeline_root, "quarantine", name)
        assert s + q == b, name


def test_silver_quarantine_rate_below_threshold(pipeline_root):
    con = duckdb.connect()
    for name, meta in DATASETS.items():
        q = _count(con, pipeline_root, "quarantine", name)
        assert q / meta["count"] < 0.05, name
        if meta.get("dirty") is not False and meta["count"] > 100:
            assert q > 0, name  # dirty rows were actually caught


def test_silver_pk_unique(pipeline_root):
    con = duckdb.connect()
    for name in DATASETS:
        pk = pk_of(name)
        total = _count(con, pipeline_root, "silver", name)
        distinct = con.execute(f"SELECT COUNT(DISTINCT {pk}) FROM read_parquet('{pipeline_root}/data/silver/{name}.parquet')").fetchone()[0]
        assert total == distinct, name


def test_silver_fk_integrity(pipeline_root):
    con = duckdb.connect()
    checks = [("voyages", "vessel_id", "vessels", "vessel_id"), ("voyages", "departure_port_id", "ports", "port_id"),
              ("crew_assignments", "crew_id", "crew_members", "crew_id"),
              ("stock_movements", "item_id", "inventory_items", "item_id"),
              ("deliveries", "po_id", "purchase_orders", "po_id"),
              ("work_orders", "asset_id", "assets", "asset_id"),
              ("fuel_bunkering", "supplier_id", "suppliers", "supplier_id")]
    for child, col, parent, pcol in checks:
        # FKs are validated against the dimension as received (Bronze): a parent
        # quarantined for its own defect must not cascade-quarantine its children.
        bad = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/{child}.parquet') c "
            f"LEFT JOIN read_parquet('{pipeline_root}/data/bronze/{parent}.parquet') p ON c.{col} = p.{pcol} "
            f"WHERE c.{col} <> '' AND p.{pcol} IS NULL").fetchone()[0]
        assert bad == 0, (child, col)


def test_silver_contract_not_null(pipeline_root):
    con = duckdb.connect()
    for name, cols in SCHEMAS.items():
        for c in cols:
            if not c["nullable"]:
                n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/{name}.parquet') "
                                f"WHERE {c['name']} IS NULL OR {c['name']} = ''").fetchone()[0]
                assert n == 0, (name, c["name"])


def test_vessel_linkage_exactly_one(pipeline_root):
    con = duckdb.connect()
    for name in ("assets", "documents"):
        bad = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/{name}.parquet') "
                          "WHERE (vessel_id = '') = (warehouse_id = '')").fetchone()[0]
        assert bad == 0, name
    for name in ("work_orders", "inspections"):
        bad = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/{name}.parquet') "
                          "WHERE vessel_id = '' AND warehouse_id = ''").fetchone()[0]
        assert bad == 0, name


def test_conformance_reports_link_audit_or_document(pipeline_root):
    con = duckdb.connect()
    bad = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/conformance_reports.parquet') "
                      "WHERE audit_id = '' AND document_id = ''").fetchone()[0]
    assert bad == 0


def test_quarantine_has_reasons(pipeline_root):
    con = duckdb.connect()
    rows = con.execute(f"SELECT _quarantine_reason FROM read_parquet('{pipeline_root}/data/quarantine/crew_members.parquet') LIMIT 5").fetchall()
    assert rows and all(r[0] for r in rows)


def test_conflict_safety_rows_quarantined_for_steward_review(pipeline_root):
    con = duckdb.connect()
    total = 0
    for name in ("documents", "audits", "conformance_reports", "incidents"):
        n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/quarantine/{name}.parquet') "
                        "WHERE _quarantine_reason LIKE '%sync_conflict_steward_review%'").fetchone()[0]
        total += n
        # no such row may survive in Silver
        s = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/{name}.parquet') "
                        "WHERE _sync_status = 'conflict'").fetchone()[0]
        assert s == 0, name
    assert total > 0


# --- gold ---
def test_gold_marts_exist_and_nonempty(pipeline_root):
    con = duckdb.connect()
    for mart in GOLD_MARTS:
        assert (pipeline_root / "data" / "gold" / f"{mart}.parquet").exists()
        assert _count(con, pipeline_root, "gold", mart) > 0, mart


def test_gold_voyage_reconciles_to_silver(pipeline_root):
    con = duckdb.connect()
    silver = _count(con, pipeline_root, "silver", "voyages")
    gold = con.execute(f"SELECT SUM(voyages) FROM read_parquet('{pipeline_root}/data/gold/gold_voyage_performance.parquet')").fetchone()[0]
    assert gold == silver


def test_gold_inventory_reconciles_to_silver(pipeline_root):
    con = duckdb.connect()
    silver = _count(con, pipeline_root, "silver", "inventory_items")
    gold = con.execute(f"SELECT SUM(items) FROM read_parquet('{pipeline_root}/data/gold/gold_inventory_health.parquet')").fetchone()[0]
    assert gold == silver


def test_gold_crew_certification_reconciles(pipeline_root):
    con = duckdb.connect()
    silver_crew = _count(con, pipeline_root, "silver", "crew_members")
    gold = con.execute(f"SELECT SUM(crew_count) FROM read_parquet('{pipeline_root}/data/gold/gold_crew_certification.parquet')").fetchone()[0]
    assert gold == silver_crew


def test_gold_supplier_reconciles(pipeline_root):
    con = duckdb.connect()
    silver_po = _count(con, pipeline_root, "silver", "purchase_orders")
    gold = con.execute(f"SELECT SUM(purchase_orders) FROM read_parquet('{pipeline_root}/data/gold/gold_supplier_performance.parquet')").fetchone()[0]
    assert gold == silver_po


def test_gold_work_order_cost_reconciles(pipeline_root):
    con = duckdb.connect()
    silver = _count(con, pipeline_root, "silver", "work_orders")
    gold = con.execute(f"SELECT SUM(work_orders) FROM read_parquet('{pipeline_root}/data/gold/gold_work_order_cost.parquet')").fetchone()[0]
    assert gold == silver


def test_gold_maintenance_backlog_reconciles(pipeline_root):
    con = duckdb.connect()
    open_silver = con.execute(f"SELECT COUNT(*) FROM read_parquet('{pipeline_root}/data/silver/work_orders.parquet') WHERE status <> 'completed'").fetchone()[0]
    gold = con.execute(f"SELECT SUM(open_work_orders) FROM read_parquet('{pipeline_root}/data/gold/gold_maintenance_backlog.parquet')").fetchone()[0]
    assert gold == open_silver


def test_gold_has_no_pii_columns(pipeline_root):
    con = duckdb.connect()
    pii = {"email", "phone", "passport_number", "seafarer_id", "contact_email"}
    for mart in GOLD_MARTS:
        cols = set(_cols(con, pipeline_root, "gold", mart))
        assert not (cols & pii), mart


# --- quality ---
def test_quality_report_passes(pipeline_root):
    report = json.loads((pipeline_root / "data" / "quality_report.json").read_text(encoding="utf-8"))
    assert report["overall"]["passed"] is True
    assert report["overall"]["quarantine_rate_pct"] < 5.0
    assert set(report["datasets"]) == set(DATASETS)


# --- PII / masking ---
def test_masking_deterministic():
    assert hash_value("a@example.com") == hash_value("a@example.com")
    assert hash_value("a@example.com") != hash_value("b@example.com")
    assert hash_value(None) is None


def test_masking_formats():
    assert mask_email("jane.doe@example.com") == "j***@example.com"
    assert mask_phone("+44 20 79460042") == "******42"
    assert mask_passport("A1234567") == "******67"


def test_gold_pii_free_by_construction():
    for name in DATASETS:
        assert pii_columns_of(name) == [c for c in ("email", "phone", "passport_number", "seafarer_id", "contact_email") if c in columns_of(name)]
