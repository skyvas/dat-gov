"""Governance: every dataset has a catalog entry, a contract and an owner;
PII is classified; every Gold table is traceable in lineage."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from dat_gov.config import CATALOG_DIR, CONTRACTS_DIR, DATA_DIR, DATASETS, GOVERNANCE_DIR
from dat_gov.lineage import GOLD_SOURCES, build_lineage


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_every_dataset_has_catalog_contract_and_owner():
    owners = _yaml(GOVERNANCE_DIR / "owners.yaml")
    owned = {d for sub in owners["subdomains"].values() for d in sub["datasets"]}
    for name in DATASETS:
        assert (CATALOG_DIR / f"{name}.yaml").exists(), name
        assert (CONTRACTS_DIR / f"{name}.yaml").exists(), name
        assert name in owned, name
        contract = _yaml(CONTRACTS_DIR / f"{name}.yaml")
        assert contract["primary_key"]
        assert contract["columns"]


def test_pii_fields_are_classified():
    for name in DATASETS:
        contract = _yaml(CONTRACTS_DIR / f"{name}.yaml")
        catalog = _yaml(CATALOG_DIR / f"{name}.yaml")
        pii_in_contract = {c["name"] for c in contract["columns"] if "pii" in c}
        assert pii_in_contract == set(catalog.get("pii_fields") or []), name
        if pii_in_contract:
            assert catalog["classification"] in ("Internal", "Confidential", "Restricted"), name


def test_every_gold_table_is_traceable_in_lineage():
    graph = build_lineage()
    edges = {(e["from"], e["to"]) for e in graph["edges"]}
    for gold, sources in GOLD_SOURCES.items():
        assert sources, gold
        for src in sources:
            assert (f"silver.{src}", f"gold.{gold}") in edges, (src, gold)
    assert (DATA_DIR / "lineage.json").exists()
    stored = json.loads((DATA_DIR / "lineage.json").read_text(encoding="utf-8"))
    assert len(stored["edges"]) == len(graph["edges"])


def test_access_roles_cover_all_datasets():
    roles = _yaml(GOVERNANCE_DIR / "policies" / "access_roles.yaml")["roles"]
    assert set(roles) >= {"Admin", "Registrar", "Faculty", "Finance", "Analyst", "Auditor", "Viewer"}
    assert set(roles["Admin"]["datasets"]) >= set(DATASETS)
