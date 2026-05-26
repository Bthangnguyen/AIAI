# Teammate Handoff — `feature/web1-e2e-integration`

**Date:** 2026-05-25  
**Branch:** `feature/web1-e2e-integration`  
**Scope:** Web1 mock E2E (P0–P7) + Web2 compare/admin/reorder (P0–P8 mock) + P8 live scaffold  
**Status:** Mock workflow **validated** — **not** production-ready

---

## 1. Validated status (re-run on handoff machine)

| Check | Result | Command |
|-------|--------|---------|
| Typecheck | **Validated** ✓ | `cd fleet-route-optimizer-cvrptw/webui && npm run typecheck` |
| Lint | **Validated** ✓ (1 warning) | `npm run lint` — `JourneyPlayback.tsx` exhaustive-deps |
| Production build | **Validated** ✓ | `npm run build` |
| Vitest | **Validated** ✓ **45/45** | `npm run test` |
| Playwright mock E2E | **Validated** ✓ **24/24** | `npm run test:e2e` |
| Gateway unit tests (focused) | **Validated** ✓ **31/31** | See [Gateway pytest](#gateway-pytest) |

### Gateway pytest

Recommended command (uses `conftest.py` — **do not** pass `--noconftest` for admin/plan_alternatives tests):

```powershell
cd layer2_3_gateway
python -m pytest tests/test_layer4_client.py tests/test_walking_tolerance.py tests/test_p6_contract.py tests/test_llm_extractor.py tests/test_admin_pois.py tests/test_plan_alternatives.py tests/test_poi_qa.py -q -m "not integration"
```

### Not verified in this handoff

| Check | Status |
|-------|--------|
| `npm run test:e2e:live` | **Not verified** — requires Docker + `travel.env` + LLM key |
| `pytest -m live` | **Not verified** — requires full stack bootstrap |
| Manual reorder → real L4 `/re-route` | **Not verified** — mock E2E only |
| Admin auth security | **Not verified** — placeholder only (see [Known limitations](#3-known-limitations)) |
| Full gateway pytest suite (`tests/`) | **Not verified** — many tests need Postgres `@ db` host + live LLM |

---

## 2. Completed work

### Web1 — Builder + mock E2E (P0–P7)

- Chat clarification flow (budget / days)
- SSE build pipeline with error/partial states
- Re-route infeasible toast (mock)
- Mock gateway (`scripts/mock-gateway.mjs`) with scenario routing
- Playwright specs: happy-path, clarification, build-error, solver-partial, reroute-infeasible, gateway-smoke

### Web2 — Compare, reorder, admin (P0–P8 mock)

| Phase | Deliverable |
|-------|-------------|
| P0 | `/admin` shell, `plan_alternatives` gateway proxy, mock 3-plan response |
| P1 | Compare tab — 3 columns (Cân bằng / Tiết kiệm / Thoải mái) |
| P2 | `PlanMetricsGrid` — 8 metrics + validator warning badges |
| P3 | Apply variant → draft + toast + compare cache |
| P4 | Manual POI reorder (↑↓) + badge Thủ công + Cập nhật lộ trình |
| P5 | `/admin/pois` — table + map pin selection |
| P6 | Inline edit category/tags |
| P7 | `/admin/qa` — 5 issue types + filter |
| P8 | Playwright compare + admin + reorder mock specs |

### Backend additions

- `layer2_3_gateway/app/api/admin_pois.py` — list, patch, QA summary/list
- `layer2_3_gateway/app/services/poi_qa.py` — pure QA checks
- `POST /v1/trip/plan_alternatives` — proxy to L4 `/plan-multi`
- `fleet-route-optimizer-cvrptw/src/services/plan_metrics.py` — per-plan metrics for compare UI

### P8 live scaffold (committed, not sign-off)

- `scripts/bootstrap-fullstack.ps1`
- `layer2_3_gateway/tests/test_live_stack.py`
- `fleet-route-optimizer-cvrptw/webui/playwright.config.live.ts`
- `fleet-route-optimizer-cvrptw/webui/e2e/live/*.spec.ts`

---

## 3. Known limitations

### Security — Admin (placeholder)

- **Assumed:** `/admin/*` Next.js routes are **public** — no middleware, no login
- **Assumed:** Gateway `require_admin()` allows requests when `ADMIN_TOKEN=""` (empty = no check)
- Frontend `gatewayFetch` does **not** send `X-Admin-Token`
- **Not production-ready** — see `docs/superpowers/plans/` (local, gitignored) for hardening plan

### Environment-dependent pytest failures

| Test / file | Why it fails without stack |
|-------------|---------------------------|
| `test_plan_trip_minimal` | Needs Postgres (`SQL_HOST=db` or running Docker DB) |
| `test_vector_sql.py` | Needs `sentence_transformers` + DB |
| `test_end_to_end.py`, `test_complex_constraints_e2e.py` | Integration — Postgres + embeddings |
| `test_llm_extractor.py` (integration marker) | Live LLM calls |

Running `pytest tests/` without `-m "not integration"` and without Docker will produce many failures — **expected**, not a regression in mock workflow.

### Live stack

- Full stack requires: Docker Desktop, `layer2_3_gateway/travel.env` (copy from `travel.env.example`), LLM API key
- Windows: Gateway Docker uses `LAYER4_BASE_URL=http://host.docker.internal:8000`
- **`test:e2e:live` not run** on handoff — teammate must bootstrap and sign off locally

### Reorder + real solver

- Mock E2E (`manual-reorder.spec.ts`) validates UI flow only
- **Not verified:** `handleApplyManualOrder` → Gateway `re_route` → L4 `/re-route` with OR-Tools on real data

### Compare tab architecture

- **Assumed:** Opening Compare or refreshing plans re-runs L2→L3→L4 pipeline via `plan_alternatives` (3 solver runs)
- This is by design for fresh metrics; may be slow on live stack

### Minor code notes (not blockers)

- `layer2_3_gateway/app/main.py` — CORS `allow_origins=["*"]` with `TODO: restrict in production`
- `TripToolbar.tsx` — `console.log` on Export JSON (intentional dev helper)
- `ItineraryMap.tsx` / `ErrorBoundary.tsx` — `console.warn` / `console.error` for fallback diagnostics

---

## 4. Remaining phases / next work

### Web1 P8 — Live sign-off (**not verified**)

1. Copy `travel.env.example` → `travel.env`, add LLM key + `ADMIN_TOKEN`
2. `.\scripts\bootstrap-fullstack.ps1 -Local`
3. `pytest -m live` with `LIVE_INTEGRATION=1`
4. `npm run test:e2e:live`
5. Confirm mock regression: `npm run test:e2e` (24/24)

### Web2 post-handoff (priority from planning doc)

1. **Admin auth** — middleware + mandatory `ADMIN_TOKEN` (highest priority before any public deploy)
2. **Live reorder verify** — `e2e/live/manual-reorder.spec.ts` + pytest re-route live
3. **Env hardening** — sync pytest markers in `pyproject.toml`, validate script

### Out of scope for this branch

- CI GitHub Actions with LLM secrets
- Production CORS lockdown
- Mobile app live E2E

---

## 5. Setup requirements

### Mock workflow (fastest — **validated**)

```powershell
# Terminal 1
cd fleet-route-optimizer-cvrptw/webui
npm install
npm run mock:gateway

# Terminal 2
copy .env.local.example .env.local   # NEXT_PUBLIC_GATEWAY_URL=http://localhost:8001
npm run dev
# → http://localhost:3000
```

Mock guide: `.local/WEB1_WEB_MOCK_GUIDE.md` (local, not in git)

### Full stack (live tests — **not verified** here)

```powershell
copy layer2_3_gateway\travel.env.example layer2_3_gateway\travel.env
# Edit: OPENROUTER_API_KEY or OPENAI_API_KEY, ADMIN_TOKEN

.\scripts\bootstrap-fullstack.ps1 -Local
```

See `fleet-route-optimizer-cvrptw/webui/README.md` → Full-stack E2E section.

### Gateway unit tests

```powershell
cd layer2_3_gateway
pip install fastapi uvicorn sqlalchemy pydantic-settings httpx psycopg geoalchemy2 geojson-pydantic alembic pgvector openai instructor slowapi
python -m pytest tests/test_layer4_client.py tests/test_walking_tolerance.py tests/test_p6_contract.py tests/test_llm_extractor.py tests/test_admin_pois.py tests/test_plan_alternatives.py tests/test_poi_qa.py -q -m "not integration"
```

---

## 6. Repository hygiene (handoff audit)

| Check | Result |
|-------|--------|
| Broken imports (typecheck/build) | None found |
| `.next/` / `travel.env` / `.local/` committed | No — gitignored |
| Temp files (`.tmp`, `.bak`) | None found |
| Debug `debugger` statements | None in webui/src |
| TODO/FIXME in changed code | CORS TODO in `main.py` only (pre-existing pattern) |

---

## 7. Unresolved risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Public admin UI + open API | **High** | Implement auth before deploy; disable `ADMIN_ENABLED` in prod |
| Live stack untested on CI | Medium | Local sign-off only; document in PR |
| Compare = 3× solver cost | Medium | Cache or lazy-load if perf issue on live |
| LLM non-determinism in live E2E | Low | Soft assertions in `helpers-live.ts` |
| `test_plan_trip_minimal` fails without DB | Low | Use focused pytest command above |

---

## 8. Assumptions

- Teammates develop on **Windows** with Docker Desktop
- Mock gateway on `:8001` is sufficient for UI/feature work
- `travel.env` secrets stay local (never committed)
- Web2 P5–P7 UI is **mock-validated**; live admin against Postgres POIs is **assumed** to work but **not verified**

---

## 9. Suggested git commit message

```
feat(web2): compare, admin POI/QA, manual reorder + mock E2E (24 specs)

Web2 P0–P8 on mock gateway: 3-plan compare with metrics/apply, admin
POI list/edit and QA dashboard, timeline manual reorder with re-route UI.

Gateway: admin POI API, plan_alternatives proxy, poi_qa service.
L4: plan_metrics for compare columns.

Validated: typecheck, build, lint, vitest 45/45, playwright mock 24/24,
gateway unit 31/31 (focused suite).

Not verified: live stack, test:e2e:live, real L4 reorder, admin auth.
See docs/TEAMMATE_HANDOFF.md.
```

---

## 10. PR description (draft)

### Summary

- **Web2 compare:** 3 columns (Balanced / Budget / Chill) with validator metrics, apply-to-draft, cached compare state
- **Web2 admin:** `/admin/pois` list+map+edit, `/admin/qa` dashboard with 5 data-quality checks
- **Web2 reorder:** Timeline ↑↓ manual order + "Cập nhật lộ trình" (mock re-route)
- **Backend:** Admin POI CRUD/QA APIs, `plan_alternatives` gateway proxy, L4 `plan_metrics`
- **Tests:** +10 Playwright mock specs, +11 vitest, +15 gateway unit tests

### Validated

- [x] `npm run typecheck` / `npm run build` / `npm run lint`
- [x] Vitest 45/45
- [x] Playwright mock E2E 24/24
- [x] Gateway focused pytest 31/31 (`-m "not integration"`)

### Not verified (explicit)

- [ ] `npm run test:e2e:live`
- [ ] `pytest -m live` with `LIVE_INTEGRATION=1`
- [ ] Manual reorder against real L4 solver
- [ ] Admin auth (placeholder — public routes)

### Known limitations

- Admin UI/API has no real auth; `ADMIN_TOKEN=""` skips token check
- Compare re-fetches via full L2→L3→L4 pipeline (3 solver runs)
- Full `pytest tests/` needs Postgres + optional LLM for integration tests

### Test plan for reviewer

1. `npm run mock:gateway` + `npm run dev` → build itinerary → Compare tab → apply Chill
2. Timeline → move POI ↓ → "Cập nhật lộ trình" → toast
3. `/admin/pois` → search, edit category
4. `/admin/qa` → filter by issue type
5. `npm run test:e2e` → 24/24

### Next recommended task

Admin auth hardening, then `bootstrap-fullstack.ps1 -Local` + `test:e2e:live` sign-off.

---

## 11. Quick handoff notes

**Pull branch:** `feature/web1-e2e-integration`

**Start coding in 2 minutes:**
```powershell
cd fleet-route-optimizer-cvrptw/webui
npm run mock:gateway    # terminal 1
npm run dev             # terminal 2
```

**Do not claim production-ready.** Mock path is solid; live path and admin security need explicit follow-up.

**Questions?** Read `.local/WEB1_IMPLEMENTATION_PLAN.md` and `.local/WEB2_IMPLEMENTATION_PLAN.md` (local plans, not in git).
