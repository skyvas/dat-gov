"""Registry: datasets, schemas, owners, source systems.

Governance concept demonstrated: a single registry is the source of truth
for counts, primary keys, foreign keys and source systems, so the generator,
the Bronze/Silver/Gold transforms, the contracts and the tests all agree
instead of drifting apart.
"""

from __future__ import annotations

from pathlib import Path

SEED = 42
# Reference "today" for future-date validation; the synthetic world ends here.
REFERENCE_DATE = "2026-11-20"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DOMAIN = "Maritime Supply Chain & Fleet Operations"
COMPANY = "Northgate Maritime"

SUBDOMAINS = {
    "fleet": {"owner": "Fleet Director", "steward": "Fleet Operations Steward"},
    "crew": {"owner": "Crewing Manager", "steward": "Crewing Steward"},
    "warehouse": {"owner": "Warehouse Manager", "steward": "Inventory Steward"},
    "procurement": {"owner": "Procurement Manager", "steward": "Procurement Steward"},
    "maintenance": {"owner": "Technical Manager", "steward": "Maintenance Steward"},
    "compliance": {"owner": "Compliance Officer", "steward": "Compliance Steward"},
}

DOMAIN_OWNER = "Chief Operating Officer"


def col(name: str, dtype: str, nullable: bool = True, pii: bool = False) -> dict:
    """One column definition: name, DuckDB type, nullability, PII flag."""
    return {"name": name, "type": dtype, "nullable": nullable, "pii": pii}


