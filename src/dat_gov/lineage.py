"""Lineage: dataset -> Bronze -> Silver -> Gold, from the real pipeline.

Governance concept demonstrated: lineage is derived from the registry
and the actual Gold queries, not hand-drawn — if a mart stops reading a
dataset, the lineage changes with it.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import DATASETS, GOLD_MARTS
from .transform_gold import QUERIES


def build_lineage(root: Path) -> dict:
    """Return (and write data/lineage.json) the lineage graph."""
    nodes = []
    edges = []
    for name, meta in DATASETS.items():
        nodes.append({"id": name, "kind": "dataset", "subdomain": meta["subdomain"]})
        edges.append({"from": f"raw:{name}", "to": f"bronze:{name}", "kind": "ingest"})
        edges.append({"from": f"bronze:{name}", "to": f"silver:{name}", "kind": "validate"})
    for mart, sql in QUERIES.items():
        nodes.append({"id": mart, "kind": "gold_mart"})
        for ds in DATASETS:
            if ds in sql:
                edges.append({"from": f"silver:{ds}", "to": mart, "kind": "aggregate"})
    lineage = {"domain": "Maritime Supply Chain & Fleet Operations", "nodes": nodes, "edges": edges,
               "gold_marts": GOLD_MARTS}
    out = root / "data" / "lineage.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lineage, indent=2), encoding="utf-8")
    return lineage
