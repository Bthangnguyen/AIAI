# -*- coding: utf-8 -*-
"""Layer 3.5: Tour Guide LLM Planner (Neuro)

Selects POIs from Layer 3 candidates and assigns them to days and slots.
Uses instructor JSON mode for rigid schema output.
"""

import logging
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import settings as global_settings
from app.schemas.trip import LLMDataContract, POIResponse
from app.services.llm_client import build_llm_client

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Response Schemas for Instructor
# ═══════════════════════════════════════════════════════════════════════════════

class StopSkeleton(BaseModel):
    poi_id: str = Field(..., description="The unique UUID string of the selected POI.")
    poi_name: str = Field(..., description="Name of the selected POI.")
    slot: str = Field(
        ...,
        description="Must be one of: morning | lunch | afternoon | dinner | evening"
    )
    vibe_note: str = Field(
        ...,
        description="Short 1-sentence local context tip or explanation of why this POI fits this specific slot/day."
    )

class DaySkeleton(BaseModel):
    day_index: int = Field(..., description="0-indexed day number (0 for Day 1, 1 for Day 2).")
    date: str = Field(..., description="Friendly label for the day (e.g. 'Ngày 1')")
    stops: List[StopSkeleton] = Field(default_factory=list, description="Ordered Stops for this day.")
    narrative_title: str = Field(
        ...,
        description="A captivating theme title for the day, e.g., 'Khám phá Cố đô cổ kính' or 'Ẩm thực hoàng cung và đêm sông Hương'."
    )