# Schema per dataset. FKs are listed separately so Silver can check them.
SCHEMAS: dict[str, list[dict]] = {
    "vessels": [
        col("vessel_id", "VARCHAR", False), col("vessel_name", "VARCHAR", False),
        col("vessel_type", "VARCHAR", False), col("imo_number", "VARCHAR", False),
        col("flag", "VARCHAR", False), col("gross_tonnage", "BIGINT", False),
        col("year_built", "BIGINT", False), col("status", "VARCHAR", False),
        col("home_port_id", "VARCHAR", False),
    ],
    "voyages": [
        col("voyage_id", "VARCHAR", False), col("vessel_id", "VARCHAR", False),
        col("departure_port_id", "VARCHAR", False), col("arrival_port_id", "VARCHAR", False),
        col("departure_date", "DATE", False), col("arrival_date", "DATE", True),
        col("cargo_type", "VARCHAR", False), col("cargo_tonnes", "DOUBLE", False),
        col("voyage_status", "VARCHAR", False), col("fuel_consumed_tonnes", "DOUBLE", True),
    ],
    "ports": [
        col("port_id", "VARCHAR", False), col("port_name", "VARCHAR", False),
        col("country", "VARCHAR", False), col("region", "VARCHAR", False),
        col("unlocode", "VARCHAR", False), col("port_type", "VARCHAR", False),
    ],
    "crew_members": [
        col("crew_id", "VARCHAR", False), col("first_name", "VARCHAR", False),
        col("last_name", "VARCHAR", False), col("rank", "VARCHAR", False),
        col("nationality", "VARCHAR", False), col("date_of_birth", "DATE", False),
        col("email", "VARCHAR", False, pii=True), col("phone", "VARCHAR", False, pii=True),
        col("passport_number", "VARCHAR", False, pii=True), col("seafarer_id", "VARCHAR", False, pii=True),
        col("employment_status", "VARCHAR", False),
    ],
    "crew_assignments": [
        col("assignment_id", "VARCHAR", False), col("crew_id", "VARCHAR", False),
        col("vessel_id", "VARCHAR", False), col("role", "VARCHAR", False),
        col("embark_date", "DATE", False), col("disembark_date", "DATE", True),
        col("assignment_status", "VARCHAR", False),
    ],
    "certifications": [
        col("certification_id", "VARCHAR", False), col("crew_id", "VARCHAR", False),
        col("certification_type", "VARCHAR", False), col("issuing_authority", "VARCHAR", False),
        col("issue_date", "DATE", False), col("expiry_date", "DATE", False),
        col("cert_status", "VARCHAR", False),
    ],
    "warehouses": [
        col("warehouse_id", "VARCHAR", False), col("warehouse_name", "VARCHAR", False),
        col("location", "VARCHAR", False), col("port_id", "VARCHAR", False),
        col("capacity_sqm", "BIGINT", False), col("warehouse_type", "VARCHAR", False),
    ],
    "inventory_items": [
        col("item_id", "VARCHAR", False), col("sku", "VARCHAR", False),
        col("item_name", "VARCHAR", False), col("category", "VARCHAR", False),
        col("warehouse_id", "VARCHAR", False), col("vessel_id", "VARCHAR", True),
        col("unit", "VARCHAR", False), col("unit_cost", "DOUBLE", False),
        col("reorder_level", "BIGINT", False), col("current_qty", "BIGINT", False),
    ],
    "stock_movements": [
        col("movement_id", "VARCHAR", False), col("item_id", "VARCHAR", False),
        col("warehouse_id", "VARCHAR", False), col("vessel_id", "VARCHAR", True),
        col("movement_type", "VARCHAR", False), col("quantity", "BIGINT", False),
        col("movement_date", "DATE", False), col("reference", "VARCHAR", False),
    ],
    "suppliers": [
        col("supplier_id", "VARCHAR", False), col("supplier_name", "VARCHAR", False),
        col("country", "VARCHAR", False), col("region", "VARCHAR", False),
        col("category", "VARCHAR", False), col("contact_email", "VARCHAR", False, pii=True),
        col("rating", "DOUBLE", False), col("supplier_status", "VARCHAR", False),
    ],
    "purchase_orders": [
        col("po_id", "VARCHAR", False), col("supplier_id", "VARCHAR", False),
        col("warehouse_id", "VARCHAR", False), col("vessel_id", "VARCHAR", True),
        col("order_date", "DATE", False), col("required_date", "DATE", False),
        col("total_amount", "DOUBLE", False), col("po_status", "VARCHAR", False),
        col("currency", "VARCHAR", False),
    ],
    "deliveries": [
        col("delivery_id", "VARCHAR", False), col("po_id", "VARCHAR", False),
        col("delivery_date", "DATE", False), col("received_qty", "BIGINT", False),
        col("delivered_amount", "DOUBLE", False), col("delivery_status", "VARCHAR", False),
        col("received_by_warehouse_id", "VARCHAR", False),
    ],
    "assets": [
        col("asset_id", "VARCHAR", False), col("asset_name", "VARCHAR", False),
        col("asset_type", "VARCHAR", False), col("vessel_id", "VARCHAR", True),
        col("warehouse_id", "VARCHAR", True), col("serial_number", "VARCHAR", False),
        col("install_date", "DATE", False), col("asset_status", "VARCHAR", False),
        col("criticality", "VARCHAR", False),
    ],
    "work_orders": [
        col("wo_id", "VARCHAR", False), col("asset_id", "VARCHAR", False),
        col("vessel_id", "VARCHAR", True), col("warehouse_id", "VARCHAR", True),
        col("wo_type", "VARCHAR", False), col("priority", "VARCHAR", False),
        col("description", "VARCHAR", False), col("created_date", "DATE", False),
        col("due_date", "DATE", False), col("completed_date", "DATE", True),
        col("status", "VARCHAR", False), col("estimated_cost", "DOUBLE", False),
        col("actual_cost", "DOUBLE", True), col("estimated_hours", "DOUBLE", False),
        col("actual_hours", "DOUBLE", True), col("assigned_crew_id", "VARCHAR", True),
    ],
    "inspections": [
        col("inspection_id", "VARCHAR", False), col("asset_id", "VARCHAR", False),
        col("vessel_id", "VARCHAR", True), col("warehouse_id", "VARCHAR", True),
        col("inspection_type", "VARCHAR", False), col("inspection_date", "DATE", False),
        col("inspector", "VARCHAR", False), col("result", "VARCHAR", False),
        col("findings", "VARCHAR", False),
    ],
    "documents": [
        col("document_id", "VARCHAR", False), col("document_type", "VARCHAR", False),
        col("vessel_id", "VARCHAR", True), col("warehouse_id", "VARCHAR", True),
        col("title", "VARCHAR", False), col("issuer", "VARCHAR", False),
        col("issue_date", "DATE", False), col("expiry_date", "DATE", False),
        col("doc_status", "VARCHAR", False), col("file_reference", "VARCHAR", False),
    ],
    "audits": [
        col("audit_id", "VARCHAR", False), col("audit_type", "VARCHAR", False),
        col("vessel_id", "VARCHAR", True), col("warehouse_id", "VARCHAR", True),
        col("audit_date", "DATE", False), col("auditor", "VARCHAR", False),
        col("audit_status", "VARCHAR", False), col("findings_count", "BIGINT", False),
        col("audit_result", "VARCHAR", False),
    ],
    "conformance_reports": [
        col("report_id", "VARCHAR", False), col("audit_id", "VARCHAR", True),
        col("document_id", "VARCHAR", True), col("vessel_id", "VARCHAR", True),
        col("warehouse_id", "VARCHAR", True), col("report_date", "DATE", False),
        col("conformance_status", "VARCHAR", False), col("description", "VARCHAR", False),
    ],
    "incidents": [
        col("incident_id", "VARCHAR", False), col("vessel_id", "VARCHAR", True),
        col("warehouse_id", "VARCHAR", True), col("incident_date", "DATE", False),
        col("incident_type", "VARCHAR", False), col("severity", "VARCHAR", False),
        col("description", "VARCHAR", False), col("status", "VARCHAR", False),
        col("reported_by_crew_id", "VARCHAR", True),
    ],
    # 20th dataset: the brief enumerates 19 by name but requires 20 datasets.
    # Fuel bunkering is the natural missing fleet fact (vessel + port + supplier).
    "fuel_bunkering": [
        col("bunkering_id", "VARCHAR", False), col("vessel_id", "VARCHAR", False),
        col("port_id", "VARCHAR", False), col("supplier_id", "VARCHAR", False),
        col("bunkering_date", "DATE", False), col("fuel_type", "VARCHAR", False),
        col("quantity_tonnes", "DOUBLE", False), col("cost_amount", "DOUBLE", False),
        col("currency", "VARCHAR", False),
    ],
}

