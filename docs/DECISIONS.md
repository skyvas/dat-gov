# Decisions (ADRs)

## ADR-001: DuckDB, not Spark

**Context.** The goal is to learn governance — contracts, quality,
lineage, PII — not to operate a cluster.
**Decision.** DuckDB (in-process) + Parquet for storage and SQL.
**Consequences.** The whole pipeline runs in ~8 seconds on a laptop
with no services. The concepts transfer directly: the same Bronze /
Silver / Gold SQL and the same contract checks would run on Spark or
Snowflake with minimal changes. What we give up is distributed scale
and a metastore — neither matters at 40k rows, and both would hide
the governance ideas behind infrastructure.

## ADR-002: YAML contracts, not code-only validation

**Context.** Rules written only in Python are invisible to the
people who own the data (Registrar, Bursar) and cannot be reviewed
without reading transforms.
**Decision.** One YAML contract per Silver dataset: schema, PK,
nullability, PII tags, checks. The transform, the quality gate and
the catalog all read the same file.
**Consequences.** A rule change is a small, reviewable YAML diff.
The risk — YAML and code drifting — is contained by tests that load
the contracts and assert on the data they produce.

## ADR-003: Synthetic data, seed 42, stdlib random only

**Context.** Real university data cannot be published; a model
project needs data that is realistic, deep, and safe to commit.
**Decision.** Deterministic synthetic generation (seed 42, stdlib
`random` only, no Faker). All people are fictional; emails are
`example.edu`, phones are `+1-555-…`, gov IDs are `NB-100000`
style. Dirty rows (~2–3%) are injected deliberately.
**Consequences.** Re-running reproduces byte-identical raw CSVs, so
tests can assert exact counts and CI is stable. Distributions are
chosen to be plausible (GPA 2.0–4.0, domestic vs international
tuition, admit/yield funnel) rather than statistically exact.

## ADR-004: Parquet as the storage format

**Context.** CSV is human-readable but typeless; a database would
need a server.
**Decision.** Parquet for Bronze, Silver, Gold and quarantine, with
CSV only at the raw boundary (where source systems actually live).
**Consequences.** Types survive the pipeline, files are small, and
DuckDB reads them natively. Raw CSVs stay gitignored; 20-row samples
are committed so the shape is visible without running anything.

## ADR-005: Quarantine, never silent drops

**Context.** The easiest "quality" implementation is to filter bad
rows in a transform and move on. That hides data loss.
**Decision.** Every row that fails its contract is written to
`data/quarantine/<dataset>.parquet` with `_quarantine_reason`, and
Bronze = Silver + Quarantine is a checked invariant.
**Consequences.** Data loss is always visible and countable. The
cost is a little more code in Silver and one more directory to
explain — worth it, since this is the behaviour the whole project
is trying to teach.

## ADR-006: Gold carries no PII, by construction

**Context.** Masking at query time is easy to forget on the one
report that matters.
**Decision.** Gold marts are aggregates that never select a PII
column. Masking helpers exist (`masking.py`) for the day a Gold
table needs a tokenised identifier, but no current mart needs one.
**Consequences.** The PII test is simple and strong: no Gold column
is named like an identifier, and no Gold value equals a Silver
identifier. The trade-off is that Gold cannot answer
person-level questions — by design; those belong in Silver, behind
the access roles.
