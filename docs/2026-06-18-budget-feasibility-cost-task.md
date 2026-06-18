# Budget Feasibility & Cost Integrity Task

Date: 2026-06-18
Branch: `feature/overnight-cost-estimator`

## Goal

Make generated itineraries financially believable:

- Understand whether budget is per person or group total.
- Detect impossible or too-tight budgets before building.
- Keep planning inside budget instead of only reporting over-budget after the fact.
- Stop charging transport for virtual rest/lunch slots.
- Use one cost model everywhere in backend and UI.

## Current Failures

### 1. Budget Scope Is Misread

Observed:

```txt
User: Hue 3 days, budget 1,000,000, group 3
UI: Budget 333,333/person, 3 people
```

Expected default:

```txt
1,000,000/person/whole trip
group_budget_total = 3,000,000
```

Only treat budget as group total when user explicitly says:

```txt
tong nhom, ca nhom, budget chung, ngan sach cho ca doan
```

### 2. Planner Does Not Enforce Budget

Current flow is effectively:

```txt
choose itinerary -> estimate cost -> show over-budget
```

Expected flow:

```txt
normalize budget
-> budget feasibility check
-> build POI/transport/lodging quotas
-> choose route within budget
-> estimate cost
-> if over budget, repair/re-plan
-> if still impossible, ask user for a trade-off
```

### 3. Transport Cost Is Too High

Observed:

```txt
Transport: 1,480,224 VND for a low-budget Hue trip
```

Likely causes:

- Taxi is selected too often.
- Transport mode selection is not budget-aware enough.
- Group size is not consistently considered.
- Rest/virtual slots can create fake legs.

Expected:

```txt
short leg -> walking
solo/2 people + budget-sensitive -> motorbike_hailing often preferred
3+ people -> taxi only when group cost/person is reasonable or distance/time requires it
own transport -> time only, no per-leg fare
```

### 4. Virtual Rest/Lunch Slots Create Fake Travel Cost

Observed:

```txt
Banh Beo O Thao
Taxi 18 min · 6.4 km · 110,101 VND
Lunch/rest
Taxi 18 min · 6.4 km · 110,101 VND
```

Expected:

```txt
virtual rest/lunch/self-care slot:
- no coordinate requirement
- no independent travel leg
- no transport icon
- no distance/cost
- anchored at previous POI or between real POIs
```

If lunch is a real food POI, it must be represented as a real POI with coordinates and price.

### 5. Cost Summary Sources Diverge

Observed:

- Main "real cost estimate" and OR-Tools/stat panels can show different totals.

Expected:

```txt
CostEstimatorService is the single source of truth.
Frontend only renders cost_summary/cost_breakdown returned by backend.
No secondary UI-side recomputation except formatting.
```

## New Requirement: Budget Too Low For Request

The system must not generate a fake trip when user requirements are impossible within budget.

### Severity Levels

#### OK

Budget likely supports the request.

Action:

```txt
Build normally, but still prefer cost-aware choices.
```

#### Tight

Budget is possible only with trade-offs.

Action:

```txt
Ask user to choose:
1. Keep days, use budget mode: free/cheap POIs, local food, cheap lodging, budget transport.
2. Reduce trip days.
3. Increase budget for a fuller experience.
```

The assistant may offer a recommended default, but user confirmation is required before build.

#### Impossible

Budget cannot support required lodging/transport/locked POIs/days.

Action:

```txt
Do not build.
Explain minimum realistic estimate.
Ask user to increase budget, reduce days, remove paid items, or exclude lodging/transport from budget.
```

## Proposed Backend Components

### 1. BudgetNormalizer

Input:

- raw budget
- party size
- user wording
- existing contract fields

Output:

```json
{
  "budget_per_person": 1000000,
  "group_budget_total": 3000000,
  "budget_unit_scope": "per_person",
  "budget_period": "total_trip",
  "budget_scope_evidence": "No explicit group-total wording; default per-person for group travel."
}
```

Rules:

- If party size > 1 and no explicit group-total wording, default to `per_person`.
- If user explicitly says group budget, use `group_total`.
- Preserve prior confirmed budget scope unless user changes it.
- UI must display both group and per-person values clearly.

