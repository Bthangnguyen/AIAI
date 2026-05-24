"""Layer 2: extract and refine travel intent with LLM + deterministic gates."""

import logging
import re
import unicodedata
from typing import Optional, List, Dict, Iterable

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


SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên trích xuất thông tin từ yêu cầu của khách.
Trả về JSON theo LLMDataContract. Không tự bịa thông tin.

Trích xuất:
- destination: chỉ hỗ trợ Huế/Hue.
- budget_max hoặc budget_is_unlimited.
- num_days, tags, locked_pois, excluded_pois.
- preferred_pace, walking_tolerance, food_preferences, avoid_tags.
- time_slot, trip_duration_hours, time_window nếu có.
- transport_modes, group_type, group_size, hotel info nếu user nói.

Luôn chuẩn hóa tags bằng tiếng Anh, ví dụ culture, nature, cafe, street_food, vegetarian.
Nếu khách nhắc địa điểm cụ thể như Đại Nội, chợ Đông Ba, chùa Thiên Mụ, đưa vào locked_pois.
Không đưa tên thành phố chung chung như Huế vào locked_pois."""

CHAT_PROCESS_SYSTEM_PROMPT = """Bạn cập nhật LLMDataContract từ hội thoại du lịch.
Hãy đọc current_contract, history, message rồi trả ChatProcessResponse.

Quan trọng:
- Giữ nguyên dữ liệu cũ nếu message không sửa nó.
- Không tự set ready khi chưa rõ thông tin.
- Nếu user xác nhận tóm tắt trước đó, có thể status=ready.
- Nếu đang có itinerary, phân loại edit_intent theo action:
  add_place, remove_place, replace_place, change_budget, change_pace,
  change_time_window, add_preference, avoid_preference, rebuild_requested,
  answer_question.
