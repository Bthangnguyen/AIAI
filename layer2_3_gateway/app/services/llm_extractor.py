"""Layer 2: Extract travel intent from natural language using LLM + Instructor.

CRITICAL: Uses AsyncOpenAI to avoid blocking the FastAPI event loop.
A sync OpenAI call takes 2-5s and would freeze the entire server.
"""

import logging
from typing import Optional, List, Dict
import instructor
from openai import AsyncOpenAI

from app.config import settings as global_settings
from app.schemas.trip import LLMDataContract, ChatProcessResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên trích xuất thông tin từ yêu cầu của khách.
Phân tích yêu cầu và trả về JSON với các trường sau:
- destination: Tên thành phố/tỉnh mà khách muốn đi du lịch (ví dụ: Huế, Đà Nẵng, Hà Nội). Bắt buộc phải trích xuất nếu có.
- budget_max: Ngân sách tối đa (VND), null nếu không đề cập
- radius_km: Bán kính tìm kiếm (km), mặc định 10
- num_days: Số ngày đi, mặc định 1
- tags: Danh sách sở thích chuẩn hóa bằng tiếng Anh (ví dụ: "vegetarian" nếu khách muốn ăn chay/kiêng mặn, "culture", "street_food", "nature", "temple", "museum", "market", "beach", "indoor", "outdoor"...)
- locked_pois: Danh sách tên địa điểm khách MONG MUỐN đi. Chỉ cần khách nhắc đến tên địa điểm cụ thể (ví dụ: "Tôi muốn đi Đại Nội", "Ghé chợ Đông Ba"), hãy đưa vào danh sách này ngay lập tức.
- weather_preference: "indoor" nếu khách muốn tránh mưa/nắng, "outdoor" nếu muốn ngoài trời, null nếu không đề cập
- time_window: {start_min, end_min} nếu khách nêu khung giờ cụ thể (quy ra phút từ 0:00)

QUAN TRỌNG:
- Cứ hễ khách nhắc đến tên địa điểm cụ thể là phải đưa vào locked_pois.
- tags nên là danh sách ngắn gọn, chuẩn hóa bằng tiếng Anh.
- Không bịa thêm thông tin khách không nói."""

CHAT_PROCESS_SYSTEM_PROMPT = """Bạn là trợ lý du lịch ảo chuyên trách phân tích và cập nhật hợp đồng dữ liệu chuyến đi (LLMDataContract) từ cuộc trò chuyện với khách hàng.

Nhiệm vụ của bạn:
1. Tiếp nhận trạng thái hợp đồng hiện tại (current_contract), lịch sử trò chuyện (history) và câu chat mới nhất của khách hàng (message).
2. Trích xuất thông tin mới từ `message` và cập nhật/gộp vào `current_contract` để tạo ra `updated_contract`.
   - Nếu thông tin mới mâu thuẫn với thông tin cũ (ví dụ khách đổi ý từ 3 ngày thành 4 ngày), hãy ghi đè bằng thông tin mới.
   - Nếu khách không đề cập hoặc thông tin cũ đã có, hãy GIỮ NGUYÊN thông tin cũ từ `current_contract`.
   - Dịch các tiếng lóng ngân sách: "1 củ", "1tr", "1 triệu" -> budget_max = 1000000. "vô tư", "tẹt ga", "không giới hạn" -> budget_max = null.
   - Dịch số ngày: "3 ngày 2 đêm", "3n2đ" -> num_days = 3.
   - tags: Chuẩn hóa sở thích tiếng Anh (ví dụ: "vegetarian" nếu khách muốn ăn chay/kiêng mặn, "culture", "nature", "temple", "museum", "market", "beach", "indoor", "outdoor"...)
