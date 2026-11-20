# Offline sync

## The problem

Ships at sea have no reliable connectivity. Crew still raise work orders,
log inspections, record incidents and update documents offline. Onshore,
the warehouse ERP is always online. Both sides must converge on reconnect
without losing work or silently overwriting safety records.

## How it works

1. **Capture** — vessel-originated rows (`voyages`, `work_orders`,
   `inspections`, `documents`, `incidents`, plus vessel-linked rows of
   mixed datasets) are captured on board with `_captured_offline=true`
   (~35% of vessel-originated rows) and `_source_system=vessel-<id>`.
   Onshore rows are `warehouse-erp` with `_captured_offline=false`.
2. **Sync** — on reconnect a row's `_sync_status` is `synced`, `pending`
   (awaiting retry — never dropped) or `conflict` (both sides changed it).
3. **Resolution** — operational records resolve last-write-wins.
   Safety/compliance records (`documents`, `audits`,
   `conformance_reports`, `incidents`) do **not**: a conflict-flagged row
   is quarantined in Silver with `_quarantine_reason =
   sync_conflict_steward_review` and waits for a Compliance steward.
   It is never silently overwritten, and the quarantine record keeps the
   vessel's version for review.
4. **Audit** — Bronze preserves `_captured_offline`, `_sync_status` and
   `_source_system` forever, so any Silver row can be traced to the
   vessel and the sync state it arrived in.

## Example

A Chief Engineer updates a Safety Management Certificate offline on
VES-012 while the Compliance Officer updates the same certificate
onshore. On reconnect the row arrives with `_sync_status=conflict`.
Silver quarantines it for steward review; the onshore version stays
live until a human decides. A conflicting work order for the same
vessel, by contrast, resolves last-write-wins and syncs.
