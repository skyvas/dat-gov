"""Gold marts: PII-free aggregates reconciled to Silver.

Governance concept demonstrated: Gold is the only layer consumers see.
It contains no raw crew email / phone / passport / seafarer ID (those
columns are never selected), and every mart total can be reconciled back
to a Silver count or sum — the reconciliation figures are printed by the
CLI and checked by the tests.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

REF = "2026-11-20"

QUERIES: dict[str, str] = {
    "gold_fleet_availability": """
        SELECT v.vessel_id, v.vessel_type, v.flag,
               strftime('%Y-%m', d.month_start) AS month,
               COUNT(*) AS vessel_months,
               SUM(CASE WHEN v.status = 'active' THEN 30 ELSE 0 END) AS days_available,
               SUM(CASE WHEN v.status = 'dry-dock' THEN 30 ELSE 0 END) AS days_dry_dock,
               SUM(CASE WHEN v.status = 'laid-up' THEN 30 ELSE 0 END) AS days_laid_up,
               ROUND(100.0 * SUM(CASE WHEN v.status = 'active' THEN 1 ELSE 0 END) / COUNT(*), 2) AS availability_pct
        FROM vessels v CROSS JOIN (SELECT DISTINCT date_trunc('month', departure_date::DATE)::DATE AS month_start
                                   FROM voyages) d
        GROUP BY v.vessel_id, v.vessel_type, v.flag, month
    """,
    "gold_voyage_performance": """
        SELECT vessel_id,
               departure_port_id || '->' || arrival_port_id AS route,
               strftime('%Y-%m', departure_date::DATE) AS month,
               COUNT(*) AS voyages,
               ROUND(100.0 * SUM(CASE WHEN voyage_status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct,
               ROUND(AVG(NULLIF(fuel_consumed_tonnes, '')::DOUBLE), 2) AS avg_fuel_tonnes,
               ROUND(SUM(cargo_tonnes::DOUBLE), 1) AS total_cargo_tonnes,
               ROUND(AVG(CASE WHEN cargo_tonnes::DOUBLE > 0 THEN NULLIF(fuel_consumed_tonnes, '')::DOUBLE / cargo_tonnes::DOUBLE END), 5) AS avg_fuel_per_tonne
        FROM voyages GROUP BY vessel_id, route, month
    """,
    "gold_inventory_health": """
        SELECT warehouse_id, category, COUNT(*) AS items,
               SUM(CASE WHEN current_qty::BIGINT <= reorder_level::BIGINT THEN 1 ELSE 0 END) AS low_stock_count,
               ROUND(SUM(current_qty::BIGINT * unit_cost::DOUBLE), 2) AS stock_value,
               SUM(current_qty::BIGINT) AS total_qty
        FROM inventory_items GROUP BY warehouse_id, category
    """,
    "gold_maintenance_backlog": """
        SELECT COALESCE(vessel_id, '') AS vessel_id, COALESCE(warehouse_id, '') AS warehouse_id,
               COUNT(*) AS open_work_orders,
               SUM(CASE WHEN status = 'overdue' OR (status <> 'completed' AND due_date::DATE < DATE '2026-11-20') THEN 1 ELSE 0 END) AS overdue_work_orders,
               ROUND(SUM(estimated_cost::DOUBLE), 2) AS backlog_cost,
               ROUND(SUM(estimated_hours::DOUBLE), 1) AS backlog_hours
        FROM work_orders WHERE status <> 'completed'
        GROUP BY vessel_id, warehouse_id
    """,
    "gold_compliance_posture": """
        SELECT COALESCE(vessel_id, '') AS vessel_id, COALESCE(warehouse_id, '') AS warehouse_id,
               (SELECT COUNT(*) FROM documents d2 WHERE d2.expiry_date::DATE < DATE '2026-11-20' + INTERVAL 90 DAY
                AND COALESCE(d2.vessel_id, '') = COALESCE(documents.vessel_id, '')
                AND COALESCE(d2.warehouse_id, '') = COALESCE(documents.warehouse_id, '')) AS documents_expiring_90d,
               (SELECT COUNT(*) FROM conformance_reports c WHERE c.conformance_status IN ('non-conformance', 'overdue')
                AND COALESCE(c.vessel_id, '') = COALESCE(documents.vessel_id, '')
                AND COALESCE(c.warehouse_id, '') = COALESCE(documents.warehouse_id, '')) AS overdue_conformance,
               (SELECT COUNT(*) FROM incidents i WHERE i.status <> 'closed'
                AND COALESCE(i.vessel_id, '') = COALESCE(documents.vessel_id, '')
                AND COALESCE(i.warehouse_id, '') = COALESCE(documents.warehouse_id, '')) AS open_incidents,
               (SELECT COUNT(*) FROM incidents i2 WHERE i2.status <> 'closed' AND i2.severity = 'critical'
                AND COALESCE(i2.vessel_id, '') = COALESCE(documents.vessel_id, '')
                AND COALESCE(i2.warehouse_id, '') = COALESCE(documents.warehouse_id, '')) AS open_critical_incidents
        FROM documents GROUP BY vessel_id, warehouse_id
    """,
    "gold_crew_certification": """
        SELECT c.rank, COUNT(DISTINCT c.crew_id) AS crew_count, COUNT(cert.certification_id) AS certifications,
               SUM(CASE WHEN cert.expiry_date::DATE < DATE '2026-11-20' + INTERVAL 90 DAY AND cert.expiry_date::DATE >= DATE '2026-11-20' THEN 1 ELSE 0 END) AS certs_expiring_90d,
               SUM(CASE WHEN cert.expiry_date::DATE < DATE '2026-11-20' THEN 1 ELSE 0 END) AS certs_expired
        FROM crew_members c LEFT JOIN certifications cert ON cert.crew_id = c.crew_id
        GROUP BY c.rank
    """,
    "gold_supplier_performance": """
        WITH po AS (SELECT supplier_id, po_id, total_amount::DOUBLE AS amt FROM purchase_orders),
             del AS (SELECT po_id, COUNT(*) AS n_del,
                            SUM(CASE WHEN delivery_status = 'received' THEN 1 ELSE 0 END) AS n_recv
                     FROM deliveries GROUP BY po_id)
        SELECT po.supplier_id, COUNT(*) AS purchase_orders, ROUND(SUM(po.amt), 2) AS total_spend,
               COALESCE(SUM(del.n_del), 0) AS deliveries,
               ROUND(100.0 * COALESCE(SUM(del.n_recv), 0) / NULLIF(COALESCE(SUM(del.n_del), 0), 0), 2) AS on_time_delivery_pct
        FROM po LEFT JOIN del ON del.po_id = po.po_id
        GROUP BY po.supplier_id
    """,
    "gold_work_order_cost": """
        SELECT COALESCE(vessel_id, '') AS vessel_id, COALESCE(warehouse_id, '') AS warehouse_id,
               wo_type, strftime('%Y-%m', created_date::DATE) AS month,
               COUNT(*) AS work_orders,
               ROUND(SUM(estimated_cost::DOUBLE), 2) AS planned_cost,
               ROUND(SUM(COALESCE(NULLIF(actual_cost, '')::DOUBLE, 0)), 2) AS actual_cost,
               ROUND(SUM(COALESCE(NULLIF(actual_cost, '')::DOUBLE, 0)) - SUM(estimated_cost::DOUBLE), 2) AS cost_variance,
               ROUND(SUM(estimated_hours::DOUBLE), 1) AS planned_hours,
               ROUND(SUM(COALESCE(NULLIF(actual_hours, '')::DOUBLE, 0)), 1) AS actual_hours
        FROM work_orders GROUP BY vessel_id, warehouse_id, wo_type, month
    """,
}


def transform_gold(root: Path) -> dict[str, int]:
    """Silver -> Gold Parquet marts. Returns row count per mart."""
    silver_dir, gold_dir = root / "data" / "silver", root / "data" / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    results: dict[str, int] = {}
    try:
        for name in ("vessels", "voyages", "inventory_items", "work_orders", "documents",
                     "conformance_reports", "incidents", "crew_members", "certifications",
                     "purchase_orders", "deliveries"):
            con.execute(f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM read_parquet('{silver_dir / name}.parquet')")
        for mart, sql in QUERIES.items():
            out = gold_dir / f"{mart}.parquet"
            if out.exists():
                out.unlink()
            con.execute(f"COPY ({sql}) TO '{out}' (FORMAT PARQUET)")
            n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out}')").fetchone()[0]
            results[mart] = int(n)
            print(f"gold {mart}: rows={n}")
    finally:
        con.close()
    return results
