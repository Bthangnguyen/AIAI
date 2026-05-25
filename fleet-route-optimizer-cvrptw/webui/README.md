# TripFlow AI Web

Vietnamese web UI for Hue travel itinerary planning, connected to Layer 2–3 Gateway.

## Prerequisites

- Node.js 18+
- Gateway running at `http://localhost:8001` (see repo root README)
- Optional: Layer 4 solver `:8000`, PostgreSQL, OSRM for full pipeline

## Run locally

**Option A — Mock Gateway (khuyến nghị để test UI trước, không cần backend thật):**

```powershell
# Terminal 1
npm run mock:gateway

# Terminal 2
copy .env.local.example .env.local
npm run dev
```

Chi tiết prompt/scenario: `.local/WEB1_WEB_MOCK_GUIDE.md`

**Option B — Gateway thật:**

```powershell
cd fleet-route-optimizer-cvrptw/webui
npm install
copy .env.local.example .env.local
npm run dev
```

Open **http://localhost:3000**

## Environment

`.env.local`:

```env
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8001
```

## Checks

```powershell
npm run typecheck
npm run lint
npm run build
```

## API integration

| Function | Gateway endpoint |
|----------|------------------|
| `chatProcess` | `POST /v1/trip/chat_process` |
| `generateRealItinerary` | `POST /v1/trip/plan_trip` |
| `streamTripPlan` | `POST /v1/trip/plan_trip_stream` (SSE) |
| `reRouteDay` | `POST /v1/trip/re_route` |
| `searchPoisBackend` | `GET /v1/trip/search_pois` |

Fallback mock POI data lives in `src/data/huePois.ts` when backend POIs are unavailable.

## Full-stack E2E (live)

Prerequisites: Docker, `layer2_3_gateway/travel.env` with LLM key.

From the **repository root** (`AIAI`), use **three terminals** — each snippet assumes you started in the repo root.

```powershell
# Terminal 1 — bootstrap stack
.\scripts\bootstrap-fullstack.ps1
```

```powershell
# Terminal 2 — backend live tests
cd layer2_3_gateway
$env:LIVE_INTEGRATION="1"
python -m pytest tests/test_live_stack.py ../fleet-route-optimizer-cvrptw/tests/test_e2e_docker.py -v -m live --noconftest
```

```powershell
# Terminal 3 — Playwright live
cd fleet-route-optimizer-cvrptw/webui
npm run test:e2e:live
```

Mock E2E (no Docker/LLM): `npm run test:e2e`
