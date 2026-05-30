# Intent Clarification And Edit Execution Contract - 2026-05-27

## Core Problem

The itinerary system should not treat every user follow-up as a request to create a new trip.

When an itinerary already exists, user messages usually mean:

- add something
- remove something
- replace something
- change time preference
- change category distribution
- rebuild only if explicitly requested

The LLM should extract the operation. The backend must execute the operation deterministically.

## Non-Negotiable Rule

```txt
If current_itinerary exists
and user did not explicitly request rebuild:
    do not call the create-itinerary pipeline
    call the edit executor
```

If the edit executor cannot apply the change, it must ask a follow-up question or return `cannot_apply`.

It must not silently generate a new unrelated itinerary.

## Operation List

Supported edit operations:

| Operation | Meaning | Rebuild? |
|---|---|---:|
| `add_place` | Add one or more requested POIs/types into the current itinerary | No |
| `remove_place` | Remove matching stop(s) from the current itinerary | No |
| `replace_place` | Replace an existing stop with a new DB-resolved POI/type | No |
| `change_time` | Change daily, day-level, or POI-level time constraints/preferences | No |
| `change_distribution` | Shift category ratios/preferences with minimal itinerary changes | No |
| `rebuild_requested` | User explicitly wants to remake the whole itinerary | Yes, after confirmation |

Removed operation:

```txt
reroute_day
add_evening_activity
```

Rerouting is an internal backend action after a patch, not a user-facing operation.
Evening/night requests are handled as `change_distribution`, not as a separate operation.

## Universal Edit Executor Flow

After the LLM detects an operation, backend must:

1. Load `current_itinerary`.
2. Load the saved trip contract/preferences.
3. Validate operation requirements.
4. Resolve targets:
   - existing stop from current itinerary
   - new POI from database if needed
   - target day/time scope if needed
5. Build an edit patch.
6. Apply patch to a copy of the itinerary.
7. Re-sequence/re-optimize only affected day(s) when needed.
8. Validate:
   - requested edit is visible
   - no overlap
   - travel time exists
   - day start/end respected
   - budget respected unless user approves otherwise
   - locked POIs preserved unless user explicitly removes them
9. Return updated itinerary and edit summary.

Expected edit response:

```json
{
  "status": "edited",
  "operation": "replace_place",
  "affected_days": [2],
  "added_stops": ["Cafe Muối"],
  "removed_stops": ["Cafe cũ"],
  "unchanged_days": [1, 3],
  "warnings": []
}
```

If missing details:

```json
{
  "status": "needs_followup",
  "operation": "remove_place",
  "follow_up_questions": ["Bạn muốn xóa chùa nào? Ngày 1 và ngày 2 đều có điểm chùa."]
}
```

If impossible:

```json
{
  "status": "cannot_apply",
  "operation": "add_place",
  "reason": "Không tìm thấy POI phù hợp trong database hoặc không còn khung giờ khả thi."
}
```

## Operation Execution Details

### `add_place`

Use when user says:

```txt
thêm cafe muối ngày 2
thêm một quán chay
thêm Đại Nội
```

Backend must:

1. Detect whether query is a concrete POI or a type.
2. Search POI database only.
3. Choose best match by name/category/tags/opening hours/budget/route proximity.
4. Determine target day:
   - explicit day from user
   - otherwise best feasible day
   - ask if ambiguous and risky
5. Insert into the least disruptive feasible gap.
6. Re-sequence affected day only.
7. Preserve other days.

Important:

```txt
"thêm quán cafe" means add one cafe unless user asks for multiple.
```

### `remove_place`

Use when user says:

```txt
xóa chùa
bỏ Đấu trường Hổ Quyền
ngày 2 đừng đi cafe nữa
```

Backend must:

1. Match against current itinerary stops first, not the whole DB.
2. Match by name, fuzzy name, category/tag, and target day.
3. If one match, remove it.
4. If multiple matches, ask user to choose.
5. Re-sequence affected day only.
6. Do not refill automatically unless user asks for replacement.

Important:

```txt
"xóa chùa" means remove matching current stops.
It does not mean regenerate a new no-temple itinerary.
```

### `replace_place`

Use when user says:

```txt
đổi chùa thành quán ăn chay
thay cafe này bằng cafe muối
```

Backend must:

