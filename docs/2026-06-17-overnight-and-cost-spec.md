# TripFlow Overnight Stay And Realistic Cost Spec - 2026-06-17

## Product Goal

TripFlow must estimate a trip like a real traveler would pay for it: itinerary stops, transport between stops, tickets/entrance fees, meals/cafes, and overnight lodging for multi-day trips. The product still supports Hue-focused MVP planning only, with trip duration capped at 1-7 days.

## Scope

### P0 - Required For Final Product

1. Trip duration cap
   - Supported range: 1 to 7 days inclusive.
   - If user asks for more than 7 days, do not silently truncate.
   - Assistant must explain: current product supports up to 7 days and ask whether to plan the first 7 days or shorten the trip.
   - `change_duration` edit must also respect the same cap.

2. Overnight stay model
   - For `num_days >= 2`, itinerary must include an accommodation plan.
   - Accommodation is not treated as a normal attraction/POI stop.
   - Hotels/lodging must not appear as sightseeing stops during the day.
   - Each day must have:
     - `start_lodging`
     - `end_lodging`
     - optional `overnight_stay` summary for the night after that day.
   - For same-city Hue trips, default behavior is one lodging base for all nights unless user asks to move hotels.
   - Number of paid nights:
     - 1-day trip: 0 lodging nights by default.
     - N-day trip: `N - 1` lodging nights.
   - If user says they already have a hotel, lodging cost is 0 unless they ask to include it.
   - If user has no hotel, system auto-selects lodging based on budget and route center, but must label it as estimated.

3. Lodging budget policy
   - Budget must be interpreted as total trip budget unless user says otherwise.
   - Backend should estimate per-night lodging using trip style:
     - budget: 250k-450k VND/night
     - standard/chill: 450k-800k VND/night
     - premium: 900k-1.8m VND/night
   - If total budget is low, lodging estimate must not consume the whole budget.
   - If lodging makes the budget infeasible, assistant asks a follow-up:
     - "Ngân sách này đã bao gồm khách sạn chưa?"
     - "Mình đã có chỗ ở chưa?"
     - "Có muốn em tối ưu theo homestay/nhà nghỉ tiết kiệm không?"

4. Realistic cost breakdown
   - Replace single `budget_used` with structured cost fields:
     - `poi_ticket_cost`
     - `food_and_drink_cost`
     - `local_transport_cost`
     - `lodging_cost`
     - `misc_buffer`
     - `estimated_total_cost`
     - `budget_total`
     - `budget_remaining`
     - `budget_confidence`
   - Every stop should expose:
     - `ticket_cost`
     - `expected_spend`
     - `cost_category`
     - `cost_confidence`
   - Transport between stops should expose:
     - `distance_km`
     - `travel_time_min`
     - `transport_mode`
     - `transport_cost`
   - Day summary should expose:
     - `day_ticket_cost`
     - `day_food_cost`
     - `day_transport_cost`
     - `day_lodging_cost`
     - `day_total_cost`

5. Transport cost model
   - Use route distance when available; fallback to haversine distance with conservative multiplier.
   - Default Hue transport assumptions:
     - walking: 0 VND
     - motorbike/taxi-like estimate: base 12k + 7k/km, minimum 15k per paid leg
     - private car/taxi: base 20k + 12k/km, minimum 30k per paid leg
   - If user selects walking-only, long legs still need warning:
     - `transport_warning: "Đoạn này xa, nên cân nhắc taxi/xe máy."`
   - For group trips, transport cost can be split per person only if UI labels clearly say `per_person`.

6. Ticket and spending model
   - `entrance_fee` remains ticket/admission cost.
   - `price` should mean expected spend for food/cafe/shopping/wellness.
   - If DB currently mixes `price` and `entrance_fee`, add normalization layer:
     - culture/nature ticketed POI -> `ticket_cost = entrance_fee or price`
     - food/cafe -> `expected_spend = price or category default`
     - free public place -> both can be 0
   - Category defaults when missing:
     - street food/snack: 30k-70k
     - restaurant/local meal: 70k-180k
     - cafe/dessert: 35k-90k
     - museum/citadel/tomb: use DB fee if present, otherwise 50k-200k with low confidence

7. Budget validation
   - Budget validation must compare against `estimated_total_cost`, not only entrance fees.
   - If cost exceeds budget:
     - try cheaper POIs/food/lodging first
     - reduce paid attractions if still infeasible
     - then ask user whether to raise budget or accept a more budget-focused plan
   - Itinerary response should include warnings:
     - `budget_exceeded`
     - `lodging_included`
     - `lodging_estimated`
     - `transport_estimated`
     - `low_cost_confidence`

