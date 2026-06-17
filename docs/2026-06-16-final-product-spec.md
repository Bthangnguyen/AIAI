# TripFlow Final Product Spec - 2026-06-16

## Product Goal

TripFlow must feel like a production travel assistant for Hue: it understands messy user intent, asks only useful questions, builds a feasible itinerary with travel time, and lets the user edit the draft conversationally without rebuilding unrelated plans.

## Final Feature Set

### P0 - Production Blockers

1. Authenticated web and mobile API calls
   - Web and mobile clients must send Firebase ID tokens when available.
   - Local mock tokens remain supported for development only.
   - Protected endpoints must no longer fail for signed-in users because the frontend forgot the bearer token.

2. Reliable build pipeline
   - Chat collection must stop asking repeated follow-up questions once the core contract is complete.
   - `ready_to_plan` requires destination, days, budget or unlimited budget, time window, and distribution confirmation when intent is broad.
   - The backend returns clear errors for unsupported destinations, infeasible schedules, and auth failures.

3. Intent-correct itinerary generation
   - Distribution is always non-null.
   - Food tour, cafe hopping, culture, family/chill, night-focused, vegetarian, and budget trips use different defaults.
   - User-requested micro intents such as bun bo, com hen, che Hue, cafe muoi, vegan/vegetarian, night market, and Imperial City are locked into the POI pool when present.
   - Days must preserve natural meal/rest rhythm.

4. Trustworthy scheduler
   - No overlap.
   - Every stop exposes arrival time, visit duration, departure time, and travel time to next/previous.
   - Travel time must be conservative, using OSRM when available and fallback speed estimates when route data is missing.
   - Affected-day reroutes must preserve locked POIs and day time windows.

5. Smooth post-draft editing
   - User edit messages must become atomic operations: `add_place`, `remove_place`, `replace_place`, `change_time`, `change_distribution`, `change_budget`, `change_pace`, `rebuild_requested`.
   - Normal edits apply to the current itinerary, not a fresh unrelated rebuild.
   - Broad rebuild requests ask for confirmation before remaking the whole trip.

### P1 - Product Completeness

6. Saved trips and user account continuity
   - Google login and guest mode both work.
   - Signed-in users sync drafts to Firestore.
   - Guest users can continue using local drafts.

7. Admin POI quality console
   - Admin-only route remains hidden from normal users.
   - POI QA shows missing embeddings, bad coordinates, generic tags, duplicate names, hotels/accommodation leakage, and missing category groups.
   - Admin can patch POI metadata safely.

8. Observability and safety
   - Backend health includes DB, solver, OSRM, LLM provider, and Firebase status.
   - Circuit breakers protect solver plan and re-route calls.
   - Slow or failed LLM providers fall back without exposing secrets.

9. E2E stress testing
   - Ten build flows that pass through LLM extraction.
   - Five mixed edit flows after draft creation.
   - Each test asserts no overlap, travel time exists, requested micro intents appear, and category distribution roughly matches intent.

### P2 - Polish

10. UI finish
    - Copy should say Mapbox where the app uses Mapbox.
    - Build progress appears only while actually building.
    - Chat running state is shown by the TripFlow avatar/icon.
    - Itinerary cards expose useful warnings without overwhelming users.

11. Share/export
    - Shareable read-only itinerary link.
    - Export day timeline as text/PDF.

12. Cost controls
    - Budget alerts for cloud services.
    - LLM provider cost tracking per request type.

## Work Started In This Pass

- Replace hardcoded web bearer token with dynamic Firebase token retrieval.
- Add mobile API bearer token helper and attach it to protected requests.
- Normalize mobile SSE stream handling for both `step` and `stage` backend event names.
- Add circuit breaker protection to Layer 4 re-route calls.
- Remove the Plan/Build segmented control from the web prompt box so the main flow behaves like one natural conversation.
- Add a backend readiness gate so LLM `ready` cannot trigger itinerary generation while critical fields are missing or before the user confirms the summarized contract.
- Route `change_duration` edit operations through the controlled rebuild path after confirmation.

## Acceptance Criteria

- A signed-in user can build an itinerary from web production without a 401 caused by missing bearer token.
- Mobile stream generation accepts both old and new SSE event shapes.
- A re-route solver outage returns a controlled error instead of hanging.
- The web landing prompt no longer exposes Plan/Build mode selection to users.
- If the LLM returns `ready` too early, the backend still asks for missing destination, days, budget, time window, or interests.
- Complete first-turn requests move to confirmation instead of silently building.
- Duration changes are treated as rebuild-level edits, not ignored atomic edits.
- Repo compiles for changed TypeScript/Python modules.
