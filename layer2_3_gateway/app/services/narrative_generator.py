"""Post-solve narrative generation — template-based (no LLM dependency).

Generates per-day narrative titles, flow descriptions, and
"why this plan works" bullet points based on the actual POI sequence.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NarrativeGenerator:
    """Generates narrative descriptions for solved itineraries."""

    def generate(self, itinerary_data: dict) -> dict:
        """Generate narrative for each day in the itinerary.
        
        Args:
            itinerary_data: Dict with 'days' list, each day having 'stops'
            
        Returns:
            Updated itinerary_data with narrative fields added per day
        """
        days = itinerary_data.get("days", [])
        is_single_session = len(days) == 1

        for day in days:
            stops = day.get("stops", [])
            if not stops:
                continue

            stop_names = [s.get("poi_name", "") for s in stops if s.get("poi_id") != "__rest_break__"]
            categories = [s.get("category", "") for s in stops if s.get("poi_id") != "__rest_break__"]
            n = len(stop_names)

            if n == 0:
                continue

            # Generate title
            day["narrative_title"] = self._generate_title(
                stop_names, categories, day.get("day_index", 0), is_single_session
            )

            # Generate description
            day["narrative_description"] = self._generate_description(
                stop_names, categories, is_single_session
            )

            # Plan reasoning bullets
            day["plan_reasoning"] = self._generate_reasoning(
                stop_names, categories, day
            )

        return itinerary_data

    def _generate_title(
        self,
        names: List[str],
        categories: List[str],
        day_index: int,
        is_single_session: bool,
    ) -> str:
        """Generate a short narrative title for the day."""
        n = len(names)
        # Determine dominant vibe from categories
        vibe = self._detect_vibe(categories)

        if is_single_session:
            if n == 1:
                return f"Khám phá {names[0]}"
            elif vibe == "food":
                return f"Hành trình ẩm thực từ {names[0]}"
            elif vibe == "culture":
                return f"Ngược dòng lịch sử tại {names[0]}"
            else:
                return f"Trải nghiệm {names[0]} và {names[-1]}"
        else:
            prefix = f"Ngày {day_index + 1}"
            if n == 1:
                return f"{prefix}: Khám phá {names[0]}"
            elif vibe == "food":
                return f"{prefix}: Ẩm thực đường phố"
            elif vibe == "culture":
                return f"{prefix}: Làm quen với di sản"
            elif vibe == "nature":
                return f"{prefix}: Hòa mình thiên nhiên"
            else:
                return f"{prefix}: Từ {names[0]} đến {names[-1]}"

    def _generate_description(
        self,
        names: List[str],
        categories: List[str],
        is_single_session: bool,
    ) -> str:
        """Generate flow description as a short story."""
        n = len(names)

        if n == 1:
            return f"Một trải nghiệm tập trung tại {names[0]}, thoải mái khám phá không vội vàng."

        if n == 2:
            return (
                f"Bắt đầu tại {names[0]}, sau đó ghé {names[1]}. "
                f"Một hành trình ngắn nhưng đầy ấn tượng."
            )

        # 3+ stops
        middle = ", ".join(names[1:-1])
        return (
            f"Hành trình bắt đầu tại {names[0]}, "
            f"lần lượt ghé {middle}, "
            f"và kết thúc tại {names[-1]}. "
            f"Tổng cộng {n} điểm đến được sắp xếp tối ưu về khoảng cách."
        )

    def _generate_reasoning(
        self,
        names: List[str],
        categories: List[str],
        day: dict,
    ) -> List[str]:
        """Generate 'why this plan works' bullet points."""
        n = len(names)
        reasons = []

        reasons.append(f"{n} điểm đến được sắp xếp tối ưu về khoảng cách")

        # Category diversity
        unique_cats = len(set(categories))
        if unique_cats >= 3:
            reasons.append(f"Đa dạng {unique_cats} loại trải nghiệm khác nhau")
        elif unique_cats == 2:
            reasons.append("Kết hợp 2 loại hình trải nghiệm")

        # Time info
        total_visit = day.get("total_visit_min", 0)
        if total_visit:
            reasons.append(f"Tổng thời gian tham quan: {total_visit // 60}h{total_visit % 60:02d}")

        # Fee info
        total_fee = day.get("total_entrance_fee", 0)
        if total_fee > 0:
            reasons.append(f"Tổng phí tham quan: {total_fee:,.0f}₫")
        elif total_fee == 0:
            reasons.append("Không có phí tham quan")

        return reasons

    @staticmethod
    def _detect_vibe(categories: List[str]) -> str:
        """Detect dominant vibe from category list."""
        if not categories:
            return "mixed"

        from collections import Counter
        counts = Counter(c.lower() for c in categories)
        top_cat = counts.most_common(1)[0][0]
        total = len(categories)
        top_ratio = counts.most_common(1)[0][1] / total

        if top_ratio >= 0.5:
            if top_cat in ("food", "restaurant", "nhà hàng", "quán ăn", "street_food"):
                return "food"
            elif top_cat in ("culture", "temple", "palace", "museum", "heritage"):
                return "culture"
            elif top_cat in ("nature", "park", "garden", "lake", "beach"):
                return "nature"

        return "mixed"
