# Architecture

## Stack

Python 3.12, DuckDB (embedded analytics), PyYAML. No Spark, no Airflow,
no pandas — the whole model runs in one process in under a minute
(see `docs/DECISIONS.md` for why).

## Layout

```
src/dat_gov/
  config.py            registry: datasets, schemas, PKs, FKs, source systems
  generate.py          deterministic synthetic generation (seed 42)
  ingest.py            Bronze: raw CSV -> Parquet + audit columns
  transform_silver.py  Silver: typing, dedupe, contract + FK validation, quarantine
  transform_gold.py    Gold: 8 PII-free aggregate marts
  quality.py           quality report + 5% quarantine gate
  masking.py           SHA-256 hashing + masking helpers for PII
  lineage.py           lineage graph from registry + real Gold queries
  catalog.py           generated docs/catalog.md + docs/lineage.md
  cli.py               generate | bronze | silver | gold | quality | catalog | all | check
data/
  raw/ samples/ bronze/ silver/ gold/ quarantine/ quality_report.json lineage.json
governance/  owners, glossary, data products, catalog, contracts, policies
tests/       pytest, session fixture runs the full pipeline once in a temp dir
```

## Data flow

```
generate (seed 42, stdlib random)
  -> data/raw/*.csv            ~88,960 rows, ~2.5% dirty per dataset (refs clean)
  -> Bronze (ingest)           + _ingested_at/_source_system/_captured_offline/_sync_status/_row_hash
  -> Silver (validate)         deduped, typed, FK-checked; failures -> data/quarantine/*.parquet
  -> Gold (aggregate)          8 marts, PII-free, reconciled to Silver
  -> Quality gate              quarantine rate <= 5% per dataset and overall
  -> Catalog / lineage         generated from YAML + real Parquet schemas
```

## Determinism

Seed 42 everywhere; the same run twice produces the same raw rows, the
same Bronze hashes and the same Silver/Gold counts. Tests assert this.
