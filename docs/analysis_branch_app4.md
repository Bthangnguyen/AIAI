# Branch Analysis Report: `origin/app-4`

## 1. Exact Functionality
The `origin/app-4` branch focuses heavily on backend hardening, security, validation checks, and fault tolerance at the L2/L3 Gateway level:
- **Firebase Auth Shell Integration**:
  - Enforces Firebase token validation on all orchestrator entry points. Endpoints require a valid Firebase ID token parsed into a `FirebaseUser` via FastAPI Dependency Injection (`Depends(get_current_user)`).
- **Asynchronous Memory-Based Idempotency**:
  - Introduces a lock-secured (`asyncio.Lock`) `IdempotencyManager` using `X-Idempotency-Key` headers.
  - Prevents race conditions and double-billing LLM tokens/database routing execution by caching plans in memory for up to 300 seconds. Handles `pending` and `completed` execution states cleanly.
- **Strict Business Validation Guardrails**:
  - **Prompt Length check**: Mandates prompts to fall between `10 <= len(prompt) <= 500` characters.
  - **Spatial Focus Validation**: Enforces that the itinerary must explicitly mention "Huế" or "Hue". Rejects out-of-bounds destinations.
  - **Vague Intent Heuristic Fallback**: Rather than throwing a hard exception if the user prompt lacks specific interests (empty tags/vibe), it automatically merges high-quality default tags `["culture", "street_food", "sightseeing"]` to maintain a seamless user experience.
  - **Trip Duration limits**: Restricts trips to `1 <= num_days <= 7` days.
  - **Financial boundary check**: Enforces a minimum budget threshold of `50,000 VND`.
  - **Hotel Fallback**: Identifies cases where hotel coordinates are auto-selected and raises a warning to down-stream layers.
- **Circuit Breaker Pattern (`layer4_client.py`)**:
  - Integrates a thread-safe `CircuitBreaker` pattern managing three distinct operational states: `CLOSED` (standard routing), `OPEN` (blocking solver routing and raising a structured `CIRCUIT_BREAKER_OPEN` load warning), and `HALF-OPEN` (probing server recovery).
  - Transition trigger: 5 sequential HTTP failures or timeouts trip the circuit to `OPEN`, remaining open for a recovery window of 30 seconds.
- **Error Mapping Interface**:
  - Maps solver-side exceptions (timeouts, HTTP response failures, and unresolved network issues) to explicit API codes: `TIMEOUT`, `OSRM_UNREACHABLE`, `CIRCUIT_BREAKER_OPEN`, and `NO_FEASIBLE_ROUTE`.

## 2. File Structure Changes
- **CODEBASE NESTING ANOMALY**: The entire active repository is nested inside an additional level: `/AIAI-main/AIAI-main/`. This structural misalignment must be flattened before merging.
- **Metadata Additions**: Root directory contains auxiliary markdown specifications:
  - `Phase1.md`, `Phase2.md`, `implementation_all.md`, `phase3_implementation_plan.md`
- **Gateway Middleware**:
  - `app/middleware/firebase_verify.py`: Validates and decodes JWT credentials via Firebase Admin.

## 3. Dependencies Introduced
- **`firebase-admin`**: Required on the gateway host to initialize the Firebase Admin SDK, verify signature keys, and validate user tokens.

## 4. Database Changes
- *None* — While the branch introduces user authentication validation, it uses the existing baseline spatial POI tables without requiring direct database migrations.

## 5. Modified Files
- `AIAI-main/AIAI-main/layer2_3_gateway/app/api/trip_planner.py`
- `AIAI-main/AIAI-main/layer2_3_gateway/app/services/layer4_client.py`
- `AIAI-main/AIAI-main/layer2_3_gateway/app/middleware/firebase_verify.py`
