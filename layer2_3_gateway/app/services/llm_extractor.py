# -*- coding: utf-8 -*-
"""Layer 2: extract and refine travel intent with LLM + deterministic gates.

Rewritten to follow intent-edit-followup-plan.md:
- Create mode: LLM-driven follow-up, no hard gate bypass
- Edit mode: returns ready for actionable edits, clarifying for rebuild/info/ambiguous
"""

import logging
import re
import unicodedata
from typing import Optional, List, Dict, Tuple, Iterable, Any

import instructor
from openai import AsyncOpenAI

from app.config import settings as global_settings
from app.schemas.trip import (
    ChatProcessResponse,
    EditIntent,
    LLMDataContract,
    TimeWindowSpec,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# System Prompts
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên trích xuất thông tin từ yêu cầu của khách.
Trả về JSON theo LLMDataContract. Không tự bịa thông tin.

Trích xuất:
- destination: chỉ hỗ trợ Huế/Hue.
- budget_max hoặc budget_is_unlimited.
- num_days, tags, locked_pois, excluded_pois.
- preferred_pace, walking_tolerance, food_preferences, avoid_tags.
- time_slot, trip_duration_hours, time_window nếu có.
- transport_modes, group_type, group_size, hotel info nếu user nói.

THÊM: Phân tích và suy luận các trường sau:
- estimated_pois: Ước lượng số điểm user muốn đi (tối đa 6 POI/ngày). "buổi tối 2-3 quán" → 3. "đi Huế 3 ngày" → 18. "tìm 1 quán cafe" → 1. KHÔNG vượt quá num_days × 6.
- time_slot: Khung giờ. "buổi tối" → "evening". "cả ngày" → "full_day". "sáng mai" → "morning".
- trip_duration_hours: Thời lượng. "buổi tối" → 4-5h. "cả ngày" → 10-12h. "1 buổi sáng" → 3-4h.
- vibe: "lãng mạn" → "romantic". "khám phá" → "adventure". "chill" → "chill". "ăn uống" → "foodie".
- trip_type: "food tour" → "food_tour". "ngắm cảnh" → "sightseeing".
- allow_cafe: True nếu khách nhắc đến thích uống cafe, cafe muối, trà quán, quán nước... Mặc định False.
- allow_art: True nếu khách nhắc đến nghệ thuật, tranh ảnh, bảo tàng tranh, triển lãm... Mặc định False.
- allow_shopping: True nếu khách nhắc đến chợ Đông Ba, mua quà, mua sắm... Mặc định False.
- target_category_distribution: Phân bổ % chỉ cho 5 nhóm chính: food, culture, nature, nightlife, adventure. Tổng phải bằng đúng 1.0. Các nhóm cafe, art, shopping, wellness không bao giờ được xuất hiện trong phân bổ này! VD "văn hóa lịch sử" → {"culture": 0.70, "food": 0.20, "nature": 0.10}
- avoid_tags: "không muốn đông" → ["crowded"]. "tránh chỗ đắt" → ["expensive"].
- walking_tolerance: "low" nếu khách không muốn/hạn chế đi bộ; "high" nếu thích đi bộ khám phá; "medium" nếu không nêu."""

CHAT_PROCESS_SYSTEM_PROMPT = """\
<SYSTEM>
Bạn là LLM INTENT EXTRACTOR cho hệ thống AI-Driven Dynamic Itinerary Optimizer.
Đây là chế độ MULTI-TURN CHAT: bạn nhận conversation_state và tin nhắn mới.

Nhiệm vụ:
1. Đọc conversation_state hiện tại (CURRENT_CONTRACT).
2. Đọc tin nhắn mới (NEW_MESSAGE).
3. Extract thông tin mới từ tin nhắn.
4. Merge với state cũ — giữ nguyên dữ liệu cũ nếu tin nhắn mới không sửa nó.
5. Cập nhật status (clarifying/ready) và sinh reply.

Bạn KHÔNG phải chatbot tư vấn du lịch.
Bạn KHÔNG được tự bịa địa điểm, quán ăn, rating.
Bạn chỉ extract và merge.
Luôn ưu tiên: ĐÚNG > RÕ > ĐỦ > ĐẸP.
</SYSTEM>

<CORE_RULES>
1. Giữ nguyên dữ liệu cũ nếu message không sửa nó.
2. Nếu user sửa thông tin cũ, ưu tiên thông tin mới nhất.
3. Không tự set status="ready" khi chưa đủ: destination + num_days + budget + time_window + ≥1 preference.
4. Nếu user xác nhận tóm tắt trước đó → status="ready".
5. Nếu user phủ định → đưa vào excluded hoặc avoid.
6. Chuẩn hóa tag tiếng Việt sang snake_case không dấu.
</CORE_RULES>

<NORMALIZATION_GUIDE>
- "cafe muối" → "cafe_muoi"
- "bún bò" → "bun_bo"
- "ăn chay" → food_preferences: ["vegetarian"], tags: ["vegetarian"]
- "đi chill" → preferred_pace: "chill"
- "Đại Nội" → locked_pois: ["Đại Nội"]
- "không đi chùa" → excluded_pois: ["chùa"], avoid_tags: ["pagoda", "temple"]
- "8h-17h" → time_window: {start_min: 480, end_min: 1020}
- "cả ngày" → time_slot: "full_day", time_window: {start_min: 480, end_min: 1260}
- "buổi tối" → time_slot: "evening", time_window: {start_min: 1080, end_min: 1320}
- "hạn chế đi bộ" → walking_tolerance: "low"
</NORMALIZATION_GUIDE>

<FOLLOW_UP_RULES>
Chỉ hỏi follow-up khi thiếu dữ liệu bắt buộc hoặc dữ liệu quá mơ hồ.
Tối đa 2 câu hỏi. Ngắn, dễ trả lời, ưu tiên dạng lựa chọn.

Các trường BẮT BUỘC cần hỏi nếu chưa có:
- destination, num_days, budget (hoặc budget_is_unlimited)
- time_window: giờ bắt đầu/kết thúc mỗi ngày (VD: "8h-17h", "cả ngày", "buổi tối")

Ví dụ tốt:
- "Mình muốn đi mấy ngày, ngân sách khoảng bao nhiêu?"
- "Mỗi ngày mình muốn đi từ mấy giờ đến mấy giờ? Hay cả ngày?"
- "Mình thích ẩm thực đường phố hay nhà hàng?"

Ví dụ xấu:
- "Bạn có thể cung cấp thêm đầy đủ thông tin chi tiết về chuyến đi không?"
</FOLLOW_UP_RULES>

<DISTRIBUTION_RULES>
Bạn PHẢI sinh target_category_distribution cho MỌI request.
Chỉ phân bổ cho 5 category keys chính: food, culture, nature, nightlife, adventure. Tổng = 1.0. Các category khác (cafe, art, shopping, wellness) KHÔNG ĐƯỢC PHÂN BỔ PHẦN TRĂM ở đây.
Nếu khách muốn đi uống nước, cafe muối, đi chợ, bảo tàng nghệ thuật, hãy đặt allow_cafe=True, allow_shopping=True, allow_art=True tương ứng trong updated_contract.

distribution_description: viết 1-2 câu tiếng Việt mô tả CỤ THỂ phong cách.
- VD "food tour" → "Ẩm thực đường phố Huế: bún bò, bánh khoái, cơm hến, chè Huế, cà phê muối"
- VD "healing" → "Không gian yên tĩnh bên sông Hương, đi bộ chậm ngắm cảnh"

Nếu user không nói rõ, dùng balanced: {food: 0.35, culture: 0.35, nature: 0.20, nightlife: 0.05, adventure: 0.05}

LUẬT CÂN BẰNG PHÂN PHỐI (DISTRIBUTION BALANCE GATES):
Nếu bạn sinh ra target_category_distribution có một nhóm chiếm >60% (Ví dụ: food: 0.80) mà người dùng KHÔNG yêu cầu rõ rệt loại hình tour lệch (như foodtour thuần túy):
1. Bạn PHẢI đặt status="clarifying", phase="confirming", distribution_locked=False.
2. Trả lời bằng câu hỏi gợi ý cân bằng để khách cân nhắc trong trường `reply`: "Em thấy mình muốn đi ẩm thực nhiều đúng không ạ? Mình có muốn kết hợp thêm địa danh văn hóa, lăng tẩm hoặc thiên nhiên ở Huế để lịch trình đa dạng hơn không, hay chỉ tập trung ăn uống thôi ạ?".
3. Nếu khách trả lời "đồng ý", "chỉ tập trung ăn thôi", "không cần", "đúng rồi" hoặc gật đầu, hãy đặt distribution_locked=True và cho phép lịch trình đi lệch.
</DISTRIBUTION_RULES>

<SCOPE_RULES>
Xác định SCOPE:
- estimated_pois: Tối đa 6 POI mỗi ngày. "1 quán cafe" → 1. "food tour" → 5-6. "cả ngày" → 5-6. Nhiều ngày: num_days × (4-6). Không rõ → null. KHÔNG BAO GIỜ vượt quá num_days × 6.
- trip_duration_hours: "uống cafe sáng" → 1.5. "cả ngày" → 10. Không rõ → null.
- KHÔNG tự scale up. "1 quán cafe" không được thành "lịch trình 1 ngày".
</SCOPE_RULES>

<REPLY_GENERATION>
Bạn PHẢI sinh reply trong trường `reply` của ChatProcessResponse.

NGUYÊN TẮC TỔNG QUÁT:
- Tự nhiên, đừng máy móc. Đọc hiểu ý user thay vì match từ khóa.
- Nếu user cung cấp đủ thông tin (destination, days, budget, ≥1 preference) → hỏi xác nhận ngắn, phase="confirming".
- Nếu user xác nhận (bất kỳ cách nào: "ok", "được", "đúng rồi", "ừ", "đi", gật đầu ngữ cảnh) → status="ready", phase="ready".
- Nếu thiếu thông tin quan trọng → hỏi 1-2 câu ngắn, status="clarifying", phase="collecting".
- Nếu user nói thêm thông tin sau khi xác nhận → merge và hỏi xác nhận lại.

LẦN ĐẦU (chưa có history):
- Diễn giải lại ý user, đề xuất defaults hợp lý.
- Nếu thiếu info quan trọng: hỏi 1-2 câu. status="clarifying", phase="collecting".
- Nếu user đã cho đủ info (VD: "Huế 2 ngày, 1 triệu, văn hóa ẩm thực"): tóm tắt ngắn, hỏi xác nhận. status="clarifying", phase="confirming".

XÁC NHẬN — DÙNG NGỮ CẢNH, KHÔNG MATCH TỪ KHÓA:
- User nói "đúng rồi", "ok", "được", "ừ", "chốt", "đi thôi", "vâng", "đồng ý" → ĐÓ LÀ XÁC NHẬN → status="ready".
- User nói "ok nhưng đổi budget 2 triệu" → CHƯA xác nhận, cần merge rồi hỏi lại.
- User nói thêm info mới mà KHÔNG phản đối → merge, hỏi xác nhận lại.

Giọng em/mình, tối đa 3 câu.
</REPLY_GENERATION>"""

EDIT_INTENT_SYSTEM_PROMPT = """\
<SYSTEM>
Bạn là Edit Intent Extractor cho TripFlow.

User đã có itinerary draft. Nhiệm vụ: đọc yêu cầu chỉnh sửa và trả ChatProcessResponse.

Không tạo lịch mới trong câu trả lời.
Không tự chọn POI cụ thể nếu user chỉ nói loại địa điểm.
Không trả lời dài.
</SYSTEM>

<BACKEND_FIELDS>
- edit_intent.action: add_place | remove_place | replace_place | change_time | change_distribution | change_budget | change_pace | add_preference | avoid_preference | rebuild_requested | info_reply | answer_question
- edit_intent.target: tên POI hoặc nhóm bị tác động.
- edit_intent.target_count: số lượng nếu user nói rõ.
- edit_intent.raw_message: nguyên văn tin nhắn user.
</BACKEND_FIELDS>

<RULES>
1. Giữ nguyên state cũ, chỉ extract phần user muốn đổi.
2. User nói "làm lại hết", "tạo lại", "reset lịch" -> action="rebuild_requested".
3. User hỏi thông tin/so sánh -> action="info_reply" hoặc "answer_question".
4. User thêm một điểm cụ thể -> action="add_place", target=tên điểm.
5. User thêm nhiều điểm cùng loại -> action="add_place", target=loại điểm, target_count nếu có.
6. User bỏ một điểm -> action="remove_place", target=tên điểm hoặc loại.
7. User thay A bằng B -> action="replace_place", target=A.
8. User đổi ngân sách -> action="change_budget".
9. User đổi nhịp/chill/dày hơn/ít hơn -> action="change_pace".
10. User đổi giờ bắt đầu/kết thúc -> action="change_time". User muốn tăng hoạt động buổi tối -> action="change_distribution".
11. User muốn thêm sở thích/tag -> action="add_preference".
12. User muốn tránh thứ gì -> action="avoid_preference".
13. User muốn nhiều/ít hơn một nhóm POI -> action="change_distribution".
</RULES>

<REPLY>
reply: một câu ngắn xác nhận đã hiểu.
Chỉ set status="clarifying" khi thiếu target bắt buộc.
VD: user nói "bỏ chỗ đó" nhưng không rõ chỗ nào → status="clarifying", reply hỏi "Mình muốn bỏ điểm nào ạ?"
Nếu đủ thông tin → status="ready", reply xác nhận ngắn gọn.
</REPLY>"""

# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_FIELDS = [
    "destination",
    "num_days",
    "budget",
    "interests",
    "time_window",
]

FOLLOW_UP_QUESTIONS = {
    "destination": "Mình muốn đi đâu ạ? Hiện tại em hỗ trợ lên lịch trình Huế nhé!",
    "num_days": "Mình dự định đi bao nhiêu ngày ạ?",
    "budget": "Ngân sách chuyến đi khoảng bao nhiêu ạ? (ví dụ: 500k, 1 triệu, thoải mái)",
    "interests": "Mình thích trải nghiệm gì? (ví dụ: văn hóa, ẩm thực, cafe, thiên nhiên...)",
    "pace": "Mình muốn lịch trình nhịp nào? Chill, cân bằng, hay đi nhiều?",
    "walking": "Mức đi bộ bạn thích? Ít, vừa phải, hay thích đi bộ khám phá?",
    "food": "Mình có yêu cầu gì về ăn uống không? (ăn chay, không cay, hải sản...)",
    "must_visit": "Có điểm nào mình nhất định muốn ghé không? (ví dụ: Đại Nội, café muối...)",
    "avoid": "Mình có muốn tránh điều gì không? (chỗ đông, leo núi, nhà hàng đắt...)",
    "time_window": "Mỗi ngày mình muốn bắt đầu và kết thúc khoảng mấy giờ ạ? (ví dụ: 8h-17h, cả ngày, buổi sáng, buổi tối)",
    "transport": "Mình di chuyển bằng gì? Taxi, xe máy, đi bộ...?",
    "group": "Mình đi mấy người? Đi một mình, cặp đôi, gia đình hay nhóm bạn?",
    "hotel": "Mình ở khách sạn nào? Hay để em chọn khách sạn trung tâm mặc định?",
    "confirmation": "Mình xác nhận tạo lịch trình theo thông tin trên chứ ạ?",
    "general": "Mình cho em biết thêm về chuyến đi nhé!",
}

UNLIMITED_BUDGET_MARKERS = (
    "thoai mai", "khong gioi han", "unlimited", "bao nhieu cung duoc",
    "khong quan tam", "khong co gioi han", "no limit",
)

NEGATIVE_OR_ANY_MARKERS = (
    "khong", "k co", "ko co", "khong co", "khong can",
    "duoc het", "gi cung duoc", "tuy", "mac dinh",
    "ok", "duoc", "chua biet", "khong biet", "skip",
)

LOCKED_POI_MAP = {
    "dai noi": "Đại Nội",
    "chua thien mu": "Chùa Thiên Mụ",
    "lang tu duc": "Lăng Tự Đức",
    "lang khai dinh": "Lăng Khải Định",
    "lang minh mang": "Lăng Minh Mạng",
    "cho dong ba": "Chợ Đông Ba",
    "cau truong tien": "Cầu Trường Tiền",
    "cafe muoi": "Café Muối",
    "bun bo hue": "Bún Bò Huế",
    "song huong": "Sông Hương",
}

LLM_MAX_TOKENS = 6000

# Actions that never trigger itinerary rebuild
_INFO_ACTIONS = frozenset({"info_reply", "answer_question"})

# Actions that are concrete edit operations (frontend should execute)
_ACTIONABLE_EDITS = frozenset({
    "add_place", "remove_place", "replace_place",
    "change_time", "change_distribution", "change_budget",
    "change_pace", "add_preference", "avoid_preference",
    "change_time_window",
})


# ═══════════════════════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════════════════════

class LLMExtractorService:
    """Extracts structured travel intent from natural language."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if global_settings.LLM_PROVIDER == "openrouter":
                base_client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=global_settings.OPENROUTER_API_KEY,
                )
            elif global_settings.LLM_PROVIDER == "shopaikey":
                base_client = AsyncOpenAI(
                    base_url="https://api.shopaikey.com/v1",
                    api_key=global_settings.OPENAI_API_KEY,
                )
            else:
                base_client = AsyncOpenAI(api_key=global_settings.OPENAI_API_KEY)

            # shopaikey/openrouter proxy to DeepSeek which doesn't support
            # OpenAI function calling. Use JSON mode instead.
            if global_settings.LLM_PROVIDER in ("shopaikey", "openrouter"):
                self._client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
            else:
                self._client = instructor.from_openai(base_client)
        return self._client

    # ═══════════════════════════════════════════════════════════════════════════
    # Core extraction (Layer 2 one-shot entry point)
    # ═══════════════════════════════════════════════════════════════════════════

    async def extract_intent(
        self,
        user_prompt: str,
        hotel_lat: Optional[float] = None,
        hotel_lon: Optional[float] = None,
        hotel_name: Optional[str] = None,
        num_days: int = 1,
    ) -> LLMDataContract:
        """Parse user text into structured LLMDataContract (one-shot)."""
        try:
            contract = await self.client.chat.completions.create(
                model=global_settings.LLM_MODEL,
                response_model=LLMDataContract,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=2,
                timeout=60.0,
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            contract = LLMDataContract(num_days=num_days, tags=["general"])

        self._override_hotel(contract, hotel_lat, hotel_lon, hotel_name)
        if contract.num_days == 1 and num_days > 1:
            contract.num_days = num_days
            self._mark_confirmed(contract, "num_days")
        self._apply_message_hints(contract, user_prompt)
        self._apply_backend_failsafes(contract, user_prompt)
        logger.debug(f"LLM extracted: {contract.model_dump_json(indent=2)}")
        return contract

    # ═══════════════════════════════════════════════════════════════════════════
    # Multi-turn chat dispatcher
    # ═══════════════════════════════════════════════════════════════════════════

    async def process_chat_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
        has_draft: bool = False,
    ) -> Dict:
        """Process one chat turn — dispatches to create or edit flow."""
        clean_message = (message or "").strip()
        if has_draft:
            return await self._process_edit_turn(clean_message, history, current_contract)
        return await self._process_create_turn(clean_message, history, current_contract)

    # ═══════════════════════════════════════════════════════════════════════════
    # Create mode — LLM-driven follow-up, no hard gate bypass
    # ═══════════════════════════════════════════════════════════════════════════

    async def _process_create_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
    ) -> Dict:
        """Create-mode chat turn: LLM drives follow-up questions.

        Decision order:
        1. Empty message → ask for destination
        2. LLM extraction + merge
        3. Huế-only gate
        4. If LLM returned a reply → RESPECT IT (R1)
        5. If LLM call failed/timeout:
           a. If 2 or more critical fields missing → combined Vietnamese fallback (R2)
           b. Else → Safety net fallbacks (Case B, C, D, E)
        """
        if not message:
            contract = current_contract.model_copy(deep=True)
            return self._collecting_response(contract, ["destination"])

        # ── Step 1: LLM extraction ──
        candidate = None
        llm_reply = ""
        llm_ready = False
        llm_phase = "collecting"
        try:
            history_str = "\n".join([f"{h['role']}: {h['content']}" for h in history])
            prompt = (
                f"CURRENT_CONTRACT:\n{current_contract.model_dump_json(indent=2)}\n\n"
                f"HISTORY:\n{history_str}\n\n"
                f"NEW_MESSAGE:\n{message}"
            )
            response: ChatProcessResponse = await self.client.chat.completions.create(
                model=global_settings.LLM_MODEL,
                response_model=ChatProcessResponse,
                messages=[
                    {"role": "system", "content": CHAT_PROCESS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=LLM_MAX_TOKENS,
                max_retries=2,
                timeout=60.0,
            )
            candidate = response.updated_contract
            llm_reply = response.reply or ""
            llm_ready = response.status == "ready"
            llm_phase = response.phase or "collecting"
            logger.info(
                f"Chat turn OK — status={response.status}, "
                f"phase={llm_phase}, reply_len={len(llm_reply)}"
            )
        except Exception as e:
            logger.error(f"Chat turn LLM failed, using deterministic: {e}")

        # ── Step 2: Merge + post-processing ──
        contract = self._merge_contracts(current_contract, candidate)
        self._apply_message_hints(contract, message)
        self._apply_answer_to_last_question(contract, message, current_contract.last_question_field)
        self._apply_backend_failsafes(contract, message)
        self._deduplicate_locked_pois(contract)

        # ── Step 3: Huế only gate ──
        unsupported_reply = self._unsupported_destination_reply(contract)
        if unsupported_reply:
            contract.confirmation_pending = False
            contract.ready_to_plan = False
            return self._make_response(
                contract, "clarifying", unsupported_reply, phase="collecting",
                missing_fields=["destination"]
            )

        # ── Step 4: Fully LLM-Driven Dialog State (R1) ──
        if llm_reply:
            status = "ready" if llm_ready else "clarifying"
            if llm_ready:
                contract.confirmation_pending = False
                contract.ready_to_plan = True
            else:
                if llm_phase == "confirming":
                    contract.confirmation_pending = True
                    contract.ready_to_plan = False
                else:
                    contract.confirmation_pending = False
            return self._make_response(
                contract, status, llm_reply, phase=llm_phase,
                missing_fields=response.missing_fields if response else []
            )

        # ── Step 5: Combined Fallback Questions on LLM Failure/Timeout (R2) ──
        critical_missing = self._critical_missing(contract)
        if critical_missing:
            if len(critical_missing) >= 2:
                # Specific combination 1: destination & num_days
                if "destination" in critical_missing and "num_days" in critical_missing and len(critical_missing) == 2:
                    reply = "Dạ, mình dự định đi đâu và đi trong mấy ngày thế ạ? Hiện tại em đang hỗ trợ đắc lực tại khu vực Huế nhé!"
                # Specific combination 2: num_days & budget
                elif "num_days" in critical_missing and "budget" in critical_missing and len(critical_missing) == 2:
                    reply = "Mình muốn đi Huế trong mấy ngày và ngân sách dự kiến khoảng bao nhiêu để em thiết kế lịch trình phù hợp ạ?"
                # Specific combination 3: budget & interests
                elif "budget" in critical_missing and "interests" in critical_missing and len(critical_missing) == 2:
                    reply = "Để dễ dàng chọn điểm ăn chơi, mình dự định chi tiêu khoảng bao nhiêu và thích trải nghiệm gì nhất ở Huế ạ? (như văn hóa, ẩm thực, hay cà phê...)"
                # Other combinations
                else:
                    field_labels = {
                        "destination": "điểm đến",
                        "num_days": "số ngày đi",
                        "budget": "ngân sách",
                        "interests": "sở thích",
                        "time_window": "khung giờ hoạt động",
                    }
                    labels = [field_labels[f] for f in critical_missing if f in field_labels]
                    if len(labels) > 1:
                        fields_str = ", ".join(labels[:-1]) + " và " + labels[-1]
                    else:
                        fields_str = labels[0]
                    reply = f"Dạ, để em thiết kế lịch trình trọn vẹn nhất tại Huế, mình chia sẻ thêm giúp em về {fields_str} nhé!"
            else:
                reply = FOLLOW_UP_QUESTIONS.get(critical_missing[0], FOLLOW_UP_QUESTIONS["general"])

            contract.confirmation_pending = False
            contract.ready_to_plan = False
            contract.last_question_field = critical_missing[0]
            return self._make_response(
                contract, "clarifying", reply, phase="collecting",
                missing_fields=critical_missing
            )

        # ── Step 6: Safety Fallbacks (Case B, C, D, E when LLM failed) ──
        # Case B: User explicitly asks to generate ("tạo lịch đi")
        if self._is_generate_request(message):
            has_preference = bool(contract.tags or contract.trip_type or contract.locked_pois)
            if has_preference:
                contract.confirmation_pending = False
                contract.ready_to_plan = True
                reply = "Dạ đủ thông tin rồi, em tạo lịch trình ngay đây!"
                return self._make_response(contract, "ready", reply, phase="ready")
            contract.confirmation_pending = True
            contract.ready_to_plan = False
            reply = self._build_confirmation_reply(contract)
            return self._make_response(contract, "clarifying", reply, phase="confirming")

        # Case C: SAFETY NET — user obviously confirmed
        if self._is_confirmation(message):
            has_preference = bool(
                contract.tags or contract.trip_type
                or contract.locked_pois or contract.food_preferences
            )
            if contract.destination and contract.num_days and has_preference:
                contract.confirmation_pending = False
                contract.ready_to_plan = True
                reply = "Dạ em bắt đầu tạo lịch trình ngay đây!"
                return self._make_response(contract, "ready", reply, phase="ready")

        # Case D: LLM failed (no reply) but we have enough data → deterministic confirm
        has_collected_preference = bool(
            contract.tags
            or contract.trip_type
            or contract.locked_pois
            or contract.food_preferences
        )
        if contract.destination and contract.num_days and has_collected_preference:
            contract.confirmation_pending = True
            contract.ready_to_plan = False
            reply = self._build_confirmation_reply(contract)
            return self._make_response(contract, "clarifying", reply, phase="confirming")

        # Case E: LLM failed entirely — deterministic fallback
        missing = self._missing_fields(contract)
        if missing:
            return self._collecting_response(contract, missing)
        reply = FOLLOW_UP_QUESTIONS["general"]
        return self._make_response(contract, "clarifying", reply, phase="collecting")

    # ═══════════════════════════════════════════════════════════════════════════
    # Edit mode — returns ready for actionable edits, clarifying for ambiguous
    # ═══════════════════════════════════════════════════════════════════════════

    async def _process_edit_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
    ) -> Dict:
        """Edit-mode chat turn.

        Per intent-edit-followup-plan.md:
        - info_reply/answer_question → clarifying (info)
        - rebuild_requested → clarifying + rebuild confirmation
        - Operation missing target → clarifying + follow-up question
        - Actionable operation with enough data → ready + edit_intent
        """
        contract = current_contract.model_copy(deep=True)
        intent = self._detect_edit_intent(message)
        llm_reply = ""

        if message:
            try:
                history_str = "\n".join([f"{h['role']}: {h['content']}" for h in history[-8:]])
                prompt = (
                    f"CURRENT_CONTRACT:\n{contract.model_dump_json(indent=2)}\n\n"
                    f"HISTORY:\n{history_str}\n\n"
                    f"NEW_MESSAGE:\n{message}"
                )
                response: ChatProcessResponse = await self.client.chat.completions.create(
                    model=global_settings.LLM_MODEL,
                    response_model=ChatProcessResponse,
                    messages=[
                        {"role": "system", "content": EDIT_INTENT_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=LLM_MAX_TOKENS,
                    max_retries=2,
                    timeout=60.0,
                )
                if response.updated_contract:
                    contract = self._merge_contracts(contract, response.updated_contract)
                if response.edit_intent:
                    intent = response.edit_intent
                    if not intent.raw_message:
                        intent.raw_message = message
                llm_reply = response.reply or ""
                logger.info(
                    f"Edit turn OK — action={intent.action}, "
                    f"target={intent.target}, reply_len={len(llm_reply)}"
                )
            except Exception as e:
                logger.warning(f"Edit-intent LLM classification failed, using rules: {e}")

        self._apply_message_hints(contract, message)
        self._apply_backend_failsafes(contract, message)
        self._deduplicate_locked_pois(contract)

        action = intent.action

        # ── Safety net: rebuild confirmation from history ──
        # If user says "ok" and previous assistant message was a rebuild confirmation,
        # treat this as rebuild confirmation even if LLM/rules missed it.
        if action in _INFO_ACTIONS and self._is_confirmation(message):
            last_assistant_msg = ""
            for h in reversed(history):
                if h.get("role") == "assistant":
                    last_assistant_msg = h.get("content", "").lower()
                    break
            if "làm lại" in last_assistant_msg or "rebuild" in last_assistant_msg:
                rebuild_intent = EditIntent(
                    action="rebuild_requested", target=None, constraints={},
                    raw_message=message,
                )
                reply = llm_reply or "Dạ em tạo lại toàn bộ lịch trình ngay đây!"
                return self._make_response(contract, "ready", reply, phase="editing",
                                           edit_intent=rebuild_intent)

        # ── Route 1: Info questions → clarifying (info) ──
        if action in _INFO_ACTIONS:
            reply = llm_reply or "Em chưa có thông tin chi tiết về điều này."
            return self._make_response(contract, "clarifying", reply, phase="info",
                                       edit_intent=intent)

        # ── Route 2: Rebuild → clarifying + rebuild confirmation ──
        if action == "rebuild_requested":
            reply = self._build_rebuild_confirmation(contract, intent)
            return self._make_response(contract, "clarifying", reply, phase="editing",
                                       edit_intent=intent)

        # ── Route 3: Operation missing target → clarifying + follow-up ──
        followup = self._needs_edit_followup(action, intent, message)
        if followup:
            reply = llm_reply or followup
            return self._make_response(contract, "clarifying", reply, phase="editing",
                                       edit_intent=intent)

        # ── Route 4: Actionable operation with enough data → ready ──
        if action in _ACTIONABLE_EDITS:
            reply = llm_reply or self._edit_reply(intent)
            logger.info(f"Edit turn result: action={action}, status=ready")
            return self._make_response(contract, "ready", reply, phase="editing",
                                       edit_intent=intent)

        # ── Fallback: unknown action → clarifying ──
        reply = llm_reply or self._edit_reply(intent)
        return self._make_response(contract, "clarifying", reply, phase="editing",
                                   edit_intent=intent)

    # ═══════════════════════════════════════════════════════════════════════════
    # Response builders
    # ═══════════════════════════════════════════════════════════════════════════

    def _make_response(
        self,
        contract: LLMDataContract,
        status: str,
        reply: str,
        phase: str = "collecting",
        missing_fields: Optional[List[str]] = None,
        edit_intent: Optional[EditIntent] = None,
    ) -> Dict:
        return {
            "status": status,
            "reply": reply,
            "updated_contract": contract,
            "phase": phase,
            "missing_fields": missing_fields or [],
            "next_question": reply if status == "clarifying" else None,
            "requires_confirmation": phase == "confirming",
            "edit_intent": edit_intent,
        }

    def _collecting_response(self, contract: LLMDataContract, missing: List[str]) -> Dict:
        next_field = missing[0]
        question = FOLLOW_UP_QUESTIONS.get(next_field, FOLLOW_UP_QUESTIONS["general"])
        contract.confirmation_pending = False
        contract.ready_to_plan = False
        contract.last_question_field = next_field
        return self._make_response(contract, "clarifying", question, phase="collecting",
                                   missing_fields=missing)

    def _build_confirmation_reply(self, contract: LLMDataContract) -> str:
        budget = "ngân sách thoải mái" if contract.budget_is_unlimited else f"ngân sách khoảng {int(contract.budget_max or 0):,} VND"
        must_visit = ", ".join(contract.locked_pois) if contract.locked_pois else "không có điểm bắt buộc"
        avoid = ", ".join((contract.avoid_tags or []) + (contract.excluded_pois or [])) if (contract.avoid_tags or contract.excluded_pois) else "không có yêu cầu tránh riêng"
        tags = ", ".join(contract.tags) if contract.tags else "tổng hợp"
        transport = ", ".join(contract.transport_modes) if contract.transport_modes else "taxi + walking"
        group = contract.group_type or (f"{contract.group_size} người" if contract.group_size else "chưa rõ")
        hotel = contract.hotel_name if contract.hotel_name and contract.hotel_name != "Hotel" else "khách sạn trung tâm Huế mặc định"
        return (
            "Dạ em tóm tắt lại trước khi tạo lịch nhé: "
            f"đi {contract.destination or 'Huế'} {contract.num_days} ngày, {budget}, "
            f"sở thích {tags}, nhịp {contract.preferred_pace or 'balanced'}, "
            f"ăn uống {', '.join(contract.food_preferences) if contract.food_preferences else 'không yêu cầu riêng'}, "
            f"điểm bắt buộc: {must_visit}, tránh: {avoid}, phương tiện {transport}, nhóm {group}, xuất phát từ {hotel}. "
            "Mình xác nhận tạo lịch trình theo thông tin này chứ ạ?"
        )

    def _build_rebuild_confirmation(self, contract: LLMDataContract, intent: EditIntent) -> str:
        """Build rebuild confirmation summary per intent-edit-followup-plan.md."""
        parts = [f"Mình sẽ làm lại toàn bộ lịch. Hiện mình hiểu intent của bạn là:"]
        parts.append(f"- {contract.destination or 'Huế'}, {contract.num_days} ngày")
        if contract.budget_max:
            parts.append(f"- ngân sách {int(contract.budget_max):,} VND")
        elif contract.budget_is_unlimited:
            parts.append(f"- ngân sách thoải mái")
        if contract.tags:
            parts.append(f"- sở thích: {', '.join(contract.tags)}")
        if contract.locked_pois:
            parts.append(f"- nhất định ghé: {', '.join(contract.locked_pois)}")
        if contract.excluded_pois or contract.avoid_tags:
            avoid_list = (contract.excluded_pois or []) + (contract.avoid_tags or [])
            parts.append(f"- tránh: {', '.join(avoid_list)}")
        if contract.food_preferences:
            parts.append(f"- ăn uống: {', '.join(contract.food_preferences)}")
        parts.append("\nBạn muốn giữ các ý này và thay đổi phần nào khi rebuild?")
        return "\n".join(parts)

    # ═══════════════════════════════════════════════════════════════════════════
    # Edit intent detection (rule-based fallback)
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_edit_intent(self, message: str) -> EditIntent:
        text = self._normalize(message)
        action = "answer_question"
        if any(word in text for word in ("tao lai", "lam lai", "xay lai", "rebuild", "reset lich")):
            action = "rebuild_requested"
        elif any(word in text for word in ("thay", "doi", "replace")) and any(word in text for word in ("bang", "thanh")):
            action = "replace_place"
        elif any(word in text for word in ("them", "add", "bo sung", "chen")):
            action = "add_place"
        elif any(word in text for word in ("xoa", "bo ", "remove", "khong di", "bo het")):
            action = "remove_place"
        elif any(word in text for word in ("ngan sach", "budget", "trieu", " tr ", " cu ")):
            action = "change_budget"
        elif any(word in text for word in ("chill", "nhe", "thu tha", "nhieu diem", "di nhieu", "day hon")):
            action = "change_pace"
        elif any(word in text for word in ("gio bat dau", "gio ket thuc", "sang som", "muon hon")):
            action = "change_time_window"
        elif any(word in text for word in ("nhieu hon", "it hon", "it lai", "nhieu len")) and any(word in text for word in ("cafe", "an", "van hoa", "chua")):
            action = "change_distribution"
        elif any(word in text for word in ("tranh", "khong muon", "dung di")):
            action = "avoid_preference"
        elif any(word in text for word in ("thich", "muon an", "uu tien")):
            action = "add_preference"
        return EditIntent(action=action, target=message or None, constraints={}, raw_message=message or "")

    def _needs_edit_followup(self, action: str, intent: EditIntent, message: str) -> Optional[str]:
        """Check if an edit operation needs follow-up to resolve ambiguity."""
        text = self._normalize(message)

        if action == "remove_place":
            # Check if message contains a recognizable target (POI or category)
            has_poi = any(poi_key in text for poi_key in LOCKED_POI_MAP)
            # Use specific category phrases to avoid false matches (e.g. "chỗ" → "cho")
            category_phrases = (
                "quan cafe", "ca phe", "cafe", "chua ", "lang ",
                "cho dong", "quan an", "nha hang", "bun", "com",
                "tat ca", "het", "bo het",
            )
            has_category = any(cat in text for cat in category_phrases)
            if not has_poi and not has_category:
                return "Mình muốn bỏ điểm nào ạ? Cho em biết tên điểm hoặc loại (cafe, chùa, quán ăn...)."

        if action == "replace_place":
            if not intent.target:
                return "Mình muốn thay điểm nào bằng điểm gì ạ?"

        return None

    def _edit_reply(self, intent: EditIntent) -> str:
        replies = {
            "add_place": "Dạ em sẽ tìm địa điểm phù hợp và chèn vào lịch hiện tại.",
            "remove_place": "Dạ em sẽ bỏ địa điểm đó khỏi lịch và tối ưu lại ngày tương ứng.",
            "replace_place": "Dạ em hiểu là mình muốn thay địa điểm trong lịch hiện tại.",
            "change_budget": "Dạ em sẽ cập nhật ngân sách và tối ưu lại lịch nếu cần.",
            "change_pace": "Dạ em sẽ chỉnh nhịp lịch trình theo yêu cầu mới.",
            "change_time_window": "Dạ em sẽ cập nhật khung giờ và tính lại lịch trình.",
            "change_time": "Dạ em sẽ cập nhật khung giờ và tính lại lịch trình.",
            "change_distribution": "Dạ em sẽ điều chỉnh tỉ lệ loại địa điểm theo yêu cầu.",
            "add_preference": "Dạ em sẽ thêm sở thích này vào lịch hiện tại.",
            "avoid_preference": "Dạ em sẽ tránh yêu cầu đó khi tối ưu lại.",
            "rebuild_requested": "Dạ em sẽ tạo lại toàn bộ lịch trình theo yêu cầu mới.",
            "answer_question": "Dạ em đã nhận được câu hỏi/yêu cầu của mình.",
        }
        return replies.get(intent.action, replies["answer_question"])

    # ═══════════════════════════════════════════════════════════════════════════
    # Contract merging
    # ═══════════════════════════════════════════════════════════════════════════

    def _merge_contracts(
        self,
        current: LLMDataContract,
        candidate: Optional[LLMDataContract],
    ) -> LLMDataContract:
        merged = current.model_copy(deep=True)
        if candidate is None:
            return merged

        scalar_fields = [
            "destination",
            "weather_preference",
            "time_slot",
            "trip_duration_hours",
            "vibe",
            "trip_type",
            "preferred_pace",
            "walking_tolerance",
            "group_type",
            "group_size",
            "target_category_distribution",
            "distribution_description",
            "allow_cafe",
            "allow_art",
            "allow_shopping",
            "distribution_locked",
        ]
        for field in scalar_fields:
            value = getattr(candidate, field, None)
            if value is not None:
                setattr(merged, field, value)

        if candidate.num_days and candidate.num_days > 0:
            merged.num_days = candidate.num_days
        if candidate.budget_is_unlimited:
            merged.budget_is_unlimited = True
            merged.budget_max = None
        elif candidate.budget_max is not None:
            merged.budget_max = candidate.budget_max
            merged.budget_is_unlimited = False
        if candidate.radius_km:
            merged.radius_km = candidate.radius_km
        if candidate.time_window is not None and candidate.time_window.start_min is not None:
            merged.time_window = candidate.time_window
        if candidate.estimated_pois is not None:
            merged.estimated_pois = candidate.estimated_pois

        for field in [
            "tags",
            "locked_pois",
            "excluded_pois",
            "food_preferences",
            "avoid_tags",
            "transport_modes",
            "confirmed_fields",
        ]:
            setattr(merged, field, self._merge_unique(getattr(merged, field), getattr(candidate, field)))

        if candidate.hotel_lat is not None:
            merged.hotel_lat = candidate.hotel_lat
        if candidate.hotel_lon is not None:
            merged.hotel_lon = candidate.hotel_lon
        if candidate.hotel_name and candidate.hotel_name != "Hotel":
            merged.hotel_name = candidate.hotel_name
        merged.hotel_confirmed = merged.hotel_confirmed or candidate.hotel_confirmed
        merged.default_hotel_ok = merged.default_hotel_ok or candidate.default_hotel_ok
        return merged

    # ═══════════════════════════════════════════════════════════════════════════
    # Deterministic hints extraction
    # ═══════════════════════════════════════════════════════════════════════════

    def _apply_message_hints(self, contract: LLMDataContract, raw_text: str) -> None:
        if not raw_text:
            return
        text = self._normalize(raw_text)
        raw_lower = raw_text.lower()

        # 1. Location spelling/display name normalization for locked POIs
        if contract.locked_pois:
            normalized_pois = []
            for poi in contract.locked_pois:
                norm_poi = self._normalize(poi)
                matched_name = None
                for key, display_name in LOCKED_POI_MAP.items():
                    if key == norm_poi or key in norm_poi:
                        matched_name = display_name
                        break
                if matched_name:
                    normalized_pois.append(matched_name)
                else:
                    normalized_pois.append(poi)
            contract.locked_pois = normalized_pois

        # 2. (Disabled per request) Pure numerical time range parsing and time slot heuristics
        # Let the LLM decide time_window and time_slot completely, no overrides.

        # 4. Safe interest and preference parsing (prevents "chưa" matching "chùa")
        has_culture = (
            any(word in text for word in ("lich su", "van hoa", "dai noi", "lang tam")) or
            "chùa" in raw_lower or
            "chua thien mu" in text or
            "ngoi chua" in text or
            "di chua" in text
        )
        if has_culture:
            contract.tags = self._merge_unique(contract.tags, ["culture"])

        if any(word in text for word in ("cafe", "ca phe")):
            contract.tags = self._merge_unique(contract.tags, ["cafe"])

        if any(word in text for word in ("an uong", "bun bo", "am thuc", "mon an", "street food", "dac san")):
            contract.tags = self._merge_unique(contract.tags, ["street_food"])

        if any(word in text for word in ("thien nhien", "bien", "song", "nui", "ngoai troi")):
            contract.tags = self._merge_unique(contract.tags, ["nature"])

        if any(word in text for word in ("an chay", "chay", "vegan", "vegetarian", "kieng man")):
            contract.tags = self._merge_unique(contract.tags, ["vegetarian"])
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["vegetarian"])

    def _apply_answer_to_last_question(
        self,
        contract: LLMDataContract,
        raw_text: str,
        last_field: Optional[str],
    ) -> None:
        if not last_field:
            return
        text = self._normalize(raw_text)
        if any(marker in text for marker in NEGATIVE_OR_ANY_MARKERS):
            if last_field == "hotel":
                contract.default_hotel_ok = True
                contract.hotel_confirmed = True

    def _apply_backend_failsafes(self, contract: LLMDataContract, raw_text: str) -> None:
        city_blacklist = {
            "hue", "da nang", "ha noi", "sai gon", "ho chi minh", "tp hcm", "tphcm"
        }
        if contract.locked_pois:
            contract.locked_pois = [
                poi for poi in contract.locked_pois
                if self._normalize(poi).strip() not in city_blacklist
            ]

    # ═══════════════════════════════════════════════════════════════════════════
    # Field validation
    # ═══════════════════════════════════════════════════════════════════════════

    def _critical_missing(self, contract: LLMDataContract) -> List[str]:
        """Critical fields that MUST exist before any generation.

        Without these, the planning pipeline will either fail or produce
        a low-quality result. Budget is critical because it heavily
        influences POI selection and scoring. Time window determines
        which POIs are open and how many can fit in a day.
        """
        missing = []
        if not contract.destination or not self._is_hue(contract.destination):
            missing.append("destination")
        if not contract.num_days or contract.num_days < 1:
            missing.append("num_days")
        if contract.budget_max is None and not contract.budget_is_unlimited:
            missing.append("budget")
        # Daily start/end time — needed for solver scheduling
        has_time_window = (
            (contract.time_window and contract.time_window.start_min is not None)
            or contract.time_slot in {"morning", "afternoon", "evening", "night", "full_day"}
        )
        if not has_time_window:
            missing.append("time_window")
        # User interests — critical for target_category_distribution.
        # Without this, distribution defaults to generic balanced which
        # won't match user intent and biases POI selection.
        has_interests = bool(
            contract.tags
            or contract.trip_type
            or contract.locked_pois
            or contract.food_preferences
        )
        if not has_interests:
            missing.append("interests")
        return missing

    def _missing_fields(self, contract: LLMDataContract) -> List[str]:
        missing = []
        for field in REQUIRED_FIELDS:
            if not self._is_field_collected(contract, field):
                missing.append(field)
        return missing

    def _is_field_collected(self, contract: LLMDataContract, field: str) -> bool:
        confirmed = set(contract.confirmed_fields or [])
        if field in confirmed:
            return True
        if field == "destination":
            return bool(contract.destination and self._is_hue(contract.destination))
        if field == "num_days":
            return contract.num_days is not None and contract.num_days > 0 and "num_days" in confirmed
        if field == "budget":
            return contract.budget_max is not None or contract.budget_is_unlimited
        if field == "interests":
            return bool(contract.tags)
        if field == "pace":
            return bool(contract.preferred_pace)
        if field == "walking":
            return bool(contract.walking_tolerance)
        if field == "food":
            return bool(contract.food_preferences or {"vegetarian", "vegan", "chay"}.intersection(set(contract.tags)))
        if field == "must_visit":
            return bool(contract.locked_pois)
        if field == "avoid":
            return bool(contract.avoid_tags or contract.excluded_pois)
        if field == "time_window":
            # time_slot like "multi_day" or "full_day" is too vague — need actual start/end
            if contract.time_window and contract.time_window.start_min is not None:
                return True
            # Specific time_slot values that imply a clear window
            useful_slots = {"morning", "afternoon", "evening", "night", "full_day"}
            return contract.time_slot in useful_slots
        if field == "transport":
            return bool(contract.transport_modes)
        if field == "group":
            return bool(contract.group_type or contract.group_size)
        if field == "hotel":
            has_specific_hotel = bool(
                (contract.hotel_lat is not None and contract.hotel_lon is not None)
                or (contract.hotel_name and contract.hotel_name != "Hotel")
            )
            return has_specific_hotel or contract.hotel_confirmed or contract.default_hotel_ok
        return False

    def _unsupported_destination_reply(self, contract: LLMDataContract) -> Optional[str]:
        if contract.destination and not self._is_hue(contract.destination):
            return "Dạ hiện tại em chỉ hỗ trợ lên lịch trình tại Huế thôi ạ. Mình có muốn đổi sang khám phá Huế không?"
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # Utility helpers
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _normalize(text: str) -> str:
        """Remove Vietnamese diacritics, lowercase, collapse whitespace."""
        if not text:
            return ""
        text = text.lower().strip()
        # Decompose unicode then remove combining marks
        nfkd = unicodedata.normalize("NFKD", text)
        ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
        # đ → d
        ascii_text = ascii_text.replace("đ", "d").replace("Đ", "d")
        # collapse whitespace
        return re.sub(r"\s+", " ", ascii_text).strip()

    @staticmethod
    def _is_confirmation(text: str) -> bool:
        """Detect user confirmation messages."""
        normalized = text.lower().strip()
        # Remove diacritics for matching
        nfkd = unicodedata.normalize("NFKD", normalized)
        ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
        ascii_text = ascii_text.replace("đ", "d")

        exact_confirms = {
            "ok", "oke", "okie", "duoc", "dc", "di", "di thoi",
            "yes", "co", "u", "uh", "duoc roi", "ok luon",
            "chot", "xac nhan", "tao di", "bat dau di",
            # Vietnamese natural confirmations
            "dung roi", "dung", "chinh xac", "dong y",
            "ok roi", "ro roi", "vang", "oke luon", "di luon",
            "duoc a", "ok a", "duoc luon",
        }
        # Exact match for short messages
        if ascii_text in exact_confirms:
            return True
        # Check for explicit confirmation phrases in longer text
        confirm_phrases = (
            "len lich di", "tao lich di", "chot di", "bat dau di",
            "xac nhan", "ok luon", "duoc roi", "dung roi",
            "dong y", "chinh xac", "di luon", "tao di",
        )
        return any(phrase in ascii_text for phrase in confirm_phrases)

    @staticmethod
    def _is_generate_request(text: str) -> bool:
        """Detect explicit generation requests."""
        normalized = text.lower().strip()
        markers = (
            "tao lich", "tạo lịch", "len lich", "lên lịch",
            "bat dau", "bắt đầu", "generate", "build",
            "lap lich", "lập lịch",
        )
        return any(m in normalized for m in markers)

    @staticmethod
    def _is_hue(destination: str) -> bool:
        """Check if destination refers to Huế."""
        if not destination:
            return False
        normalized = destination.lower().strip()
        return any(h in normalized for h in ("huế", "hue", "hué"))

    @staticmethod
    def _parse_days(text: str) -> Optional[int]:
        """Parse number of days from text like '3 ngay', '2 ngày'."""
        match = re.search(r"(\d+)\s*ngay", text)
        if match:
            days = int(match.group(1))
            return days if 1 <= days <= 14 else None
        return None

    @staticmethod
    def _parse_budget(text: str) -> Optional[float]:
        """Parse budget from text like '1 trieu', '500k', '2tr'."""
        # "X triệu" or "X trieu" or "Xtr"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:trieu|tr\b)", text)
        if match:
            return float(match.group(1)) * 1_000_000
        # "Xk"
        match = re.search(r"(\d+)\s*k\b", text)
        if match:
            return float(match.group(1)) * 1_000
        # Plain number >= 100000 (likely VND)
        match = re.search(r"(\d{6,})", text)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _parse_time_range(text: str) -> Optional[Tuple[int, int]]:
        """Parse time range like '8h-17h' → (480, 1020)."""
        match = re.search(r"(\d{1,2})\s*[hg:]?\s*(?:00)?\s*[-–]\s*(\d{1,2})\s*[hg:]?\s*(?:00)?", text)
        if match:
            start_h = int(match.group(1))
            end_h = int(match.group(2))
            if 0 <= start_h <= 23 and 0 <= end_h <= 23 and start_h < end_h:
                return start_h * 60, end_h * 60
        return None

    @staticmethod
    def _merge_unique(base: Optional[List[str]], additions: Optional[List[str]]) -> List[str]:
        """Merge two lists preserving order, removing duplicates."""
        base = base or []
        additions = additions or []
        seen = set(base)
        result = list(base)
        for item in additions:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _mark_confirmed(contract: LLMDataContract, field: str) -> None:
        if contract.confirmed_fields is None:
            contract.confirmed_fields = []
        if field not in contract.confirmed_fields:
            contract.confirmed_fields.append(field)

    @staticmethod
    def _override_hotel(
        contract: LLMDataContract,
        lat: Optional[float],
        lon: Optional[float],
        name: Optional[str],
    ) -> None:
        if lat is not None:
            contract.hotel_lat = lat
        if lon is not None:
            contract.hotel_lon = lon
        if name and name != "Hotel":
            contract.hotel_name = name

    def _extract_common_locked_pois(self, text: str) -> List[str]:
        """Recognize well-known Huế POIs from normalized text."""
        found = []
        for key, display_name in LOCKED_POI_MAP.items():
            if key in text:
                found.append(display_name)
        return found

    @staticmethod
    def _deduplicate_locked_pois(contract: LLMDataContract) -> None:
        if contract.locked_pois:
            seen = set()
            unique = []
            for poi in contract.locked_pois:
                key = poi.lower().strip()
                if key not in seen:
                    seen.add(key)
                    unique.append(poi)
            contract.locked_pois = unique
