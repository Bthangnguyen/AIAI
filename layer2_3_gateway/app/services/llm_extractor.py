"""Layer 2: Extract travel intent from natural language using LLM + Instructor.

CRITICAL: Uses AsyncOpenAI to avoid blocking the FastAPI event loop.
A sync OpenAI call takes 2-5s and would freeze the entire server.
"""

import logging
from typing import Optional
import instructor
from openai import AsyncOpenAI

from app.config import settings as global_settings
from app.schemas.trip import LLMDataContract

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên trích xuất thông tin từ yêu cầu của khách.
Phân tích yêu cầu và trả về JSON với các trường sau:
- budget_max: Ngân sách tối đa (VND), null nếu không đề cập
- radius_km: Bán kính tìm kiếm (km), mặc định 10
- num_days: Số ngày đi, mặc định 1
- tags: Danh sách sở thích (culture, street_food, nature, temple, museum, market, beach, indoor, outdoor...)
- locked_pois: Danh sách tên địa điểm khách MONG MUỐN đi. Chỉ cần khách nhắc đến tên địa điểm cụ thể (ví dụ: "Tôi muốn đi Đại Nội", "Ghé chợ Đông Ba"), hãy đưa vào danh sách này ngay lập tức.
- weather_preference: "indoor" nếu khách muốn tránh mưa/nắng, "outdoor" nếu muốn ngoài trời, null nếu không đề cập
- time_window: {start_min, end_min} nếu khách nêu khung giờ cụ thể (quy ra phút từ 0:00)

QUAN TRỌNG:
- Cứ hễ khách nhắc đến tên địa điểm cụ thể là phải đưa vào locked_pois.
- tags nên là danh sách ngắn gọn, chuẩn hóa bằng tiếng Anh.
- Không bịa thêm thông tin khách không nói."""


class LLMExtractorService:
    """Extracts structured travel intent from natural language.
    
    Uses AsyncOpenAI + Instructor for non-blocking Pydantic-validated extraction.
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            # AsyncOpenAI: non-blocking HTTP calls to OpenAI API
            if global_settings.LLM_PROVIDER == "openrouter":
                base_client = AsyncOpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=global_settings.OPENROUTER_API_KEY
                )
            else:
                base_client = AsyncOpenAI(api_key=global_settings.OPENAI_API_KEY)
            self._client = instructor.from_openai(base_client)
        return self._client

    async def extract_intent(
        self,
        user_prompt: str,
        hotel_lat: float,
        hotel_lon: float,
        hotel_name: str = "Hotel",
        num_days: int = 1,
    ) -> LLMDataContract:
        """Parse user text into structured LLMDataContract (non-blocking)."""
        try:
            # AWAIT: async call, does NOT block event loop
            contract = await self.client.chat.completions.create(
                model=global_settings.LLM_MODEL,
                response_model=LLMDataContract,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=2,
            )

            # Override hotel info (comes from client, not LLM)
            contract.hotel_lat = hotel_lat
            contract.hotel_lon = hotel_lon
            contract.hotel_name = hotel_name
            if contract.num_days == 1 and num_days > 1:
                contract.num_days = num_days

            logger.debug(f"LLM extracted: {contract.model_dump_json(indent=2)}")
            return contract

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Fallback: return minimal contract (no crash)
            return LLMDataContract(
                hotel_lat=hotel_lat,
                hotel_lon=hotel_lon,
                hotel_name=hotel_name,
                num_days=num_days,
                tags=["general"],
            )
