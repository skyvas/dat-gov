# Data products

Defined in `governance/data_products.yaml`. Five products, each with an
owner, Gold inputs, consumers and an SLA (daily refresh by 06:00 UTC,
freshness under 24h).

| Product | Owner | Gold inputs | Consumers |
|---|---|---|---|
| Fleet Availability | Fleet Director | gold_fleet_availability | Fleet Manager, Vessel Master |
| Inventory Health | Warehouse Manager | gold_inventory_health | Warehouse Manager, Procurement |
| Maintenance Backlog | Technical Manager | gold_maintenance_backlog, gold_work_order_cost | Chief Engineer, Fleet Manager |
| Compliance Posture | Compliance Officer | gold_compliance_posture, gold_crew_certification | Compliance Officer, Auditor, Fleet Manager |
| Voyage Performance | Fleet Director | gold_voyage_performance, gold_fleet_availability | Fleet Manager, Analyst |

Each product is PII-free (its Gold inputs are) and reconciles to Silver:
e.g. Voyage Performance voyage counts sum to the Silver `voyages` count.
