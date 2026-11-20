"""Synthetic data generation (deterministic, seed 42, stdlib random only).

Governance concept demonstrated: synthetic data with depth — realistic
maritime values, consistent foreign keys, and a controlled ~2-3% dirty
share per dataset (never in the reference tables ports / warehouses) so
the Silver contract checks and quarantine path have something real to do.
No real personal data is used anywhere.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from .config import DATASETS, REFERENCE_DATE, SCHEMAS, SEED, columns_of

REF = date.fromisoformat(REFERENCE_DATE)

PORTS = [
    ("Singapore", "Singapore", "Asia-Pacific", "SGSIN", "container"), ("Rotterdam", "Netherlands", "Europe", "NLRTM", "container"),
    ("Shanghai", "China", "Asia-Pacific", "CNSHA", "container"), ("Houston", "United States", "Americas", "USHOU", "bulk"),
    ("Antwerp", "Belgium", "Europe", "BEANR", "container"), ("Busan", "South Korea", "Asia-Pacific", "KRPUS", "container"),
    ("Dubai", "United Arab Emirates", "Middle East", "AEDXB", "container"), ("Los Angeles", "United States", "Americas", "USLAX", "container"),
    ("Hamburg", "Germany", "Europe", "DEHAM", "container"), ("Santos", "Brazil", "Americas", "BRSSZ", "bulk"),
    ("Mumbai", "India", "Asia-Pacific", "INNSA", "container"), ("Tokyo", "Japan", "Asia-Pacific", "JPTYO", "container"),
    ("Felixstowe", "United Kingdom", "Europe", "GBFXT", "container"), ("Valencia", "Spain", "Europe", "ESVLC", "container"),
    ("Jeddah", "Saudi Arabia", "Middle East", "SAJED", "container"), ("Cape Town", "South Africa", "Africa", "ZACPT", "bulk"),
    ("Sydney", "Australia", "Oceania", "AUSYD", "container"), ("Vancouver", "Canada", "Americas", "CAVAN", "bulk"),
    ("Piraeus", "Greece", "Europe", "GRPIR", "container"), ("New York", "United States", "Americas", "USNYC", "container"),
    ("Kaohsiung", "Taiwan", "Asia-Pacific", "TWKHH", "container"), ("Algeciras", "Spain", "Europe", "ESALG", "container"),
    ("Port Klang", "Malaysia", "Asia-Pacific", "MYPKG", "container"), ("Genoa", "Italy", "Europe", "ITGOA", "container"),
    ("Montreal", "Canada", "Americas", "CAMTR", "bulk"), ("Durban", "South Africa", "Africa", "ZADUR", "container"),
    ("Istanbul", "Turkiye", "Europe", "TRIST", "container"), ("Manila", "Philippines", "Asia-Pacific", "PHMNL", "container"),
    ("Auckland", "New Zealand", "Oceania", "NZAKL", "container"), ("Le Havre", "France", "Europe", "FRLEH", "container"),
    ("Colombo", "Sri Lanka", "Asia-Pacific", "LKCMB", "container"), ("Panama City", "Panama", "Americas", "PAPTY", "container"),
    ("Gdansk", "Poland", "Europe", "PLGDN", "container"), ("Bangkok", "Thailand", "Asia-Pacific", "THBKK", "bulk"),
    ("Alexandria", "Egypt", "Africa", "EGALY", "container"), ("Oslo", "Norway", "Europe", "NOOSL", "bulk"),
    ("Marseille", "France", "Europe", "FRMRS", "container"), ("Chennai", "India", "Asia-Pacific", "INMAA", "bulk"),
    ("Valparaiso", "Chile", "Americas", "CLVAP", "bulk"), ("Halifax", "Canada", "Americas", "CAHAL", "container"),
    ("Abidjan", "Cote d'Ivoire", "Africa", "CIABJ", "bulk"), ("Gothenburg", "Sweden", "Europe", "SEGOT", "container"),
    ("Brisbane", "Australia", "Oceania", "AUBNE", "bulk"), ("Qingdao", "China", "Asia-Pacific", "CNTAO", "container"),
    ("Lagos", "Nigeria", "Africa", "NGLOS", "bulk"), ("Jakarta", "Indonesia", "Asia-Pacific", "IDJKT", "container"),
    ("Buenos Aires", "Argentina", "Americas", "ARBUE", "container"), ("Kobe", "Japan", "Asia-Pacific", "JPUKB", "container"),
    ("Liverpool", "United Kingdom", "Europe", "GBLIV", "bulk"), ("Pusan", "South Korea", "Asia-Pacific", "KRPUS", "bulk"),
    ("Salalah", "Oman", "Middle East", "OMSAL", "container"), ("Ningbo", "China", "Asia-Pacific", "CNNGB", "container"),
    ("Dublin", "Ireland", "Europe", "IEDUB", "container"), ("Callao", "Peru", "Americas", "PECLL", "bulk"),
    ("Tema", "Ghana", "Africa", "GHTEM", "bulk"), ("Surabaya", "Indonesia", "Asia-Pacific", "IDSUB", "bulk"),
    ("St Petersburg", "Russia", "Europe", "RULED", "bulk"), ("Abu Dhabi", "United Arab Emirates", "Middle East", "AEAUH", "bulk"),
    ("Yokohama", "Japan", "Asia-Pacific", "JPYOK", "container"), ("Tanjung Pelepas", "Malaysia", "Asia-Pacific", "MYTPP", "container"),
    ("Freeport", "Bahamas", "Americas", "BSFPO", "container"), ("Mombasa", "Kenya", "Africa", "KEMBA", "bulk"),
    ("Tangier", "Morocco", "Africa", "MATNG", "container"), ("Haifa", "Israel", "Middle East", "ILHFA", "container"),
]

VESSEL_TYPES = ["container", "bulk carrier", "tanker", "offshore support", "tug"]
FLAGS = ["Panama", "Liberia", "Singapore", "Malta", "Marshall Islands", "Bahamas", "Cyprus", "United Kingdom", "Netherlands", "Norway"]
RANKS = ["Master", "Chief Officer", "Chief Engineer", "Second Engineer", "Able Seaman", "Ordinary Seaman", "Cook", "Electrician", "Bosun", "Deck Cadet", "Engine Cadet", "Steward"]
NATIONALITIES = ["Philippines", "India", "Indonesia", "Ukraine", "Poland", "Greece", "United Kingdom", "Croatia", "Myanmar", "Bangladesh", "Romania", "China"]
FIRST = ["Arjun", "Maria", "Ivan", "Rajesh", "Elena", "Tomasz", "Aisha", "Dmitri", "Sofia", "Liam", "Priya", "Anders", "Kenji", "Fatima", "Piotr", "Grace", "Viktor", "Nadia", "Carlos", "Hana", "Oleg", "Mei", "Stefan", "Lara", "Yusuf", "Ingrid", "Marco", "Anita", "Sergei", "Dalia", "Kofi", "Rosa", "Nikolai", "Tara", "Emil", "Zara", "Felix", "Ines", "Ravi", "Olga"]
LAST = ["Patel", "Santos", "Kowalski", "Novak", "Garcia", "Kim", "Okafor", "Silva", "Petrov", "Nguyen", "Muller", "Costa", "Ivanov", "Reyes", "Dube", "Larsen", "Tanaka", "Ali", "Berg", "Moreau", "Singh", "Fischer", "Adeyemi", "Kaur", "Lindqvist", "Rossi", "Haddad", "Varga", "Mensah", "Dubois", "Chen", "Khan", "Sorensen", "Marino", "Osei", "Klein", "Nakamura", "Iversen", "Diaz", "Ahmad"]
CARGO = ["containers", "iron ore", "crude oil", "grain", "coal", "LNG", "vehicles", "general cargo", "chemicals", "timber"]
CATEGORIES = ["engine spares", "safety", "deck", "electrical", "provisions"]
ITEM_NAMES = {"engine spares": ["Fuel injector", "Turbocharger kit", "Piston ring set", "Lube oil filter", "Cylinder liner", "Fuel pump"],
              "safety": ["Life jacket", "Fire extinguisher", "Immersion suit", "Safety harness", "EPIRB battery", "Smoke detector"],
              "deck": ["Mooring rope", "Anchor chain link", "Paint - marine grey", "Wire rope sling", "Fender", "Hatch seal"],
              "electrical": ["Circuit breaker", "Cable tray", "LED floodlight", "Battery 12V", "Motor starter", "Sensor - temperature"],
              "provisions": ["Rice 25kg", "Canned vegetables", "Drinking water 1.5L", "Coffee beans", "Frozen chicken", "Cooking oil"]}
SUPPLIER_CATS = ["engine spares", "safety equipment", "provisions", "fuel", "deck stores", "electrical", "repair services"]
DOC_TYPES = ["Safety Management Certificate", "Load Line Certificate", "Class Certificate", "Insurance Certificate", "Crew Medical Certificate", "Pollution Prevention Certificate", "Ship Sanitation Certificate", "Minimum Safe Manning Document"]
AUDIT_TYPES = ["ISM", "ISPS", "Port State Control", "internal"]
CERT_TYPES = ["STCW Basic Safety", "Medical Fitness", "GMDSS", "Tanker Endorsement", "Proficiency in Survival Craft", "Advanced Fire Fighting", "Security Awareness", "Bridge Resource Management"]
ASSET_TYPES = ["main engine", "generator", "crane", "pump", "compressor", "navigation radar", "lifeboat", "forklift", "boiler", "winch"]
WO_TYPES = ["planned", "corrective", "dry-dock", "emergency"]
INCIDENT_TYPES = ["near miss", "oil spill", "injury", "equipment failure", "fire", "collision", "grounding", "security incident"]


def _d(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, max((end - start).days, 0)))


def _iso(d: date | None) -> str:
    return "" if d is None else d.isoformat()


def _money(rng: random.Random, lo: float, hi: float) -> str:
    return f"{rng.uniform(lo, hi):.2f}"


def generate_all(root: Path) -> dict[str, int]:
    """Generate every raw CSV under ``root/data/raw``. Returns row counts."""
    rng = random.Random(SEED)
    raw_dir = root / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, list[dict]] = {}

    # --- reference tables first (no dirty rows) ---
    ports = [{"port_id": f"PRT-{i+1:03d}", "port_name": p[0], "country": p[1], "region": p[2],
              "unlocode": p[3], "port_type": p[4]} for i, p in enumerate(PORTS[:64])]
    data["ports"] = ports
    port_ids = [p["port_id"] for p in ports]

    warehouses = [{"warehouse_id": f"WH-{i+1:02d}", "warehouse_name": f"Northgate Depot {n}",
                   "location": rng.choice(port_ids) and ports[i % len(ports)]["port_name"],
                   "port_id": ports[i % len(ports)]["port_id"],
                   "capacity_sqm": str(rng.randint(2000, 40000)),
                   "warehouse_type": rng.choice(["onshore depot", "quayside store", "bonded store"])}
                  for i, n in enumerate(["Singapore", "Rotterdam", "Houston", "Shanghai", "Dubai", "Felixstowe", "Busan", "Santos"])]
    data["warehouses"] = warehouses
    wh_ids = [w["warehouse_id"] for w in warehouses]

    # --- fleet ---
    prefixes = ["Northgate", "Atlantic", "Pacific", "Meridian", "Harbour", "Seafarer", "Oceanic", "Polar"]
    suffixes = ["Pioneer", "Voyager", "Endeavour", "Sentinel", "Mariner", "Navigator", "Explorer", "Guardian", "Trader", "Carrier", "Falcon", "Heron"]
    vessels = []
    for i in range(48):
        name = f"{prefixes[i % len(prefixes)]} {suffixes[(i * 3) % len(suffixes)]} {i // 12 + 1}" if i >= 24 else f"{prefixes[i % len(prefixes)]} {suffixes[i % len(suffixes)]}"
        vessels.append({"vessel_id": f"VES-{i+1:03d}", "vessel_name": name,
                        "vessel_type": rng.choice(VESSEL_TYPES), "imo_number": f"{rng.randint(1000000, 9999999)}",
                        "flag": rng.choice(FLAGS), "gross_tonnage": str(rng.randint(3000, 180000)),
                        "year_built": str(rng.randint(1998, 2024)),
                        "status": rng.choices(["active", "dry-dock", "laid-up", "decommissioned"], weights=[85, 7, 5, 3])[0],
                        "home_port_id": rng.choice(port_ids)})
    data["vessels"] = vessels
    vessel_ids = [v["vessel_id"] for v in vessels]
    {v["vessel_id"]: v["status"] for v in vessels}

    voyages = []
    for i in range(3200):
        dep = _d(rng, date(2023, 1, 1), date(2026, 11, 15))
        arr = dep + timedelta(days=rng.randint(2, 45))
        arr = min(arr, REF)
        dep_p, arr_p = rng.sample(port_ids, 2)
        voyages.append({"voyage_id": f"VOY-{i+1:05d}", "vessel_id": rng.choice(vessel_ids),
                        "departure_port_id": dep_p, "arrival_port_id": arr_p,
                        "departure_date": _iso(dep), "arrival_date": _iso(arr),
                        "cargo_type": rng.choice(CARGO), "cargo_tonnes": f"{rng.uniform(500, 120000):.1f}",
                        "voyage_status": rng.choices(["completed", "in-transit", "delayed", "cancelled"], weights=[80, 10, 7, 3])[0],
                        "fuel_consumed_tonnes": f"{rng.uniform(20, 900):.1f}"})
    data["voyages"] = voyages

    # --- crew ---
    crew = []
    for i in range(1800):
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        crew.append({"crew_id": f"CRW-{i+1:05d}", "first_name": fn, "last_name": ln,
                     "rank": rng.choice(RANKS), "nationality": rng.choice(NATIONALITIES),
                     "date_of_birth": _iso(_d(rng, date(1965, 1, 1), date(2004, 12, 31))),
                     "email": f"{fn.lower()}.{ln.lower()}{i}@example-seafarer.com",
                     "phone": f"+{rng.randint(10, 99)} {rng.randint(100, 999)} {rng.randint(100000, 999999)}",
                     "passport_number": f"{rng.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{rng.randint(1000000, 9999999)}",
                     "seafarer_id": f"SEA-{rng.randint(100000, 999999)}",
                     "employment_status": rng.choices(["active", "on leave", "off-hired"], weights=[80, 12, 8])[0]})
    data["crew_members"] = crew
    crew_ids = [c["crew_id"] for c in crew]
    crew_rank = {c["crew_id"]: c["rank"] for c in crew}

    assignments = []
    for i in range(4500):
        emb = _d(rng, date(2024, 1, 1), date(2026, 11, 1))
        dis = emb + timedelta(days=rng.randint(30, 240)) if rng.random() < 0.6 else None
        if dis and dis > REF:
            dis = None
        cid = rng.choice(crew_ids)
        assignments.append({"assignment_id": f"ASN-{i+1:05d}", "crew_id": cid, "vessel_id": rng.choice(vessel_ids),
                            "role": crew_rank[cid], "embark_date": _iso(emb), "disembark_date": _iso(dis),
                            "assignment_status": rng.choices(["active", "completed", "cancelled"], weights=[45, 50, 5])[0]})
    data["crew_assignments"] = assignments

    certs = []
    for i in range(3600):
        issue = _d(rng, date(2021, 1, 1), date(2026, 6, 1))
        expiry = issue + timedelta(days=rng.randint(365, 1825))
        status = "expired" if expiry < REF else "valid"
        certs.append({"certification_id": f"CER-{i+1:05d}", "crew_id": rng.choice(crew_ids),
                      "certification_type": rng.choice(CERT_TYPES),
                      "issuing_authority": rng.choice(["MCA", "USCG", "DMA", "AMSA", "Flag Administration", "Class Society"]),
                      "issue_date": _iso(issue), "expiry_date": _iso(expiry), "cert_status": status})
    data["certifications"] = certs

    # --- warehouse / inventory ---
    items = []
    for i in range(6000):
        cat = rng.choice(CATEGORIES)
        vid = rng.choice(vessel_ids) if rng.random() < 0.35 else ""
        items.append({"item_id": f"ITM-{i+1:05d}", "sku": f"SKU-{cat[:3].upper()}-{i+1:05d}",
                      "item_name": rng.choice(ITEM_NAMES[cat]), "category": cat,
                      "warehouse_id": rng.choice(wh_ids), "vessel_id": vid,
                      "unit": rng.choice(["each", "kg", "litre", "box", "metre"]),
                      "unit_cost": _money(rng, 2, 4500), "reorder_level": str(rng.randint(2, 50)),
                      "current_qty": str(rng.randint(0, 400))})
    data["inventory_items"] = items
    {it["item_id"]: it for it in items}

    movements = []
    for i in range(25000):
        it = rng.choice(items)
        movements.append({"movement_id": f"MOV-{i+1:05d}", "item_id": it["item_id"],
                          "warehouse_id": it["warehouse_id"], "vessel_id": it["vessel_id"],
                          "movement_type": rng.choices(["receipt", "issue", "transfer", "adjustment", "damage"], weights=[35, 40, 12, 8, 5])[0],
                          "quantity": str(rng.randint(1, 120)),
                          "movement_date": _iso(_d(rng, date(2024, 1, 1), REF)),
                          "reference": f"REF-{rng.randint(10000, 99999)}"})
    data["stock_movements"] = movements

    # --- procurement ---
    suppliers = []
    for i in range(140):
        suppliers.append({"supplier_id": f"SUP-{i+1:03d}", "supplier_name": f"{rng.choice(['Marine', 'Global', 'Pacific', 'Atlantic', 'Nordic', 'Harbour'])} {rng.choice(['Supply', 'Trading', 'Marine Services', 'Logistics', 'Engineering'])} {i+1}",
                          "country": rng.choice(["Singapore", "Netherlands", "China", "United States", "United Kingdom", "India", "Japan", "Germany", "UAE", "South Korea"]),
                          "region": rng.choice(["Asia-Pacific", "Europe", "Americas", "Middle East"]),
                          "category": rng.choice(SUPPLIER_CATS),
                          "contact_email": f"sales{i}@supplier{i}.example.com",
                          "rating": f"{rng.uniform(2.5, 5.0):.1f}",
                          "supplier_status": rng.choices(["active", "on hold", "blacklisted"], weights=[88, 9, 3])[0]})
    data["suppliers"] = suppliers
    sup_ids = [s["supplier_id"] for s in suppliers]

    pos = []
    for i in range(4800):
        od = _d(rng, date(2024, 1, 1), date(2026, 11, 10))
        pos.append({"po_id": f"PO-{i+1:05d}", "supplier_id": rng.choice(sup_ids),
                    "warehouse_id": rng.choice(wh_ids),
                    "vessel_id": rng.choice(vessel_ids) if rng.random() < 0.4 else "",
                    "order_date": _iso(od), "required_date": _iso(od + timedelta(days=rng.randint(3, 60))),
                    "total_amount": _money(rng, 100, 250000), "po_status": rng.choices(["ordered", "partially delivered", "delivered", "cancelled"], weights=[25, 20, 50, 5])[0],
                    "currency": rng.choice(["USD", "USD", "USD", "EUR", "SGD"])})
    data["purchase_orders"] = pos
    {p["po_id"]: p for p in pos}

    deliveries = []
    for i in range(3800):
        po = rng.choice(pos)
        dd = date.fromisoformat(po["order_date"]) + timedelta(days=rng.randint(1, 45))
        dd = min(dd, REF)
        deliveries.append({"delivery_id": f"DEL-{i+1:05d}", "po_id": po["po_id"], "delivery_date": _iso(dd),
                           "received_qty": str(rng.randint(1, 500)), "delivered_amount": _money(rng, 50, 200000),
                           "delivery_status": rng.choices(["received", "partial", "rejected"], weights=[80, 15, 5])[0],
                           "received_by_warehouse_id": po["warehouse_id"]})
    data["deliveries"] = deliveries

    # --- maintenance: assets (exactly one of vessel/warehouse) ---
    def _loc(rng_: random.Random) -> tuple[str, str]:
        if rng_.random() < 0.7:
            return rng_.choice(vessel_ids), ""
        return "", rng_.choice(wh_ids)

    assets = []
    for i in range(9500):
        vid, wid = _loc(rng)
        assets.append({"asset_id": f"AST-{i+1:05d}", "asset_name": f"{rng.choice(ASSET_TYPES).title()} unit {i+1}",
                       "asset_type": rng.choice(ASSET_TYPES), "vessel_id": vid, "warehouse_id": wid,
                       "serial_number": f"SN-{rng.randint(100000, 999999)}",
                       "install_date": _iso(_d(rng, date(2010, 1, 1), date(2025, 12, 31))),
                       "asset_status": rng.choices(["operational", "under repair", "out of service", "retired"], weights=[80, 10, 7, 3])[0],
                       "criticality": rng.choices(["low", "medium", "high", "critical"], weights=[30, 35, 25, 10])[0]})
    data["assets"] = assets

    wos = []
    for i in range(9000):
        a = rng.choice(assets)
        created = _d(rng, date(2024, 1, 1), date(2026, 11, 15))
        due = created + timedelta(days=rng.randint(1, 90))
        done = created + timedelta(days=rng.randint(1, 60)) if rng.random() < 0.55 else None
        if done and done > REF:
            done = None
        status = "completed" if done else rng.choices(["open", "in progress", "on hold", "overdue"], weights=[40, 35, 10, 15])[0]
        wos.append({"wo_id": f"WO-{i+1:05d}", "asset_id": a["asset_id"], "vessel_id": a["vessel_id"], "warehouse_id": a["warehouse_id"],
                    "wo_type": rng.choice(WO_TYPES), "priority": rng.choices(["low", "medium", "high", "urgent"], weights=[25, 40, 25, 10])[0],
                    "description": f"{rng.choice(WO_TYPES).title()} maintenance on {a['asset_type']}",
                    "created_date": _iso(created), "due_date": _iso(due), "completed_date": _iso(done),
                    "status": status, "estimated_cost": _money(rng, 100, 80000),
                    "actual_cost": _money(rng, 100, 90000) if done else "",
                    "estimated_hours": f"{rng.uniform(1, 120):.1f}",
                    "actual_hours": f"{rng.uniform(1, 130):.1f}" if done else "",
                    "assigned_crew_id": rng.choice(crew_ids) if rng.random() < 0.7 else ""})
    data["work_orders"] = wos

    inspections = []
    for i in range(4200):
        a = rng.choice(assets)
        inspections.append({"inspection_id": f"INS-{i+1:05d}", "asset_id": a["asset_id"],
                            "vessel_id": a["vessel_id"], "warehouse_id": a["warehouse_id"],
                            "inspection_type": rng.choice(["routine", "class survey", "safety", "port state", "pre-voyage"]),
                            "inspection_date": _iso(_d(rng, date(2024, 1, 1), REF)),
                            "inspector": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                            "result": rng.choices(["pass", "fail", "conditional"], weights=[80, 8, 12])[0],
                            "findings": rng.choice(["No findings", "Minor wear noted", "Seal replacement recommended", "Corrosion on housing", "Calibration due"])})
    data["inspections"] = inspections

    # --- compliance ---
    docs = []
    for i in range(7500):
        vid, wid = _loc(rng)
        issue = _d(rng, date(2021, 1, 1), date(2026, 1, 1))
        expiry = issue + timedelta(days=rng.randint(365, 1825))
        docs.append({"document_id": f"DOC-{i+1:05d}", "document_type": rng.choice(DOC_TYPES),
                     "vessel_id": vid, "warehouse_id": wid,
                     "title": f"{rng.choice(DOC_TYPES)} — {vid or wid}",
                     "issuer": rng.choice(["Class Society", "Flag Administration", "Port Authority", "Insurer", "Medical Centre"]),
                     "issue_date": _iso(issue), "expiry_date": _iso(expiry),
                     "doc_status": "expired" if expiry < REF else "valid",
                     "file_reference": f"s3://northgate-docs/{rng.randint(100000, 999999)}.pdf"})
    data["documents"] = docs
    doc_ids = [d["document_id"] for d in docs]

    audits = []
    for i in range(850):
        vid, wid = _loc(rng)
        audits.append({"audit_id": f"AUD-{i+1:04d}", "audit_type": rng.choice(AUDIT_TYPES),
                       "vessel_id": vid, "warehouse_id": wid,
                       "audit_date": _iso(_d(rng, date(2023, 1, 1), REF)),
                       "auditor": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                       "audit_status": rng.choices(["completed", "in progress", "scheduled"], weights=[75, 15, 10])[0],
                       "findings_count": str(rng.randint(0, 18)),
                       "audit_result": rng.choices(["conformant", "observation", "non-conformance"], weights=[60, 28, 12])[0]})
    data["audits"] = audits
    audit_ids = [a["audit_id"] for a in audits]

    conformance = []
    for i in range(1400):
        vid, wid = _loc(rng)
        use_audit = rng.random() < 0.55
        conformance.append({"report_id": f"REP-{i+1:04d}",
                            "audit_id": rng.choice(audit_ids) if use_audit else "",
                            "document_id": "" if use_audit else rng.choice(doc_ids),
                            "vessel_id": vid, "warehouse_id": wid,
                            "report_date": _iso(_d(rng, date(2024, 1, 1), REF)),
                            "conformance_status": rng.choices(["conformant", "observation", "non-conformance", "overdue"], weights=[55, 25, 12, 8])[0],
                            "description": rng.choice(["Annual ISM conformance review", "ISPS follow-up", "Document expiry review", "Port State Control follow-up", "Internal audit closure"])})
    data["conformance_reports"] = conformance

    incidents = []
    for i in range(950):
        vid, wid = _loc(rng)
        incidents.append({"incident_id": f"INC-{i+1:04d}", "vessel_id": vid, "warehouse_id": wid,
                          "incident_date": _iso(_d(rng, date(2023, 1, 1), REF)),
                          "incident_type": rng.choice(INCIDENT_TYPES),
                          "severity": rng.choices(["minor", "major", "critical"], weights=[70, 22, 8])[0],
                          "description": rng.choice(["Reported and logged for review", "Crew member treated on board", "Containment completed", "Equipment isolated pending repair"]),
                          "status": rng.choices(["open", "investigating", "closed"], weights=[20, 25, 55])[0],
                          "reported_by_crew_id": rng.choice(crew_ids) if rng.random() < 0.8 else ""})
    data["incidents"] = incidents

    bunkering = []
    for i in range(2600):
        bunkering.append({"bunkering_id": f"BUN-{i+1:04d}", "vessel_id": rng.choice(vessel_ids),
                          "port_id": rng.choice(port_ids), "supplier_id": rng.choice(sup_ids),
                          "bunkering_date": _iso(_d(rng, date(2024, 1, 1), REF)),
                          "fuel_type": rng.choice(["VLSFO", "MGO", "LNG", "HFO"]),
                          "quantity_tonnes": f"{rng.uniform(50, 2500):.1f}",
                          "cost_amount": _money(rng, 20000, 1200000), "currency": "USD"})
    data["fuel_bunkering"] = bunkering

    # --- dirty rows: ~2.5% per dataset, never ports / warehouses ---
    _inject_dirty(data, rng)

    counts = {}
    for name, rows in data.items():
        path = raw_dir / f"{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns_of(name))
            writer.writeheader()
            writer.writerows(rows)
        counts[name] = len(rows)
    return counts


def _inject_dirty(data: dict[str, list[dict]], rng: random.Random) -> None:
    """Overwrite ~2.5% of rows in each non-reference dataset with one defect each."""
    for name, rows in data.items():
        if DATASETS[name].get("dirty") is False or not rows:
            continue
        pk = DATASETS[name]["pk"]
        cols = SCHEMAS[name]
        n_dirty = max(1, int(len(rows) * 0.025))
        idxs = rng.sample(range(len(rows)), n_dirty)
        for j, idx in enumerate(idxs):
            row = rows[idx]
            kind = j % 7
            if kind == 0:  # duplicate PK: copy an earlier row's PK
                row[pk] = rows[rng.randrange(len(rows))][pk]
            elif kind == 1:  # null required field (non-PK)
                req = [c["name"] for c in cols if not c["nullable"] and c["name"] != pk]
                if req:
                    row[rng.choice(req)] = ""
            elif kind == 2 and any(c["name"] in ("email", "contact_email") for c in cols):
                field = "email" if "email" in row else "contact_email"
                row[field] = "not-an-email"
            elif kind == 3:  # future date
                date_cols = [c["name"] for c in cols if c["type"] == "DATE"]
                if date_cols:
                    row[rng.choice(date_cols)] = "2027-06-01"
            elif kind == 4:  # negative cost / qty / amount
                num_cols = [c["name"] for c in cols if c["type"] in ("DOUBLE", "BIGINT")
                            and any(k in c["name"] for k in ("cost", "qty", "amount", "tonnes", "quantity"))]
                if num_cols:
                    row[rng.choice(num_cols)] = "-5"
            elif kind == 5:  # invalid FK
                fk_cols = {"vessel_id": "VES-999", "port_id": "PRT-999", "crew_id": "CRW-99999",
                           "asset_id": "AST-99999", "supplier_id": "SUP-999", "warehouse_id": "WH-99",
                           "po_id": "PO-99999", "item_id": "ITM-99999", "audit_id": "AUD-9999",
                           "document_id": "DOC-99999"}
                cand = [c for c in fk_cols if c in row and row[c] != ""]
                if cand:
                    row[rng.choice(cand)] = fk_cols[rng.choice(cand)] if False else ""
                    # set exactly one FK invalid (re-pick deterministically)
                    target = rng.choice(cand)
                    row[target] = fk_cols[target]
            else:  # expired-then-renewed confusion / inconsistent dates
                if "issue_date" in row and "expiry_date" in row and row["issue_date"] and row["expiry_date"]:
                    row["expiry_date"] = row["issue_date"]  # expiry not after issue
                    if "cert_status" in row:
                        row["cert_status"] = "valid"
                elif "departure_date" in row and "arrival_date" in row and row["arrival_date"]:
                    row["arrival_date"] = "2020-01-01"  # arrival before departure
                elif "embark_date" in row and "disembark_date" in row and row["disembark_date"]:
                    row["disembark_date"] = "2020-01-01"
                else:
                    req = [c["name"] for c in cols if not c["nullable"] and c["name"] != pk]
                    if req:
                        row[rng.choice(req)] = ""