class ItinerarySkeleton(BaseModel):
    days: List[DaySkeleton] = Field(default_factory=list, description="Days of the planned trip.")
    summary: str = Field(
        ...,
        description="Catchy 2-3 sentence overview describing the entire planned itinerary vibe, pace, and themes in Vietnamese."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# Prompt Templates
# ═══════════════════════════════════════════════════════════════════════════════

LLM_PLANNER_SYSTEM_PROMPT = """Bạn là CHUYÊN GIA LÊN KẾ HOẠCH DU LỊCH (Tour Guide Planner) chuyên nghiệp hàng đầu tại Huế.
Nhiệm vụ của bạn là nhận:
1. Bản hợp đồng tham số chuyến đi (TRIP_CONTRACT) của du khách (ngân sách, số ngày, sở thích, mô tả đặc biệt, yêu cầu ăn uống).
2. Danh sách 30 điểm du lịch ứng viên tốt nhất (CANDIDATES_POOL) được lọc từ cơ sở dữ liệu (tên thật, tọa độ thật, giá vé thật).

Bạn hãy thiết kế một BỘ KHUNG Ý TƯỞNG LỊCH TRÌNH VĨ MÔ (Itinerary Skeleton) cực kỳ thông minh, tự nhiên kiểu con người theo các quy tắc sau:

<PLANNING_RULES>
1. TÔN TRỌNG TUYỆT ĐỐI YÊU CẦU CỤ THỂ CỦA KHÁCH (CRITICAL):
   - Đọc kỹ mô tả chuyến đi (`Special Description / Requests`) và sở thích ẩm thực (`Food preferences`) của khách.
   - Nếu khách yêu cầu các món cụ thể (ví dụ: bún bò Huế, nước rau má, cơm hến, bánh bèo, chè hẻm...) hay địa điểm cụ thể, bạn PHẢI tìm các POIs tương ứng trong CANDIDATES_POOL (dựa theo tên POI hoặc mô tả/tag) và phân bổ chúng vào buổi thích hợp.
   - Ví dụ: Khách muốn ăn bún bò buổi sáng/trưa -> chọn POI bún bò xếp vào slot `morning` hoặc `lunch`. Khách muốn uống nước rau má buổi chiều -> xếp POI nước rau má vào slot `afternoon`.
   - Giữ lại 100% các điểm bắt buộc được đánh dấu là `[REQUIRED/LOCKED]` trong danh sách ứng viên. Không được phép bỏ sót bất kỳ điểm locked nào!

2. PHÂN BỔ BUỔI TỰ NHIÊN LINH HOẠT (HUMAN LOGIC):
   - Phân chia các điểm dừng vào các buổi hợp lý trong ngày: `morning` (sáng), `lunch` (ăn trưa), `afternoon` (chiều), `dinner` (ăn tối), `evening` (tối).
   - Logic du lịch tự nhiên nhưng phải phục vụ tối đa mong muốn của khách, KHÔNG áp dụng công thức cứng nhắc nếu khách có gu khác:
     * Tận dụng buổi sáng mát mẻ cho các hoạt động di chuyển ngoài trời nhiều.
     * Buổi trưa: Chọn địa điểm ăn trưa (`lunch`) ngon lành theo gu ẩm thực của khách.
     * Buổi chiều xế: Xếp các quán cafe muối, quán nước rau má, nhà vườn hoặc chùa nhẹ nhàng để nghỉ ngơi hồi sức.
     * Buổi tối (`evening` / `dinner`): Xếp các hoạt động ẩm thực tối, chợ đêm, đi thuyền sông Hương hoặc chill nhẹ.
   - Tránh dồn dập các điểm tham quan nặng nề liên tục; phân bổ xen kẽ các chặng dừng ăn uống/nghỉ ngơi để đảm bảo chuyến đi thư thái.

3. KHÔNG CẦN CHÈN GIỜ CHI TIẾT:
   - Bạn chỉ cần gán điểm vào các slot `morning`, `lunch`, `afternoon`, `dinner`, `evening`.
   - Hệ thống vi mô phía sau sẽ tự động tính toán khoảng cách OSRM và chèn mốc giờ chính xác. Bạn tuyệt đối không tự tiện ghi mốc giờ cụ thể vào các văn bản mô tả.

4. CHỈ CHỌN POI TỪ DANH SÁCH ỨNG VIÊN CÓ SẴN:
   - Bạn chỉ được chọn các điểm nằm trong danh sách CANDIDATES_POOL được cung cấp dưới đây. TUYỆT ĐỐI không tự bịa ra UUID hoặc địa điểm mới không có trong danh sách!
</PLANNING_RULES>

Trả về kết quả dưới định dạng JSON khớp chính xác với cấu trúc ItinerarySkeleton định kiểu nghiêm ngặt. Viết tất cả các nội dung (vibe_note, narrative_title, summary) bằng tiếng Việt tự nhiên, truyền cảm hứng và khớp sát với ý đồ của khách hàng."""

# ═══════════════════════════════════════════════════════════════════════════════
# Planner Service Class
# ═══════════════════════════════════════════════════════════════════════════════

class ItineraryPlannerService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = build_llm_client()
        return self._client

    def _min_to_time(self, minutes: int) -> str:
        h = minutes // 60
        m = minutes % 60
        return f"{h:02d}:{m:02d}"

    def _serialize_candidates(self, candidates: List[POIResponse]) -> str:
        lines = []
        for p in candidates:
            locked_str = " [REQUIRED/LOCKED]" if p.is_locked else ""
            lines.append(
                f"- UUID: {p.uuid}\n"
                f"  Name: {p.name}{locked_str}\n"
                f"  Category: {p.category} (Group: {p.category_group or 'N/A'})\n"
                f"  Price/Fee: {int(p.entrance_fee or p.price):,} VND\n"
                f"  Hours: {self._min_to_time(p.open_time)} - {self._min_to_time(p.close_time)}\n"
                f"  PriorityScore: {p.priority_score} (UtilityScore: {p.utility_score:.2f})\n"
                f"  Description: {p.description or 'N/A'}\n"
            )
        return "\n".join(lines)

    async def build_skeleton(
        self,
        contract: LLMDataContract,
        candidates: List[POIResponse]
    ) -> ItinerarySkeleton:
        """Calls DeepSeek/GPT via Instructor to generate ItinerarySkeleton JSON."""
        logger.info(f"🧠 LLM Planner: Planning Itinerary Skeleton for {contract.num_days} days...")
        
        serialized_pois = self._serialize_candidates(candidates)
        prompt = (
            f"TRIP_CONTRACT:\n"
            f"- Destination: {contract.destination or 'Huế'}\n"
            f"- Days: {contract.num_days}\n"
            f"- Target Budget: {f'{int(contract.budget_max):,} VND' if contract.budget_max else 'Unlimited'}\n"
            f"- Special Description / Requests: {contract.distribution_description or 'No special requests'}\n"
            f"- Food preferences: {contract.food_preferences or []}\n"
            f"- Vibe preference: {contract.vibe or 'balanced'}\n"
            f"- Style: {contract.trip_type or 'mixed'}\n"
            f"- Focus tags: {contract.tags or []}\n"
            f"- Avoid: {contract.avoid_tags or []}\n"
            f"- Locked/Must-visit POIs: {contract.locked_pois or []}\n"
            f"- Excluded POIs: {contract.excluded_pois or []}\n\n"
            f"CANDIDATES_POOL:\n"
            f"{serialized_pois}\n"
        )

        try:
            skeleton: ItinerarySkeleton = await self.client.chat.completions.create(
                model=global_settings.LLM_MODEL,
                response_model=ItinerarySkeleton,
                messages=[
                    {"role": "system", "content": LLM_PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_retries=2,
                timeout=60.0,
            )
            logger.info(
                f"🧠 LLM Planner successfully created skeleton. "
                f"Days count: {len(skeleton.days)}, summary_len={len(skeleton.summary)}"
            )
            return skeleton
        except Exception as e:
            logger.error(f"🧠 LLM Planner skeleton generation failed: {e}")
            raise e