### P1 - Strong Product Polish

8. User intent extraction changes
   - LLM contract should include:
     - `budget_scope`: `total_trip | per_day | excludes_hotel | includes_hotel | unknown`
     - `has_lodging`: boolean or null
     - `lodging_preference`: budget/homestay/hotel/resort/central/quiet/etc.
     - `lodging_budget_per_night`
     - `cost_priority`: save_money/balanced/comfort/premium
   - For multi-day trips with unclear lodging, assistant should ask at most one lodging question.

9. UI display
   - Show a cost summary panel:
     - Tickets
     - Food & drinks
     - Transport
     - Lodging
     - Buffer
     - Total
   - Show "ước tính" labels where confidence is not high.
   - For lodging, show:
     - name or "Khách sạn trung tâm Huế ước tính"
     - nights
     - estimated nightly rate
     - total lodging cost

10. Admin/POI QA
   - Admin QA should detect:
     - food/cafe POIs with missing expected spend
     - ticketed attractions with missing entrance fee
     - hotels with missing nightly rate
     - lodging accidentally tagged as attraction
   - Admin should be able to set:
     - `cost_type`
     - `expected_spend_min`
     - `expected_spend_max`
     - `nightly_rate_min`
     - `nightly_rate_max`
     - `cost_confidence`

## Data Contract Additions

### LLMDataContract

```json
{
  "num_days": 3,
  "budget_max": 1000000,
  "budget_scope": "total_trip",
  "has_lodging": null,
  "lodging_preference": ["central", "budget"],
  "lodging_budget_per_night": null,
  "cost_priority": "balanced"
}
```

### Itinerary Response

```json
{
  "cost_summary": {
    "poi_ticket_cost": 350000,
    "food_and_drink_cost": 520000,
    "local_transport_cost": 280000,
    "lodging_cost": 900000,
    "misc_buffer": 205000,
    "estimated_total_cost": 2255000,
    "budget_total": 2500000,
    "budget_remaining": 245000,
    "budget_confidence": "medium"
  },
  "lodging_plan": {
    "nights": 2,
    "mode": "estimated_default",
    "name": "Khách sạn trung tâm Huế ước tính",
    "nightly_rate": 450000,
    "total_cost": 900000,
    "included_in_budget": true
  }
}
```

## Acceptance Criteria

- A 3-day Hue trip returns 2 lodging nights unless user says they already have lodging.
- A 1-day Hue trip does not add overnight lodging by default.
- An 8-day request is blocked with a follow-up/unsupported duration message, not silently planned.
- Cost summary total includes tickets, food/drinks, transport, lodging, and buffer.
- Budget warnings use total estimated cost, not only POI entrance fees.
- Hotels/accommodation are allowed in lodging plan but never appear as normal sightseeing stops.
- E2E tests cover:
  - 1-day food tour no lodging
  - 3-day budget trip with estimated lodging
  - 3-day trip where user already has hotel
  - 8-day trip rejected/clarified
  - budget exceeded because lodging + transport make plan infeasible

## Implementation Plan

1. Add schema fields for budget scope, lodging intent, lodging plan, and cost summary.
2. Add deterministic extraction for:
   - "đã có khách sạn"
   - "chưa có chỗ ở"
   - "ngân sách chưa gồm khách sạn"
   - "bao gồm khách sạn"
   - requests longer than 7 days.
3. Add `CostEstimatorService` in gateway:
   - normalize POI cost
   - estimate transport cost per leg
   - estimate lodging cost
   - build itinerary/day/stop cost summaries.
4. Update Layer 4 response enrichment to attach cost summary after scheduling.
5. Update UI cost panel and lodging display.
6. Add unit + live E2E tests.

## Addendum - Lodging Map Pin, LLM Transport Policy, And Transport UI

This addendum supersedes earlier assumptions in this spec where they conflict.

### A. Lodging Selection

#### A1. User Already Has Lodging

If the user says they already have lodging, the product should not search the DB by hotel name as the primary UX. The user should choose the lodging base on the map.

Flow:

1. User says they already have lodging.
2. Assistant asks: `Bạn chọn vị trí chỗ ở trên bản đồ giúp mình nhé.`
3. UI enters `select_lodging_base` mode.
4. User clicks anywhere on the map or clicks an existing hotel/lodging marker.
5. Frontend sends selected base to backend.

