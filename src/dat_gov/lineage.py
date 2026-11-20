"""Lineage: the explicit Bronze -> Silver -> Gold graph.

Governance idea demonstrated here: lineage is not inferred from logs
after the fact, it is declared in code alongside the transforms that
create it. Every Gold table can be traced back to the Silver datasets
it was built from, and every Silver dataset to its Bronze source and
its raw file. That is what lets an auditor answer "where did this
number come from?" and lets an owner assess blast radius ("if I change
`students`, what breaks?").
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import DATASETS, GOLD_TABLES, GOVERNANCE_DIR

# Gold table -> Silver datasets it reads. Kept in sync with transform_gold.py.
GOLD_SOURCES: dict[str, list[str]] = {
    "gold_admissions_funnel": ["applications"],
    "gold_enrollment": ["enrollments", "students", "sections", "courses"],
    "gold_student_retention": ["students"],
    "gold_finance_summary": ["tuition_charges", "payments", "financial_aid"],
    "gold_faculty_teaching_load": ["sections", "courses", "faculty", "enrollments"],
}


def build_lineage() -> dict:
    """Return the lineage graph as plain data (nodes + edges)."""
    nodes: list[dict] = []
    edges: list[dict] = []
    for name, subdomain in DATASETS.items():
        for layer in ("bronze", "silver"):
            nodes.append(
                {
                    "id": f"{layer}.{name}",
                    "layer": layer,
                    "dataset": name,
                    "subdomain": subdomain,
                }
            )
        edges.append({"from": f"bronze.{name}", "to": f"silver.{name}", "kind": "clean+validate"})
    for gold in GOLD_TABLES:
        nodes.append({"id": f"gold.{gold}", "layer": "gold", "dataset": gold, "subdomain": "cross-domain"})
        for src in GOLD_SOURCES[gold]:
            edges.append({"from": f"silver.{src}", "to": f"gold.{gold}", "kind": "aggregate"})
    return {"university": "Northbridge University", "nodes": nodes, "edges": edges}


def to_mermaid(graph: dict) -> str:
    """Render the lineage graph as a Mermaid flowchart."""
    lines = ["flowchart LR"]
    for edge in graph["edges"]:
        src = edge["from"].replace(".", "_")
        dst = edge["to"].replace(".", "_")
        lines.append(f"    {src} --> {dst}")
    lines.append("")
    lines.append("    %% Bronze = raw as received, Silver = cleaned + validated,")
    lines.append("    %% Gold = business marts (PII masked).")
    return "\n".join(lines)


def write_lineage(out_json: Path, out_md: Path | None = None) -> dict:
    """Write data/lineage.json and (optionally) docs/lineage.md with Mermaid."""
    graph = build_lineage()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    if out_md is not None:
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(
            "# Lineage\n\n"
            "Generated from `src/dat_gov/lineage.py` — do not edit by hand.\n\n"
            "```mermaid\n"
            + to_mermaid(graph)
            + "\n```\n\n"
            "## How to read it\n\n"
            "Every Silver dataset has exactly one Bronze parent (its raw file). "
            "Every Gold mart lists its Silver sources in "
            "`GOLD_SOURCES`; change a Silver dataset and this graph tells you "
            "which Gold marts need re-running.\n",
            encoding="utf-8",
        )
    return graph


def gold_sources(gold_table: str) -> list[str]:
    """Silver datasets a Gold table depends on (empty list if unknown)."""
    return list(GOLD_SOURCES.get(gold_table, []))


def upstream_of(dataset: str) -> list[str]:
    """Bronze/Silver ancestors of a dataset or Gold table."""
    graph = build_lineage()
    out: list[str] = []
    node = f"silver.{dataset}" if dataset in DATASETS else f"gold.{dataset}"
    seen = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        for edge in graph["edges"]:
            if edge["to"] == cur and edge["from"] not in seen:
                seen.add(edge["from"])
                out.append(edge["from"])
                stack.append(edge["from"])
    return sorted(out)


def governance_dir() -> Path:
    """Governance root (kept for callers that build paths from lineage)."""
    return GOVERNANCE_DIR