### 2. BudgetFeasibilityService

Input:

- destination
- num_days
- party size
- budget per person/group total
- lodging mode
- transport policy
- locked POIs
- distribution/preferences

Output:

```json
{
  "severity": "ok|tight|impossible",
  "estimated_min_cost_per_person": 0,
  "estimated_min_group_total": 0,
  "recommended_budget_per_person": 0,
  "blocking_reasons": [],
  "tradeoff_options": []
}
```

Minimum estimate buckets:

- lodging minimum
- food baseline
- transport baseline
- locked POI tickets
- basic buffer

### 3. Budget Quota Builder

Convert normalized budget into category quotas:

```txt
lodging quota
food quota
ticket quota
transport quota
reserve quota
```

Use quotas to influence:

- POI pool selection
- paid attraction count
- food/cafe price level
- lodging class
- transport mode preference

### 4. Budget-Aware Planner Repair

After draft estimate:

```txt
if total <= budget:
  accept
else:
  repair:
    reduce paid attractions
    replace expensive POIs with cheaper/free POIs of same intent
    switch transport modes where practical
    lower lodging option if system-selected
    reduce optional/rest paid items
  re-estimate
if still over:
  return tradeoff prompt instead of fake itinerary
```

### 5. Virtual Slot Cost Handling

Mark non-POI slots:

```json
{
  "is_virtual": true,
  "slot_type": "rest|lunch_break|buffer",
  "cost_policy": "none",
  "travel_policy": "anchor_previous"
}
```

Rules:

- No leg from real POI to virtual slot.
- No leg from virtual slot to next real POI.
- Real leg should be computed from previous real POI to next real POI.
- UI should hide mode/distance/fare for virtual slots.

### 6. Cost Single Source Of Truth

Backend:

- `CostEstimatorService.enrich()` owns total and breakdown.
- Post-build and post-edit flows must call it.
- OR-Tools/stat panels must not have independent cost totals.

Frontend:

- Render backend `cost_summary`.
- If missing, show "Dang tinh chi phi" rather than recompute a different total.

## Acceptance Criteria

### A. Group Budget

Input:

```txt
Hue 3 days, budget 1 million, group 3
```

Expected:

```txt
budget_per_person = 1,000,000
group_budget_total = 3,000,000
```

### B. Explicit Group Total

Input:

```txt
Hue 3 days, total group budget 1 million, group 3
```

Expected:

```txt
budget_per_person ~= 333,333
group_budget_total = 1,000,000
```

### C. Low Budget Feasibility

Input:

```txt
Hue 3 days, 200k/person, need lodging and transport
```

Expected:

```txt
No itinerary build.
Assistant explains budget is impossible and asks for trade-off.
```

### D. Tight Budget Trade-Off

Input:

```txt
Hue 3 days, 500k/person, local food, cheap, has no lodging
```

Expected:

```txt
Assistant asks whether to use budget mode / reduce days / increase budget.
```

### E. Rest Slot Transport Bug

Any virtual rest/lunch slot:

Expected:

```txt
No taxi/walking/motorbike icon.
No distance.
No fare.
No duplicate leg cost.
```

### F. Budget Repair

If first draft estimate exceeds budget:

Expected:

```txt
System tries repair/re-plan before returning itinerary.
Final result is within budget or explicitly asks user for trade-off.
```

### G. Cost Consistency

Expected:

```txt
Top cost summary, day cards, transport legs, and OR/stat panels use the same backend cost_summary.
No conflicting total numbers.
```

## Implementation Order

1. Fix BudgetNormalizer and UI display of per-person/group budget.
2. Fix virtual rest/lunch slot travel and cost handling.
3. Make transport mode policy budget-aware and group-aware.
4. Add BudgetFeasibilityService before build confirmation.
5. Add budget quota builder to planner input.
6. Add repair/re-plan loop after cost estimate.
7. Remove/disable any duplicate UI-side cost recomputation.
8. Add E2E tests for all acceptance criteria.

## Notes

- POI price data is assumed clean. `0 VND` means truly free.
- The solution must not hardcode specific POIs or individual user examples.
- LLM can explain trade-offs and interpret budget wording, but backend must validate numeric feasibility.
