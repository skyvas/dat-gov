# Governance

## Ownership

Domain owner: Chief Operating Officer. Each subdomain has an owner and a
steward (`governance/owners.yaml`). Example: the Fleet Director owns
`vessels`/`voyages`; a dispute over a vessel's status goes to them, not
to whoever happens to hold the file.

## Glossary

`governance/glossary.yaml` defines 32 terms (vessel, voyage, IMO number,
ISM, ISPS, dry-dock, Port State Control, seafarer…). Example: "dry-dock"
means a vessel out of service in a dock for hull work — so a dry-docked
vessel counts as *unavailable* in `gold_fleet_availability`, not as idle.

## Catalog & contracts

One catalog YAML and one contract YAML per dataset (20 each). A contract
names the schema (column, type, nullable, PII), PK, not-null columns and
FKs — and Silver enforces it. Example: `documents` requires exactly one
of `vessel_id`/`warehouse_id`; a document claiming both (or neither) is
quarantined, not stored.

## Access & PII

Nine roles in `governance/policies/access_roles.yaml`, each with a dataset
list and masked columns. Example: an Analyst may read voyage and work-order
data but sees crew email/phone/passport/seafarer ID only masked; only the
Compliance Officer and Crewing Manager see clear PII. Gold contains no raw
PII at all — masking is SHA-256 hashing (deterministic) plus display masks.

## Retention

`governance/policies/retention_policy.yaml`: incidents 10 years, crew and
audits 7 years, documents 5 years after expiry, default 5 years. Bronze is
immutable while retained; deletion applies to all layers together.

## Quality

`governance/policies/quality_policy.yaml`: completeness 98%, validity 97%,
uniqueness 100%, consistency 97%, timeliness 95%; the pipeline fails if
any dataset's quarantine rate exceeds 5%. Quality is computed from the
real Bronze/Silver counts in `data/quality_report.json`.

## Offline sync

See `docs/OFFLINE_SYNC.md`. Example: a work order raised offline on
VES-012 syncs as `pending`, then `synced`; a conflicting Safety Management
Certificate does not overwrite — it is quarantined for steward review.
