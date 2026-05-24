# System Design Specification - Interactive Travel Clarification Flow & Gateway Bugfixes

This document specifies the architecture, data structures, and test suites for:
1. **Interactive Clarification Chat Flow (Workspace-driven):** Staging incomplete user requests in the chat workspace, asking targeted clarifying questions, and auto-triggering CVRP itinerary generation once all required parameters are 100% complete.
2. **0-Day Empty Itinerary Bugfix:** Blacklisting general city names (like "Huế") from being locked as POIs.
3. **Strict Vegetarian Filtering Bugfix:** Enforcing that meat restaurants are never scheduled in a vegetarian plan.

---

## 1. Architectural Overview

### Component Diagram & Flow
```
[User Chat Input] ────────► [Next.js page.tsx]
                                 │
                    /chat_process│ (checks completeness)
                                 ▼
                     [LLMExtractorService]
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
        [status: "clarifying"]         [status: "ready"]
                   │                           │
          Show AI Question             Auto-trigger /plan_trip
                   │                           │
         Await next response           Builds & Renders Itinerary
```

---

## 2. API Design & Data Contracts

### 1. Endpoint: `POST /v1/trip/chat_process`
Evaluates the latest chat message in the context of the conversation history and updates/merges the extracted parameters.

#### Request Body
```json
{
  "message": "User's latest input text",
  "history": [
    {"role": "user", "content": "previous text..."},
    {"role": "assistant", "content": "previous AI reply..."}
  ],
  "current_contract": {
    "destination": "Huế",
    "num_days": null,
    "budget_max": null,
    "tags": []
  }
}
```

#### Response Body
```json
{
  "status": "clarifying" | "ready",
  "reply": "AI conversational Vietnamese question or ready message",
  "updated_contract": {
    "destination": "Huế",
    "num_days": 3,
    "budget_max": 1000000.0,
    "tags": ["vegetarian", "cafe_muoi"]
  }
}
```

---

## 3. Detailed Component Designs

### A. `LLMExtractorService` Updates (`llm_extractor.py`)
- We will add the method `process_chat_turn` that accepts `message`, `history`, and `current_contract`.
- A specialized LLM call using `instructor` will parse the input and history to extract/update fields in `LLMDataContract`.
- **Blacklist:** Any extracted destination in `locked_pois` matching general city names (`Huế`, `Đà Nẵng`, `Hà Nội`, `Sài Gòn`, `Hồ Chí Minh`) will be sanitized and excluded to prevent the "0-day empty itinerary" bug.
- **Vegetarian Tag:** If keywords like "ăn chay", "chay", "vegan", "vegetarian" are present, `"vegetarian"` is explicitly added to `tags`.
- **State Evaluation:** The service checks if:
  - `destination` is valid.
  - `num_days` is a valid integer >= 1.
  - `budget_max` is present (or explicitly marked infinite/null with "luxury" tags).
  - If any mandatory field is missing, `status` is set to `"clarifying"`, and a polite, conversational Vietnamese follow-up question is generated focusing on the first missing field.
  - If all core fields are satisfied, `status` is set to `"ready"`.

### B. `SpatialFilterService` Updates (`spatial_filter.py`)
- **City Blacklist:** Inside `_phase1_force_include`, any locked names matching the city blacklist `{"huế", "hue", "đà nẵng", "da nang", "hà nội", "ha noi", "sài gòn", "sai gon", "hồ chí minh", "ho chi minh"}` are filtered out.
- **Strict Vegetarian Exclusion:** Inside `_query_tier`, if any variation of `"vegetarian"`, `"vegan"`, or `"buddhist"` is present in the contract tags, we apply a strict SQLAlchemy constraint:
  `POI.category != "restaurant"` or `POI.tags` overlapping `["vegetarian", "vegan", "buddhist"]`.
  This guarantees meat restaurants (e.g. *Bún Bò Huế Bà Tuyết*) are never returned as candidate POIs for vegetarian plans.

### C. WebUI Integration (`page.tsx`)
- Modify `handleChatSend` to call `/v1/trip/chat_process`.
- If `"clarifying"`, append the AI response to the message log, update `intent` state, and await user response.
- If `"ready"`, display the AI readiness message, then automatically trigger `generateRealItinerary` using the completed contract parameters.

---

## 4. Test Specifications & Edge Cases (40 Cases)

We will implement a rigorous test suite (`tests/test_chat_clarification.py`) containing 40 comprehensive unit and integration test cases covering:
1. **Happy Paths (10 cases):** Complete one-shot prompts immediately transition to `"ready"`. Handles Vietnamese slang ("1 củ", "2tr", "4n3đ").
2. **Missing Parameters (10 cases):** Correctly flags missing `destination`, `num_days`, `budget_max`, or `interests` and asks direct Vietnamese follow-ups.
3. **Multi-turn History Accumulation (10 cases):** Simulates step-by-step chats, verifying the contract merges and retains prior turn state without regression.
4. **Edge Cases & Complex Constraints (10 cases):**
   - Unlimited budget (parses budget as null, sets luxury tags, transitions to `ready`).
   - Invalid number of days (negative/zero) normalized safely.
   - Negative constraints ("không leo núi", "không ăn cay", "tránh lăng tẩm") correctly parsed.
   - Junk/spam inputs handled politely.
   - Out-of-bounds destinations (e.g. "Paris") politely redirected to supported regions.
