"""Governance completeness tests (run against the real project root)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from dat_gov.config import DATASETS, GOLD_MARTS, SCHEMAS, SUBDOMAINS


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_every_dataset_has_catalog_contract_and_owner(project_root):
    owners = _yaml(project_root / "governance" / "owners.yaml")
    assert owners["domain_owner"]["name"] == "Chief Operating Officer"
    assert set(owners["subdomains"]) == set(SUBDOMAINS)
    for name, meta in DATASETS.items():
        assert (project_root / "governance" / "catalog" / f"{name}.yaml").exists(), name
        assert (project_root / "governance" / "contracts" / f"{name}.yaml").exists(), name
        cat = _yaml(project_root / "governance" / "catalog" / f"{name}.yaml")
        assert cat["owner"] == SUBDOMAINS[meta["subdomain"]]["owner"]
        assert cat["subdomain"] == meta["subdomain"]
        assert cat["description"] and cat["retention"] and cat["classification"]


def test_contracts_match_config_schemas(project_root):
    for name, cols in SCHEMAS.items():
        contract = _yaml(project_root / "governance" / "contracts" / f"{name}.yaml")
        assert [s["column"] for s in contract["schema"]] == [c["name"] for c in cols], name
        assert contract["primary_key"]


def test_glossary_has_30_plus_terms(project_root):
    glossary = _yaml(project_root / "governance" / "glossary.yaml")
    terms = glossary["terms"]
    assert len(terms) >= 30
    assert all(t["definition"] and t["subdomain"] for t in terms)
    names = {t["term"] for t in terms}
    assert {"vessel", "voyage", "IMO number", "ISM", "ISPS", "dry-dock", "Port State Control", "seafarer"} <= names


def test_data_products_reference_real_gold_marts(project_root):
    products = _yaml(project_root / "governance" / "data_products.yaml")["data_products"]
    assert len(products) == 5
    for p in products:
        assert p["owner"] and p["consumers"] and p["sla"]
        for mart in p["gold_inputs"]:
            assert mart in GOLD_MARTS, mart


def test_access_roles_nine_roles(project_root):
    roles = _yaml(project_root / "governance" / "policies" / "access_roles.yaml")["roles"]
    assert len(roles) == 9
    names = {r["role"] for r in roles}
    assert names == {"Fleet Manager", "Vessel Master", "Chief Engineer", "Warehouse Manager", "Procurement",
                     "Compliance Officer", "Auditor", "Analyst", "Viewer"}
    for r in roles:
        assert r["datasets"] and "masked_columns" in r


def test_policies_exist(project_root):
    for f in ("pii_policy.yaml", "retention_policy.yaml", "quality_policy.yaml", "offline_sync_policy.yaml"):
        assert (project_root / "governance" / "policies" / f).exists()
    quality = _yaml(project_root / "governance" / "policies" / "quality_policy.yaml")
    assert quality["quarantine_threshold_pct"] == 5.0


def test_lineage_json_covers_all_datasets(pipeline_root):
    lineage = json.loads((pipeline_root / "data" / "lineage.json").read_text(encoding="utf-8"))
    node_ids = {n["id"] for n in lineage["nodes"]}
    assert set(DATASETS) <= node_ids
    assert set(GOLD_MARTS) <= node_ids
    assert lineage["edges"]


def test_catalog_md_generated(pipeline_root):
    text = (pipeline_root / "docs" / "catalog.md").read_text(encoding="utf-8")
    for name in DATASETS:
        assert name in text
