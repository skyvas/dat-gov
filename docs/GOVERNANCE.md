# Governance — each pillar, with a concrete example

Governance here is not a policy document stapled to a pipeline. Each
pillar is a file the pipeline reads, a check it runs, or a test that
fails if the pillar is missing.

## 1. Ownership

`governance/owners.yaml` names a domain owner (Chief Data Officer,
Provost Office) and, per subdomain, an owner and a steward. Example:
`students` is owned by the Registrar — not by "the data team". If a
student record is wrong, there is one named office to ask.
`tests/test_governance.py` fails if any dataset is missing from the
owners file.

## 2. Data contracts

`governance/contracts/students.yaml` (and one file per dataset) states
the schema, primary key, nullability, PII tags, and checks: email
format, date of birth not in the future, term in the allowed list,
`applicant_id` must exist in `applicants`. `transform_silver.py`
enforces the contract; `quality.py` re-checks the written Silver
files against the same contract. A contract change is a reviewable
YAML diff, not a code change buried in a transform.

## 3. Data quality as a gate

`quality.py` checks, per dataset: Bronze = Silver + Quarantine,
primary key unique, not-null columns actually non-null, quarantine
rate ≤ 5%. It also reconciles Gold to Silver (Gold enrolments =
Silver enrolments; Gold billed = sum of Silver charges; funnel
applied ≥ admitted ≥ enrolled). The report lands in
`data/quality_report.json`, and `cli check` exits 1 when it fails,
so CI blocks a bad run. On the reference run every check passes
with 1,056 quarantined rows (2.4% of raw).

## 4. Quarantine, not silent drops

A row that breaks its contract goes to
`data/quarantine/<dataset>.parquet` with `_quarantine_reason`, e.g.
`duplicate_pk:applicant_id=APP-000123; format:email:email`.
Concrete example: 30 raw applicants have `email = "not-an-email"`,
20 have a future date of birth, 40 are exact duplicates. All 120
are quarantined, counted, and inspectable — the pipeline never
decides on its own that a row "doesn't matter". Fix the source,
re-run, and the row promotes.

## 5. Catalog

`governance/catalog/*.yaml` is the human-readable entry per dataset:
description, owner, classification, PII fields, retention, source
system, upstream/downstream. `catalog.py` renders it into
`docs/catalog.md`, merging in the actual Silver Parquet schema, so
the dictionary cannot drift from the data. If a column exists in
Silver but not in the contract, the catalog build is the place you
notice — the contract is the schema of record.

## 6. Lineage

`src/dat_gov/lineage.py` declares the graph: every Silver dataset
has exactly one Bronze parent; every Gold mart lists its Silver
sources (`GOLD_SOURCES`). It is emitted as `data/lineage.json` and
as a Mermaid diagram in `docs/lineage.md`. Concrete use: change
`students`, and the graph tells you `gold_enrollment` and
`gold_student_retention` need re-running. `test_governance.py`
asserts every Gold table is traceable.

## 7. PII and masking

`governance/policies/pii_policy.yaml` classifies fields (Public /
Internal / Confidential / Restricted) and states the masking rules:
email keeps only its domain, phone keeps only the last 4 digits,
`gov_id` is only ever a SHA-256 hash outside Silver. Silver keeps
PII because operations need it; Gold drops it entirely — no Gold
query selects a name, email, phone, gov_id or date of birth.
`tests/test_pii.py` asserts that no Gold column and no Gold value
contains a raw identifier, and that hashing is deterministic.

## 8. Access control

`governance/policies/access_roles.yaml` defines 7 roles. Examples:
Faculty sees enrolments and sections but never finance or gov IDs;
Finance sees billing but only masked student identity; Analyst and
Viewer see Gold only. This repo enforces the strongest version of
the rule structurally — Gold simply has no PII to leak — and
documents the role matrix for the day a real access layer is added.

## 9. Retention

`governance/policies/retention_policy.yaml`: 7 years by default, 10
for departments/courses (accreditation), 90 days for quarantine
rows, and a rule that deleting Silver must delete its Bronze source
on the same clock. Gold aggregates may outlive Silver because they
contain no PII.

## Checklist: adding a new subdomain

1. Add the subdomain + owner to `governance/owners.yaml`.
2. Add the dataset to `config.DATASETS` (FK targets first).
3. Write `governance/contracts/<dataset>.yaml` and
   `governance/catalog/<dataset>.yaml`.
4. Generate its raw CSV in `generate.py` (with dirty rows, so the
   quality story stays honest).
5. Add its Gold sources to `lineage.GOLD_SOURCES` if a mart uses it.
6. Add the role matrix entry in `access_roles.yaml`.
7. Run `python -m dat_gov.cli all && python -m pytest -q` — the
   governance tests will tell you what you missed.
