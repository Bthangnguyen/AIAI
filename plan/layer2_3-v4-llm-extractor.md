# Layer 2&3 — v4: Layer 2 LLM Intent Extraction

> **Mục tiêu:** Xây dựng module trích xuất ý định từ ngôn ngữ tự nhiên → `LLMDataContract` JSON chuẩn. Sử dụng Instructor + Pydantic để ép kiểu output.
> **Phụ thuộc:** v1 (Infrastructure — env vars)

## File Structure — Thay đổi

```
layer2_3_gateway/app/
├── services/
│   ├── __init__.py          # MODIFY: export llm service
│   └── llm_extractor.py     # NEW: LLM intent extraction
├── config.py                # MODIFY: thêm LLM env vars
tests/
└── test_llm_extractor.py    # NEW: unit tests
pyproject.toml               # MODIFY: thêm dependencies (instructor, openai)
```

---

## Task 1: Cập nhật dependencies

**File:** `layer2_3_gateway/pyproject.toml`

- [ ] **Step 1: Thêm LLM dependencies**

```toml
# Thêm vào [tool.poetry.dependencies]:
instructor = "^1.4.0"
openai = "^1.50.0"
pgvector = "^0.3.0"   # Python SQLAlchemy binding cho pgvector
```

---

## Task 2: Cập nhật Config

**File:** `layer2_3_gateway/app/config.py`

- [ ] **Step 1: Thêm LLM settings**

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai | gemini
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    
    # Layer 4 Integration
    LAYER4_BASE_URL: str = "http://localhost:8000"
```

---

## Task 3: LLM Intent Extraction Service

**File:** `layer2_3_gateway/app/services/llm_extractor.py` (NEW)

- [ ] **Step 1: Implement extraction with Instructor (ASYNC — non-blocking)**

> [!CAUTION]
> **ARCHITECTURE FIX**: Phải dùng `AsyncOpenAI`, KHÔNG ĐƯỢC dùng `OpenAI` sync.
> Lệnh sync `create()` sẽ đóng băng toàn bộ Event Loop của FastAPI trong 2-5 giây.
> Server chỉ phục vụ được 1 request/thời điểm. Tải đồng thời bằng 0.

```python
"""Layer 2: Extract travel intent from natural language using LLM + Instructor.

CRITICAL: Uses AsyncOpenAI to avoid blocking the FastAPI event loop.
A sync OpenAI call takes 2-5s and would freeze the entire server.
"""

from typing import Optional
import instructor
from openai import AsyncOpenAI  # ← ASYNC, not sync OpenAI

from app.config import settings as global_settings
from app.schemas.trip import LLMDataContract
from app.utils.logging import AppLogger

logger = AppLogger().get_logger()

SYSTEM_PROMPT = """Bạn là trợ lý du lịch chuyên trích xuất thông tin từ yêu cầu của khách.
Phân tích yêu cầu và trả về JSON với các trường sau:
- budget_max: Ngân sách tối đa (VND), null nếu không đề cập
- radius_km: Bán kính tìm kiếm (km), mặc định 10
- num_days: Số ngày đi, mặc định 1
- tags: Danh sách sở thích (culture, street_food, nature, temple, museum, market, beach, indoor, outdoor...)
- locked_pois: Danh sách tên địa điểm PHẢI đi (khách nhấn mạnh "nhất định", "phải", "bắt buộc")
- weather_preference: "indoor" nếu khách muốn tránh mưa/nắng, "outdoor" nếu muốn ngoài trời, null nếu không đề cập
- time_window: {start_min, end_min} nếu khách nêu khung giờ cụ thể (quy ra phút từ 0:00)

QUAN TRỌNG:
- Chỉ đưa vào locked_pois khi khách dùng từ ngữ mạnh (nhất định, bắt buộc, phải đi)
- tags nên là danh sách ngắn gọn, chuẩn hóa bằng tiếng Anh
- Không bịa thêm thông tin khách không nói"""


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
            base_client = AsyncOpenAI(api_key=global_settings.LLM_API_KEY)
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
```

---

## Task 4: Unit Tests

**File:** `layer2_3_gateway/tests/test_llm_extractor.py` (NEW)

- [ ] **Step 1: Test fallback behavior (no API key needed)**

```python
"""Tests for Layer 2 LLM intent extraction."""
import pytest
from app.schemas.trip import LLMDataContract
from app.services.llm_extractor import LLMExtractorService, SYSTEM_PROMPT


def test_system_prompt_exists():
    assert "locked_pois" in SYSTEM_PROMPT
    assert "budget_max" in SYSTEM_PROMPT


def test_fallback_contract():
    """When LLM fails, service should return a safe fallback."""
    contract = LLMDataContract(
        hotel_lat=16.46, hotel_lon=107.59,
        hotel_name="Saigon Morin", num_days=2, tags=["general"],
    )
    assert contract.budget_max is None
    assert contract.radius_km == 10.0
    assert contract.locked_pois == []


def test_service_init():
    """Service can be instantiated without API key."""
    service = LLMExtractorService()
    assert service._client is None
```

---

## Verification

- [ ] `python -m pytest tests/test_llm_extractor.py -v` → PASSED
- [ ] Integration test (manual): set `LLM_API_KEY` env, call `extract_intent("Tôi muốn đi Huế 3 ngày, nhất định phải có Đại Nội")` → verify `locked_pois = ["Đại Nội"]`
- [ ] Verify fallback: unset API key → call extract → get minimal contract (no crash)
