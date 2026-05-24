# Interactive Clarification Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an interactive chat-clarification flow that accumulates user preferences, asks targeted follow-up questions, blacklists generic city names from locked POIs, strictly filters non-vegetarian restaurants when a vegetarian preference is requested, and auto-triggers CVRP itinerary generation once all required parameters are 100% complete.

**Architecture:** We will introduce a new backend `/chat_process` API that utilizes `LLMExtractorService` to merge new answers into the `LLMDataContract` state and evaluate completeness. In the spatial filter, we'll implement city name sanitization and strict vegetarian categories via PostGIS SQLAlchemy queries. Finally, we'll hook the React frontend chat handler to automate building triggers.

**Tech Stack:** Python, FastAPI, SQLAlchemy, PostgreSQL (PostGIS), React (Next.js, TypeScript).

---

## Proposed File Responsibilities

| File Path | Description | Action |
| :--- | :--- | :--- |
| `layer2_3_gateway/app/services/llm_extractor.py` | Core LLM intent extraction and history-based state-machine updates. | Modify |
| `layer2_3_gateway/app/services/spatial_filter.py` | City name blacklist sanitization & strict vegetarian database filtering. | Modify |
| `layer2_3_gateway/app/api/trip_planner.py` | Add the new `/v1/trip/chat_process` HTTP POST endpoint. | Modify |
| `layer2_3_gateway/tests/test_chat_clarification.py` | Massive unit test suite covering 40+ complex edge cases. | Create |
| `fleet-route-optimizer-cvrptw/webui/src/app/page.tsx` | Front-end chat integration to handle multi-turn follow-up and auto-build. | Modify |

---

## Tasks Checklist

### Task 1: Backend Chat API & LLM Service Logic

