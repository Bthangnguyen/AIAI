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

from app.config import settings as global_settings
from app.schemas.trip import (
    ChatProcessResponse,
    EditIntent,
    LLMDataContract,
    OperationItem,
    TimeWindowSpec,
)
from app.services.distribution_policy import apply_distribution_policy
from app.services.edit_intent_planner import EditIntentPlanner
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# System Prompts
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên trích xuất thông tin từ yêu cầu của khách.
Trả về JSON theo LLMDataContract. Không tự bịa thông tin địa điểm hay rating.

Quy tắc Trích xuất & Suy luận:
1. destination: chỉ hỗ trợ Huế/Hue.
2. Ngân sách (Budget):
   - Trích xuất số tiền tối đa (budget_max) dưới dạng số (float) từ các cụm từ (ví dụ: "1tr5" -> 1500000, "800k" -> 800000, "2 củ" -> 2000000).
   - Nếu ngân sách không giới hạn, đặt budget_is_unlimited = True.
   - Xác định budget.scope ("per_person" nếu đi nhóm và không nói tổng cộng, hoặc "group_total" nếu ghi rõ "tổng nhóm", "chung") và budget.period ("total_trip" hoặc "per_day").
   - normalized budget: Tính toán và điền budget_per_person và group_budget_total tương ứng dựa trên group_size.
3. Khung giờ & Buổi hoạt động (Time Window Specs):
   - Chuyển các buổi hoạt động trong ngày thành time_window (phút tính từ nửa đêm):
     * "buổi sáng" / "sáng" -> time_slot="morning", time_window: {start_min: 480, end_min: 720}
     * "buổi chiều" / "chiều" -> time_slot="afternoon", time_window: {start_min: 780, end_min: 1080}
     * "buổi tối" / "tối" -> time_slot="evening", time_window: {start_min: 1080, end_min: 1320}
     * "cả ngày" -> time_slot="full_day", time_window: {start_min: 480, end_min: 1260}
4. Quyết định Vận hành (Chỗ ở & Phương tiện):
   - Nếu khách đã có chỗ ở ("đã có khách sạn/chỗ ở", "co phong roi") -> lodging_mode="user_has_lodging", has_lodging=True.
   - Nếu khách chưa có hoặc nhờ chọn hộ ("chưa có", "chọn giúp tôi", "cho o em tu chon") -> lodging_mode="system_select_lodging", has_lodging=False.
   - Nếu khách đã có phương tiện ("tự lái", "có xe") -> transport_policy="user_has_transport".
   - Nếu khách chưa có phương tiện ("đi taxi/grab", "chưa có xe", "thuê xe") -> transport_policy="system_suggest_per_leg".
5. target_category_distribution: Phân bổ % chỉ cho 5 nhóm chính: food, culture, nature, nightlife, adventure. Tổng phải bằng đúng 1.0. Các nhóm cafe, art, shopping, wellness không bao giờ được xuất hiện trong phân bổ này!
   - allow_cafe: True nếu khách nhắc đến thích uống cafe, cafe muối, trà quán, quán nước... Mặc định False.
   - allow_art: True nếu khách nhắc đến nghệ thuật, bảo tàng tranh, triển lãm... Mặc định False.
   - allow_shopping: True nếu khách nhắc đến chợ Đông Ba, mua quà, mua sắm... Mặc định False.
   - walking_tolerance: Mức đi bộ ưa thích (low, medium, high).
6. trích xuất các điểm du lịch bắt buộc (locked_pois), điểm loại trừ (excluded_pois) và tags nếu người dùng đề cập.
   - Nếu khách nói "đi kết hợp luôn", "kết hợp", "đi cả ngày", hoặc không nêu rõ sở thích cụ thể -> đặt tags = ["culture", "street_food", "sightseeing"], vibe = "chill", và trip_type = "mixed".
"""

CHAT_PROCESS_SYSTEM_PROMPT = """\
<SYSTEM>
Bạn là LLM INTENT EXTRACTOR cho hệ thống AI-Driven Dynamic Itinerary Optimizer.
Đây là chế độ MULTI-TURN CHAT: bạn nhận conversation_state hiện tại (CURRENT_CONTRACT) và tin nhắn mới (NEW_MESSAGE).

Nhiệm vụ chính:
1. Đọc conversation_state hiện tại (CURRENT_CONTRACT).
2. Đọc tin nhắn mới (NEW_MESSAGE).
3. Trích xuất thông tin mới từ tin nhắn và suy luận các giá trị tương ứng.
4. Gộp (Merge) thông minh với dữ liệu cũ — GIỮ NGUYÊN các dữ liệu cũ nếu tin nhắn mới không sửa đổi hay mâu thuẫn với chúng. Đặc biệt giữ nguyên thông tin tọa độ khách sạn (hotel_lat, hotel_lon) và phương tiện di chuyển một khi đã thu thập, tránh reset trạng thái về unknown.
5. Cập nhật trạng thái đàm thoại (status: "ready" hoặc "clarifying"), giai đoạn (phase: "collecting", "confirming", hoặc "ready") và sinh câu trả lời tự nhiên (reply).
</SYSTEM>

<CORE_RULES>
1. Giữ nguyên dữ liệu cũ nếu tin nhắn không sửa đổi nó. Tránh reset lodging_mode, transport_policy, hotel_lat, hotel_lon về unknown khi người dùng không nhắc lại.
2. Nếu người dùng sửa thông tin cũ, ưu tiên thông tin mới nhất.
3. Không tự ý thiết lập status="ready" nếu chưa thu thập đủ các trường quyết định bắt buộc: destination, num_days, budget (hoặc budget_is_unlimited), time_window/time_slot, lodging_mode, transport_policy, party.size.
4. Nếu tất cả các thông tin đã đầy đủ nhưng người dùng chưa xác nhận bản tóm tắt -> đặt status="clarifying", phase="confirming", requires_confirmation=True.
5. Nếu người dùng xác nhận tóm tắt trước đó (bằng các từ như "ok", "được", "đúng rồi", "ừ", "chốt", "đi thôi", "đồng ý") -> đặt status="ready", phase="ready".
6. Nếu khách nói "đi kết hợp luôn", "kết hợp", "đi cả ngày", hoặc không nêu rõ sở thích cụ thể -> đặt tags = ["culture", "street_food", "sightseeing"], vibe = "chill", và trip_type = "mixed" để tránh lỗi thiếu thông tin chi tiết.
</CORE_RULES>

<NORMALIZATION_GUIDE>
- Ngân sách (Budget):
  * "1tr5" -> budget_max=1500000, budget.amount=1500000
  * "800k" -> budget_max=800000, budget.amount=800000
  * "2 triệu/2tr" -> budget_max=2000000, budget.amount=2000000
  * "2 củ" -> budget_max=2000000, budget.amount=2000000
  * Nếu đi nhóm 3 người và nói "ngân sách 1 triệu" -> budget.scope="per_person", budget.amount=1000000, budget_per_person=1000000, group_budget_total=3000000.
  * Chỉ dùng budget.scope="group_total" khi khách nói rõ "tổng nhóm", "cả nhóm", "chung".
- Khung giờ hoạt động (Time Window):
  * "buổi sáng" -> time_slot="morning", time_window: {start_min: 480, end_min: 720}
  * "buổi chiều" -> time_slot="afternoon", time_window: {start_min: 780, end_min: 1080}
  * "buổi tối" -> time_slot="evening", time_window: {start_min: 1080, end_min: 1320}
  * "cả ngày" -> time_slot="full_day", time_window: {start_min: 480, end_min: 1260}
- Chỗ ở & Phương tiện:
  * "đã có khách sạn/chỗ ở" -> lodging_mode="user_has_lodging", has_lodging=True.
  * "chưa có/chọn giúp tôi" -> lodging_mode="system_select_lodging", has_lodging=False.
  * "tự lái/có xe riêng" -> transport_policy="user_has_transport".
  * "đi taxi/grab/chưa có xe" -> transport_policy="system_suggest_per_leg".
</NORMALIZATION_GUIDE>

