# Decisions (ADRs)

## ADR-1 — DuckDB, not Spark

The model is ~89k rows. Spark would add a cluster, JVM tuning and a
multi-minute startup for a dataset DuckDB scans in milliseconds. DuckDB
gives real SQL, Parquet and in-process execution with zero infrastructure.
Revisit if a single dataset exceeds ~10M rows or streaming is required.

## ADR-2 — YAML contracts, not code-only validation

Contracts live in `governance/contracts/*.yaml` so owners and stewards can
read and change them without touching Python. Silver loads the same
registry the contracts are generated from, so code and YAML cannot drift
silently — and the generated catalog proves it.

## ADR-3 — Quarantine, never silent drop

A row that fails a contract is stored in `data/quarantine/*.parquet` with
`_quarantine_reason`. Dropping it would hide a data-quality problem and
break reconciliation (Bronze in = Silver + quarantined, always).

## ADR-4 — Offline-sync model: last-write-wins, except safety

Operational records (work orders, stock movements) resolve conflicts by
last-write-wins — a vessel's latest state is usually right. Safety and
compliance records (documents, audits, conformance reports, incidents)
never do: a conflict is quarantined for steward review, because silently
overwriting a certificate or an incident report is a safety risk.

## ADR-5 — Synthetic data, stdlib random only, seed 42

No faker, no real personal data. Deterministic generation makes every run
reproducible and every test assertable on exact counts.

## ADR-6 — Gold is PII-free by construction

Gold queries never select a PII column. Masking/hashing exists for
Silver-level display, but Gold consumers cannot leak what Gold never had.

## ADR-7 — Generated catalog, not hand-written docs

`docs/catalog.md` is generated from YAML + real Parquet schemas. A
hand-written catalog drifts within a week; a generated one is wrong only
if the source is wrong, and then the tests catch it.
