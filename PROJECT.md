# Project: Huế POIs Parallel Enrichment

## Architecture
- **Data Flow**: Custom enrichment script extracts POIs from PostGIS -> Performs parallel lookup, local Vietnamese name synchronization, and coordinate checks -> Performs a synchronized double-ingestion into `travel.poi` and `travel.poi_catalog`.
- **Database Tables**:
  - `travel.poi` (Geography coordinates, integer hours, double pricing, 1536-dim embeddings, priority range 0.0-1.0)
  - `travel.poi_catalog` (Geometry coordinates, TIME opens_at/closes_at, integer ticket_price, priority 1-10, non-null description)
- **OSRM Snapping**: Connected to live container `routing_osrm_hue` on port 5000 to verify coordinates and snap land-based coordinates, excluding lagoon floating restaurants.
- **Frontend Validation**: TypeScript static check (`npm run typecheck` under `fleet-route-optimizer-cvrptw/webui/`) validates frontend-backend contracts.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Database & CSV Discovery | Auditing database schemas, CSV data, and OSRM snapping. | None | DONE |
| 2 | Enrichment & Sync Plan | Design mapping rules for local Vietnamese names, coordinate verification logic, and double-ingestion. | M1 | DONE |
| 3 | Worker Implementation | Implement the `enrich_and_ingest.py` script to fetch, enrich, check coordinates, and double-ingest POIs. | M2 | PLANNED |
| 4 | Review & Verification | Run reviews on ingestion script, verify snapping anomalies, and run TypeScript typecheck. | M3 | PLANNED |
| 5 | final Acceptance | Final audit by Forensic Auditor, verify database tables have correct records, and issue handoff. | M4 | PLANNED |

## Interface Contracts
### `travel.poi` ↔ `travel.poi_catalog`
- **ID Sync**: `travel.poi_catalog.poi_id` must match `str(travel.poi.uuid)` exactly to preserve database referential integrity.
- **Coordinates Sync**: `poi.coordinates` (Geography) and `poi_catalog.geom` (Geometry) must match spatial locations.
- **Hours Mapping**: `poi.open_time` & `poi.close_time` (int minutes from midnight) mapped to `poi_catalog.opens_at` & `poi_catalog.closes_at` (TIME 'HH:MM:SS').
- **Pricing Mapping**: `poi.entrance_fee` (double precision) mapped to `poi_catalog.ticket_price` (integer).
- **Priority Mapping**: `poi.priority_score` (double 0.0-1.0) mapped to `poi_catalog.priority` (integer 1-10).
- **Description Mapping**: `poi.description` (nullable) mapped to `poi_catalog.description` (non-null, fallback to empty string if needed).

## Code Layout
- `layer2_3_gateway/ingestion/` - Contains ingestion scripts.
- `layer2_3_gateway/app/models/poi.py` - Contains SQLAlchemy ORM models.
- `fleet-route-optimizer-cvrptw/webui/` - Contains React/TypeScript frontend and configuration files.
- `scratch/` - Contain inspection scripts.