Contract fields:

```json
{
  "has_lodging": true,
  "hotel_confirmed": true,
  "hotel_name": "Chỗ ở của bạn",
  "hotel_lat": 16.4637,
  "hotel_lon": 107.5909,
  "lodging_selection": {
    "status": "user_has_lodging",
    "selection_method": "map_pin",
    "lat": 16.4637,
    "lon": 107.5909,
    "name": "Chỗ ở của bạn",
    "hotel_poi_id": null
  }
}
```

Rules:

- Map-selected lodging is used as the route base for every day unless user asks to change lodging.
- Map-selected lodging is not a sightseeing/activity stop.
- Lodging cost is 0 when user already has lodging, unless the user explicitly asks to include lodging cost.
- If the user clicked a DB hotel marker, keep `hotel_poi_id` when possible.
- If the user clicked an arbitrary map point, use `Chỗ ở của bạn`.
- Coordinates should not be shown as normal user-facing text.

#### A2. User Needs Lodging

If the user does not have lodging, backend selects a real `hotel` POI from DB.

Selection inputs:

- budget
- lodging preference
- route center / cluster center
- distance to planned route
- nightly rate from DB `price`

Rules:

- Hotel POIs may be used as lodging base.
- Hotel POIs must not appear as daytime attractions.
- Selected hotel should appear in:
  - `lodging_plan`
  - `start_lodging`
  - `end_lodging`
  - `overnight_stay`
- `price` for hotel means nightly rate.

### B. POI Pricing Source Of Truth

POI pricing data in DB is already cleaned and accurate.

Rules:

- `0` means real 0 VND, not missing data.
- Backend must not invent ticket/food prices when DB value is 0.
- Stop cost must be directly traceable to DB values.

Field meaning:

- `entrance_fee`: ticket/admission cost.
- `price`:
  - food/cafe/shopping/wellness/nightlife: expected spend.
  - hotel: nightly rate.
  - culture/nature/adventure: only use as spend/ticket if DB explicitly stores it there.

Stop output:

```json
{
  "ticket_cost": 0,
  "expected_spend": 85000,
  "price_source": "db_price",
  "cost_confidence": "high"
}
```

Allowed `price_source`:

- `db_entrance_fee`
- `db_price`
- `zero_cost`

### C. LLM-Selected Transport Policy

Transport choice should be LLM-driven from user context. Backend should not hardcode the primary mode while LLM is available.

Backend role:

- execute the LLM policy
- compute distance, time, and cost
- validate feasibility
- add warnings
- use deterministic fallback only when LLM is unavailable or returns invalid policy

LLM input context:

- group size
- group type
- budget
- pace
- time window
- whether user already has transport
- explicit transport preference from user
- trip type and destination

LLM output contract:

```json
{
  "transport_plan": {
    "availability": "needs_transport",
    "primary_mode": "motorbike_hailing",
    "fallback_mode": "taxi",
    "cost_policy": "per_leg",
    "walking_threshold_km": 1.0,
    "cost_scope": "total_group",
    "reason": "Đi 1-2 người, ngân sách tiết kiệm, Huế phù hợp xe máy công nghệ; các chặng gần có thể đi bộ."
  }
}
```

Enums:

- `availability`: `has_own_transport | needs_transport | unknown`
- `primary_mode`: `walking | bicycle | motorbike | motorbike_hailing | taxi | car | mixed`
- `fallback_mode`: `taxi | motorbike_hailing | car | none`
- `cost_policy`: `time_only | per_leg | daily_rental | none`
- `cost_scope`: `total_group | per_person | unknown`

Rules:

- If user has transport available:
  - `cost_policy=time_only`
  - transport cost is 0
  - travel time is still calculated
- If user needs transport:
  - LLM selects primary mode from group size, budget, pace, and preference.
- If two POIs are close:
  - backend may mark that specific leg as walking if `distance_km <= walking_threshold_km`
  - this does not change the whole trip primary mode.
- If LLM chooses walking for a long leg:
  - backend adds warning and suggests fallback mode for that leg.
- If LLM policy is invalid/missing:
  - backend fallback can infer from explicit facts only.

### D. Transport Time And Cost Calculation

Distance:

- prefer routed distance from OSRM/solver when available
- fallback: `haversine_km * 1.25`

Travel time:

```txt
travel_time_min = ceil(distance_km / 30kmh * 60 + buffer)
```

