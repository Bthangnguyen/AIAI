# System Change Summary - 2026-05-27

## Context

This document summarizes the backend, solver, conversation, and deployment-related changes made while debugging the AI travel optimizer MVP.

Primary goals:

- Understand travel intent from flexible user input.
- Generate realistic itineraries without time overlap.
- Respect user time windows, food/culture/cafe intent, budget, and locked POIs.
- Make generated schedules feel usable for real travelers, not just technically feasible.

## Major Fixes

### 1. Timeline Overlap And Travel Time

Fixed scheduler behavior that previously allowed overlapping stops.

Changes:

- Added `travel_time_to_next_min` to itinerary stop model.
- Solver post-processing now computes:
  - `arrival_time_min`
  - `departure_time_min`
  - `visit_duration_min`
  - `travel_time_from_prev_min`
  - `travel_time_to_next_min`
- Timeline is re-sequenced using previous departure plus travel time, so next stop cannot start before prior stop finishes.

Files:

- `fleet-route-optimizer-cvrptw/src/models/domain.py`
- `fleet-route-optimizer-cvrptw/src/services/travel_solver.py`
- `fleet-route-optimizer-cvrptw/webui/src/lib/api.ts`

### 2. Realistic Travel Time Clamp

OSRM driving durations were too optimistic for tourist schedules. Example: around 10 km could appear as 7 minutes.

Added a sanity floor in `DistanceCacheService`:

- Taxi/motorbike: about `22 km/h`
- Bus: about `15 km/h`
- Walking: about `5 km/h`
- Minimum transfer time for non-zero hops

Result from smoke test:

```txt
haversine_km = 9.61
matrix_dist_km = 15.22
duration_min = 41.5
implied_kmh = 22.0
```

File:

- `fleet-route-optimizer-cvrptw/src/services/distance_cache.py`

### 3. Meal, Rest, And Human Day Rhythm

Added post-solve itinerary rhythm normalization.

Rules:

- Full-day schedules should not be compressed into the earliest possible hours.
- Long days need visible meal/rest breaks.
- Lunch and dinner are inserted when missing.
- Rest breaks are inserted after long continuous activity.
- Inserted virtual stops are re-sequenced to avoid overlap.

Files:

- `fleet-route-optimizer-cvrptw/src/services/rest_inserter.py`
- `fleet-route-optimizer-cvrptw/src/services/travel_plan_service.py`

### 4. Food Tour Intent Policy

Food tour previously looked like a generic sightseeing itinerary with some restaurants.

Added food-tour-specific policy:

- Detect food-tour style prompts such as food tour, street food, local food, Hue cuisine, cheap local food.
- Prioritize food/cafe/local eating POIs.
- Exclude unrelated temples/historical POIs unless user asks for them.
- Default food-tour full-day start is around `09:00`, not current time.
- Food tour is paced across the day with light walking/rest gaps.

Example target rhythm:

```txt
09:00 food
10:15 cafe/local snack
11:30 lunch/snack
13:00 walk/rest
14:30 cafe
16:00 snack
18:30 dinner
20:00 evening food/walk
```

Files:

- `layer2_3_gateway/app/services/llm_extractor.py`
- `layer2_3_gateway/app/services/spatial_filter.py`
- `layer2_3_gateway/app/services/layer4_client.py`
- `fleet-route-optimizer-cvrptw/src/services/rest_inserter.py`

### 5. Universal POI Count And Overfill Control

The solver could overfill non-food itineraries because it received too many candidate POIs.

Changed gateway behavior:

- If extractor estimates desired POI count, only pass a bounded POI pool to solver.
- Strict count is used when user explicitly asks for an exact/near-exact number.
- Non-strict count allows small flexibility.

File:

- `layer2_3_gateway/app/services/layer4_client.py`

### 6. Conversation Flow Fixes

Fixed repeated/generic follow-up questions.

Example broken flow:

```txt
User: Đại Nội, cafe muối, ăn chay
Agent: Bạn muốn đi đâu và trong bao nhiêu ngày?
User: Huế, 3 ngày
Agent: Cho em biết thêm...
```

Expected behavior now:

```txt
User: Đại Nội, cafe muối, ăn chay
Agent: Bạn muốn đi đâu và đi bao nhiêu ngày?
User: Huế, 3 ngày
Agent: Dạ đủ thông tin rồi, em tạo lịch trình ngay đây!
```

Fixes:

- Explicit `num_days` now overrides default `1`.
- Common locked POIs are merged instead of only being filled when list is empty.
- If destination + duration + preference/locked POIs are present, backend returns `ready`.

File:

- `layer2_3_gateway/app/services/llm_extractor.py`

### 7. LLM Token/Credit Issue

Observed OpenRouter error:

```txt
Error code: 402
requested up to 8192 tokens, but can only afford 7526
```

Fix:

- Added `max_tokens=2048` to LLM extraction/chat/edit calls.
- Deterministic fallback remains available when LLM fails.

File:

- `layer2_3_gateway/app/services/llm_extractor.py`

### 8. Data/DB Discovery

Investigated why app saw only around 61-69 POIs instead of 1699.

Finding:

- Current running DB volume only had `61` rows in `travel.poi`.
- Running container was using compose project from `layer2_3_gateway`, volume `layer2_3_gateway_travel_data`.
- Root compose uses a different volume name.

Conclusion:

- The 1699 POIs were not in the live DB used by the running gateway.
- Need to standardize on one compose file/volume and import the full POI dataset into that DB.

Recommended target:

- Use root `docker-compose.yml` from `Routing Engine`.
- Confirm after import:

```sql
select count(*) from travel.poi;
```

## Remaining Risks

- Need re-import/verify the full 1699 POI dataset in the active DB.
- Some Vietnamese text in terminal output appears mojibake due PowerShell/container encoding, but API may still serve UTF-8 correctly.
- Solver can still be slow for larger candidate pools; for 50 active users, queue/worker architecture is recommended.
- Virtual meal/rest stops may need improved UI display so travel time before/after break is visually clearer.

## Recommended Next Steps

1. Standardize Docker startup to one compose project.
2. Import the 1699 POIs into the active `travel.poi` table.
3. Add a quick admin health endpoint showing:
   - POI count
   - DB host/schema
   - embedding/vector completeness
4. Add async job queue for itinerary generation before cloud deployment for 50 users.
5. Add regression tests for:
   - no overlap
   - travel-time realism
   - food-tour ratio
   - second-trip chat flow
   - POI count in DB