1. Resolve old target from current itinerary.
2. Resolve replacement from DB.
3. Preserve original day and approximate time slot if possible.
4. Remove old stop.
5. Insert new stop.
6. Re-sequence affected day only.
7. Validate opening hours, travel time, and budget.

If old target or replacement is ambiguous, ask follow-up.

### `change_time`

Use when user says:

```txt
đừng đi trước 9h
ngày 2 đi muộn hơn
cho Đại Nội vào buổi sáng
```

Backend must classify scope:

- Whole trip daily start/end.
- One day start/end.
- One POI preferred time window.
- Avoid time window.

Then:

1. Update only that scoped time constraint.
2. Preserve POI set if still feasible.
3. Re-sequence affected day(s).
4. If infeasible, ask before dropping or replacing stops.

Important:

```txt
"thêm hoạt động buổi tối" is not a global daily start-time change.
```

### Evening Requests

Use when user says:

```txt
muốn có hoạt động buổi tối
thêm chuyến đi buổi tối
tối có gì chơi không
```

These requests map to `change_distribution` and mean:

```txt
Increase evening/night-compatible distribution or preference.
```

It does not mean:

```txt
Create a hard slot after 18:00.
Change all days to start at 18:00.
Force every day to have a night stop.
```

Backend must:

1. Update preference/distribution toward evening-compatible POIs.
2. Increase weight for:
   - nightlife
   - night market
   - walking street
   - river walk
   - dessert
   - cafe
   - local food
   - POIs open in the user's preferred time window
3. Let timing be decided by:
   - user's `preferred_time_window`
   - POI opening hours
   - route feasibility
   - day start/end
   - pace and meal policy

## 2026-05-29 Update: Smooth Post-Draft Editing

Post-draft chat is the most important UX surface. The system should feel like a
normal AI conversation, but the backend must still apply edits deterministically.

Do not run the full create-itinerary pipeline on every post-draft message.
Instead:

```txt
current_itinerary
+ compact itinerary summary
+ user edit message
+ short edit history
-> Edit Intent Agent
-> pending_edit_plan
-> user confirmation
-> deterministic edit executor
-> re-time/re-route affected day(s)
-> validator
-> updated itinerary
```

The LLM may understand the request and propose structured operations. It must
not directly generate a replacement itinerary JSON, because that can lose POI
ids, invent POIs, break travel times, and rebuild outside the user's intent.

### Pending Edit Plan

User can enter multiple edit messages before applying. The assistant should
merge them into `pending_edit_plan` and apply them only when the user confirms.

Example:

```txt
User: bỏ 2 quán bún bò ngày 2, thêm 1 quán chè vào buổi chiều
Assistant: Em sẽ bỏ 2 điểm bún bò ở ngày 2 và thêm 1 quán chè vào buổi chiều ngày 2. Anh xác nhận em sửa nhé?
User: ok
Backend: apply batch edit
```

Expected pending response:

```json
{
  "status": "pending_confirmation",
  "requires_confirmation": true,
  "operations": [
    {
      "type": "remove_place",
      "target_day": 2,
      "target_category": "food",
      "target_micro_tags": ["bun_bo"],
      "target_count": 2,
      "resolution_strategy": "current_itinerary_match"
    },
    {
      "type": "add_place",
      "target_day": 2,
      "query": "quán chè",
      "target_category": "food",
      "target_micro_tags": ["che", "dessert"],
      "target_count": 1,
      "time_window": {"start_min": 840, "end_min": 1020},
      "resolution_strategy": "vector_search_then_suggest"
    }
  ],
  "affected_days": [2],
  "assistant_reply": "Em sẽ bỏ 2 quán bún bò ở ngày 2 và thêm 1 quán chè vào buổi chiều ngày 2. Anh xác nhận em sửa nhé?"
}
```

### Expanded Operation Set

The deterministic edit operation set should be:

| Operation | Meaning | Rebuild? |
|---|---|---:|
| `add_place` | Add one or more named/semantic POIs | No |
| `remove_place` | Remove named/type/count-matched current stops | No |
| `replace_place` | Replace an existing stop with a DB-resolved POI/type | No |
| `swap_places` | Swap two existing stops | No |
| `move_place` | Move existing stop(s) to another day/time/position | No |
| `change_time` | Change daily/day/POI time windows | No |
| `change_duration` | Increase/decrease number of trip days | Usually yes, after confirmation |
| `change_distribution` | Shift category ratios/preferences | Sometimes, after confirmation if broad |
| `rebuild_requested` | Remake whole itinerary | Yes, after confirmation |
| `answer_info` | User asks information only | No |