Buffer:

- inner-city leg: +5 minutes
- long leg >= 8 km: +10 minutes

Cost:

- walking: 0
- own transport / time_only: 0
- motorbike_hailing per leg: `max(15000, 12000 + distance_km * 7000)`
- taxi/car per leg: `max(35000, 20000 + distance_km * 14000)`
- daily_rental motorbike: charge daily rental + fuel + parking once per day, not per leg.

### E. Transport Leg Output

Each adjacent pair of stops should have a transport leg object.

```json
{
  "from_stop_id": "poi_a",
  "from_name": "Đại Nội",
  "to_stop_id": "poi_b",
  "to_name": "Cà phê muối",
  "mode": "motorbike_hailing",
  "mode_label": "Xe máy công nghệ",
  "distance_km": 4.8,
  "travel_time_min": 14,
  "transport_cost": 46000,
  "cost_policy": "per_leg",
  "cost_scope": "total_group",
  "icon": "motorbike",
  "warning": null
}
```

Legs may be exposed:

- day-level `transport_legs[]`
- stop-level `transport_from_prev`

Both are allowed during transition, but UI should prefer day-level `transport_legs[]` once available.

### F. UI Requirements

#### F1. Timeline

Between two POIs, show a compact transport row/card:

```txt
Đại Nội
↓ Xe máy công nghệ · 14 phút · 4.8 km · 46.000đ
Cà phê muối
```

If user has transport:

```txt
↓ Xe máy cá nhân · 14 phút · 4.8 km · Đã có phương tiện
```

If walking:

```txt
↓ Đi bộ · 8 phút · 650 m · 0đ
```

If daily rental:

```txt
↓ Xe máy thuê theo ngày · 14 phút · 4.8 km · đã tính trong phí thuê ngày
```

Show warnings inline only when needed:

```txt
Đoạn này hơi xa để đi bộ, nên chuyển sang taxi/xe máy.
```

#### F2. Map

Map route segments must show mode icons:

- walking icon: walking legs
- motorbike icon: motorbike, motorbike_hailing, rental motorbike
- car icon: taxi/car
- home/lodging icon: lodging base
- fallback/unknown icon: mixed/unknown

Route segment popup/tooltip should show:

```txt
Đại Nội → Cà phê muối
Xe máy công nghệ
14 phút · 4.8 km · 46.000đ
```

#### F3. Lodging Pin

When user chooses lodging on map:

- show a lodging/home pin
- label: `Chỗ ở của bạn`
- show action: `Đổi vị trí`
- do not display raw coordinates in normal UI

### G. Acceptance Criteria Additions

- If user has lodging, UI allows selecting lodging base on map.
- Selected lodging base is used for route start/end and cost/time calculations.
- If user has transport, transport cost is 0 but travel time remains.
- LLM-selected transport policy is visible in the confirmation/build context.
- Timeline shows transport mode, time, distance, and cost between adjacent POIs.
- Map shows transport mode icons on route segments.
- POI cost uses DB values exactly; 0 remains 0.
- Backend deterministic transport fallback is used only when LLM is unavailable or invalid.

## Addendum - Cost, Transport Map Clutter, Virtual Stops, And Post-Draft Edit Regression

This addendum captures the latest product decisions after testing the MVP locally on 2026-06-17.

### H. Map Transport Icon Policy

Problem:

- Rendering one transport icon for every route leg makes the map visually noisy.
- Dense Hue itineraries can have 8-12 route legs per day, so icons overlap POI pins and route lines.
- The map should help users understand geography first; detailed transport data belongs in the timeline.

Decision:

- Hide transport mode icons on the map by default.
- Map should show:
  - POI pins
  - lodging/home pin
  - route lines
- Timeline remains the primary UI for transport details:
  - mode
  - time
  - distance
  - cost
- Optional future UI:
  - add a `Show transport icons` toggle
  - default state is off
  - if enabled, render only significant non-walking legs or one summarized icon per long route segment.

Acceptance criteria:

- Default map view has no floating transport icons between POIs.
- Route lines and POI/hotel pins remain visible and readable.
- No transport marker should cover POI markers.
- Timeline still shows every valid travel leg.

### I. Virtual Stop Policy

Problem:

- Rest/meal/free-time blocks can appear as itinerary items without real coordinates.
- If backend treats them as real POIs, the UI can show invalid transport rows such as `0 km · 0đ`.

Definitions:

Virtual/non-travel stops include:

- `__rest_break__`
- `__meal_break__`
- `__food_walk__`
- `free_time`
- `hotel_checkin`
- any item with no trusted location

Rules:

- Virtual stops are time blocks, not travel destinations.
- Backend must not create a paid transport leg to a virtual stop unless it has a real DB-backed coordinate.
- Timeline may display the virtual stop as:
  - `Nghỉ nhẹ 30 phút`
  - `Ăn trưa tự túc`
  - `Thời gian tự do`
- Timeline must not display:
  - `0 km`
  - `0đ`
  - fake route rows for virtual stops.
- If the user asks to rest at a specific cafe/park/hotel and backend resolves it to a real POI, it is no longer virtual and normal transport applies.

Implementation rule:

- Add helper like `is_virtual_stop(stop)` in backend cost/enrichment and frontend timeline mapping.
- When sequencing stops:
  - travel leg should connect previous real location to next real location
  - virtual stop only consumes time
  - if a virtual stop sits between two real POIs, it does not reset `prev_location`.

Acceptance criteria:

- No `0 km · 0đ` transport row appears before/after rest blocks.
- Rest blocks still affect time feasibility.
- Route distance/cost ignores virtual stops unless they have real coordinates.

### J. Single Cost Source Of Truth

Problem:

- UI currently shows multiple cost totals:
  - real estimated cost panel after cost enrichment
  - OR-Tools optimization panel cost
  - day/timeline item totals
- After adding transport and lodging, these values can diverge and confuse users.

Decision:

- `cost_summary.estimated_total_cost` is the only product-facing total trip cost.
- `cost_summary` owns:
  - tickets
  - food/cafe
  - local transport
  - lodging
  - misc buffer
  - budget remaining/exceeded
- OR-Tools panel must not show a competing `estimated cost` unless clearly labeled as solver-internal.

UI policy:

- Top cost panel:
  - show `cost_summary.estimated_total_cost`
  - show budget warning from `cost_summary.budget_remaining`
- OR-Tools panel:
  - keep route optimization stats:
    - total distance
    - served POIs
    - time/day
    - solver time
  - remove or relabel `Chi phí ước tính`.
- If a cost metric remains in OR-Tools, label it as:
  - `Chi phí POI trước enrichment`
  - or `Solver cost proxy`
  - and do not compare it to user budget.
- Day total should use enriched day fields:
  - `day_ticket_cost + day_food_cost + day_transport_cost + day_lodging_cost`
- Timeline should not recalculate total cost from POI cards alone.

Acceptance criteria:

- The same final total appears in top panel and any trip summary.
- Budget exceeded/remaining is based only on `cost_summary.estimated_total_cost`.
- OR-Tools panel cannot contradict the top cost panel.

### K. Post-Draft Edit Capabilities - Current State

Current deterministic/LLM-assisted edit operations:

1. `add_place`
   - Adds one resolved POI to an existing day.
   - Can use:
     - target day
     - time window
     - preferred time
     - after-target placement
     - vector/name search for a new POI.

2. `remove_place`
   - Removes matching POIs from the current itinerary.
   - Supports:
     - target day
     - target count
     - broad category/micro-tag matching.

3. `replace_place`
   - Finds an existing POI and replaces it with a newly resolved POI.
   - Keeps approximate schedule position.

4. `move_place`
   - Moves an existing POI to another day/time/position.
   - Can place a POI after another target when extracted.

5. `swap_places`
   - Swaps two existing stops if both can be matched.

6. `change_time` / `change_time_window`
   - Currently treated partly as move/rebuild depending on extraction and operation shape.
   - Needs stricter separation:
     - changing one POI time should edit that day only
     - changing trip-wide active hours may require rerun/rebuild.

7. `change_distribution`
   - Rebuild-level operation.
   - Used when user asks for more/less culture, food, cafe, evening activities, etc.

8. `change_budget`
   - Rebuild-level operation.
   - Should preserve locked/user-liked POIs when possible.

9. `change_pace`
   - Rebuild-level operation.
   - Should adjust number of POIs/day, rest blocks, and daily active hours.

10. `change_duration`
   - Rebuild-level operation.
   - Must respect 1-7 day cap.

11. `add_preference` / `avoid_preference`
   - Rebuild-level operation.
   - Should update contract distribution/preferences and regenerate around existing accepted intent.

12. `rebuild_requested`
   - Does not immediately rebuild.
   - Assistant must summarize interpreted changes and ask confirmation.
   - After user confirms, rebuild the full itinerary.