<DISTRIBUTION_RULES>
Bạn PHẢI phân bổ target_category_distribution cho MỌI yêu cầu.
1. Chỉ phân bổ cho 5 category keys chính: food, culture, nature, nightlife, adventure. Tổng = 1.0. Các category khác (cafe, art, shopping, wellness) KHÔNG ĐƯỢC PHÂN BỔ % ở đây.
2. Nếu khách thích uống nước, cafe, đi chợ, bảo tàng nghệ thuật -> đặt allow_cafe=True, allow_shopping=True, allow_art=True tương ứng.
   - walking_tolerance: Mức đi bộ ưa thích (low, medium, high).
3. Nếu khách không nói rõ sở thích -> dùng balanced: {food: 0.35, culture: 0.35, nature: 0.20, nightlife: 0.05, adventure: 0.05}.
4. Nếu khách chỉ tập trung vào một danh mục lệch (ví dụ: food: 0.80) mà người dùng không yêu cầu rõ rệt tour chuyên biệt -> hỏi làm rõ để cân bằng, trừ khi khách xác nhận đồng ý đi lệch thì khóa distribution_locked=True.
</DISTRIBUTION_RULES>

<REPLY_GENERATION>
Phát biểu tự nhiên bằng tiếng Việt trong vai trợ lý TripFlow, tối đa 3 câu.
- Nếu thiếu thông tin quan trọng -> đặt status="clarifying", phase="collecting", hỏi tự nhiên 1-2 câu để thu thập.
- Nếu đủ thông tin -> đặt status="clarifying", phase="confirming", tóm tắt lại các điểm hiểu được và hỏi xác nhận: "Dạ em tóm tắt lại trước khi tạo lịch nhé: đi Huế 3 ngày, ngân sách 1 triệu/người... Mình xác nhận tạo lịch trình theo thông tin này chứ ạ?"
- Nếu khách đồng ý/xác nhận -> đặt status="ready", phase="ready", trả lời ngắn gọn xác nhận tạo lịch trình.
</REPLY_GENERATION>
"""

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
    "hotel",
    "group",
    "transport",
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

LOCKED_POI_MAP: dict[str, Any] = {}


LLM_MAX_TOKENS = 6000

# Actions that never trigger itinerary rebuild
_INFO_ACTIONS = frozenset({"info_reply", "answer_question"})

SEMANTIC_EDIT_SYSTEM_PROMPT = """\
<SYSTEM>
You are TripFlow's semantic itinerary edit planner.

The user already has an itinerary draft. Read CURRENT_ITINERARY_SUMMARY,
CURRENT_CONTRACT, HISTORY, and NEW_MESSAGE, then return ChatProcessResponse JSON.
You do not rewrite the itinerary directly. Backend executes your operations.
</SYSTEM>

<OUTPUT_CONTRACT>
- status: "clarifying" for edit previews because backend asks confirmation before applying.
- phase: "editing" for edits, "info" for information answers.
- requires_confirmation: true for edit operations.
- updated_contract: keep the current contract unless the user changes trip-wide settings.
- edit_intent.action: "modify_itinerary" for multi-operation edits, otherwise the operation type.
- edit_intent.operations: atomic OperationItem list.
- pending_edit_plan: include status="pending_confirmation", requires_confirmation=true, operations, affected_days, assistant_reply, raw_message.
</OUTPUT_CONTRACT>

<OPERATION_SCHEMA>
type: add_place | remove_place | replace_place | move_place | swap_places | change_time | change_duration | change_distribution | change_budget | change_pace | rebuild_requested | ask_info
target: existing POI/category to affect. For remove/move/replace, MUST use STOP_ID exactly from CURRENT_ITINERARY_SUMMARY when a matching stop exists. If STOP_ID is missing, use exact stop name.
query: search text for add/replace new POI, e.g. "mon an vat Hue buoi chieu".
target_day: 1-based day number.
target_count: count if user specifies or implies.
target_category: food | cafe | culture | nature | nightlife | adventure.
target_micro_tags: bun_bo | com_hen | che_hue | cafe_muoi | snack | dessert | vegetarian | walking_street | night_market | dai_noi | lang_khai_dinh | lang_minh_mang | lang_huong.
time_window: preferred minutes from midnight.
target_time_min: exact arrival/start minute.
position: before | after | first | last | best_gap.
relative_to: existing stop anchor name.
resolution_strategy: current_itinerary_match | name_search | vector_search_then_suggest.
</OPERATION_SCHEMA>

<RULES>
1. Understand semantics, not keywords. "di bo/pho di bo" means walking_street/nightlife, never remove.
2. Do not rebuild unless user explicitly says rebuild/reset/lam lai het/tao lai.
3. Preserve core/locked intent stops unless user explicitly asks to remove them.
4. Vague remove like "bo quan an nang bung" should target category=food or a non-signature heavy meal; avoid removing requested signature dishes if possible.
5. Vague add like "mon an vat buoi chieu" => add_place query="mon an vat Hue buoi chieu", category=food, target_micro_tags=["snack"], time_window={start_min:840,end_min:1020}.
6. "thay A bang B" => replace_place target=A query=B.
7. "chuyen A sang ngay N" => move_place target=<matching STOP_ID> target_day=N.
8. "sau X" => position="after", relative_to=<matching STOP_ID>. "dau/cuoi lich" => first/last.
9. If user asks a question, return info/ask_info and no edit operations.
10. Handle unpunctuated compound Vietnamese sentences (e.g. "bỏ A thay bằng B bỏ C bỏ D đi") by splitting them into a sequence of distinct atomic operations (e.g. replace_place for A->B, remove_place for C, remove_place for D).
</RULES>

<FEW_SHOT_EXAMPLES>
User: "giảm số lượng điểm bỏ nhà hàng cung đình thay bằng quán bún bò bỏ Đại nội huế bỏ Huế cooking class đi"
JSON operations:
[
  {"type": "replace_place", "target": "Nhà hàng Cung Đình Tịnh Gia Viên", "query": "quán bún bò"},
  {"type": "remove_place", "target": "Đại Nội Huế"},
  {"type": "remove_place", "target": "Hue Citadel Night Tour"},
  {"type": "remove_place", "target": "Hue Cooking Class"}
]
Explanation: Notice how "bỏ Đại Nội Huế" is expanded to remove BOTH the daytime "Đại Nội Huế" and the nighttime "Hue Citadel Night Tour" if both exist, to completely remove the concept as requested by the user. "thay bằng" is translated as a single replace_place operation.
</FEW_SHOT_EXAMPLES>