Anything outside this set should become:

```txt
needs_followup
cannot_apply
answer_info
```

It must not silently rebuild the itinerary.

### Add Place Resolution

For `add_place`, the backend should use the POI database only.

Resolution policy:

```txt
Concrete POI query:
    exact/fuzzy name search first
    vector search fallback

Semantic/type query:
    vector search + category/micro-tag filters
    rank by fit, opening hours, route proximity, budget, novelty

High-confidence single result:
    include as recommended_addition in pending_edit_plan

Medium confidence / multiple good options:
    return 2-3 suggestions for user choice
```

Example:

```txt
User: thêm 1 quán chè vào buổi chiều ngày 2

Search:
    vector_query = "quán chè Huế địa phương ngon buổi chiều"
    filters = category_group in food/cafe
    micro_tags contains che/dessert
    open during 14:00-17:00
    near day 2 route if possible

Output:
    one recommended POI if confidence is high
    otherwise 2-3 candidate POIs
```

The assistant can say:

```txt
Em tìm được 3 quán chè hợp buổi chiều ngày 2. Em đề xuất Chè Hẻm vì gần tuyến nhất. Anh muốn em thêm quán này không?
```

If the user says "cứ chọn quán ngon nhất", the system can auto-pick the highest
ranked feasible result.

### General Or Bulk Remove

For `remove_place`, match current itinerary first, not the whole DB.

Example:

```txt
User: bỏ 2 quán bún bò ngày 2

Scope:
    day_index = 2
Match:
    current stops only
    category_group = food
    micro_tags contains bun_bo
Action:
    remove exactly 2 matching stops if available
Tie-break:
    remove lower utility
    remove duplicate subtype first
    remove worse route position first
    preserve locked stops unless explicitly requested
```

If fewer than 2 matches exist:

```txt
status = needs_followup
assistant_reply = "Ngày 2 hiện chỉ có 1 quán bún bò. Anh muốn em bỏ điểm đó thôi hay bỏ thêm một quán ăn tương tự?"
```

### Change Duration Versus Change Time

`change_time` means changing hours inside existing days:

```txt
đừng đi trước 9h
cho Đại Nội vào buổi sáng
ngày 2 kết thúc trước 19h
```

`change_duration` means changing the number of trip days:

```txt
tăng lên 4 ngày
rút còn 2 ngày
thêm một ngày nữa
ngày cuối bỏ đi
```

Behavior:

```txt
Increase days:
    preserve current draft
    ask whether to spread existing stops or add new experiences
    build new day(s) using quota POI builder after confirmation

Decrease days:
    ask confirmation because stops may be dropped/compressed
    preserve locked POIs
    reassign highest-value feasible stops into remaining days
```

### Swap And Move

`swap_places`:

```txt
đổi chỗ Đại Nội với cafe muối
swap hai điểm đầu ngày 2
cho Cầu Trường Tiền lên trước Chợ Đông Ba
```

Backend:

1. Resolve both targets from current itinerary.
2. Swap positions or time slots.
3. Re-time affected day(s).
4. Validate opening hours and travel time.

`move_place`:

```txt
chuyển Đại Nội sang sáng ngày 2
đưa cafe muối qua ngày cuối
cho điểm này đi buổi chiều
```

Backend:

1. Resolve target stop.
2. Resolve destination scope: day, time window, before/after another stop.
3. Remove from old position.
4. Insert into best feasible slot in target scope.
5. Re-time/re-route affected day(s).
6. Ask before dropping other stops if infeasible.

### Diversity In Quota Builder

POI quota is not enough by itself. Each bucket must enforce per-day diversity.

Suggested micro-tag caps:

```txt
food tour:
    bun_bo: max 1/day
    com_hen: max 1/day
    banh_hue: max 1-2/day
    che: max 1/day
    cafe_muoi: max 1/day
    nem_lui_banh_khoai: max 1/day
    market_food: max 1/day

culture:
    lang_vua: max 1-2/day
    dai_noi_hoang_thanh: max 1/day
    chua_tam_linh: max 1/day
    museum_gallery: max 1/day

nature:
    river_waterfront: max 1/day
    hill_lake_lagoon: max 1/day
    garden_park: max 1/day
```

