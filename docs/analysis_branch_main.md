# Branch Analysis Report: `main` (Baseline)

## 1. Exact Functionality
The `main` branch serves as the production-hardened baseline for the AIAI Travel Optimizer. Its core features include:
- **Mobile Frontend (React Native / Expo)**:
  - **Glassmorphic Dark Theme**: A highly refined UI featuring slate backgrounds, royal hue accents, gold borders, and ambient colored backdrops.
  - **Conversational Chat Interface**: Real-time conversation loop with AI, which constructs an LLM Travel Contract dynamically step-by-step.
  - **Pre-flight Health Checks**: Validates the availability of the L2/L3 Gateway API before initiating any downstream routing solver calls.
  - **Real-Time Progress Tracking (SSE)**: Pushes routing pipeline progress directly to the screen via Server-Sent Events (SSE). It parses real-time logs through `useTripPipeline.ts`.
  - **GPS Routing & Map View**: Offers interactive routing visualizations, maps, and JIT (Just-In-Time) rerouting dynamically updated through current location coordinates.
- **Backend Gateway (FastAPI)**:
  - **Asynchronous Execution**: Complete DB I/O isolation where slow LLM/embedding network calls execute outside active database sessions, preventing connection pool exhaustion.
  - **L2 Intent Extractor**: Uses OpenAI/Gemini models to translate user prompts into structural `LLMDataContract` structures.
  - **L3 Spatial & Semantic Filter**: Executes fast spatial queries in PostgreSQL/PostGIS (within 50ms) to pull nearby Points of Interest (POIs) based on coordinates, radius, and tags.
  - **L4 Solver Proxy Client**: Marshals filtered POIs, hotel depot constraints, and budget limits to forward them to the Layer 4 OSRM/OR-Tools solver.

## 2. File Structure Changes
The `main` branch establishes the flat, clean repository layout:
- **`/layer2_3_gateway`**: The FastAPI-based orchestrator backend.
  - `app/api/trip_planner.py`: Primary endpoint router exposing `/plan_trip`, `/plan_trip_stream`, `/chat_process`, `/health`, `/search_pois`, and `/re_route`.
  - `app/services/layer4_client.py`: The HTTP wrapper querying the solver at `/plan` and `/re-route`.
- **`/mobile layer/AITravelOptimizer`**: The Expo-based React Native workspace.
  - `app/screens/HomeScreen.tsx`: Modern Glassmorphic Dark UI containing the chat interface, floating contextual suggestion chips, and the interactive voice microphone indicator.
  - `app/screens/LoadingScreen.tsx`: Real-time pipeline progress screen utilizing standard React Native `Animated` API rotating circular gradients and rendering 9 separate stages.
  - `app/services/api/tripService.ts`: Core client service wrapping fetch and `react-native-sse` streams.

## 3. Dependencies Introduced
- **Frontend**:
  - `react-native-sse` for event-driven stream parsing.
  - `expo-linear-gradient` for modern visual styles.
  - `@react-navigation/native-stack` for layout screen transitions.
- **Backend**:
  - `fastapi` and `uvicorn` for web routing.
  - `httpx` for non-blocking HTTP requests.
  - `sqlalchemy` + `asyncpg` for PostgreSQL async connections.
  - `geoalchemy2` for PostGIS spatial types support.
  - `slowapi` for endpoint rate-limiting.

## 4. Database Changes
- Spatial database table `point_of_interest` utilizing PostGIS `GEOMETRY(Point, 4326)` to store coordinate attributes.
- Spatial index on `coordinates` to accelerate radius querying down to sub-10ms performance.
- Heuristic scoring queries selecting hotel hubs under budget parameters.

## 5. Modified Files
*(None — This branch serves as the baseline project repository against which other branches are compared.)*
