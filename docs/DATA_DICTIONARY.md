# Data dictionary

The authoritative dictionary is the generated catalog:

- **`docs/catalog.md`** — generated from `governance/catalog/*.yaml`,
  `governance/contracts/*.yaml` and the real Silver Parquet schemas.
  Regenerate with `python -m dat_gov.cli catalog`.
- **`governance/glossary.yaml`** — 32 business terms with definitions
  and owning subdomains.
- **`governance/contracts/*.yaml`** — per-dataset schema, PK, not-null
  columns, FKs and PII flags (the contract Silver enforces).
- **`data/lineage.json`** / **`docs/lineage.md`** — raw -> Bronze ->
  Silver -> Gold lineage.