This prevents itineraries from being technically on-intent but repetitive.

### Coverage Decision

The deterministic edit intent set above covers the important post-draft cases:

| User need | Operation |
|---|---|
| Add a named POI | `add_place` |
| Add a type of place | `add_place` with vector search suggestions |
| Remove a named stop | `remove_place` |
| Remove several stops by type/count | `remove_place` with target count and micro-tags |
| Replace A with B | `replace_place` |
| Swap two stops | `swap_places` |
| Move stop to another day/time | `move_place` |
| Start later/end earlier | `change_time` |
| Put a stop morning/afternoon/evening | `move_place` or `change_time` |
| Add more food/culture/nightlife flavor | `change_distribution` |
| Increase/decrease trip days | `change_duration` |
| Whole trip remake | `rebuild_requested` after confirmation |

This is enough for MVP if every operation has:

```txt
target resolver
POI resolver when needed
affected-day retimer/rerouter
validator
confirmation gate
```
4. If no preferred time window exists and the request is ambiguous, ask:

```txt
Bạn muốn hoạt động buổi tối nằm khoảng sau bữa tối, hay chỉ muốn lịch có nhiều lựa chọn phù hợp buổi tối hơn?
```

### `change_distribution`

Use when user says:

```txt
cho nhiều văn hóa hơn
bớt chùa, thêm ăn uống
ít cafe lại
```

Backend must:

1. Count current itinerary distribution.
2. Interpret requested direction.
3. Calculate the minimal changes needed.
4. Preserve locked/high-quality stops when compatible.
5. Replace/drop only the minimum necessary stops.
6. If the edit would change more than about 30% of stops, ask confirmation before restructuring.

For evening/night requests, increase weight for:

- nightlife
- night market
- walking street
- river walk
- dessert
- cafe
- local food
- POIs open in the user's preferred time window

Timing must still be decided by the user's preferred time window, POI opening hours, route feasibility, day start/end, pace, and meal policy.

Important:

```txt
Distribution edit is a minimal-diff patch by default.
It is not a silent rebuild.
```

### `rebuild_requested`

Use only when user explicitly says:

```txt
làm lại hết
tạo lại từ đầu
bỏ lịch này đi
rebuild lại toàn bộ
```

Backend must not rebuild immediately.

Required flow:

1. LLM/backend summarizes all known user intent:
   - destination
   - num days
   - budget
   - daily time window
   - pace
   - preferred distribution
   - locked POIs
   - excluded POIs
   - latest follow-up changes
2. Ask the user what they want to change in the rebuild.
3. Wait for user confirmation.
4. Only then call the create-itinerary pipeline.
5. Preserve constraints unless user explicitly discards them.
6. Replace the old itinerary only after the new itinerary passes validation.

Expected rebuild confirmation:

```txt
Mình sẽ làm lại toàn bộ lịch. Hiện mình hiểu intent của bạn là:
- Huế, 3 ngày
- ngân sách ...
- muốn ...
- không muốn ...
- các thay đổi gần đây: ...

Bạn muốn giữ các ý này và thay đổi phần nào khi rebuild?
```

## Create-Mode Clarification Gate

Before first itinerary generation, the LLM must make sure critical fields are known:

| Field | Ask If Missing? |
|---|---:|
| destination | Yes |
| num_days | Yes |
| budget or budget policy | Yes |
| daily start/end or preferred time window | Yes |
| pace | Yes if unclear |
| main intent | Yes if vague |
| distribution | Yes if one-keyword intent may make the trip incomplete |

Example:

```txt
User: Huế 3 ngày, văn hóa
System should ask: Bạn muốn lịch văn hóa có xen kẽ món ăn địa phương/cafe/điểm ngoài trời không,
hay chỉ muốn tham quan văn hóa còn ăn uống tự túc?
```

## Acceptance Criteria

The edit system is correct only when:

- Normal edit requests never create a brand-new unrelated itinerary.
- Rebuild happens only after explicit `rebuild_requested` plus user confirmation.
- Evening/night requests only change distribution/preference, not global day start time.
- `reroute_day` no longer exists as an operation.
- Add/remove/replace changes are visible in the current itinerary.
- Unaffected days stay stable.
- Affected days have no overlap and valid travel time.
- The system asks follow-up questions when an operation is underspecified.
- The system returns `cannot_apply` instead of hallucinating a new plan.
