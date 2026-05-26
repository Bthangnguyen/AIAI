# Branch Analysis Report: `origin/feature/web1-e2e-integration`

## 1. Exact Functionality
The `origin/feature/web1-e2e-integration` branch implements multi-itinerary planning and advanced constraint-based dynamic routing:
- **Itinerary Alternative Planning**:
  - Exposes the `/plan_alternatives` POST endpoint on the L2/L3 Gateway.
  - Queries the Layer 4 Solver's `/plan-multi` route to compute three distinct trip variants simultaneously for a single user prompt:
    1. **Balanced**: Standard optimization balancing cost and utility.
    2. **Budget**: Strict cost-minimization strategy.
    3. **Chill**: Relaxes velocity and density parameters for a relaxed sightseeing vibe.
- **Dynamic Transport Modes Extraction**:
  - Dynamically extracts and translates transport modes from the LLM Travel Contract using helper `transport_modes_from_contract(contract)`.
  - Enables user preference translation (e.g., "taxi", "walking", "bus") to form strict solver constraints instead of assuming taxi and walking defaults.
- **Itinerary-Aware Rerouting Constraints**:
  - Resolves active rerouting parameters dynamically using `_re_route_constraints`.
  - When the user requests a route recalculation, the Gateway inspects the original itinerary constraints to preserve active modes (e.g., preserving walking tolerances or bus preferences). Fallback is taxi and walking.

## 2. File Structure Changes
The codebase maintains the standard flat baseline layout structure:
- **`layer2_3_gateway/app/services/transport_modes.py`**: A new helper module translating conversational contract preferences into routing solver modes.

## 3. Dependencies Introduced
- *None* — Leverages existing `httpx` and `fastapi` routing systems.

## 4. Database Changes
- *None* — Extends the API parameters sent downstream to the solver without requiring any modifications to the database schema.

## 5. Modified Files
- `layer2_3_gateway/app/api/trip_planner.py`
- `layer2_3_gateway/app/services/layer4_client.py`
- `layer2_3_gateway/app/services/transport_modes.py`
