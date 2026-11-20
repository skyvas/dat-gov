# Northgate Maritime — Data Governance Model

A complete, runnable data-governance model for a fictional maritime company:
**Northgate Maritime** — an onshore warehouse (always online) plus a fleet of
ships at sea (offline, sync on reconnect). One domain, six subdomains,
20 datasets, ~89,000 synthetic rows, medallion pipeline, YAML contracts,
and an offline-sync model with steward review for safety records.

> Note on counts: the brief enumerates 19 datasets by name but requires 20.
> The 20th is `fuel_bunkering` (fleet) — the natural missing fact linking
> vessel + port + supplier. The 19 named datasets keep their specified
> counts; the total is 88,960 raw rows (~95k as specified, approximately).

## Domain / subdomain map

| Subdomain | Datasets |
|---|---|
| fleet | vessels (48), voyages (3,200), ports (64, reference), fuel_bunkering (2,600) |
| crew | crew_members (1,800), crew_assignments (4,500), certifications (3,600) |
| warehouse | warehouses (8, reference), inventory_items (6,000), stock_movements (25,000) |
| procurement | suppliers (140), purchase_orders (4,800), deliveries (3,800) |
| maintenance | assets (9,500), work_orders (9,000), inspections (4,200) |
| compliance | documents (7,500), audits (850), conformance_reports (1,400), incidents (950) |

## Medallion

- **Bronze** — raw as received, immutable. Adds `_ingested_at`, `_source_file`,
  `_source_system` (`warehouse-erp` onshore, `vessel-<id>` at sea),
  `_captured_offline`, `_sync_status` (`synced`/`pending`/`conflict`),
  `_batch_id`, `_row_hash`. ~35% of vessel-originated rows are offline-captured.
- **Silver** — typed, deduped on PK, contract-validated, FK-checked against
  conformed dimensions. Failures are quarantined with `_quarantine_reason`,
  never silently dropped. Conflict-flagged safety/compliance rows go to
  steward review (`sync_conflict_steward_review`).
- **Gold** — 8 PII-free marts, reconciled to Silver: fleet availability,
  voyage performance, inventory health, maintenance backlog, compliance
  posture, crew certification, supplier performance, work-order cost.

## Governance pillars

- **Ownership** — `governance/owners.yaml` (domain owner: Chief Operating
  Officer; one owner + steward per subdomain).
- **Glossary** — `governance/glossary.yaml` (32 business terms).
- **Data products** — `governance/data_products.yaml` (5 products, Gold
  inputs, consumers, SLA/freshness).
- **Catalog & contracts** — `governance/catalog/*.yaml` and
  `governance/contracts/*.yaml`, one per dataset (20 each).
- **Policies** — `governance/policies/`: access roles (9 roles), PII
  (hash + mask), retention, quality (quarantine threshold 5%),
  offline sync (last-write-wins except safety/compliance).
- **Catalog generation** — `docs/catalog.md` + `data/lineage.json` are
  generated from the YAML + real Parquet schemas, so they cannot drift.

## Offline sync

Vessels capture data offline and sync on reconnect — see
`docs/OFFLINE_SYNC.md`. Last-write-wins for operational records; safety /
compliance conflicts are quarantined for steward review, never overwritten.

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m dat_gov.cli all        # generate -> bronze -> silver -> gold -> quality -> catalog
.venv/bin/python -m pytest -q              # tests
.venv/bin/ruff check src tests scripts     # lint
make run | make test | make lint | make catalog | make clean
```

Outputs: `data/raw/*.csv`, `data/bronze|silver|gold|quarantine/*.parquet`,
`data/quality_report.json`, `data/lineage.json`, `docs/catalog.md`,
`docs/lineage.md`. Samples: `data/samples/` (20-row CSVs).

## How to add a subdomain

1. Add the subdomain + owner/steward to `governance/owners.yaml` and
   `src/dat_gov/config.py` (`SUBDOMAINS`, `SCHEMAS`, `DATASETS`, `FOREIGN_KEYS`).
2. Add generation in `src/dat_gov/generate.py`, a catalog + contract YAML,
   and a Gold mart (or extend one) in `src/dat_gov/transform_gold.py`.
3. Add tests in `tests/` covering counts, contracts, FKs and Gold reconciliation.
4. Run `python -m dat_gov.cli all` and `pytest -q` — the quality gate must pass.

## Docs

- `docs/ARCHITECTURE.md`, `docs/GOVERNANCE.md`, `docs/DECISIONS.md`,
  `docs/OFFLINE_SYNC.md`, `docs/DATA_PRODUCTS.md`, `docs/DATA_DICTIONARY.md`
  (pointer to the generated catalog).