- Output vẫn phải có updated_contract."""

EDIT_INTENT_SYSTEM_PROMPT = """Bạn phân loại yêu cầu chỉnh sửa itinerary hiện tại.
Trả ChatProcessResponse với phase='editing', updated_contract giữ trạng thái hiện tại,
và edit_intent gồm action, target, constraints, raw_message.
Nếu user chỉ hỏi thông tin, action='answer_question'."""

REQUIRED_FIELDS = [
    "destination",
    "num_days",
    "budget",
    "interests",
    "pace",
    "walking",
    "food",
    "must_visit",
    "avoid",
    "time_window",
    "transport",
    "group",
    "hotel",
]

FIELD_LABELS = {
    "destination": "điểm đến",
    "num_days": "số ngày",
    "budget": "ngân sách",
    "interests": "sở thích chính",
    "pace": "nhịp đi",
    "walking": "mức đi bộ",
    "food": "ăn uống/kiêng kỵ",
    "must_visit": "địa điểm bắt buộc",
    "avoid": "điều muốn tránh",
    "time_window": "khung giờ đi mỗi ngày",
    "transport": "phương tiện",
    "group": "nhóm đi",
    "hotel": "khách sạn/điểm xuất phát",
}

FOLLOW_UP_QUESTIONS = {
    "destination": "Dạ mình muốn lên lịch ở Huế đúng không ạ? Hiện hệ thống chỉ hỗ trợ Huế.",
    "num_days": "Dạ mình muốn đi Huế trong mấy ngày ạ?",
    "budget": "Dạ ngân sách tối đa cho cả chuyến là khoảng bao nhiêu ạ? Nếu thoải mái ngân sách, mình có thể nói 'vô tư'.",
    "interests": "Mình thích kiểu trải nghiệm nào nhất ở Huế ạ? Ví dụ văn hóa lịch sử, ăn uống, cafe, thiên nhiên, chùa/lăng tẩm.",
    "pace": "Mình muốn nhịp lịch trình như thế nào ạ: chill thư thả, cân bằng, hay đi được nhiều điểm?",
    "walking": "Mức đi bộ của mình thế nào ạ: ít đi bộ, vừa phải, hay đi bộ nhiều cũng ổn?",
    "food": "Mình có yêu cầu ăn uống hay kiêng kỵ gì không ạ? Ví dụ ăn chay, không cay, thích bún bò/cafe muối, hoặc không có.",
    "must_visit": "Có địa điểm nào bắt buộc muốn ghé không ạ? Ví dụ Đại Nội, chùa Thiên Mụ, chợ Đông Ba; nếu không có thì nói 'không có'.",
    "avoid": "Có điều gì mình muốn tránh không ạ? Ví dụ chỗ đông, quá đắt, leo núi, nắng trưa; nếu không có thì nói 'không có'.",
    "time_window": "Mỗi ngày mình muốn bắt đầu và kết thúc khoảng mấy giờ ạ? Ví dụ 8h-21h, buổi sáng, buổi tối, hoặc cả ngày.",
    "transport": "Mình muốn di chuyển chủ yếu bằng gì ạ: taxi/ô tô, đi bộ, xe máy, hay kết hợp?",
    "group": "Chuyến này mình đi một mình, cặp đôi, gia đình hay bạn bè ạ? Khoảng bao nhiêu người?",
    "hotel": "Mình đã có khách sạn/điểm xuất phát chưa ạ? Nếu chưa, em dùng khách sạn trung tâm Huế mặc định nhé?",
}

UNLIMITED_BUDGET_MARKERS = (
    "vo tu",
    "tet ga",
    "khong gioi han",
    "thoai mai ngan sach",
    "khong quan trong ngan sach",
)
CONFIRMATION_MARKERS = (
    "ok",
    "oke",
    "dong y",
    "xac nhan",
    "dung roi",
    "chuan",
    "tao di",
    "lam di",
    "len lich di",
    "bat dau",
)
NEGATIVE_OR_ANY_MARKERS = (
    "khong co",
    "khong can",
    "tuy",
    "sao cung duoc",
    "mac dinh",
    "chua biet",
    "khong biet",
)


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
        """Parse user text into structured LLMDataContract."""
        try:
            contract = await self.client.chat.completions.create(
                model=global_settings.LLM_MODEL,
                response_model=LLMDataContract,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_retries=2,
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

    async def process_chat_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
        has_draft: bool = False,
    ) -> Dict:
        """Process one chat turn for collection, confirmation, or itinerary edits."""
        clean_message = (message or "").strip()
        if has_draft:
            return await self._process_edit_turn(clean_message, history, current_contract)

        if not clean_message:
            contract = current_contract.model_copy(deep=True)
            missing = self._missing_fields(contract)
            return self._collecting_response(contract, missing or ["destination"])

        candidate = None
        try:
            history_str = "\n".join([f"{h['role']}: {h['content']}" for h in history])
            prompt = (
                f"CURRENT_CONTRACT:\n{current_contract.model_dump_json(indent=2)}\n\n"
                f"HISTORY:\n{history_str}\n\n"
                f"NEW_MESSAGE:\n{clean_message}"
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
            candidate = response.updated_contract
        except Exception as e:
            logger.error(f"Chat turn LLM processing failed, using deterministic merge: {e}")

        contract = self._merge_contracts(current_contract, candidate)
        self._apply_message_hints(contract, clean_message)
        self._apply_answer_to_last_question(contract, clean_message, current_contract.last_question_field)
        self._apply_backend_failsafes(contract, clean_message)

        unsupported_reply = self._unsupported_destination_reply(contract)
        if unsupported_reply:
            contract.confirmation_pending = False
            contract.ready_to_plan = False
            contract.last_question_field = "destination"
            return {
                "status": "clarifying",
                "reply": unsupported_reply,
                "updated_contract": contract,
                "phase": "collecting",
                "missing_fields": ["destination"],
                "next_question": unsupported_reply,
                "requires_confirmation": False,
                "edit_intent": None,
            }

        missing = self._missing_fields(contract)
        if current_contract.confirmation_pending and not missing and self._is_confirmation(clean_message):
            contract.confirmation_pending = False
            contract.ready_to_plan = True
            contract.last_question_field = None
            return {
                "status": "ready",
                "reply": "Dạ em đã xác nhận đủ thông tin. Em bắt đầu tạo lịch trình tối ưu cho mình ngay đây.",
                "updated_contract": contract,
                "phase": "ready",
                "missing_fields": [],
                "next_question": None,
                "requires_confirmation": False,
                "edit_intent": None,
            }

        if missing:
            return self._collecting_response(contract, missing)

        contract.confirmation_pending = True
        contract.ready_to_plan = False
        contract.last_question_field = "confirmation"
        reply = self._build_confirmation_reply(contract)
        return {
            "status": "clarifying",
            "reply": reply,
            "updated_contract": contract,
            "phase": "confirming",
            "missing_fields": [],
            "next_question": reply,
            "requires_confirmation": True,
            "edit_intent": None,
        }

    async def _process_edit_turn(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_contract: LLMDataContract,
    ) -> Dict:
        contract = current_contract.model_copy(deep=True)
        intent = self._detect_edit_intent(message)
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
                    max_retries=2,
                )
                if response.updated_contract:
                    contract = self._merge_contracts(contract, response.updated_contract)
                if response.edit_intent:
                    intent = response.edit_intent
            except Exception as e:
                logger.warning(f"Edit-intent LLM classification failed, using rules: {e}")

        self._apply_message_hints(contract, message)
        reply = self._edit_reply(intent)
        return {
            "status": "clarifying",
            "reply": reply,
            "updated_contract": contract,
            "phase": "editing",
            "missing_fields": [],
            "next_question": None,
            "requires_confirmation": False,
            "edit_intent": intent,
        }

    def _collecting_response(self, contract: LLMDataContract, missing: List[str]) -> Dict:
        next_field = missing[0]
        question = FOLLOW_UP_QUESTIONS[next_field]
        contract.confirmation_pending = False
        contract.ready_to_plan = False
        contract.last_question_field = next_field
        return {
            "status": "clarifying",
            "reply": question,
            "updated_contract": contract,
            "phase": "collecting",
            "missing_fields": missing,
            "next_question": question,
            "requires_confirmation": False,
            "edit_intent": None,
        }

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
        ]
        for field in scalar_fields:
            value = getattr(candidate, field)
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
        if candidate.time_window is not None:
            merged.time_window = candidate.time_window

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

    def _apply_message_hints(self, contract: LLMDataContract, raw_text: str) -> None:
        text = self._normalize(raw_text)

        if "hue" in text or "di hue" in text:
            contract.destination = "Huế"
            self._mark_confirmed(contract, "destination")

        days = self._parse_days(text)
        if days:
            contract.num_days = days
            self._mark_confirmed(contract, "num_days")

        budget = self._parse_budget(text)
        if budget is not None:
            contract.budget_max = budget
            contract.budget_is_unlimited = False
            self._mark_confirmed(contract, "budget")
        if any(marker in text for marker in UNLIMITED_BUDGET_MARKERS):
            contract.budget_max = None
            contract.budget_is_unlimited = True
            self._mark_confirmed(contract, "budget")

        if any(word in text for word in ("lich su", "van hoa", "dai noi", "lang tam", "chua")):
            contract.tags = self._merge_unique(contract.tags, ["culture"])
            self._mark_confirmed(contract, "interests")
        if any(word in text for word in ("cafe", "ca phe")):
            contract.tags = self._merge_unique(contract.tags, ["cafe"])
            self._mark_confirmed(contract, "interests")
        if any(word in text for word in ("an uong", "bun bo", "am thuc", "mon an", "street food")):
            contract.tags = self._merge_unique(contract.tags, ["street_food"])
            self._mark_confirmed(contract, "interests")
        if any(word in text for word in ("thien nhien", "bien", "song", "nui", "ngoai troi")):
            contract.tags = self._merge_unique(contract.tags, ["nature"])
            self._mark_confirmed(contract, "interests")

        if any(word in text for word in ("an chay", "chay", "vegan", "vegetarian", "kieng man")):
            contract.tags = self._merge_unique(contract.tags, ["vegetarian"])
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["vegetarian"])
            self._mark_confirmed(contract, "food")
            self._mark_confirmed(contract, "interests")
        if any(word in text for word in ("khong cay", "it cay")):
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["not_spicy"])
            self._mark_confirmed(contract, "food")
        if any(marker in text for marker in NEGATIVE_OR_ANY_MARKERS):
            if contract.last_question_field in ("food", "must_visit", "avoid"):
                self._mark_confirmed(contract, contract.last_question_field)

        locked = self._extract_common_locked_pois(text)
        if locked:
            contract.locked_pois = self._merge_unique(contract.locked_pois, locked)
            self._mark_confirmed(contract, "must_visit")

        if any(word in text for word in ("tranh", "khong muon", "dung", "bo qua")):
            self._mark_confirmed(contract, "avoid")
            if "dong" in text:
                contract.avoid_tags = self._merge_unique(contract.avoid_tags, ["crowded"])
            if "dat" in text:
                contract.avoid_tags = self._merge_unique(contract.avoid_tags, ["expensive"])
            if "leo nui" in text:
                contract.avoid_tags = self._merge_unique(contract.avoid_tags, ["climbing"])

        if any(word in text for word in ("chill", "thu tha", "nhe", "nghi nhieu")):
            contract.preferred_pace = "chill"
            self._mark_confirmed(contract, "pace")
        elif any(word in text for word in ("nhieu diem", "di nhieu", "day", "intense", "kin lich")):
            contract.preferred_pace = "intense"
            self._mark_confirmed(contract, "pace")
        elif "can bang" in text or "balanced" in text:
            contract.preferred_pace = "balanced"
            self._mark_confirmed(contract, "pace")

        if any(word in text for word in ("it di bo", "khong di bo nhieu", "di bo it")):
            contract.walking_tolerance = "low"
            self._mark_confirmed(contract, "walking")
        elif any(word in text for word in ("di bo nhieu", "thich di bo", "walking nhieu")):
            contract.walking_tolerance = "high"
            self._mark_confirmed(contract, "walking")
        elif "di bo" in text or "vua phai" in text:
            contract.walking_tolerance = "medium"
            self._mark_confirmed(contract, "walking")

        if "buoi toi" in text or "toi" in text:
            contract.time_slot = "evening"
            contract.time_window = contract.time_window or TimeWindowSpec(start_min=1080, end_min=1320)
            self._mark_confirmed(contract, "time_window")
        elif "buoi sang" in text or "sang" in text:
            contract.time_slot = "morning"
            contract.time_window = contract.time_window or TimeWindowSpec(start_min=480, end_min=720)
            self._mark_confirmed(contract, "time_window")
        elif "ca ngay" in text or "full day" in text:
            contract.time_slot = "full_day"
            contract.time_window = contract.time_window or TimeWindowSpec(start_min=480, end_min=1260)
            self._mark_confirmed(contract, "time_window")

        start_end = self._parse_time_range(text)
        if start_end:
            contract.time_window = TimeWindowSpec(start_min=start_end[0], end_min=start_end[1])
            self._mark_confirmed(contract, "time_window")

        modes = []
        if "taxi" in text or "oto" in text or "o to" in text:
            modes.append("taxi")
        if "di bo" in text:
            modes.append("walking")
        if "bus" in text or "xe buyt" in text:
            modes.append("bus")
        if "xe may" in text:
            modes.append("taxi")
        if modes:
            contract.transport_modes = self._merge_unique(contract.transport_modes, modes)
            self._mark_confirmed(contract, "transport")

        if "mot minh" in text or "solo" in text:
            contract.group_type = "solo"
            contract.group_size = contract.group_size or 1
            self._mark_confirmed(contract, "group")
        elif any(word in text for word in ("cap doi", "nguoi yeu", "vo chong")):
            contract.group_type = "couple"
            contract.group_size = contract.group_size or 2
            self._mark_confirmed(contract, "group")
        elif "gia dinh" in text:
            contract.group_type = "family"
            self._mark_confirmed(contract, "group")
        elif "ban be" in text or "nhom ban" in text:
            contract.group_type = "friends"
            self._mark_confirmed(contract, "group")
        group_size = re.search(r"(\d+)\s*nguoi", text)
        if group_size:
            contract.group_size = int(group_size.group(1))
            self._mark_confirmed(contract, "group")

        if any(word in text for word in ("khach san", "hotel", "homestay")):
            contract.hotel_confirmed = True
            self._mark_confirmed(contract, "hotel")
        if any(word in text for word in ("khach san mac dinh", "trung tam hue", "chua biet khach san")):
            contract.default_hotel_ok = True
            contract.hotel_confirmed = True
            self._mark_confirmed(contract, "hotel")

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
            if last_field in REQUIRED_FIELDS:
                self._mark_confirmed(contract, last_field)

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
            return bool(contract.time_window or contract.time_slot)
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

    def _build_confirmation_reply(self, contract: LLMDataContract) -> str:
        budget = "ngân sách thoải mái" if contract.budget_is_unlimited else f"ngân sách khoảng {int(contract.budget_max or 0):,} VND"
        must_visit = ", ".join(contract.locked_pois) if contract.locked_pois else "không có điểm bắt buộc"
        avoid = ", ".join(contract.avoid_tags + contract.excluded_pois) if (contract.avoid_tags or contract.excluded_pois) else "không có yêu cầu tránh riêng"
        tags = ", ".join(contract.tags) if contract.tags else "tổng hợp"
        transport = ", ".join(contract.transport_modes) if contract.transport_modes else "taxi + walking"
        group = contract.group_type or (f"{contract.group_size} người" if contract.group_size else "chưa rõ")
        hotel = contract.hotel_name if contract.hotel_name and contract.hotel_name != "Hotel" else "khách sạn trung tâm Huế mặc định"
        return (
            "Dạ em tóm tắt lại trước khi tạo lịch nhé: "
            f"đi {contract.destination or 'Huế'} {contract.num_days} ngày, {budget}, "
            f"sở thích {tags}, nhịp {contract.preferred_pace}, mức đi bộ {contract.walking_tolerance}, "
            f"ăn uống {', '.join(contract.food_preferences) if contract.food_preferences else 'không yêu cầu riêng'}, "
            f"điểm bắt buộc: {must_visit}, tránh: {avoid}, phương tiện {transport}, nhóm {group}, xuất phát từ {hotel}. "
            "Mình xác nhận tạo lịch trình theo thông tin này chứ ạ?"
        )

    def _detect_edit_intent(self, message: str) -> EditIntent:
        text = self._normalize(message)
        action = "answer_question"
        if any(word in text for word in ("tao lai", "lam lai", "xay lai", "rebuild", "reset lich")):
            action = "rebuild_requested"
        elif any(word in text for word in ("thay", "doi", "replace")) and any(word in text for word in ("bang", "thanh")):
            action = "replace_place"
        elif any(word in text for word in ("them", "add", "bo sung", "chen")):
            action = "add_place"
        elif any(word in text for word in ("xoa", "bo ", "remove", "khong di")):
            action = "remove_place"
        elif any(word in text for word in ("ngan sach", "budget", "trieu", " tr", " cu", "k")):
            action = "change_budget"
        elif any(word in text for word in ("chill", "nhe", "thu tha", "nhieu diem", "di nhieu", "day hon")):
            action = "change_pace"
        elif any(word in text for word in ("gio", "sang", "chieu", "toi")):
            action = "change_time_window"
        elif any(word in text for word in ("tranh", "khong muon", "dung")):
            action = "avoid_preference"
        elif any(word in text for word in ("thich", "muon an", "uu tien")):
            action = "add_preference"
        return EditIntent(action=action, target=message or None, constraints={}, raw_message=message)

    def _edit_reply(self, intent: EditIntent) -> str:
        replies = {
            "add_place": "Dạ em sẽ tìm địa điểm phù hợp và chèn vào lịch hiện tại.",
            "remove_place": "Dạ em sẽ bỏ địa điểm đó khỏi lịch và tối ưu lại ngày tương ứng.",
            "replace_place": "Dạ em hiểu là mình muốn thay địa điểm trong lịch hiện tại.",
            "change_budget": "Dạ em sẽ cập nhật ngân sách và tối ưu lại lịch nếu cần.",
            "change_pace": "Dạ em sẽ chỉnh nhịp lịch trình theo yêu cầu mới.",
            "change_time_window": "Dạ em sẽ cập nhật khung giờ và tính lại lịch trình.",
            "add_preference": "Dạ em sẽ thêm sở thích này vào lịch hiện tại.",
            "avoid_preference": "Dạ em sẽ tránh yêu cầu đó khi tối ưu lại.",
            "rebuild_requested": "Dạ em sẽ tạo lại toàn bộ lịch trình theo yêu cầu mới.",
            "answer_question": "Dạ em đã nhận được câu hỏi/yêu cầu của mình.",
        }
        return replies.get(intent.action, replies["answer_question"])

    def _apply_backend_failsafes(self, contract: LLMDataContract, raw_text: str) -> None:
        city_blacklist = {
            "hue", "da nang", "ha noi", "sai gon", "ho chi minh", "tp hcm", "tphcm"
        }
        if contract.locked_pois:
            contract.locked_pois = [
                poi for poi in contract.locked_pois
                if self._normalize(poi).strip() not in city_blacklist
            ]

        raw_text_lower = self._normalize(raw_text)
        if any(keyword in raw_text_lower for keyword in ("chay", "an chay", "kieng man", "vegan", "vegetarian")):
            contract.tags = self._merge_unique(contract.tags, ["vegetarian"])
            contract.food_preferences = self._merge_unique(contract.food_preferences, ["vegetarian"])
            self._mark_confirmed(contract, "food")

        if contract.num_days is not None and contract.num_days <= 0:
            contract.num_days = 1

    def _override_hotel(
        self,
        contract: LLMDataContract,
        hotel_lat: Optional[float],
        hotel_lon: Optional[float],
        hotel_name: Optional[str],
    ) -> None:
        if hotel_lat is not None:
            contract.hotel_lat = hotel_lat
        if hotel_lon is not None:
            contract.hotel_lon = hotel_lon
        if hotel_name is not None:
            contract.hotel_name = hotel_name
        if hotel_lat is not None or hotel_lon is not None or hotel_name is not None:
            contract.hotel_confirmed = True
            self._mark_confirmed(contract, "hotel")

    @staticmethod
    def _normalize(value: str) -> str:
        text = unicodedata.normalize("NFD", (value or "").lower())
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        return text.replace("đ", "d")

    @staticmethod
    def _merge_unique(left: Iterable[str], right: Iterable[str]) -> List[str]:
        result = []
        seen = set()
        for value in list(left or []) + list(right or []):
            if value is None:
                continue
            key = str(value).strip()
            if key and key.lower() not in seen:
                seen.add(key.lower())
                result.append(key)
        return result

    def _mark_confirmed(self, contract: LLMDataContract, field: str) -> None:
        if field not in contract.confirmed_fields:
            contract.confirmed_fields.append(field)

    @staticmethod
    def _parse_days(text: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*(ngay|days?|n\b)", text)
        if match:
            return max(1, int(match.group(1)))
        match = re.search(r"(\d+)n\d*d?", text)
        if match:
            return max(1, int(match.group(1)))
        return None

    @staticmethod
    def _parse_budget(text: str) -> Optional[float]:
        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*(trieu|tr|cu)\b", text)
        if match:
            return float(match.group(1).replace(",", ".")) * 1_000_000
        match = re.search(r"(\d+(?:[\.,]\d+)?)\s*k\b", text)
        if match:
            return float(match.group(1).replace(",", ".")) * 1_000
        match = re.search(r"\b(\d{5,})\b", text)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _parse_time_range(text: str) -> Optional[tuple[int, int]]:
        match = re.search(r"(\d{1,2})\s*h?\s*(?:-|den|toi)\s*(\d{1,2})\s*h?", text)
        if not match:
            return None
        start = int(match.group(1))
        end = int(match.group(2))
        if 0 <= start < end <= 24:
            return start * 60, end * 60
        return None

    @staticmethod
    def _extract_common_locked_pois(text: str) -> List[str]:
        candidates = {
            "dai noi": "Đại Nội",
            "cho dong ba": "Chợ Đông Ba",
            "chua thien mu": "Chùa Thiên Mụ",
            "lang tu duc": "Lăng Tự Đức",
            "lang khai dinh": "Lăng Khải Định",
            "cafe muoi": "Cafe muối",
            "bun bo": "Bún bò Huế",
        }
        return [label for key, label in candidates.items() if key in text]

    def _is_hue(self, destination: str) -> bool:
        text = self._normalize(destination)
        return "hue" in text

    def _is_confirmation(self, message: str) -> bool:
        text = self._normalize(message)
        return any(marker in text for marker in CONFIRMATION_MARKERS)