3. Đánh giá tính đầy đủ của hợp đồng:
   - Các trường BẮT BUỘC: `destination` (chỉ hỗ trợ Huế/Hue), `num_days` (phải >= 1), và `budget_max` (trừ khi khách nói ngân sách vô tư/không giới hạn).
   - Nếu THIẾU bất kỳ trường bắt buộc nào:
     * Set `status = "clarifying"`.
     * Tạo `reply` bằng tiếng Việt tự nhiên, thân thiện để hỏi khách duy nhất MỘT thông tin còn thiếu đầu tiên theo thứ tự ưu tiên (Destination -> Days -> Budget). Ví dụ: "Dạ anh/chị muốn đi du lịch ở đâu ạ?" hoặc "Dạ mình muốn đi trong mấy ngày ạ?"
   - Nếu ĐỦ tất cả trường bắt buộc:
     * Set `status = "ready"`.
     * Tạo `reply` bằng tiếng Việt thông báo rằng bạn đã thu thập đủ thông tin và đang tiến hành xây dựng lịch trình tối ưu (ví dụ: "Dạ em đã nhận đủ thông tin rồi ạ. Em đang lên lịch trình tối ưu cho mình đây, đợi em một chút nhé!").
4. Xử lý trường hợp đặc biệt:
   - Nếu khách chọn địa điểm ngoài Huế (ví dụ "Hà Nội", "Đà Nẵng", "Paris"): đặt `destination` theo ý khách, nhưng set `status = "clarifying"`, và `reply` phải là câu hỏi khéo léo nói rằng hệ thống hiện tại chỉ hỗ trợ Huế và hỏi khách có muốn đổi sang đi Huế không.
   - Tránh đưa tên thành phố chung chung vào `locked_pois` (ví dụ "Huế", "Đà Nẵng"...) để tránh lỗi.
"""


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
        hotel_lat: Optional[float] = None,
        hotel_lon: Optional[float] = None,
        hotel_name: Optional[str] = None,
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
            if hotel_lat is not None:
                contract.hotel_lat = hotel_lat
            if hotel_lon is not None:
                contract.hotel_lon = hotel_lon
            if hotel_name is not None:
                contract.hotel_name = hotel_name
            if contract.num_days == 1 and num_days > 1:
                contract.num_days = num_days

            # Backend failsafes
            self._apply_backend_failsafes(contract, user_prompt)

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

    async def process_chat_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
    ) -> Dict:
        """Processes a single chat turn in the interactive clarification flow."""
        try:
            # Prepare instructions for OpenAI
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
                max_retries=2,
            )

            # Extract fields and apply failsafes
            updated_contract = response.updated_contract
            self._apply_backend_failsafes(updated_contract, message)

            # Whitelist checks for supported city
            status = response.status
            reply = response.reply

            if updated_contract.destination:
                dest_lower = updated_contract.destination.lower()
                if "huế" not in dest_lower and "hue" not in dest_lower:
                    status = "clarifying"
                    reply = "Dạ hiện tại em chỉ hỗ trợ lên lịch trình tại Huế thôi ạ. Anh/chị có muốn đổi kế hoạch sang khám phá Huế xinh đẹp không ạ?"

            # Safety fallback for num_days
            if updated_contract.num_days is not None and updated_contract.num_days <= 0:
                updated_contract.num_days = 1

            return {
                "status": status,
                "reply": reply,
                "updated_contract": updated_contract,
            }

        except Exception as e:
            logger.error(f"Chat turn processing failed: {e}")
            # Safe fallback response
            return {
                "status": "clarifying",
                "reply": "Dạ em xin lỗi, hệ thống đang gặp chút sự cố nhỏ. Anh/chị có thể nói rõ hơn mong muốn đi Huế mấy ngày và ngân sách bao nhiêu không ạ?",
                "updated_contract": current_contract,
            }

    def _apply_backend_failsafes(self, contract: LLMDataContract, raw_text: str):
        """Sanitizes city names from locked POIs and enforces strict vegetarian tag."""
        # 1. City Name Blacklist for locked_pois
        city_blacklist = {
            "huế", "hue", "đà nẵng", "da nang", "hà nội", "ha noi",
            "sài gòn", "sai gon", "hồ chí minh", "ho chi minh", "tp hcm", "tphcm"
        }
        if contract.locked_pois:
            contract.locked_pois = [
                poi for poi in contract.locked_pois
                if poi.lower().strip() not in city_blacklist
            ]

        # 2. Vegetarian keyword scanning
        veg_keywords = ["chay", "ăn chay", "kiêng mặn", "chay tịnh", "vegan", "vegetarian"]
        raw_text_lower = raw_text.lower()
        if any(keyword in raw_text_lower for keyword in veg_keywords):
            if "vegetarian" not in contract.tags:
                contract.tags.append("vegetarian")