**Files:**
- Modify: [llm_extractor.py](file:///d:/Workspaces/AI%20travel%20optimizer/Routing%20Engine/layer2_3_gateway/app/services/llm_extractor.py)
- Modify: [trip_planner.py](file:///d:/Workspaces/AI%20travel%20optimizer/Routing%20Engine/layer2_3_gateway/app/api/trip_planner.py)

- [ ] **Step 1: Write a failing unit test for `process_chat_turn`**
  Add a temporary test inside `layer2_3_gateway/tests/test_llm_extractor.py`:
  ```python
  import pytest
  from app.schemas.trip import LLMDataContract
  from app.services.llm_extractor import LLMExtractorService

  @pytest.mark.anyio
  async def test_process_chat_turn_extraction():
      service = LLMExtractorService()
      current = LLMDataContract(destination=None, num_days=1, budget_max=None, tags=[])
      # Mock the LLM client call if offline, but run_command checks integration
      res = await service.process_chat_turn(
          message="Tôi muốn đi Huế 3 ngày ngân sách 1 triệu",
          history=[],
          current_contract=current
      )
      assert res["status"] == "clarifying" or res["status"] == "ready"
      assert res["updated_contract"].destination == "Huế"
      assert res["updated_contract"].num_days == 3
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `docker exec -t travel-gateway pytest tests/test_llm_extractor.py -k test_process_chat_turn_extraction`
  Expected: FAIL with `AttributeError: 'LLMExtractorService' object has no attribute 'process_chat_turn'`

- [ ] **Step 3: Implement `process_chat_turn` in `llm_extractor.py`**
  Add the method to the class `LLMExtractorService`:
  ```python
      async def process_chat_turn(
          self,
          message: str,
          history: list,
          current_contract: LLMDataContract
      ) -> dict:
          """Analyze the new chat message in the context of history to update the contract."""
          # Assemble conversational context
          messages = [
              {"role": "system", "content": (
                  "Bạn là trợ lý du lịch hỗ trợ thu thập thông tin để lập lịch trình.\n"
                  "Phân tích tin nhắn của người dùng kết hợp với lịch sử chat và cập nhật thông tin chuyến đi.\n"
                  "Bạn cần cập nhật các trường: destination, num_days (số ngày, mặc định 1), budget_max (ngân sách VNĐ, null nếu chưa biết), tags (sở thích, ví dụ: 'vegetarian' nếu muốn ăn chay, 'cafe_muoi'...). \n"
                  "Hãy trả về JSON chứa:\n"
                  "- updated_contract: Dữ liệu LLMDataContract đầy đủ cập nhật mới nhất.\n"
                  "- status: 'ready' nếu ĐÃ CÓ ĐẦY ĐỦ các thông tin: destination (điểm đến), num_days (số ngày >= 1), budget_max (ngân sách, hoặc được xác nhận là vô hạn/luxury), và tags/sở thích du lịch. Ngược lại, trả về 'clarifying'.\n"
                  "- reply: Nếu status là 'clarifying', sinh một câu hỏi tiếng Việt ngắn gọn, tự nhiên tập trung vào đúng một trường thông tin còn thiếu. Nếu status là 'ready', sinh một câu chúc mừng sẵn sàng tạo lịch trình.\n"
                  "\n"
                  "LƯU Ý CỰC KỲ QUAN TRỌNG:\n"
                  "1. Tuyệt đối KHÔNG đưa tên thành phố/tỉnh thành chung chung (như 'Huế', 'Đà Nẵng', 'Hà Nội'...) vào trường locked_pois của updated_contract.\n"
                  "2. Nếu người dùng đề cập đến ăn chay, chay, vegetarian, vegan, hãy chắc chắn thêm 'vegetarian' vào danh sách tags.\n"
                  "3. Giữ nguyên các thông tin cũ đã được trích xuất nếu người dùng không thay đổi chúng."
              )}
          ]
          for turn in history:
              messages.append({"role": turn["role"], "content": turn["content"]})
          messages.append({"role": "user", "content": message})

          # We can use instructor to parse this directly into a custom schema
          from pydantic import BaseModel, Field
          class ChatTurnResult(BaseModel):
              status: str = Field(..., description="'ready' or 'clarifying'")
              reply: str = Field(..., description="Conversational reply in Vietnamese")
              updated_contract: LLMDataContract

          try:
              res = await self.client.chat.completions.create(
                  model=global_settings.LLM_MODEL,
                  response_model=ChatTurnResult,
                  messages=messages,
                  max_retries=2,
              )
              
              # Sanitize city names from locked_pois
              city_blacklist = {"huế", "hue", "đà nẵng", "da nang", "hà nội", "ha noi", "sài gòn", "sai gon", "hồ chí minh", "ho chi minh"}
              if res.updated_contract.locked_pois:
                  res.updated_contract.locked_pois = [
                      p for p in res.updated_contract.locked_pois
                      if p.strip().lower() not in city_blacklist
                  ]
              
              # Force vegetarian tag if chay keywords are in the tags or message
              chay_keywords = ["chay", "ăn chay", "vegetarian", "vegan"]
              if any(k in message.lower() for k in chay_keywords):
                  if "vegetarian" not in res.updated_contract.tags:
                      res.updated_contract.tags.append("vegetarian")

              return {
                  "status": res.status,
                  "reply": res.reply,
                  "updated_contract": res.updated_contract
              }
          except Exception as e:
              logger.error(f"process_chat_turn extraction failed: {e}")
              # Fallback
              return {
                  "status": "clarifying",
                  "reply": "Có lỗi xảy ra khi xử lý thông tin. Bạn có thể cho biết cụ thể điểm đến và số ngày dự kiến không?",
                  "updated_contract": current_contract
              }
  ```

- [ ] **Step 4: Implement `/v1/trip/chat_process` in `trip_planner.py`**
  First define a schema for the request in `layer2_3_gateway/app/schemas/trip.py` or inline in `trip_planner.py`.
  Let's add the route to `layer2_3_gateway/app/api/trip_planner.py`:
  ```python
  from pydantic import BaseModel
  class ChatProcessRequest(BaseModel):
      message: str
      history: List[dict] = []
      current_contract: LLMDataContract

  @router.post("/chat_process")
  @limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
  async def chat_process(request: Request, body: ChatProcessRequest):
      """Hội thoại gợi ý & hỏi đáp thông minh trước khi dựng lịch trình."""
      res = await llm_service.process_chat_turn(
          message=body.message,
          history=body.history,
          current_contract=body.current_contract
      )
      return res
  ```

- [ ] **Step 5: Run tests to verify they pass**
  Run: `docker exec -t travel-gateway pytest tests/test_llm_extractor.py -k test_process_chat_turn_extraction`
  Expected: PASS

- [ ] **Step 6: Commit changes**
  ```bash
  git add layer2_3_gateway/app/services/llm_extractor.py layer2_3_gateway/app/api/trip_planner.py
  git commit -m "feat: add backend follow-up chat process API"
  ```

---

### Task 2: Backend Spatial Filter & Strict Vegetarian Exclusions

**Files:**
- Modify: [spatial_filter.py](file:///d:/Workspaces/AI%20travel%20optimizer/Routing Engine/layer2_3_gateway/app/services/spatial_filter.py)

- [ ] **Step 1: Write a failing test for vegetarian exclusion**
  Add a test inside `layer2_3_gateway/tests/test_spatial_filter.py`:
  ```python
  @pytest.mark.anyio
  async def test_vegetarian_restaurant_strict_exclusion(db_session):
      from app.services.spatial_filter import SpatialFilterService
      from app.schemas.trip import LLMDataContract
      
      service = SpatialFilterService()
      contract = LLMDataContract(
          hotel_lat=16.4637,
          hotel_lon=107.5905,
          num_days=3,
          tags=["vegetarian"]
      )
      # Run queries
      pois = await service.get_optimized_pois(contract, db_session)
      
      # Assert that ALL restaurant POIs returned are vegetarian
      for poi in pois:
          if poi.category == "restaurant":
              tags_lower = [t.lower() for t in (poi.tags or [])]
              assert any(t in tags_lower for t in ["vegetarian", "vegan", "buddhist"])
  ```

- [ ] **Step 2: Run test to verify it fails**
  Run: `docker exec -t travel-gateway pytest tests/test_spatial_filter.py -k test_vegetarian_restaurant_strict_exclusion`
  Expected: FAIL

- [ ] **Step 3: Modify `_phase1_force_include` in `spatial_filter.py`**
  Filter out common city names to prevent the 0-day empty itinerary bug:
  ```python
      async def _phase1_force_include(
          self,
          locked_names: List[str],
          hotel_lat: float,
          hotel_lon: float,
          db_session: AsyncSession,
          safety_radius_km: float = 50.0,
      ) -> List[POIResponse]:
          """Query POIs by name within safety radius, mark is_locked=True."""
          if not locked_names:
              return []

          # Sanitize city names from locked_names
          city_blacklist = {"huế", "hue", "đà nẵng", "da nang", "hà nội", "ha noi", "sài gòn", "sai gon", "hồ chí minh", "ho chi minh"}
          locked_names = [name for name in locked_names if name.strip().lower() not in city_blacklist]
          
          if not locked_names:
              return []
  ```

- [ ] **Step 4: Modify `_query_tier` in `spatial_filter.py`**
  Add strict category-based vegetarian filtering to `_query_tier`:
  ```python
          # Strict diet filtering
          is_vegetarian = any(
              t.lower() in ["vegetarian", "vegan", "buddhist", "ăn chay", "chay"]
              for t in (contract.tags or [])
          )
          if is_vegetarian:
              conditions.append(or_(
                  POI.category != "restaurant",
                  POI.tags.any("vegetarian"),
                  POI.tags.any("vegan"),
                  POI.tags.any("buddhist"),
              ))
  ```

- [ ] **Step 5: Run test to verify it passes**
  Run: `docker exec -t travel-gateway pytest tests/test_spatial_filter.py -k test_vegetarian_restaurant_strict_exclusion`
  Expected: PASS

- [ ] **Step 6: Commit changes**
  ```bash
  git add layer2_3_gateway/app/services/spatial_filter.py
  git commit -m "feat: add city blacklist and strict vegetarian filtering in spatial query"
  ```

---

### Task 3: Comprehensive Test Suite (40 Test Cases)

**Files:**
- Create: `layer2_3_gateway/tests/test_chat_clarification.py`

- [ ] **Step 1: Write the failing tests file with 40 cases**
  We will create `test_chat_clarification.py` defining tests across 4 key test groups (Happy path, Missing single param, History accumulation, Edge cases & constraints).
  Each test asserts that the LLM response yields correct statuses, labels, tags, and conversational responses.
  
- [ ] **Step 2: Run all 40 test cases**
  Run: `docker exec -t travel-gateway pytest tests/test_chat_clarification.py -v`
  Expected: PASS on all 40 test cases

- [ ] **Step 3: Commit tests**
  ```bash
  git add layer2_3_gateway/tests/test_chat_clarification.py
  git commit -m "test: add comprehensive 40-case test suite for interactive chat clarification"
  ```

---

### Task 4: Frontend Chat Panel Integration

**Files:**
- Modify: [page.tsx](file:///d:/Workspaces/AI%20travel%20optimizer/Routing Engine/fleet-route-optimizer-cvrptw/webui/src/app/page.tsx)

- [ ] **Step 1: Edit `handleChatSend` in `page.tsx`**
  Modify `handleChatSend` to query `/v1/trip/chat_process` and manage state integration:
  ```typescript
    async function handleChatSend(message: string) {
      if (isRunning) return
      setMessages((items) => [...items, { role: "user", content: message }])

      setIsRunning(true)
      try {
        const historyData = messages.map(m => ({ role: m.role, content: m.content }))
        const response = await fetch(`${GW_URL}${GW_PREFIX}/chat_process`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: message,
            history: historyData,
            current_contract: intent || {
              destination: "Huế",
              num_days: 1,
              budget_max: null,
              tags: []
            }
          })
        })

        if (!response.ok) {
          throw new Error("Chat process API error")
        }

        const data = await response.json()
        setIntent(data.updated_contract)
        setMessages((items) => [...items, { role: "assistant", content: data.reply }])

        if (data.status === "ready") {
          // All fields complete, auto-trigger full CVRP itinerary plan rebuild
          setStatus("building")
          const nextDraft = await generateRealItinerary(
            message,
            data.updated_contract.num_days,
            data.updated_contract.budget_max,
            data.updated_contract.destination,
            data.updated_contract.tags
          )
          setDraft(nextDraft)
          setStatus("live")
          setScreen("builder")
        }
      } catch (e: any) {
        setToastMessage("Lỗi xử lý chat: " + e.message)
      } finally {
        setIsRunning(false)
      }
    }
  ```

- [ ] **Step 2: Build WebUI locally to ensure no compiler/lint errors**
  Run: `npm run build` inside `fleet-route-optimizer-cvrptw/webui`
  Expected: Build succeeds with 0 TS/ESLint errors.

- [ ] **Step 3: Commit changes**
  ```bash
  git add fleet-route-optimizer-cvrptw/webui/src/app/page.tsx
  git commit -m "feat: integrate interactive clarification flow on the frontend chat panel"
  ```
