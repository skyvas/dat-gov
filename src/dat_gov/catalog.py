"""Catalog + lineage docs generated from YAML governance + real schemas.

Governance concept demonstrated: the published catalog is generated,
not hand-typed, from governance/catalog/*.yaml, governance/contracts/*.yaml
and the actual Silver Parquet schemas — so it cannot drift from reality.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import yaml

from .config import DATASETS, GOLD_MARTS
from .lineage import build_lineage


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def build_catalog(root: Path) -> Path:
    """Write docs/catalog.md, docs/lineage.md and data/lineage.json."""
    lineage = build_lineage(root)
    (root / "docs").mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    lines = ["# Northgate Maritime — Data Catalog", "",
             "Generated from `governance/catalog/*.yaml`, `governance/contracts/*.yaml` and the real Silver Parquet schemas.",
             "Do not edit by hand — regenerate with `python -m dat_gov.cli catalog`.", "",
             "## Datasets", ""]
    try:
        for name, meta in DATASETS.items():
            cat = _load_yaml(root / "governance" / "catalog" / f"{name}.yaml")
            contract = _load_yaml(root / "governance" / "contracts" / f"{name}.yaml")
            silver = root / "data" / "silver" / f"{name}.parquet"
            schema_txt = ""
            if silver.exists():
                rel = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{silver}')")
                schema_txt = ", ".join(f"{r[0]}:{r[1]}" for r in rel.fetchall())
            lines += [f"### {name}", "",
                      f"- Subdomain: {meta['subdomain']} | Owner: {cat.get('owner', '')} | Classification: {cat.get('classification', '')}",
                      f"- Description: {cat.get('description', '')}",
                      f"- PII fields: {', '.join(cat.get('pii_fields', [])) or 'none'} | Retention: {cat.get('retention', '')}",
                      f"- Source system: {cat.get('source_system', '')} | Quality rules: {', '.join(cat.get('quality_rules', []))}",
                      f"- Contract PK: {contract.get('primary_key', '')}",
                      f"- Silver schema: {schema_txt}", ""]
        lines += ["## Gold marts", ""] + [f"- {m}" for m in GOLD_MARTS] + [""]
    finally:
        con.close()
    out = root / "docs" / "catalog.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    md = ["# Lineage", "", "Raw -> Bronze -> Silver -> Gold. Full graph in `data/lineage.json`.", ""]
    for e in lineage["edges"]:
        md.append(f"- `{e['from']}` -> `{e['to']}` ({e['kind']})")
    (root / "docs" / "lineage.md").write_text("\n".join(md), encoding="utf-8")
    print(f"catalog: wrote {out} ({len(DATASETS)} datasets, {len(GOLD_MARTS)} gold marts)")
    return out
