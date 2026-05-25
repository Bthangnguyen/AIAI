"""Layer 2: Extract travel intent from natural language using LLM + Instructor.

CRITICAL: Uses AsyncOpenAI to avoid blocking the FastAPI event loop.
A sync OpenAI call takes 2-5s and would freeze the entire server.
"""

import logging
from typing import Optional, List, Dict
import instructor
from openai import AsyncOpenAI
from fastapi import HTTPException, status

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
- Không bịa thêm thông tin khách không nói.

THÊM: Phân tích và suy luận các trường sau:
- estimated_pois: Ước lượng số địa điểm user muốn đi. "buổi tối 2-3 quán" → 3. "đi Huế 3 ngày" → 15-20. "tìm 1 quán cafe" → 1.
- time_slot: Khung giờ. "buổi tối" → "evening". "cả ngày" → "full_day". "sáng mai" → "morning".
- trip_duration_hours: Thời lượng. "buổi tối" → 4-5h. "cả ngày" → 10-12h. "1 buổi sáng" → 3-4h.
- vibe: "lãng mạn" → "romantic". "khám phá" → "adventure". "chill" → "chill". "ăn uống" → "foodie".
- trip_type: "food tour" → "food_tour". "cafe hopping" → "cafe_hopping". "ngắm cảnh" → "sightseeing".
- target_category_distribution: Suy luận từ ý định. VD "văn hóa lịch sử" → {"culture": 0.50, "food": 0.20, "cafe": 0.15, "nature": 0.10, "shopping": 0.05}
- avoid_tags: "không muốn đông" → ["crowded"]. "tránh chỗ đắt" → ["expensive"]."""

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

THÊM: Cập nhật các trường scheduling hints khi khách đề cập:
- estimated_pois: Ước lượng số địa điểm user muốn. "2-3 quán" → 3. "cả ngày" → 8-12.
- time_slot: "buổi tối" → "evening". "cả ngày" → "full_day".
- trip_duration_hours: "buổi tối" → 4-5. "cả ngày" → 10-12.
- vibe: "lãng mạn" → "romantic". "chill" → "chill".
- trip_type: "food tour" → "food_tour". "nghiêm túc" → "sightseeing".
- target_category_distribution: Suy luận từ ý định.
- avoid_tags: "không muốn đông" → ["crowded"].
- preferred_pace: "thư thả" → "chill". "nhiều chỗ" → "intense".
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
            elif global_settings.LLM_PROVIDER == "gemini":
                base_client = AsyncOpenAI(
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    api_key=global_settings.OPENAI_API_KEY
                )
            else:
                base_client = AsyncOpenAI(api_key=global_settings.OPENAI_API_KEY)
            self._client = instructor.from_openai(base_client, mode=instructor.Mode.JSON)
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
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error_code": "LLM_SERVICE_ERROR",
                    "message": f"Dịch vụ AI phân tích ý định du lịch đang gặp sự cố: {str(e)}. Vui lòng thử lại sau ít phút."
                }
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
            # Safely dump current_contract to JSON
            if hasattr(current_contract, "model_dump_json"):
                contract_json = current_contract.model_dump_json(indent=2)
            elif isinstance(current_contract, dict):
                import json
                contract_json = json.dumps(current_contract, indent=2, ensure_ascii=False)
            else:
                contract_json = str(current_contract)

            prompt = (
                f"CURRENT_CONTRACT:\n{contract_json}\n\n"
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
            
            # Smart programmatic merge fallback:
            # If the LLM returned empty/default/null fields in updated_contract, but they were already set in current_contract,
            # we should restore them to prevent information loss due to LLM context parsing variations.
            
            # Helper to get/set fields safely on both dict and objects
            def get_field(obj, field_name):
                if isinstance(obj, dict):
                    return obj.get(field_name)
                return getattr(obj, field_name, None)

            def set_field(obj, field_name, val):
                if isinstance(obj, dict):
                    obj[field_name] = val
                else:
                    setattr(obj, field_name, val)

            # Destination fallback
            curr_dest = get_field(current_contract, "destination")
            upd_dest = get_field(updated_contract, "destination")
            if not upd_dest and curr_dest:
                set_field(updated_contract, "destination", curr_dest)
            
            # Budget max fallback
            curr_budget = get_field(current_contract, "budget_max")
            upd_budget = get_field(updated_contract, "budget_max")
            if not upd_budget and curr_budget:
                # Unless the user explicitly states unlimited budget in their new message, preserve current budget
                msg_lower = message.lower()
                unlimited_keywords = ["vô tư", "tẹt ga", "không giới hạn", "thoải mái", "unlimited", "no limit"]
                if not any(kw in msg_lower for kw in unlimited_keywords):
                    set_field(updated_contract, "budget_max", curr_budget)
            
            # Num days fallback
            curr_days = get_field(current_contract, "num_days")
            upd_days = get_field(updated_contract, "num_days")
            if upd_days == 1 and curr_days and curr_days > 1:
                # Simple check: did the user type "1 ngày", "1 ngày 1 đêm", "1n1đ" in their new message?
                # If not, preserve the previous number of days.
                msg_lower = message.lower()
                one_day_keywords = ["1 ngày", "1 ngay", "một ngày", "mot ngay", "1n", "1d"]
                if not any(kw in msg_lower for kw in one_day_keywords):
                    set_field(updated_contract, "num_days", curr_days)
            elif not upd_days and curr_days:
                set_field(updated_contract, "num_days", curr_days)

            # Radius km fallback
            curr_radius = get_field(current_contract, "radius_km")
            upd_radius = get_field(updated_contract, "radius_km")
            if (upd_radius == 10.0 or not upd_radius) and curr_radius and curr_radius != 10.0:
                set_field(updated_contract, "radius_km", curr_radius)

            # Merge locked_pois
            curr_locked = get_field(current_contract, "locked_pois") or []
            upd_locked = get_field(updated_contract, "locked_pois") or []
            if curr_locked:
                for poi in curr_locked:
                    if poi not in upd_locked:
                        upd_locked.append(poi)
                set_field(updated_contract, "locked_pois", upd_locked)

            # Merge tags
            curr_tags = get_field(current_contract, "tags") or []
            upd_tags = get_field(updated_contract, "tags") or []
            if curr_tags:
                for tag in curr_tags:
                    if tag not in upd_tags:
                        upd_tags.append(tag)
                set_field(updated_contract, "tags", upd_tags)
                        
            # Merge other scheduling hints if they are missing
            for field in ["estimated_pois", "time_slot", "trip_duration_hours", "vibe", "trip_type", "preferred_pace", "walking_tolerance", "hotel_lat", "hotel_lon", "hotel_name"]:
                curr_val = get_field(current_contract, field)
                upd_val = get_field(updated_contract, field)
                if upd_val is None and curr_val is not None:
                    set_field(updated_contract, field, curr_val)

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