# (column, referenced dataset, referenced column)
FOREIGN_KEYS: dict[str, list[tuple[str, str, str]]] = {
    "vessels": [("home_port_id", "ports", "port_id")],
    "voyages": [("vessel_id", "vessels", "vessel_id"), ("departure_port_id", "ports", "port_id"),
                ("arrival_port_id", "ports", "port_id")],
    "crew_assignments": [("crew_id", "crew_members", "crew_id"), ("vessel_id", "vessels", "vessel_id")],
    "certifications": [("crew_id", "crew_members", "crew_id")],
    "warehouses": [("port_id", "ports", "port_id")],
    "inventory_items": [("warehouse_id", "warehouses", "warehouse_id"), ("vessel_id", "vessels", "vessel_id")],
    "stock_movements": [("item_id", "inventory_items", "item_id"), ("warehouse_id", "warehouses", "warehouse_id"),
                        ("vessel_id", "vessels", "vessel_id")],
    "purchase_orders": [("supplier_id", "suppliers", "supplier_id"), ("warehouse_id", "warehouses", "warehouse_id"),
                        ("vessel_id", "vessels", "vessel_id")],
    "deliveries": [("po_id", "purchase_orders", "po_id"),
                   ("received_by_warehouse_id", "warehouses", "warehouse_id")],
    "assets": [("vessel_id", "vessels", "vessel_id"), ("warehouse_id", "warehouses", "warehouse_id")],
    "work_orders": [("asset_id", "assets", "asset_id"), ("vessel_id", "vessels", "vessel_id"),
                    ("warehouse_id", "warehouses", "warehouse_id"),
                    ("assigned_crew_id", "crew_members", "crew_id")],
    "inspections": [("asset_id", "assets", "asset_id"), ("vessel_id", "vessels", "vessel_id"),
                    ("warehouse_id", "warehouses", "warehouse_id")],
    "documents": [("vessel_id", "vessels", "vessel_id"), ("warehouse_id", "warehouses", "warehouse_id")],
    "audits": [("vessel_id", "vessels", "vessel_id"), ("warehouse_id", "warehouses", "warehouse_id")],
    "conformance_reports": [("audit_id", "audits", "audit_id"), ("document_id", "documents", "document_id"),
                            ("vessel_id", "vessels", "vessel_id"),
                            ("warehouse_id", "warehouses", "warehouse_id")],
    "incidents": [("vessel_id", "vessels", "vessel_id"), ("warehouse_id", "warehouses", "warehouse_id"),
                  ("reported_by_crew_id", "crew_members", "crew_id")],
    "fuel_bunkering": [("vessel_id", "vessels", "vessel_id"), ("port_id", "ports", "port_id"),
                       ("supplier_id", "suppliers", "supplier_id")],
}