<REPLY>
Vietnamese, short, preview exactly what will change.
</REPLY>"""

# Actions that are concrete edit operations (frontend should execute)
_ACTIONABLE_EDITS = frozenset({
    "add_place", "remove_place", "replace_place",
    "swap_places", "move_place", "change_time", "change_duration", "change_distribution", "change_budget",
    "change_pace", "add_preference", "avoid_preference",
    "change_time_window",
    "modify_itinerary",
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
        """Compatibility hook for tests that patch the raw Instructor client."""
        if self._client is None:
            self._client = build_llm_client()
        return self._client

    async def _create_completion(self, **kwargs):
        raw_kwargs = dict(kwargs)
        raw_kwargs.pop("operation_name", None)
        raw_kwargs.setdefault("model", global_settings.LLM_MODEL)
        return await self.client.chat.completions.create(**raw_kwargs)

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
        import os
        if os.environ.get("MOCK_LLM") == "True" or os.environ.get("MOCK_LLM") == "true":
            p_lower = user_prompt.lower()
            if "500k" in p_lower and "dai noi" in p_lower:
                contract = LLMDataContract(
                    destination="Huế",
                    budget_max=500000.0,
                    num_days=1,
                    tags=["bun bo", "cuisine", "food"],
                    locked_pois=["Đại Nội Huế"],
                    hotel_name=hotel_name or "Hue Century Riverside Hotel",
                    hotel_lat=hotel_lat or 16.4637,
                    hotel_lon=hotel_lon or 107.5905,
                    hotel_confirmed=True,
                    ready_to_plan=True,
                    preferred_pace="balanced",
                    target_category_distribution={"food": 0.40, "culture": 0.40, "nature": 0.10, "nightlife": 0.05, "adventure": 0.05}
                )
            elif "an chay" in p_lower and "2 ngay" in p_lower:
                contract = LLMDataContract(
                    destination="Huế",
                    budget_max=2000000.0,
                    num_days=2,
                    tags=["vegetarian", "chay"],
                    hotel_name=hotel_name or "Hue Century Riverside Hotel",
                    hotel_lat=hotel_lat or 16.4637,
                    hotel_lon=hotel_lon or 107.5905,
                    hotel_confirmed=True,
                    ready_to_plan=True,
                    preferred_pace="balanced",
                    target_category_distribution={"food": 0.30, "culture": 0.40, "nature": 0.20, "nightlife": 0.05, "adventure": 0.05}
                )
            elif "3 phuong an" in p_lower or "3 ngay o hue" in p_lower:
                contract = LLMDataContract(
                    destination="Huế",
                    budget_max=3000000.0,
                    num_days=3,
                    tags=["general"],
                    hotel_name=hotel_name or "Hue Century Riverside Hotel",
                    hotel_lat=hotel_lat or 16.4637,
                    hotel_lon=hotel_lon or 107.5905,
                    hotel_confirmed=True,
                    ready_to_plan=True,
                    preferred_pace="balanced",
                    target_category_distribution={"food": 0.35, "culture": 0.35, "nature": 0.20, "nightlife": 0.05, "adventure": 0.05}
                )
            else:
                contract = LLMDataContract(
                    destination="Huế",
                    budget_max=1000000.0,
                    num_days=num_days,
                    tags=["general"],
                    hotel_name=hotel_name or "Hue Century Riverside Hotel",
                    hotel_lat=hotel_lat or 16.4637,
                    hotel_lon=hotel_lon or 107.5905,
                    hotel_confirmed=True,
                    ready_to_plan=True,
                    preferred_pace="balanced",
                    target_category_distribution={"food": 0.35, "culture": 0.35, "nature": 0.20, "nightlife": 0.05, "adventure": 0.05}
                )
            return contract

        try:
            contract = await self._create_completion(
                response_model=LLMDataContract,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                operation_name="intent_extraction",
                max_retries=2,
                timeout=60.0,
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            contract = LLMDataContract(num_days=num_days, tags=["general"])
            llm_success = False
        else:
            llm_success = True

        self._override_hotel(contract, hotel_lat, hotel_lon, hotel_name)
        if contract.num_days == 1 and num_days > 1:
            contract.num_days = num_days
            self._mark_confirmed(contract, "num_days")
        if not llm_success:
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
        current_itinerary: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Process one chat turn — dispatches to create or edit flow."""
        import os
        if (os.environ.get("MOCK_LLM") == "True" or os.environ.get("MOCK_LLM") == "true") and not os.environ.get("PYTEST_CURRENT_TEST"):
            contract = current_contract.model_copy(deep=True)
            self._apply_message_hints(contract, message)
            self._apply_backend_failsafes(contract, message)
            contract.ready_to_plan = True
            contract.destination = "Huế"
            if not contract.num_days:
                contract.num_days = 2
            if not contract.budget_max:
                contract.budget_max = 2000000.0
                
            return {
                "status": "ready",
                "reply": f"Dạ em đã ghi nhận thông tin chuyến đi Huế {contract.num_days} ngày của mình ạ. Em sẽ lên lịch trình ngay!",
                "updated_contract": contract,
                "phase": "ready",
                "missing_fields": [],
                "next_question": None,
                "requires_confirmation": False
            }

        clean_message = (message or "").strip()
        if has_draft:
            return await self._process_edit_turn(clean_message, history, current_contract, current_itinerary)
        return await self._process_create_turn(clean_message, history, current_contract)

    # ═══════════════════════════════════════════════════════════════════════════
    # Create mode — LLM-driven follow-up, no hard gate bypass
    # ═══════════════════════════════════════════════════════════════════════════

    async def _process_create_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
        current_itinerary: Optional[Dict[str, Any]] = None,
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
        if current_contract.confirmation_pending and not self._message_changes_confirmed_contract(message):
            contract = current_contract.model_copy(deep=True)
            contract.confirmation_pending = False
            contract.ready_to_plan = True
            contract.decision_state.ready_for_build = True
            contract.decision_state.next_action = "build"
            return self._make_response(
                contract,
                "ready",
                "Dạ đủ thông tin rồi, em bắt đầu tạo lịch trình ngay đây!",
                phase="ready",
                missing_fields=[],
                requires_confirmation=False,
            )

        candidate = None
        response = None
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
            response: ChatProcessResponse = await self._create_completion(
                response_model=ChatProcessResponse,
                messages=[
                    {"role": "system", "content": CHAT_PROCESS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                operation_name="chat_turn",
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
        llm_success = response is not None and candidate is not None
        contract = self._merge_contracts(current_contract, candidate)
        if not llm_success:
            self._apply_message_hints(contract, message)
            self._apply_answer_to_last_question(contract, message, current_contract.last_question_field)
            self._apply_backend_failsafes(contract, message)
            self._enforce_operational_decision_evidence(contract, current_contract, message)
        self._sync_decision_fields(contract)
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

        if contract.num_days and contract.num_days > 7:
            contract.confirmation_pending = False
            contract.ready_to_plan = False
            return self._make_response(
                contract,
                "clarifying",
                "Hiện tại TripFlow hỗ trợ lập lịch tối đa 7 ngày. Mình muốn em lên lịch 7 ngày đầu hay rút chuyến đi xuống tối đa 7 ngày ạ?",
                phase="collecting",
                missing_fields=["num_days"],
                requires_confirmation=False,
            )

        critical_missing = self._critical_missing(contract)

        # ── Step 4: Fully LLM-Driven Dialog State (R1) ──
        if llm_reply:
            if critical_missing:
                contract.confirmation_pending = False
                contract.ready_to_plan = False
                contract.last_question_field = critical_missing[0]
                contract.decision_state.ready_for_confirmation = False
                contract.decision_state.ready_for_build = False
                contract.decision_state.missing_decisions = critical_missing
                contract.decision_state.next_action = "ask_followup"
                return self._make_response(
                    contract, "clarifying", contract.assistant_reply or llm_reply or self._critical_missing_reply(critical_missing),
                    phase="collecting", missing_fields=critical_missing,
                    requires_confirmation=False,
                )

            llm_missing_fields = response.missing_fields if response else []
            blocking_llm_missing = [
                field for field in llm_missing_fields
                if field in REQUIRED_FIELDS and not self._is_field_collected(contract, field)
            ]
            if not blocking_llm_missing and current_contract.confirmation_pending:
                if self._contract_changed_after_confirmation(current_contract, contract):
                    contract.confirmation_pending = True
                    contract.ready_to_plan = False
                    return self._make_response(
                        contract, "clarifying", self._build_confirmation_reply(contract),
                        phase="confirming", missing_fields=[], requires_confirmation=True,
                    )
                contract.confirmation_pending = False
                contract.ready_to_plan = True
                return self._make_response(
                    contract,
                    "ready",
                    "Dạ đủ thông tin rồi, em bắt đầu tạo lịch trình ngay đây!",
                    phase="ready",
                    missing_fields=[],
                    requires_confirmation=False,
                )
            if not llm_ready and not blocking_llm_missing:
                contract.confirmation_pending = True
                contract.ready_to_plan = False
                return self._make_response(
                    contract, "clarifying", self._build_confirmation_reply(contract),
                    phase="confirming", missing_fields=[],
                    requires_confirmation=True,
                )

            status = "ready" if llm_ready else "clarifying"
            if llm_ready:
                if current_contract.confirmation_pending and self._is_confirmation(message):
                    contract.confirmation_pending = False
                    contract.ready_to_plan = True
                else:
                    contract.confirmation_pending = True
                    contract.ready_to_plan = False
                    return self._make_response(
                        contract, "clarifying", self._build_confirmation_reply(contract),
                        phase="confirming", missing_fields=[],
                        requires_confirmation=True,
                    )
            else:
                if llm_phase == "confirming":
                    contract.confirmation_pending = True
                    contract.ready_to_plan = False
                else:
                    contract.confirmation_pending = False
            return self._make_response(
                contract, status, llm_reply, phase=llm_phase,
                missing_fields=response.missing_fields if response else [],
                requires_confirmation=(llm_phase == "confirming"),
            )

        # ── Step 5: Combined Fallback Questions on LLM Failure/Timeout (R2) ──
        if current_contract.confirmation_pending and not critical_missing:
            if self._contract_changed_after_confirmation(current_contract, contract):
                contract.confirmation_pending = True
                contract.ready_to_plan = False
                return self._make_response(
                    contract, "clarifying", self._build_confirmation_reply(contract),
                    phase="confirming", missing_fields=[], requires_confirmation=True,
                )
            contract.confirmation_pending = False
            contract.ready_to_plan = True
            return self._make_response(
                contract,
                "ready",
                "Dạ đủ thông tin rồi, em bắt đầu tạo lịch trình ngay đây!",
                phase="ready",
                missing_fields=[],
                requires_confirmation=False,
            )

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
                    field_labels.update({
                        "hotel": "chỗ ở",
                        "group": "số người đi",
                        "transport": "phương tiện di chuyển",
                    })
                    labels = [field_labels[f] for f in critical_missing if f in field_labels]
                    if len(labels) > 1:
                        fields_str = ", ".join(labels[:-1]) + " và " + labels[-1]
                    elif labels:
                        fields_str = labels[0]
                    else:
                        fields_str = "thông tin còn thiếu"
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
        current_itinerary: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """Edit-mode chat turn.

        Per intent-edit-followup-plan.md:
        - info_reply/answer_question → clarifying (info)
        - rebuild_requested → clarifying + rebuild confirmation
        - Operation missing target → clarifying + follow-up question
        - Actionable operation with enough data → ready + edit_intent
        """
        contract = current_contract.model_copy(deep=True)
        planner = EditIntentPlanner()
        planned_intent = planner.build(message)
        intent = self._detect_edit_intent(message)
        llm_reply = ""

        if message:
            try:
                history_str = "\n".join([f"{h['role']}: {h['content']}" for h in history[-8:]])
                itinerary_summary = self._summarize_itinerary_for_edit(current_itinerary)
                prompt = (
                    f"CURRENT_CONTRACT:\n{contract.model_dump_json(indent=2)}\n\n"
                    f"CURRENT_ITINERARY_SUMMARY:\n{itinerary_summary}\n\n"
                    f"HISTORY:\n{history_str}\n\n"
                    f"NEW_MESSAGE:\n{message}"
                )
                response: ChatProcessResponse = await self._create_completion(
                    response_model=ChatProcessResponse,
                    messages=[
                        {"role": "system", "content": SEMANTIC_EDIT_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    operation_name="edit_intent",
                    max_tokens=LLM_MAX_TOKENS,
                    max_retries=2,
                    timeout=60.0,
                )
                if response.updated_contract:
                    contract = self._merge_contracts(contract, response.updated_contract)
                if response.edit_intent and response.edit_intent.operations:
                    intent = response.edit_intent
                    if not intent.raw_message:
                        intent.raw_message = message
                elif planned_intent.operations:
                    intent = planned_intent
                llm_reply = response.reply or ""
                logger.info(
                    f"Edit turn OK — action={intent.action}, "
                    f"target={intent.target}, reply_len={len(llm_reply)}"
                )
            except Exception as e:
                logger.warning(f"Edit-intent LLM classification failed, using rules: {e}")
                if planned_intent.operations:
                    intent = planned_intent

        llm_success = message and 'response' in locals() and response is not None
        if not llm_success:
            self._apply_message_hints(contract, message)
            self._apply_backend_failsafes(contract, message)
        self._deduplicate_locked_pois(contract)

        action = intent.action
        pending_edit_plan = None
        if intent.operations:
            pending_edit_plan = planner.pending_plan(message, intent.operations)

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
            pending_edit_plan = {
                "operations": [{"type": "rebuild_requested"}],
                "assistant_reply": reply
            }
            return self._make_response(
                contract, "clarifying", reply, phase="editing",
                edit_intent=intent, pending_edit_plan=pending_edit_plan,
                requires_confirmation=True
            )

        # ── Route 3: Operation missing target → clarifying + follow-up ──
        followup = self._needs_edit_followup(action, intent, message)
        if followup:
            reply = llm_reply or followup
            return self._make_response(contract, "clarifying", reply, phase="editing",
                                       edit_intent=intent)

        # ── Route 4: Actionable operation with enough data → ready ──
        if action in _ACTIONABLE_EDITS:
            # Let the LLM naturally decide if it is already confirmed (ready) or still needs confirmation (clarifying)
            response_obj = locals().get('response')
            status = getattr(response_obj, 'status', 'clarifying') if response_obj else "clarifying"
            req_confirm = getattr(response_obj, 'requires_confirmation', True) if response_obj else True
            
            # Enforce consistency: if status is clarifying, it MUST require confirmation
            if status == "clarifying":
                req_confirm = True

            # Helper fallback: if our robust _is_confirmation helper detects confirmation, set to ready
            if self._is_confirmation(message):
                status = "ready"
                req_confirm = False

            reply = llm_reply or (pending_edit_plan or {}).get("assistant_reply") or self._edit_reply(intent)
            logger.info(f"Edit turn result: action={action}, status={status}, requires_confirmation={req_confirm}")
            return self._make_response(
                contract, status, reply, phase="editing",
                edit_intent=intent, pending_edit_plan=pending_edit_plan if req_confirm else None,
                requires_confirmation=req_confirm,
            )

        # ── Fallback: unknown action → clarifying ──
        reply = llm_reply or self._edit_reply(intent)
        return self._make_response(contract, "clarifying", reply, phase="editing",
                                   edit_intent=intent)

    # ═══════════════════════════════════════════════════════════════════════════
    # Response builders
    # ═══════════════════════════════════════════════════════════════════════════

    def _summarize_itinerary_for_edit(self, itinerary: Optional[Dict[str, Any]]) -> str:
        """Compact draft context for the edit LLM."""
        if not itinerary:
            return "No itinerary draft provided."

        lines: list[str] = []
        for day_idx, day in enumerate((itinerary or {}).get("days", [])[:10]):
            display_day = day.get("day_number") or day.get("day") or int(day.get("day_index", day_idx)) + 1
            lines.append(
                f"Day {display_day} start={day.get('start_time_min')} end={day.get('end_time_min')}"
            )
            for stop_idx, stop in enumerate(day.get("stops", [])[:12], start=1):
                poi_id = str(stop.get("poi_id") or stop.get("id") or "")
                name = stop.get("poi_name") or stop.get("name") or "Unknown"
                cat = stop.get("category") or "general"
                arr = stop.get("arrival_time_min")
                dep = stop.get("departure_time_min")
                tags = stop.get("tags") or []
                tag_text = ",".join(str(t) for t in tags[:8])
                desc = (stop.get("description") or "")[:120].replace("\n", " ")
                lines.append(
                    f"{stop_idx}. STOP_ID={poi_id} | NAME={name} | CATEGORY={cat} | "
                    f"TIME={arr}-{dep} | TAGS=[{tag_text}] | DESC={desc}"
                )
        return "\n".join(lines) if lines else "Itinerary has no stops."

    def _make_response(
        self,
        contract: LLMDataContract,
        status: str,
        reply: str,
        phase: str = "collecting",
        missing_fields: Optional[List[str]] = None,
        edit_intent: Optional[EditIntent] = None,
        pending_edit_plan: Optional[Dict[str, Any]] = None,
        requires_confirmation: Optional[bool] = None,
    ) -> Dict:
        contract.assistant_reply = reply
        contract.follow_up_questions = [reply] if status == "clarifying" and phase == "collecting" else []
        contract.decision_state.missing_decisions = missing_fields or []
        contract.decision_state.ready_for_confirmation = status == "clarifying" and phase == "confirming"
        contract.decision_state.ready_for_build = status == "ready" or phase == "ready"
        if status == "ready" or phase == "ready":
            contract.decision_state.next_action = "build"
        elif phase == "confirming":
            contract.decision_state.next_action = "confirm_before_build"
        else:
            contract.decision_state.next_action = "ask_followup"
        return {
            "status": status,
            "reply": reply,
            "updated_contract": contract,
            "phase": phase,
            "missing_fields": missing_fields or [],
            "next_question": reply if status == "clarifying" else None,
            "requires_confirmation": (phase == "confirming") if requires_confirmation is None else requires_confirmation,
            "edit_intent": edit_intent,
            "pending_edit_plan": pending_edit_plan,
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
        if contract.transport_plan.availability == "needs_transport":
            transport = "em sẽ gợi ý theo từng chặng"
        elif contract.transport_plan.availability == "has_own_transport":
            transport = "phương tiện riêng"
        else:
            transport = ", ".join(contract.transport_modes) if contract.transport_modes else "taxi + walking"
        group = f"{contract.group_size} người" if contract.group_size else (contract.group_type or "chưa rõ")
        if contract.has_lodging is False:
            hotel = "chỗ nghỉ em sẽ chọn từ dữ liệu"
        elif contract.has_lodging and not (contract.hotel_lat and contract.hotel_lon):
            hotel = "chỗ ở bạn sẽ chọn trên bản đồ"
        elif contract.hotel_name and contract.hotel_name != "Hotel":
            hotel = contract.hotel_name
        else:
            hotel = "khách sạn trung tâm Huế mặc định"
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
        elif any(word in text for word in ("doi cho", "swap")):
            action = "swap_places"
        elif any(word in text for word in ("chuyen", "dua ")) or ("sang" in text and any(poi_key in text for poi_key in LOCKED_POI_MAP)):
            action = "move_place"
        elif any(word in text for word in ("tang len", "rut con", "them mot ngay", "bot ngay")):
            action = "change_duration"
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
            has_target = any(op.target for op in (intent.operations or []) if op.type == "remove_place")
            has_poi = any(poi_key in text for poi_key in LOCKED_POI_MAP) or bool(intent.target) or has_target
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
            "budget_scope",
            "time_slot",
            "trip_duration_hours",
            "vibe",
            "trip_type",
            "preferred_pace",
            "walking_tolerance",
            "has_lodging",
            "lodging_mode",
            "lodging_budget_per_night",
            "cost_priority",
            "transport_policy",
            "group_type",
            "group_size",
            "preference_mode",
            "assistant_reply",
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
            if candidate.num_days != 1 or "num_days" in (candidate.confirmed_fields or []) or merged.num_days == 1:
                merged.num_days = candidate.num_days
        if candidate.budget_is_unlimited:
            merged.budget_is_unlimited = True
            merged.budget_max = None
        elif candidate.budget_max is not None:
            merged.budget_max = candidate.budget_max
            merged.budget_is_unlimited = False
        if candidate.radius_km:
            if candidate.radius_km != 10.0 or "radius" in (candidate.confirmed_fields or []) or merged.radius_km == 10.0:
                merged.radius_km = candidate.radius_km
        if candidate.time_window is not None and candidate.time_window.start_min is not None:
            merged.time_window = candidate.time_window
        if candidate.estimated_pois is not None:
            merged.estimated_pois = candidate.estimated_pois
        if getattr(candidate, "lodging_selection", None):
            current_selection = merged.lodging_selection.model_dump()
            next_selection = candidate.lodging_selection.model_dump()
            current_selection.update({k: v for k, v in next_selection.items() if v not in (None, "", "unknown", "none")})
            merged.lodging_selection = type(merged.lodging_selection)(**current_selection)
        if getattr(candidate, "transport_plan", None):
            current_plan = merged.transport_plan.model_dump()
            next_plan = candidate.transport_plan.model_dump()
            current_plan.update({k: v for k, v in next_plan.items() if v not in (None, "", "unknown")})
            merged.transport_plan = type(merged.transport_plan)(**current_plan)
        if getattr(candidate, "party", None):
            current_party = merged.party.model_dump()
            next_party = candidate.party.model_dump()
            current_party.update({k: v for k, v in next_party.items() if v not in (None, "", "unknown")})
            merged.party = type(merged.party)(**current_party)
        if getattr(candidate, "decision_state", None):
            current_decision = merged.decision_state.model_dump()
            next_decision = candidate.decision_state.model_dump()
            current_decision.update({k: v for k, v in next_decision.items() if v not in (None, "", "unknown", [])})
            merged.decision_state = type(merged.decision_state)(**current_decision)

        for field in [
            "tags",
            "locked_pois",
            "excluded_pois",
            "food_preferences",
            "avoid_tags",
            "lodging_preference",
            "transport_modes",
            "confirmed_fields",
            "follow_up_questions",
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
        ascii_text = (
            unicodedata.normalize("NFKD", raw_text.replace("đ", "d").replace("Đ", "D"))
            .encode("ascii", "ignore")
            .decode("ascii")
            .lower()
        )

        if re.search(r"\bhu(?:e|\?)(?:\b|\s|$|,|\.)", text):
            contract.destination = "Huế"
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["destination"])

        parsed_days = self._parse_days(text)
        if parsed_days:
            contract.num_days = parsed_days
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["num_days"])

        parsed_budget = self._parse_budget(text)
        if parsed_budget is not None:
            contract.budget_max = parsed_budget
            contract.budget_is_unlimited = False
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["budget"])

        parsed_time_range = self._parse_time_range(text)
        if parsed_time_range is not None:
            start_min, end_min = parsed_time_range
            contract.time_window = TimeWindowSpec(start_min=start_min, end_min=end_min)
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["time_window"])

        has_hotel_text = "khach san" in text or "kh?ch s?n" in text or "cho o" in text or "ch? ?" in text
        has_existing_lodging = any(phrase in text for phrase in (
            "da co khach san", "co khach san roi", "da co cho o", "co cho o roi", "co cho o", "co phong roi",
            "co san khach san", "co san cho o", "khach san co san", "cho o co san", "phong co san",
            "khach san co roi", "cho o co roi", "phong co roi", "khach san san roi", "cho o san roi"
        ))
        needs_lodging = (
            any(phrase in text for phrase in (
                "chua co khach san", "chua co cho o", "can khach san", "tim khach san", "can cho o", "tim cho o",
                "ban chon khach san", "ban chon cho o", "em chon khach san", "em chon cho o", "he thong chon",
                "chon giup toi", "chon ho", "tim ho", "dat ho"
            ))
            or (has_hotel_text and any(phrase in text for phrase in (
                "chua co", "can ", "tim ", "tu chon", "ban chon", "ban tu chon", "tuy ban", "ban quyet",
                "chon giup", "chon ho", "tim ho"
            )))
        )
        if has_existing_lodging:
            contract.has_lodging = True
            contract.lodging_mode = "user_has_lodging"
            contract.hotel_confirmed = True
            contract.lodging_selection.status = "user_has_lodging"
            contract.lodging_selection.selection_method = "map_pin"
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["hotel"])
        elif needs_lodging:
            contract.has_lodging = False
            contract.lodging_mode = "system_select_lodging"
            contract.lodging_selection.status = "needs_lodging"
            contract.hotel_confirmed = True
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["hotel"])

        if any(phrase in text for phrase in ("chua gom khach san", "khong gom khach san", "khong bao gom khach san", "chua bao gom khach san")):
            contract.budget_scope = "excludes_hotel"
        elif any(phrase in text for phrase in ("gom khach san", "bao gom khach san", "ca khach san", "bao tron khach san")) or (
            has_hotel_text and any(phrase in text for phrase in ("bao gom", "bao g?m", "gom", "g?m", "ca "))
        ):
            contract.budget_scope = "includes_hotel"
        elif parsed_budget is not None and contract.budget_scope == "unknown":
            contract.budget_scope = "total_trip"

        if any(word in text for word in ("homestay", "nha nghi", "hostel")):
            contract.lodging_preference = self._merge_unique(contract.lodging_preference, ["budget", "homestay"])
            contract.cost_priority = contract.cost_priority or "save_money"
        if any(word in text for word in ("resort", "sang", "premium", "cao cap")):
            contract.lodging_preference = self._merge_unique(contract.lodging_preference, ["premium"])
            contract.cost_priority = contract.cost_priority or "premium"
        if any(word in text for word in ("trung tam", "gan trung tam")):
            contract.lodging_preference = self._merge_unique(contract.lodging_preference, ["central"])

        parsed_group_size = re.search(r"(\d+)\s*(?:nguoi\b|ng\b|ban\b|khach\b)", text)
        if parsed_group_size:
            contract.group_size = int(parsed_group_size.group(1))
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["group"])
        if any(phrase in text for phrase in ("mot minh", "di mot minh", "solo", "mot nguoi")):
            contract.group_size = 1
            contract.group_type = "solo"
            contract.party.size = 1
            contract.party.type = "solo"
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["group"])

        if parsed_budget is not None:
            group_total_words = ("tong nhom", "ca nhom", "budget chung", "ngan sach chung", "tong budget nhom")
            per_person_words = ("moi nguoi", "tren nguoi", "mot nguoi", "nguoi mot", "per person")
            party_size = int(contract.group_size or contract.party.size or 1)
            if any(phrase in text for phrase in group_total_words):
                contract.budget_unit_scope = "group_total"
                contract.budget.scope = "group_total"
                contract.budget_scope_evidence = "User explicitly used group-total budget wording."
            elif any(phrase in text for phrase in per_person_words) or party_size > 1:
                contract.budget_unit_scope = "per_person"
                contract.budget.scope = "per_person"
                contract.budget_scope_evidence = "User gave a group size and did not use group-total wording."
            else:
                contract.budget_unit_scope = "group_total"
                contract.budget.scope = "group_total"
                contract.budget_scope_evidence = "Solo or no group size; per-person and group-total are equivalent."
            contract.budget.amount = parsed_budget
            contract.budget.period = "per_day" if "moi ngay" in text or "theo ngay" in text else "total_trip"
            contract.budget_period = contract.budget.period
            if contract.budget_unit_scope == "per_person":
                contract.budget_per_person = float(parsed_budget)
                contract.group_budget_total = float(parsed_budget) * max(1, party_size)
            else:
                contract.group_budget_total = float(parsed_budget)
                contract.budget_per_person = float(parsed_budget) / max(1, party_size)

        own_transport_phrases = (
            "co xe", "co xe may", "co o to", "tu lai", "xe rieng",
            "co phuong tien", "da co phuong tien", "nguoi cho",
        )
        needs_transport_phrases = (
            "chua co xe", "khong co xe", "chua co phuong tien", "khong co phuong tien",
            "chua co phuong tien rieng", "khong co phuong tien rieng", "can xe", "can phuong tien",
            "bat grab", "di taxi", "goi xe", "thue xe",
        )
        if any(phrase in text for phrase in needs_transport_phrases):
            contract.transport_policy = "system_suggest_per_leg"
            contract.transport_plan.availability = "needs_transport"
            if contract.transport_plan.cost_policy == "time_only":
                contract.transport_plan.cost_policy = "per_leg"
            contract.transport_plan.reason = contract.transport_plan.reason or "User needs transport suggestions."
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["transport"])
        elif any(phrase in text for phrase in own_transport_phrases):
            contract.transport_policy = "user_has_transport"
            contract.transport_plan.availability = "has_own_transport"
            contract.transport_plan.cost_policy = "time_only"
            contract.transport_plan.reason = contract.transport_plan.reason or "User said they already have transport."
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["transport"])

        if any(word in text for word in ("xe may", "motorbike")):
            contract.transport_modes = self._merge_unique(contract.transport_modes, ["motorbike"])
            if contract.transport_plan.primary_mode in ("mixed", "walking"):
                contract.transport_plan.primary_mode = "motorbike"
        if "taxi" in text or "o to" in text or "oto" in text or "car" in text:
            contract.transport_modes = self._merge_unique(contract.transport_modes, ["taxi"])
            contract.transport_plan.primary_mode = "taxi"
        if "grab" in text or "goi xe" in text:
            contract.transport_modes = self._merge_unique(contract.transport_modes, ["motorbike_hailing"])
            contract.transport_plan.primary_mode = "motorbike_hailing"
        if "thue xe" in text:
            contract.transport_plan.cost_policy = "daily_rental"

        # 1. (Disabled) Spelling normalization for locked POIs is removed to disable background locking.


        # 2. (Disabled per request) Pure numerical time range parsing and time slot heuristics
        # Let the LLM decide time_window and time_slot completely, no overrides.
        if "dai noi" in ascii_text:
            contract.tags = self._merge_unique(contract.tags, ["culture", "dai_noi"])
            contract.locked_pois = self._merge_unique(contract.locked_pois, ["\u0110\u1ea1i N\u1ed9i Hu\u1ebf"])

        if "bun bo" in ascii_text:
            contract.tags = self._merge_unique(contract.tags, ["bun_bo", "food"])
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["bun_bo"])

        if "cafe muoi" in ascii_text or "ca phe muoi" in ascii_text:
            contract.tags = self._merge_unique(contract.tags, ["cafe_muoi", "cafe"])
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["cafe_muoi"])
            contract.allow_cafe = True


        # 4. Safe interest and preference parsing (prevents "chưa" matching "chùa")
        has_culture = (
            any(word in text for word in ("lich su", "van hoa", "v?n h?a", "dai noi", "lang tam")) or
            "chùa" in raw_lower or
            "chua thien mu" in text or
            "ngoi chua" in text or
            "di chua" in text
        )
        if has_culture:
            contract.tags = self._merge_unique(contract.tags, ["culture"])

        if any(word in text for word in ("cafe", "ca phe")):
            contract.tags = self._merge_unique(contract.tags, ["cafe"])
        if any(word in text for word in ("cafe muoi", "ca phe muoi")):
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["cafe_muoi"])

        if any(word in text for word in ("an uong", "bun bo", "am thuc", "?m th?c", "mon an", "street food", "food tour", "dac san")):
            contract.tags = self._merge_unique(contract.tags, ["street_food"])
            if "food tour" in text:
                contract.trip_type = contract.trip_type or "food_tour"
        if any(word in text for word in ("che hue", "che ")):
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["che_hue"])

        if any(word in text for word in ("thien nhien", "bien", "song", "nui", "ngoai troi")):
            contract.tags = self._merge_unique(contract.tags, ["nature"])

        if any(word in text for word in ("an chay", "chay", "vegan", "vegetarian", "kieng man")):
            contract.tags = self._merge_unique(contract.tags, ["vegetarian"])
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["vegetarian"])

        if any(phrase in text for phrase in (
            "khong co so thich", "so thich khong co", "khong co gi dac biet",
            "khong gi dac biet", "khong dac biet", "khong yeu cau dac biet",
            "khong co yeu cau dac biet", "gi cung duoc", "tuy ban sap xep",
        )):
            if not contract.tags:
                contract.tags = ["general"]
            contract.preference_mode = "no_preference"
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["interests"])

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
        self._apply_time_slot_failsafe(contract, raw_text)
        apply_distribution_policy(contract, raw_text)

    def _apply_time_slot_failsafe(self, contract: LLMDataContract, raw_text: str) -> None:
        """Fill deterministic time windows for explicit Vietnamese day parts."""
        text = self._normalize(raw_text or "")
        existing = None
        if contract.time_window and contract.time_window.start_min is not None and contract.time_window.end_min is not None:
            existing = (int(contract.time_window.start_min), int(contract.time_window.end_min))
        if existing and "time_window" in (contract.confirmed_fields or []):
            return

        generic_windows = {(480, 1260), (480, 1320), (0, 1440)}
        slot_windows = [
            (("buoi chieu", "chieu", "afternoon"), "afternoon", 780, 1080),
            (("ca ngay", "full day", "full_day"), "full_day", 480, 1260),
            (("buoi sang", "sang", "morning"), "morning", 480, 720),
            (("buoi toi", "evening", "night"), "evening", 1080, 1320),
        ]
        for keywords, slot, start, end in slot_windows:
            if any(keyword in text for keyword in keywords):
                if existing and existing not in generic_windows and contract.time_slot != slot:
                    return
                contract.time_slot = slot
                if not existing or existing in generic_windows or (slot == "afternoon" and existing[0] < 780):
                    contract.time_window = TimeWindowSpec(start_min=start, end_min=end)
                if "time_window" not in (contract.confirmed_fields or []):
                    contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["time_window"])
                return

    def _sync_decision_fields(self, contract: LLMDataContract) -> None:
        """Keep the new LLM decision-state fields compatible with legacy planner fields."""
        if contract.party.size is not None:
            contract.group_size = contract.party.size
        elif contract.group_size is not None:
            contract.party.size = contract.group_size

        if contract.party.type and contract.party.type != "unknown":
            contract.group_type = contract.party.type
        elif contract.group_type:
            contract.party.type = contract.group_type

        party_size = max(1, int(contract.group_size or contract.party.size or 1))
        if contract.budget.amount is None and contract.budget_max is not None:
            contract.budget.amount = contract.budget_max
        valid_unit_scopes = {"per_person", "group_total"}
        if contract.budget.scope not in valid_unit_scopes:
            contract.budget.scope = "unknown"
        if contract.budget_unit_scope not in valid_unit_scopes:
            contract.budget_unit_scope = "unknown"

        if contract.budget.scope != "unknown" and contract.budget_unit_scope == "unknown":
            contract.budget_unit_scope = contract.budget.scope
        elif contract.budget_unit_scope != "unknown":
            contract.budget.scope = contract.budget_unit_scope

        evidence = (contract.budget_scope_evidence or "").lower()
        should_reinterpret_as_per_person = (
            party_size > 1
            and contract.budget_max is not None
            and contract.budget_unit_scope == "group_total"
            and "explicit" not in evidence
        )
        if should_reinterpret_as_per_person:
            contract.budget_unit_scope = "per_person"
            contract.budget.scope = "per_person"
            contract.budget_scope_evidence = "Group size was provided later; no explicit group-total wording, so budget is interpreted per person."
        elif contract.budget_unit_scope == "unknown" and contract.budget_max is not None:
            contract.budget_unit_scope = "per_person" if party_size > 1 else "group_total"
            contract.budget.scope = contract.budget_unit_scope
            contract.budget_scope_evidence = contract.budget_scope_evidence or "Semantic default based on party size."
        if contract.budget.period and contract.budget_period == "total_trip":
            contract.budget_period = contract.budget.period
        else:
            contract.budget.period = contract.budget_period
        if contract.budget_max is not None:
            if contract.budget_unit_scope == "per_person":
                contract.budget_per_person = float(contract.budget_max)
                contract.group_budget_total = float(contract.budget_max) * party_size
            else:
                contract.group_budget_total = float(contract.budget_max)
                contract.budget_per_person = float(contract.budget_max) / party_size

        if contract.lodging_mode == "user_has_lodging":
            contract.has_lodging = True
            contract.hotel_confirmed = True
            contract.lodging_selection.status = "user_has_lodging"
            if contract.lodging_selection.selection_method == "none":
                contract.lodging_selection.selection_method = "map_pin"
        elif contract.lodging_mode in {"system_select_lodging", "not_needed"}:
            contract.has_lodging = False
            contract.hotel_confirmed = True
            if contract.lodging_mode == "system_select_lodging":
                contract.lodging_selection.status = "needs_lodging"

        if contract.has_lodging is True and contract.lodging_mode == "unknown":
            contract.lodging_mode = "user_has_lodging"
        elif contract.has_lodging is False and contract.lodging_mode == "unknown":
            contract.lodging_mode = "system_select_lodging"
        if contract.hotel_lat is not None and contract.hotel_lon is not None:
            contract.hotel_confirmed = True
            contract.lodging_selection.lat = contract.hotel_lat
            contract.lodging_selection.lon = contract.hotel_lon
            if contract.lodging_selection.name is None:
                contract.lodging_selection.name = contract.hotel_name or "Chỗ ở của bạn"

        if contract.transport_policy == "user_has_transport":
            contract.transport_plan.availability = "has_own_transport"
            contract.transport_plan.cost_policy = "time_only"
        elif contract.transport_policy == "system_suggest_per_leg":
            contract.transport_plan.availability = "needs_transport"
            if contract.transport_plan.cost_policy == "time_only":
                contract.transport_plan.cost_policy = "per_leg"
        elif contract.transport_policy == "walking_only":
            contract.transport_plan.availability = "has_own_transport"
            contract.transport_plan.primary_mode = "walking"
            contract.transport_plan.cost_policy = "none"

        if contract.transport_plan.availability == "has_own_transport" and contract.transport_policy == "unknown":
            contract.transport_policy = "user_has_transport"
        elif contract.transport_plan.availability == "needs_transport" and contract.transport_policy == "unknown":
            contract.transport_policy = "system_suggest_per_leg"

        if contract.preference_mode == "no_preference":
            if not contract.tags:
                contract.tags = ["general"]
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["interests"])
        elif contract.tags and contract.preference_mode == "unknown":
            contract.preference_mode = "specific" if contract.tags != ["general"] else "no_preference"

    # ═══════════════════════════════════════════════════════════════════════════
    # Field validation
    # ═══════════════════════════════════════════════════════════════════════════

    def _enforce_operational_decision_evidence(
        self,
        contract: LLMDataContract,
        current_contract: LLMDataContract,
        raw_text: str,
    ) -> None:
        """Keep generic no-preference answers from filling lodging/transport."""
        has_lodging_evidence = self._mentions_lodging_decision(raw_text)
        has_transport_evidence = self._mentions_transport_decision(raw_text)

        if has_lodging_evidence and self._is_field_collected(contract, "hotel"):
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["hotel"])
        elif "hotel" not in set(current_contract.confirmed_fields or []):
            has_specific_hotel = bool(
                (current_contract.hotel_lat is not None and current_contract.hotel_lon is not None)
                or (current_contract.hotel_name and current_contract.hotel_name != "Hotel")
            )
            if not has_specific_hotel:
                contract.lodging_mode = "unknown"
                contract.has_lodging = None
                contract.hotel_confirmed = False
                contract.default_hotel_ok = False
                if contract.hotel_name == "Hotel":
                    contract.hotel_lat = None
                    contract.hotel_lon = None
                contract.lodging_selection.status = "unknown"
                contract.lodging_selection.selection_method = "none"
                contract.lodging_selection.hotel_poi_id = None
                if contract.lodging_selection.name == "Hotel":
                    contract.lodging_selection.name = None

        if has_transport_evidence and self._is_field_collected(contract, "transport"):
            contract.confirmed_fields = self._merge_unique(contract.confirmed_fields, ["transport"])
        elif "transport" not in set(current_contract.confirmed_fields or []):
            contract.transport_policy = "unknown"
            contract.transport_modes = []
            contract.transport_plan.availability = "unknown"
            contract.transport_plan.reason = None

    def _mentions_lodging_decision(self, raw_text: str) -> bool:
        text = self._normalize(raw_text or "")
        markers = (
            "cho o", "khach san", "hotel", "homestay", "nha nghi", "hostel",
            "resort", "nghi dem", "qua dem", "phong", "luu tru",
        )
        return any(marker in text for marker in markers)

    def _mentions_transport_decision(self, raw_text: str) -> bool:
        text = self._normalize(raw_text or "")
        markers = (
            "phuong tien", "taxi", "grab", "gojek",
            "di bo", "thue xe", "tu lai", "xe rieng", "co xe",
            "khong co xe", "chua co xe", "motorbike", "car",
        )
        if any(marker in text for marker in markers):
            return True
        return bool(re.search(r"\b(xe|be)\b", text))

    def _message_changes_confirmed_contract(self, raw_text: str) -> bool:
        text = self._normalize(raw_text or "")
        if not text:
            return False
        if self._mentions_lodging_decision(raw_text) or self._mentions_transport_decision(raw_text):
            return True
        change_markers = (
            "nhung", "doi", "sua", "them", "bot", "xoa", "bo ", "thay",
            "chuyen", "khong", "chua", "khoan", "dung lai", "huy",
            "budget", "ngan sach", "trieu", "k ", "vnd", "ngay",
            "gio", "sang", "chieu", "toi", "dem", "nguoi", "nhom",
            "di mot minh", "solo", "van hoa", "am thuc", "food",
            "cafe", "thien nhien", "chill", "intense", "khong thich",
        )
        if any(marker in text for marker in change_markers):
            return True
        return bool(re.search(r"\d+\s*(ngay|h|gio|tr|trieu|k|nguoi)", text))

    def _contract_changed_after_confirmation(
        self,
        current_contract: LLMDataContract,
        new_contract: LLMDataContract,
    ) -> bool:
        return self._confirmation_snapshot(current_contract) != self._confirmation_snapshot(new_contract)

    def _confirmation_snapshot(self, contract: LLMDataContract) -> Tuple[Any, ...]:
        time_window = None
        if contract.time_window:
            time_window = (contract.time_window.start_min, contract.time_window.end_min)
        party_size = contract.party.size or contract.group_size
        party_type = contract.party.type if contract.party.type != "unknown" else (contract.group_type or "unknown")
        budget_unit_scope = contract.budget_unit_scope
        if budget_unit_scope == "unknown" and contract.budget_max is not None:
            budget_unit_scope = "per_person" if (party_size or 1) > 1 else "group_total"
        preference_mode = contract.preference_mode
        if preference_mode == "unknown" and contract.tags:
            preference_mode = "specific" if contract.tags != ["general"] else "no_preference"
        hotel_location = None
        if contract.hotel_lat is not None and contract.hotel_lon is not None:
            hotel_location = (round(float(contract.hotel_lat), 5), round(float(contract.hotel_lon), 5))
        return (
            self._normalize(contract.destination or ""),
            contract.num_days,
            contract.budget_max,
            contract.budget_is_unlimited,
            budget_unit_scope,
            contract.budget_period,
            time_window,
            contract.time_slot,
            preference_mode,
            tuple(sorted(contract.tags or [])),
            tuple(sorted(contract.locked_pois or [])),
            tuple(sorted(contract.excluded_pois or [])),
            tuple(sorted(contract.avoid_tags or [])),
            contract.lodging_mode,
            contract.has_lodging,
            hotel_location,
            contract.transport_policy,
            contract.transport_plan.availability,
            tuple(sorted(contract.transport_modes or [])),
            party_size,
            party_type,
        )

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
        # User preference decision. "No preference" is a valid answer and
        # should not trigger repeated follow-up questions.
        has_interests = bool(
            contract.preference_mode in {"specific", "balanced", "no_preference"}
            or contract.tags
            or contract.trip_type
            or contract.locked_pois
            or contract.food_preferences
        )
        if not has_interests:
            missing.append("interests")
        for field in ("hotel", "group", "transport"):
            if not self._is_field_collected(contract, field):
                missing.append(field)
        return missing

    def _critical_missing_reply(self, critical_missing: List[str]) -> str:
        """Build one compact follow-up for missing fields that block generation."""
        if not critical_missing:
            return FOLLOW_UP_QUESTIONS["general"]
        labels = {
            "destination": "điểm đến",
            "num_days": "số ngày đi",
            "budget": "ngân sách",
            "interests": "sở thích chính",
            "time_window": "khung giờ đi trong ngày",
        }
        labels.update({
            "hotel": "chỗ ở",
            "group": "số người đi",
            "transport": "phương tiện di chuyển",
        })
        if len(critical_missing) == 1:
            field = critical_missing[0]
            if field == "time_window":
                return "Mình muốn lịch đi trong khung giờ nào mỗi ngày ạ? Ví dụ 8h-21h, chỉ buổi chiều, hay chỉ buổi tối."
            if field == "interests":
                return "Mình muốn chuyến đi nghiêng về gì ạ: văn hóa, ẩm thực, cafe, thiên nhiên, buổi tối hay một lịch cân bằng?"
            if field == "hotel":
                return "Mình đã có chỗ ở sẵn chưa ạ? Nếu có, mình chọn vị trí trên bản đồ; nếu chưa có, em sẽ chọn điểm nghỉ phù hợp từ dữ liệu."
            if field == "group":
                return "Mình đi mấy người để em tính chi phí di chuyển và chỗ nghỉ sát hơn ạ?"
            if field == "transport":
                return "Mình đã có phương tiện di chuyển riêng chưa, hay để em gợi ý taxi/xe máy công nghệ/đi bộ theo từng chặng?"
            return FOLLOW_UP_QUESTIONS.get(field, FOLLOW_UP_QUESTIONS["general"])
        picked = [labels.get(field, field) for field in critical_missing]
        fields = ", ".join(picked[:-1]) + " và " + picked[-1]
        return f"Để em lên lịch chắc hơn, mình bổ sung giúp em {fields} nhé."

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
            return bool(
                contract.preference_mode in {"specific", "balanced", "no_preference"}
                or contract.tags
                or contract.trip_type
                or contract.locked_pois
                or contract.food_preferences
            )
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
            return (
                contract.transport_policy in {"user_has_transport", "system_suggest_per_leg", "walking_only"}
                or bool(contract.transport_modes)
                or contract.transport_plan.availability in {"has_own_transport", "needs_transport"}
            )
        if field == "group":
            return bool(contract.party.size or contract.group_type or contract.group_size)
        if field == "hotel":
            has_specific_hotel = bool(
                (contract.hotel_lat is not None and contract.hotel_lon is not None)
                or (contract.hotel_name and contract.hotel_name != "Hotel")
            )
            return (
                contract.lodging_mode in {"user_has_lodging", "system_select_lodging", "not_needed"}
                or has_specific_hotel
                or contract.hotel_confirmed
                or contract.default_hotel_ok
                or contract.has_lodging is False
            )
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
        if any(phrase in ascii_text for phrase in confirm_phrases):
            return True

        # Robust prefix check for natural confirmations with trailing text (e.g. "ok em yêu", "đồng ý nhé")
        words = ascii_text.split()
        if words and words[0] in {"ok", "oke", "okie", "dong", "xac", "chot", "vang", "duoc", "co", "u", "uh", "yes", "dung", "chon"}:
            if words[0] == "dong" and len(words) > 1 and words[1] == "y":
                return True
            if words[0] == "xac" and len(words) > 1 and words[1] == "nhan":
                return True
            if words[0] == "dung" and len(words) > 1 and words[1] == "roi":
                return True
            if words[0] in {"ok", "oke", "okie", "chot", "vang", "duoc", "co", "u", "uh", "yes"}:
                return True

        return False

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
        normalized = LLMExtractorService._normalize(destination)
        return "hue" in normalized

    @staticmethod
    def _parse_days(text: str) -> Optional[int]:
        """Parse number of days from text like '3 ngay', '2 ngày'."""
        match = re.search(r"(\d+)\s*ng(?:a|\?)y", text)
        if match:
            days = int(match.group(1))
            return days if 1 <= days <= 14 else None
        return None

    @staticmethod
    def _parse_budget(text: str) -> Optional[float]:
        """Parse budget from text like '1 trieu', '500k', '2tr'."""
        # "X triệu" or "X trieu" or "Xtr"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:tri(?:e|\?)u|tr\b)", text)
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
        if contract.hotel_lat is not None and contract.hotel_lon is not None:
            contract.hotel_confirmed = True
            if contract.has_lodging is True or contract.lodging_mode == "user_has_lodging":
                contract.has_lodging = True
                contract.lodging_mode = "user_has_lodging"
                contract.lodging_selection.status = "user_has_lodging"
                contract.lodging_selection.selection_method = "map_pin"
            contract.lodging_selection.lat = contract.hotel_lat
            contract.lodging_selection.lon = contract.hotel_lon
            contract.lodging_selection.name = contract.hotel_name or "Chỗ ở của bạn"
            LLMExtractorService._mark_confirmed(contract, "hotel")



    @staticmethod
    def _deduplicate_locked_pois(contract: LLMDataContract) -> None:
        city_blacklist = {
            "hue", "da nang", "ha noi", "sai gon", "ho chi minh", "tp hcm", "tphcm"
        }
        if contract.locked_pois:
            seen = set()
            unique = []
            for poi in contract.locked_pois:
                norm_poi = LLMExtractorService._normalize(poi).strip()
                if norm_poi in city_blacklist:
                    continue
                key = poi.lower().strip()
                if key not in seen:
                    seen.add(key)
                    unique.append(poi)
            contract.locked_pois = unique
