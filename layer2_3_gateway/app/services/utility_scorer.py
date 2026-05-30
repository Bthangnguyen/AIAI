"""Stable POI utility scoring.

The scorer is intentionally small and inspectable. It does not try to infer
"comfort" or "novelty"; those signals are noisy in the current POI data. The
main control knobs are distribution, explicit intent tag match, real semantic
similarity when available, POI quality, and diversity.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from app.schemas.trip import POIResponse, POIScoreBreakdown, LLMDataContract


CATEGORY_GROUP_MAP = {
    "food": {
        "food", "restaurant", "nhà hàng", "quán ăn", "eatery", "street_food",
        "streetfood", "bún bò", "bún", "cơm", "cơm hến", "bánh bèo",
        "bánh khoái", "bánh canh", "chay", "dessert", "chè",
    },
    "cafe": {"cafe", "coffee", "cà phê", "ca phe", "tea", "trà"},
    "culture": {
        "culture", "cultural", "historic", "historical", "history",
        "temple", "pagoda", "tourism_attraction", "heritage", "museum",
        "bảo tàng", "landmark", "unesco", "palace", "citadel",
        "mausoleum", "tomb", "ca huế",
    },
    "nature": {"nature", "park", "công viên", "garden", "lake", "river", "beach", "lagoon"},
    "nightlife": {"nightlife", "bar", "night_market", "pub", "karaoke", "walking_street"},
    "shopping": {"shopping", "shop", "market", "chợ"},
    "art": {"art", "gallery", "nghệ thuật"},
    "wellness": {"wellness", "spa", "massage"},
    "adventure": {"adventure", "trekking", "outdoor", "sport", "hiking"},
}

NOISE_CATEGORY_GROUPS = {"hotel", "lodging", "accommodation"}
NOISE_NAME_TOKENS = {
    "hotel", "khach san", "khách sạn", "resort", "homestay", "villa",
    "motel", "hostel", "guesthouse", "apartment",
}

INTENT_TAG_ALIASES = {
    "foodie": {"food", "street_food", "streetfood", "local_food", "bun_bo", "com_hen", "banh_hue", "dessert"},
    "food": {"food", "street_food", "streetfood", "local_food", "bun_bo", "com_hen", "banh_hue", "dessert"},
    "local_cuisine": {"food", "street_food", "streetfood", "local_food", "bun_bo", "com_hen", "banh_hue", "dessert"},
    "street_food": {"street_food", "streetfood", "food", "snack", "dessert"},
    "bun_bo": {"bun_bo", "bún bò", "bun bo"},
    "che": {"che", "chè", "dessert", "hue_sweet_soup"},
    "dessert": {"che", "chè", "dessert", "hue_sweet_soup"},
    "salt_coffee": {"salt_coffee", "cafe_muoi", "cafe muối", "ca phe muoi", "cà phê muối"},
    "cafe_muoi": {"salt_coffee", "cafe_muoi", "cafe muối", "ca phe muoi", "cà phê muối"},
    "cafe_hopping": {"cafe", "coffee", "cà phê", "ca phe", "salt_coffee", "cafe_muoi"},
    "cafe": {"cafe", "coffee", "cà phê", "ca phe", "salt_coffee", "cafe_muoi"},
    "vegetarian": {"vegetarian", "vegan", "chay", "ăn chay"},
    "culture": {"culture", "cultural", "heritage", "historic", "history", "museum", "palace", "citadel", "tomb"},
    "cultural": {"culture", "cultural", "heritage", "historic", "history", "museum", "palace", "citadel", "tomb"},
    "nightlife": {"nightlife", "night_market", "walking_street", "phố đi bộ", "di dao", "đi dạo"},
    "walking_street": {"walking_street", "phố đi bộ", "di dao", "đi dạo", "nightlife"},
    "nature": {"nature", "park", "garden", "lake", "river", "outdoor"},
}


def normalize(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9\s_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _haystack(poi: POIResponse) -> str:
    fields = [
        poi.name,
        poi.category,
        poi.category_group or "",
        poi.description or "",
        " ".join(poi.tags or []),
    ]
    return normalize(" ".join(str(v) for v in fields if v))


def is_noise_poi(poi: POIResponse) -> bool:
    category = normalize(poi.category)
    group = normalize(poi.category_group or "")
    name = normalize(poi.name)
    if category in NOISE_CATEGORY_GROUPS or group in NOISE_CATEGORY_GROUPS:
        return True
    return any(token in name for token in {normalize(t) for t in NOISE_NAME_TOKENS})


class UtilityScorer:
    """Computes stable POI score from explicit planning signals."""

    WEIGHTS = {
        "distribution_boost": 0.35,
        "intent_tag_match": 0.25,
        "semantic_score": 0.20,
        "quality_score": 0.15,
        "diversity_gain": 0.05,
        "localness_score": 0.00,
        "novelty_score": 0.00,
        "comfort_score": 0.00,
        "budget_score": 0.00,
        "distance_score": 0.00,
    }

    _DEFAULT_DISTRIBUTION = {
        "culture": 0.35,
        "food": 0.30,
        "cafe": 0.15,
        "nightlife": 0.10,
        "nature": 0.10,
    }

    def score_poi(
        self,
        poi: POIResponse,
        contract: LLMDataContract,
        cosine_similarity: float | None,
        existing_categories,
        existing_tags=None,
    ) -> POIScoreBreakdown:
        semantic = self._clean_similarity(cosine_similarity)
        quality = min(1.0, max(0.0, poi.priority_score or 0.5))
        distribution = self._compute_distribution_boost(poi, contract)
        intent_tag = self._compute_intent_tag_match(poi, contract)
        budget = self._compute_budget_fit(poi, contract)

        fine_keys = self._get_fine_grained_keys(poi)
        diversity_gain = self._compute_diversity_gain(
            self._category_to_group(poi.category),
            existing_categories,
            fine_grained_keys=fine_keys,
            existing_tags=existing_tags,
        )

        return POIScoreBreakdown(
            semantic_score=semantic,
            quality_score=quality,
            distribution_boost=distribution,
            intent_tag_match=intent_tag,
            localness_score=0.5,
            novelty_score=0.5,
            comfort_score=0.5,
            budget_score=budget,
            distance_score=0.5,
            diversity_gain=diversity_gain,
        )

    def compute_utility(self, breakdown: POIScoreBreakdown) -> float:
        score = sum(self.WEIGHTS[field] * getattr(breakdown, field) for field in self.WEIGHTS)
        return max(0.0, min(1.0, score))

    @staticmethod
    def _clean_similarity(value: float | None) -> float:
        if value is None:
            return 0.5
        return max(0.0, min(1.0, float(value)))

    @staticmethod
    def _category_to_group(category: str | None) -> str:
        cat = normalize(category)
        for group, members in CATEGORY_GROUP_MAP.items():
            if cat in {normalize(m) for m in members}:
                return group
        return "other"

    def _distribution(self, contract: LLMDataContract) -> dict[str, float]:
        distribution = dict(contract.target_category_distribution or {})
        return distribution or dict(self._DEFAULT_DISTRIBUTION)

    def _compute_distribution_boost(self, poi: POIResponse, contract: LLMDataContract) -> float:
        distribution = self._distribution(contract)
        group = self._category_to_group(poi.category_group or poi.category)
        if group == "other":
            return 0.02
        max_val = max(distribution.values()) if distribution else 1.0
        val = distribution.get(group, 0.0)
        if val <= 0:
            return 0.05
        return 0.50 + 0.50 * (val / max_val)

    def _compute_intent_tag_match(self, poi: POIResponse, contract: LLMDataContract) -> float:
        intent_terms = self._expanded_intent_terms(contract)
        if not intent_terms:
            return 0.5
        hay = _haystack(poi)
        matches = 0
        for term in intent_terms:
            norm = normalize(term)
            if norm and norm in hay:
                matches += 1
        ratio = matches / max(1, min(6, len(intent_terms)))
        if matches == 0:
            return 0.20
        return min(1.0, 0.45 + ratio)

    def _expanded_intent_terms(self, contract: LLMDataContract) -> set[str]:
        raw_terms: list[str] = []
        raw_terms.extend(contract.tags or [])
        raw_terms.extend(contract.food_preferences or [])
        raw_terms.extend(contract.locked_pois or [])
        if contract.trip_type:
            raw_terms.append(contract.trip_type)
        if contract.distribution_description:
            raw_terms.append(contract.distribution_description)

        expanded: set[str] = set()
        for term in raw_terms:
            norm = normalize(term)
            if not norm:
                continue
            expanded.add(term)
            expanded.add(norm)
            expanded.update(INTENT_TAG_ALIASES.get(norm, set()))
        return expanded

    def _compute_budget_fit(self, poi: POIResponse, contract: LLMDataContract) -> float:
        if getattr(contract, "budget_is_unlimited", False) or not contract.budget_max:
            return 0.7
        cost = poi.entrance_fee or poi.price or 0.0
        if cost > contract.budget_max * 0.30:
            return 0.0
        if cost > contract.budget_max * 0.15:
            return 0.4
        return 0.8 if cost > 0 else 0.7

    def _compute_comfort(self, poi: POIResponse, contract: LLMDataContract) -> float:
        """Legacy compatibility; comfort is not used in utility weights."""
        score = 0.5
        tolerance = normalize(getattr(contract, "walking_tolerance", None) or "medium")
        hay = _haystack(poi)
        is_walking_heavy = (
            self._category_to_group(poi.category) in {"nature", "adventure"}
            or "walking" in hay
            or "hiking" in hay
            or poi.visit_duration_min >= 120
        )
        if tolerance == "low" and is_walking_heavy:
            return 0.25
        if tolerance == "high" and is_walking_heavy:
            return 0.75
        return score

    def _get_fine_grained_keys(self, poi: POIResponse) -> list[str]:
        hay = _haystack(poi)
        keys: list[str] = []
        if any(token in hay for token in ("chua", "temple", "pagoda", "spiritual")):
            keys.append("spiritual")
        if any(token in hay for token in ("lang vua", "lang ", "mausoleum", "tomb")):
            keys.append("royal_tomb")
        if any(token in hay for token in ("dai noi", "hoang thanh", "citadel", "palace")):
            keys.append("palace")
        if any(token in hay for token in ("lang nghe", "craft")):
            keys.append("craft_village")
        if any(token in hay for token in ("garden", "nature", "park", "lake", "river", "outdoor", "landscape")):
            keys.append("nature_garden")
        if any(token in hay for token in ("bun bo", "bun_bo")):
            keys.append("dish_bun_bo")
        if any(token in hay for token in ("com hen", "com_hen")):
            keys.append("dish_com_hen")
        if any(token in hay for token in ("cafe muoi", "ca phe muoi", "salt_coffee", "cafe_muoi")):
            keys.append("dish_cafe_muoi")
        if any(token in hay for token in ("banh beo", "banh nam", "banh loc", "banh khoai", "banh it")):
            keys.append("dish_banh_hue")
        if any(token in hay for token in ("che", "dessert", "hue_sweet_soup")):
            keys.append("dish_che")
        return keys

    def _compute_diversity_gain(
        self,
        category: str,
        existing_categories,
        fine_grained_keys: Iterable[str] | None = None,
        existing_tags=None,
    ) -> float:
        if isinstance(existing_categories, dict):
            cat_count = existing_categories.get(category, 0)
            if cat_count == 0:
                for raw_key, count in existing_categories.items():
                    if self._category_to_group(raw_key) == category:
                        cat_count += count
        else:
            cat_count = 1 if category in existing_categories else 0
        if cat_count == 0:
            cat_gain = 1.0
        elif cat_count == 1:
            cat_gain = 0.45
        elif cat_count == 2:
            cat_gain = 0.15
        else:
            cat_gain = 0.05

        tag_gain = 1.0
        if fine_grained_keys and existing_tags is not None:
            penalties = []
            for key in fine_grained_keys:
                count = existing_tags.get(key, 0) if isinstance(existing_tags, dict) else (1 if key in existing_tags else 0)
                if count == 1:
                    penalties.append(0.65)
                elif count >= 2:
                    penalties.append(0.95)
                else:
                    penalties.append(0.0)
            tag_gain = 1.0 - max(penalties or [0.0])
        return min(cat_gain, tag_gain)
