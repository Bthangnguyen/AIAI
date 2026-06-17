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