13. `ask_info` / `answer_question` / `info_reply`
   - No itinerary mutation.
   - Used when user asks about cost, distance, why a POI was chosen, etc.

Current known gap:

- After precise edits (`add/remove/replace/move/swap`), backend retimes the draft but does not always rerun the same enrichment layer used after initial build.
- Result: `transport_legs`, lodging references, cost summary, and day cost fields can disappear or become stale after edit.

### L. Post-Draft Edit Invariant

Every edit that mutates itinerary stops must produce a fully enriched itinerary.

Required post-edit pipeline:

```txt
current draft
→ apply edit operations
→ retime affected day(s)
→ validate no overlap
→ rebuild transport legs
→ rebuild hotel start/end legs
→ rebuild stop/day/trip cost summary
→ return updated draft
```

Rules:

- `transport_legs[]` must exist after every successful edit.
- `start_lodging`, `end_lodging`, and `overnight_stay` must survive every edit.
- Cost summary must be recalculated after every edit.
- Budget warning must be recalculated after every edit.
- The editor must not reset accepted contract fields such as:
  - destination
  - num_days
  - budget
  - hotel coordinates
  - lodging mode
  - party size
  - transport policy
  - transport plan
- Edits should preserve POI set except for the requested mutation.
- Rebuild-level operations should preserve explicit user locks/preferences where possible.

Acceptance criteria:

- Add a POI after draft: timeline still shows transport mode/distance/cost.
- Remove a POI after draft: adjacent POIs reconnect with new transport leg.
- Replace a POI after draft: old leg data is recalculated, not reused incorrectly.
- Move a POI after draft: affected source/destination days both get fresh transport legs.
- Swap two POIs: both affected days get fresh timing/transport/cost.
- Budget total changes consistently after edit.

### M. Follow-Up Edit UX Policy

User experience target:

- Editing should feel like talking to an LLM, but backend must execute deterministic, inspectable operations.

Flow:

1. User sends a natural edit request.
2. LLM breaks it into operations.
3. Backend validates operations against current itinerary.
4. If clear and low risk:
   - show concise confirmation or apply if product policy allows instant edits.
5. If ambiguous:
   - ask one focused follow-up.
6. After user confirms:
   - apply operations as one transaction
   - rerun post-edit enrichment
   - return updated itinerary.

Examples:

```txt
User: Thêm 1 quán chè vào chiều ngày 2.
Operations:
- add_place
  target_day=2
  query="quán chè"
  target_count=1
  target_category="food"
  target_micro_tags=["che"]
  time_window={start_min:840,end_min:1020}
```

```txt
User: Bỏ 2 quán bún bò ngày 2, thêm 1 quán chè buổi chiều.
Operations:
- remove_place
  target_day=2
  target_count=2
  target_micro_tags=["bun_bo"]
  target_category="food"
- add_place
  target_day=2
  target_count=1
  query="quán chè"
  target_micro_tags=["che"]
  time_window={start_min:840,end_min:1020}
```

```txt
User: Chuyển Đại Nội sang 7h sáng ngày mai, chèn cafe muối sau Đại Nội.
Operations:
- move_place
  target="Đại Nội"
  target_day=2
  target_time_min=420
- add_place
  query="cafe muối"
  target_day=2
  position="after"
  relative_to="Đại Nội"
  target_micro_tags=["cafe_muoi"]
```

### N. Implementation Plan For This Addendum

1. Hide default map transport icons.
2. Add virtual stop detection in backend enrichment and frontend timeline.
3. Make `cost_summary` the only product-facing total.
4. Remove/relabel OR-Tools competing cost metric.
5. Add post-edit enrichment wrapper:
   - `enrich_after_edit(itinerary, contract, hotel_fallback=false)`
   - reused by every successful precise edit.
6. Add tests:
   - edit add keeps `transport_legs`
   - edit remove reconnects transport
   - virtual rest does not render `0 km · 0đ`
   - top cost equals `cost_summary.estimated_total_cost`
   - OR-Tools panel no longer contradicts product cost.

## Addendum - Group Budget, Per-Person Cost, And Shared Expenses

### O. Budget Scope Policy

Problem:

- Group trips need different accounting from solo trips.
- If a user says `3 người, ngân sách 1 triệu`, real users usually mean `1 triệu / người / toàn chuyến`, not `1 triệu tổng nhóm`.
- Shared costs such as homestay and taxi should be divided across travelers.
- Per-person costs such as tickets and meals should be multiplied by party size.

