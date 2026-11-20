"""Shared configuration: paths, terms, dataset registry, constants.

Governance idea demonstrated here: a single registry is the source of
truth for which datasets exist, which subdomain owns them, and in what
order they may be processed (dependencies first, so referential checks
in Silver can trust the datasets they point at).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
QUARANTINE_DIR = DATA_DIR / "quarantine"
SAMPLES_DIR = DATA_DIR / "samples"
GOVERNANCE_DIR = ROOT / "governance"
CATALOG_DIR = GOVERNANCE_DIR / "catalog"
CONTRACTS_DIR = GOVERNANCE_DIR / "contracts"
POLICIES_DIR = GOVERNANCE_DIR / "policies"
DOCS_DIR = ROOT / "docs"

SEED = 42
UNIVERSITY = "Northbridge University"
TERMS = ["2024-Fall", "2025-Spring", "2025-Fall", "2026-Spring"]

# Dataset registry: name -> subdomain, in dependency order for Silver.
# A dataset may only reference (foreign key) datasets earlier in this list.
DATASETS: dict[str, str] = {
    "departments": "academics",
    "courses": "academics",
    "faculty": "academics",
    "sections": "academics",
    "applicants": "admissions",
    "applications": "admissions",
    "students": "registrar",
    "enrollments": "registrar",
    "tuition_charges": "finance",
    "payments": "finance",
    "financial_aid": "finance",
}

SUBDOMAINS: dict[str, list[str]] = {
    "admissions": ["applicants", "applications"],
    "registrar": ["students", "enrollments"],
    "academics": ["departments", "courses", "faculty", "sections"],
    "finance": ["tuition_charges", "payments", "financial_aid"],
}

GOLD_TABLES = [
    "gold_admissions_funnel",
    "gold_enrollment",
    "gold_student_retention",
    "gold_finance_summary",
    "gold_faculty_teaching_load",
]

# Quality thresholds (see governance/policies and quality.py).
MAX_QUARANTINE_RATE = 0.05  # fail the run if >5% of a dataset is quarantined


def ensure_dirs() -> None:
    """Create every data output directory (idempotent)."""
    for d in (RAW_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR, QUARANTINE_DIR, SAMPLES_DIR):
        d.mkdir(parents=True, exist_ok=True)