# Primary keys, counts, subdomain, source origin.
# source_origin: "onshore" (warehouse-erp) or "vessel" (vessel systems) or "mixed".
DATASETS: dict[str, dict] = {
    "vessels": {"subdomain": "fleet", "count": 48, "pk": "vessel_id", "source": "mixed"},
    "voyages": {"subdomain": "fleet", "count": 3200, "pk": "voyage_id", "source": "vessel"},
    "ports": {"subdomain": "fleet", "count": 64, "pk": "port_id", "source": "onshore", "dirty": False},
    "crew_members": {"subdomain": "crew", "count": 1800, "pk": "crew_id", "source": "onshore"},
    "crew_assignments": {"subdomain": "crew", "count": 4500, "pk": "assignment_id", "source": "mixed"},
    "certifications": {"subdomain": "crew", "count": 3600, "pk": "certification_id", "source": "mixed"},
    "warehouses": {"subdomain": "warehouse", "count": 8, "pk": "warehouse_id", "source": "onshore", "dirty": False},
    "inventory_items": {"subdomain": "warehouse", "count": 6000, "pk": "item_id", "source": "onshore"},
    "stock_movements": {"subdomain": "warehouse", "count": 25000, "pk": "movement_id", "source": "mixed"},
    "suppliers": {"subdomain": "procurement", "count": 140, "pk": "supplier_id", "source": "onshore"},
    "purchase_orders": {"subdomain": "procurement", "count": 4800, "pk": "po_id", "source": "onshore"},
    "deliveries": {"subdomain": "procurement", "count": 3800, "pk": "delivery_id", "source": "mixed"},
    "assets": {"subdomain": "maintenance", "count": 9500, "pk": "asset_id", "source": "mixed"},
    "work_orders": {"subdomain": "maintenance", "count": 9000, "pk": "wo_id", "source": "vessel"},
    "inspections": {"subdomain": "maintenance", "count": 4200, "pk": "inspection_id", "source": "vessel"},
    "documents": {"subdomain": "compliance", "count": 7500, "pk": "document_id", "source": "mixed"},
    "audits": {"subdomain": "compliance", "count": 850, "pk": "audit_id", "source": "mixed"},
    "conformance_reports": {"subdomain": "compliance", "count": 1400, "pk": "report_id", "source": "mixed"},
    "incidents": {"subdomain": "compliance", "count": 950, "pk": "incident_id", "source": "vessel"},
    "fuel_bunkering": {"subdomain": "fleet", "count": 2600, "pk": "bunkering_id", "source": "vessel"},
}

# The registry above is authoritative; keep the total honest.
TOTAL_RAW = sum(d["count"] for d in DATASETS.values())

GOLD_MARTS = [
    "gold_fleet_availability", "gold_voyage_performance", "gold_inventory_health",
    "gold_maintenance_backlog", "gold_compliance_posture", "gold_crew_certification",
    "gold_supplier_performance", "gold_work_order_cost",
]

# Datasets whose rows originate on a vessel (vessel-<id> source system).
VESSEL_ORIGINATED = {"voyages", "work_orders", "inspections", "incidents"}
# Safety / compliance datasets: sync conflicts go to steward review, never last-write-wins.
SAFETY_COMPLIANCE = {"documents", "audits", "conformance_reports", "incidents"}

BRONZE_COLUMNS = ["_ingested_at", "_source_file", "_source_system", "_captured_offline",
                  "_sync_status", "_batch_id", "_row_hash"]


def pk_of(dataset: str) -> str:
    """Primary-key column for a dataset."""
    return DATASETS[dataset]["pk"]


def columns_of(dataset: str) -> list[str]:
    """Column names for a dataset, in schema order."""
    return [c["name"] for c in SCHEMAS[dataset]]


def pii_columns_of(dataset: str) -> list[str]:
    """PII columns for a dataset."""
    return [c["name"] for c in SCHEMAS[dataset] if c["pii"]]