Decision:

- Default budget scope:
  - if group size is 1: `per_person` and `group_total` are equivalent
  - if group size > 1 and user says only `ngân sách X`: interpret as `X / người / toàn chuyến`
  - if user explicitly says `tổng nhóm`, `cả nhóm có`, `tổng budget nhóm`: use `group_total`
- Budget period defaults to `total_trip`, not per day.
- If user says `mỗi ngày`, use `per_day`.

LLM contract additions:

```json
{
  "party": {
    "size": 3,
    "type": "friends"
  },
  "budget": {
    "amount": 1000000,
    "scope": "per_person",
    "period": "total_trip"
  },
  "budget_per_person": 1000000,
  "group_budget_total": 3000000
}
```

Enums:

- `budget.scope`: `per_person | group_total | unknown`
- `budget.period`: `total_trip | per_day | unknown`

Normalization:

```txt
if budget.scope == per_person:
  budget_per_person = amount
  group_budget_total = amount * party_size

if budget.scope == group_total:
  group_budget_total = amount
  budget_per_person = amount / party_size
```

### P. Cost Allocation Model

Every cost must declare how it scales:

1. Per-person costs
   - entrance tickets
   - meals
   - cafe/dessert
   - personal tour tickets
   - wellness/spa if charged per person

2. Shared group costs
   - homestay/hotel room if charged per room/night
   - taxi/car
   - parking/fixed route fee

3. Per-vehicle costs
   - motorbike rental
   - motorbike hailing
   - bicycle rental

Rules:

- Tickets:

```txt
ticket_group_cost = ticket_price_per_person * party_size
ticket_per_person = ticket_price_per_person
```

- Food/cafe:

```txt
food_group_cost = expected_spend_per_person * party_size
food_per_person = expected_spend_per_person
```

- Lodging:

```txt
rooms_needed = ceil(party_size / room_capacity)
lodging_group_cost = rooms_needed * nightly_rate * nights
lodging_per_person = lodging_group_cost / party_size
```

- Taxi/car:

```txt
transport_group_cost = one_vehicle_leg_cost
transport_per_person = transport_group_cost / party_size
```

- Motorbike hailing:

```txt
vehicles_needed = party_size
transport_group_cost = one_motorbike_leg_cost * vehicles_needed
transport_per_person = one_motorbike_leg_cost
```

- Motorbike rental:

```txt
vehicles_needed = ceil(party_size / 2)
transport_group_cost = daily_rental_per_bike * vehicles_needed * days + fuel_estimate
transport_per_person = transport_group_cost / party_size
```

### Q. Lodging Capacity Defaults

DB should eventually store capacity fields:

```json
{
  "room_capacity": 2,
  "pricing_unit": "room_night"
}
```

Until DB is extended, backend fallback defaults:

- hotel room: capacity `2`
- nha nghi / guesthouse: capacity `2`
- homestay room: capacity `2`
- homestay whole house / villa: capacity `4`
- hostel dorm / capsule: pricing unit can be `per_bed` if tagged; otherwise capacity `1`

Pricing units:

- `per_person`
- `room_night`
- `whole_unit_night`
- `vehicle_leg`
- `vehicle_day`

Rules:

- Hotel/lodging `price` from DB is nightly rate for the pricing unit.
- If pricing unit is unknown, assume `room_night`.
- UI must label lodging estimate as shared:

```txt
Homestay 500.000đ/đêm · 2 đêm · chia 3 người ≈ 333.000đ/người
```

### R. Transport Selection With Group Cost

Transport mode choice must compare group-level cost, not only single-leg unit cost.

For each leg:

```txt
candidate modes:
  walking if distance <= threshold
  motorbike_hailing
  taxi/car
  own_transport if available
  rental if selected

compute:
  group_cost
  per_person_cost
  travel_time
  comfort/feasibility warning
```

Selection examples:

- 1 traveler:
  - walking if close
  - motorbike_hailing for most paid legs
  - taxi only if comfort/premium/weather/long leg context

- 2 travelers:
  - compare `2 motorbike_hailing` vs `1 taxi`
  - budget-sensitive trips should prefer cheaper feasible option
  - comfort/family/rain/luggage context can prefer taxi

- 3+ travelers:
  - taxi often becomes cheaper/more practical than multiple motorbike rides
  - still compare costs, do not hardcode taxi blindly

Acceptance criteria:

- A 2-person budget trip should not default every paid leg to taxi.
- A 2-person trip may choose taxi only when it is cheaper or contextually better.
- Transport output should expose:

```json
{
  "mode": "motorbike_hailing",
  "vehicles_needed": 2,
  "group_cost": 52000,
  "per_person_cost": 26000,
  "transport_cost": 52000,
  "cost_scope": "total_group"
}
```

### S. Cost Summary Contract V2

Cost summary must expose both group and per-person totals.

```json
{
  "cost_summary": {
    "group_total_cost": 2450000,
    "per_person_cost": 817000,
    "budget_per_person": 1000000,
    "group_budget_total": 3000000,
    "budget_remaining_per_person": 183000,
    "budget_remaining_group": 550000,
    "budget_scope": "per_person",
    "party_size": 3,
    "breakdown_group": {
      "tickets": 600000,
      "food_and_drink": 900000,
      "transport": 350000,
      "lodging": 500000,
      "misc_buffer": 100000
    },
    "breakdown_per_person": {
      "tickets": 200000,
      "food_and_drink": 300000,
      "transport": 117000,
      "lodging": 167000,
      "misc_buffer": 33000
    }
  }
}
```

Backward-compatible aliases during migration:

- `estimated_total_cost` should equal `group_total_cost`
- `budget_total` should equal:
  - `group_budget_total` for internal validation
  - UI must label per-person budget separately
- `budget_remaining` should equal `budget_remaining_group`

### T. Budget Feasibility With Shared Costs

Budget feasibility must compare the same scope:

```txt
if budget_scope == per_person:
  feasible = per_person_cost <= budget_per_person

if budget_scope == group_total:
  feasible = group_total_cost <= group_budget_total
```

Before planning, backend should reserve fixed/shared costs:

```txt
budget_per_person
→ lodging_per_person reserve
→ transport_per_person reserve
→ buffer_per_person reserve
→ activity_budget_per_person
```

If remaining activity budget is too low:

- do not silently generate an over-budget itinerary
- ask a follow-up or confirmation:

```txt
Với 1.000.000đ/người cho 3 ngày gồm chỗ ở và di chuyển thì khá chặt.
Mình muốn:
1. Giữ ngân sách, tối ưu siêu tiết kiệm
2. Không tính chỗ ở trong ngân sách
3. Tăng ngân sách khoảng 1.5-2 triệu/người
```

Thresholds:

- `estimated <= budget`: ok
- `estimated <= budget * 1.15`: allow with warning and cheaper suggestions
- `estimated > budget * 1.15`: ask user before final build unless user explicitly allows flexible budget

### U. UI Requirements For Group Budget

Cost panel should show:

```txt
Ước tính: 817.000đ/người
Tổng nhóm: 2.450.000đ
Ngân sách: 1.000.000đ/người
Còn lại: 183.000đ/người
```

Breakdown should show both when useful:

```txt
Chỗ nghỉ: 500.000đ nhóm · ~167.000đ/người
Di chuyển: 350.000đ nhóm · ~117.000đ/người
Vé tham quan: 600.000đ nhóm · 200.000đ/người
```

Rules:

- Never show only group total when user budget was per-person.
- Never compare group total to per-person budget.
- If budget is group total, label:

```txt
Ngân sách nhóm: 3.000.000đ
~1.000.000đ/người
```

### V. Implementation Plan For Group Budget

1. Extend contract:
   - budget object
   - budget scope
   - budget period
   - normalized `budget_per_person`
   - normalized `group_budget_total`
2. Update LLM extractor:
   - group size > 1 + ambiguous budget => default `per_person`
   - explicit `cả nhóm/tổng nhóm` => `group_total`
3. Update cost estimator:
   - multiply per-person costs by party size
   - divide shared costs by party size
   - add lodging capacity defaults
   - add vehicles needed for transport
4. Update transport selector:
   - compare taxi vs motorbike hailing using group cost
   - avoid taxi-only behavior for two-person budget trips
5. Update budget allocator:
   - reserve lodging/transport/buffer before POI selection
   - block or ask when infeasible
6. Update UI:
   - per-person total as primary display
   - group total as secondary display
   - clear budget scope label
7. Add tests:
   - 3 people, 1m/person, 500k/night homestay for 2 nights => lodging per person about 333k
   - 2 people, budget trip, transport compares taxi vs 2 motorbike hailing
   - group-total budget is not treated as per-person
   - budget warning compares correct scope
