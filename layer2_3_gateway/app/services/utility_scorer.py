"""Utility Scorer — computes per-POI utility score based on user intent + POI attributes.

Phase 0B: Bridges Layer 2/3's POI scoring with Layer 4's OR-Tools drop penalty.
Each POI gets a utility_score ∈ [0, 1] used as drop_penalty in AddDisjunction.
"""

from app.schemas.trip import POIResponse, POIScoreBreakdown, LLMDataContract


# 9 category groups mapping DB categories → distribution keys
CATEGORY_GROUP_MAP = {
    "food": {"restaurant", "nhà hàng", "quán ăn", "bún bò", "bánh mì",
             "cháo", "bún", "cơm", "hải sản", "chả cuốn", "cơm hến",
             "bánh canh", "bánh ướt", "bánh bèo", "bánh ít", "bắp",
             "bình dân", "chay", "cung đình", "bánh khoái", "food"},
    "cafe": {"cafe", "cà phê", "trà", "coffee", "tea"},
    "culture": {"historic", "historical", "history", "temple", "tourism_attraction",
                "culture", "cultural", "heritage", "museum", "bảo tàng", "landmark",
                "UNESCO", "Hoàng thành", "Kinh thành", "ca Huế", "dân gian"},
    "nature": {"nature", "park", "công viên", "garden", "lake", "river"},
    "nightlife": {"bar", "night_market", "pub", "karaoke", "nightlife"},
    "shopping": {"shop", "chợ", "market", "mua sắm", "shopping"},
    "art": {"gallery", "art", "nghệ thuật"},
    "wellness": {"spa", "massage", "wellness"},
    "adventure": {"trekking", "outdoor", "sport", "hiking", "adventure"},
}


class UtilityScorer:
    """Computes per-POI utility score based on user intent + POI attributes."""

    WEIGHTS = {
        "semantic_score":      0.20,
        "quality_score":       0.12,
        "distribution_boost":  0.24,
        "localness_score":     0.10,
        "novelty_score":       0.00,
        "budget_score":        0.08,
        "comfort_score":       0.00,
        "distance_score":      0.08,
        "diversity_gain":      0.18,
    }

    def score_poi(
        self,
        poi: POIResponse,
        contract: LLMDataContract,
        cosine_similarity: float,
        existing_categories: set,
        existing_tags: set = None,
    ) -> POIScoreBreakdown:
        """Score a single POI against user intent."""

        semantic = cosine_similarity  # from pgvector

        quality = min(1.0, poi.priority_score)  # existing field, 0-1

        distribution_boost = self._compute_distribution_boost(poi, contract)

        localness = self._compute_localness(poi)  # from tags: "local", "hidden_gem"

        novelty = self._compute_novelty(poi)  # from tags: "unique", "off_beaten_path"

        comfort = self._compute_comfort(poi, contract)  # match pace/walking tolerance

        budget = self._compute_budget_fit(poi, contract)  # fee vs budget ratio

        distance = 0.5  # placeholder — computed in spatial filter

        fine_keys = self._get_fine_grained_keys(poi)
        diversity_gain = self._compute_diversity_gain(
            poi.category,
            existing_categories,
            fine_grained_keys=fine_keys,
            existing_tags=existing_tags,
        )

        return POIScoreBreakdown(
            semantic_score=semantic,
            quality_score=quality,
            distribution_boost=distribution_boost,
            localness_score=localness,
            novelty_score=novelty,
            comfort_score=comfort,
            budget_score=budget,
            distance_score=distance,
            diversity_gain=diversity_gain,
        )

    def compute_utility(self, breakdown: POIScoreBreakdown) -> float:
        """Weighted sum of breakdown scores."""
        return sum(
            self.WEIGHTS[field] * getattr(breakdown, field)
            for field in self.WEIGHTS
        )

    # ─── Distribution boost ───

    @staticmethod
    def _category_to_group(category: str) -> str:
        """Map a DB category to one of the 9 distribution groups."""
        cat_lower = category.lower().strip()
        for group, members in CATEGORY_GROUP_MAP.items():
            if cat_lower in members:
                return group
        return "culture"  # default fallback

    # Balanced default distribution — used when LLM does not produce one
    _DEFAULT_DISTRIBUTION = {
        "food": 0.35, "culture": 0.35, "nature": 0.20,
        "nightlife": 0.05, "adventure": 0.05
    }

    def _compute_distribution_boost(self, poi: POIResponse, contract: LLMDataContract) -> float:
        """Boost score from LLM target_category_distribution.
        
        Scales the requested categories dynamically so they get a massive base boost (0.5 to 1.0)
        relative to the max requested ratio, giving them high priority over unrequested categories.
        """
        distribution = contract.target_category_distribution or self._DEFAULT_DISTRIBUTION
        group = self._category_to_group(poi.category)
        if not distribution:
            return 0.5
        max_val = max(distribution.values()) if distribution else 1.0
        val = distribution.get(group, 0.0)
        if val > 0:
            return 0.5 + 0.5 * (val / max_val)
        return 0.05

    # ─── Existing scoring methods ───

    def _compute_localness(self, poi: POIResponse) -> float:
        """Localness score based on POI tags. Supports local culture highlights."""
        if not poi.tags:
            return 0.5
        local_tags = {
            "địa phương", "quán địa phương", "local_eatery", "món huế", "streetfood", 
            "đặc sản", "dân dã", "local", "hidden_gem", "local_favorite",
            # Add cultural/historic local highlights for Hue specifically
            "di sản", "unesco", "hoàng cung", "lịch sử", "lăng mộ", "triều nguyễn", "văn hóa",
            "heritage", "historic", "historical", "culture"
        }
        matches = sum(1 for t in poi.tags if t.lower() in local_tags)
        if matches >= 2:
            return 0.9
        if matches == 1:
            return 0.7
        return 0.5

    def _compute_novelty(self, poi: POIResponse) -> float:
        """Novelty score based on POI tags."""
        if not poi.tags:
            return 0.5
        novelty_tags = {
            "độc đáo", "mới lạ", "ẩn mình", "ít người biết", "khác biệt", 
            "unique", "off_beaten_path", "hidden_gem", "rare", "unusual"
        }
        matches = sum(1 for t in poi.tags if t.lower() in novelty_tags)
        if matches >= 2:
            return 0.9
        if matches == 1:
            return 0.7
        return 0.5

    def _compute_comfort(self, poi: POIResponse, contract: LLMDataContract) -> float:
        """Comfort score based on user pace and walking tolerance."""
        score = 0.5

        if contract.preferred_pace == "chill":
            if poi.visit_duration_min > 120:
                score = 0.3
            else:
                score = 0.8 if poi.category in ("cafe", "restaurant", "spa") else 0.5
        elif contract.preferred_pace == "intense":
            score = 0.8 if poi.visit_duration_min > 60 else 0.5

        tolerance = (contract.walking_tolerance or "medium").lower()
        poi_tags = {t.lower() for t in (poi.tags or [])}
        is_walking_heavy = (
            poi.category.lower() in ("outdoor", "nature", "hiking")
            or "walking" in poi_tags
            or poi.visit_duration_min >= 120
        )

        if tolerance == "low" and is_walking_heavy:
            score = min(score, 0.25)
        elif tolerance == "high" and is_walking_heavy:
            score = max(score, 0.75)

        return score

    def _compute_budget_fit(self, poi: POIResponse, contract: LLMDataContract) -> float:
        """How well POI matches traveler's budget tier.
        
        Instead of strictly penalizing paid cultural highlights, evaluate viability 
        against the overall trip budget. Keep score high for paid spots that fit nicely.
        """
        if not contract.budget_max:
            return 0.7  # default neutral score if no budget specified
            
        poi_cost = poi.entrance_fee or poi.price or 0.0
        
        # Exceeds 30% of total budget -> heavily penalized
        if poi_cost > contract.budget_max * 0.3:
            return 0.15
            
        # Exceeds 15% of total budget -> moderately penalized but very viable
        if poi_cost > contract.budget_max * 0.15:
            return 0.5
            
        # Fits nicely within overall budget
        return 0.8 if poi_cost > 0 else 0.7

    def _get_fine_grained_keys(self, poi: POIResponse) -> list[str]:
        """Determine fine-grained sub-type/tag keys for diversity mapping."""
        keys = []
        name_lower = poi.name.lower()
        tags_lower = {t.lower() for t in (poi.tags or [])}

        # 1. Pagoda / Temple / Spiritual (Chùa, Đền, Miếu, Tổ định, Tịnh xá, Tâm linh)
        spiritual_words = {"chùa", "đền", "miếu", "tổ đình", "tịnh xá", "am", "nhà thờ"}
        spiritual_tags = {"chùa", "temple", "pagoda", "đền thờ", "tâm linh", "phật giáo", "religion", "phật học"}
        if any(w in name_lower for w in spiritual_words) or tags_lower.intersection(spiritual_tags):
            if "nhà hàng" not in name_lower and "khách sạn" not in name_lower and "quán" not in name_lower:
                keys.append("spiritual")

        # 2. Royal Tomb (Lăng tẩm)
        tomb_words = {"lăng"}
        tomb_tags = {"lăng mộ", "mausoleum", "lăng vua", "tomb"}
        if any(w in name_lower for w in tomb_words) or tags_lower.intersection(tomb_tags):
            keys.append("royal_tomb")

        # 3. Palace / Citadel (Cung điện, Hoàng thành, Đại Nội)
        palace_words = {"đại nội", "hoàng thành", "tử cấm thành", "ngọ môn", "phủ tùng thiện", "phủ kiên thái"}
        palace_tags = {"hoàng cung", "cung điện", "kinh thành", "hoàng thành", "tử cấm thành", "citadel", "palace"}
        if any(w in name_lower for w in palace_words) or tags_lower.intersection(palace_tags):
            keys.append("palace")

        # 4. Craft Village (Làng nghề, Thủ công)
        craft_words = {"làng nghề", "phường đúc"}
        craft_tags = {"làng nghề", "thủ công", "craft"}
        if any(w in name_lower for w in craft_words) or tags_lower.intersection(craft_tags):
            keys.append("craft_village")

        # 5. Nature / Garden / Landscape (Nhà vườn, Sông, Hồ)
        nature_words = {"nhà vườn", "công viên", "hồ", "sông", "đầm phá"}
        nature_tags = {"garden", "nature", "park", "lake", "river", "outdoor", "landscape"}
        if any(w in name_lower for w in nature_words) or tags_lower.intersection(nature_tags):
            keys.append("nature_garden")

        # 6. Specific Food Dishes (Bún bò, Cơm hến, Bánh Huế, Cafe muối)
        if "bún bò" in name_lower or "bun bo" in name_lower:
            keys.append("dish_bun_bo")
        elif "cơm hến" in name_lower or "com hen" in name_lower:
            keys.append("dish_com_hen")
        elif "cafe muối" in name_lower or "cafe muoi" in name_lower or "cà phê muối" in name_lower:
            keys.append("dish_cafe_muoi")
        elif any(w in name_lower for w in ["bánh bèo", "bánh nậm", "bánh lọc", "bánh khoái", "bánh ít"]):
            keys.append("dish_banh_hue")

        return keys

    def _compute_diversity_gain(
        self,
        category: str,
        existing_categories,
        fine_grained_keys: list[str] = None,
        existing_tags: set = None,
    ) -> float:
        """Marginal gain: new category/tag = high gain, repeated = decay.

        existing_categories can be a set or a dict/Counter.
        When it is a dict, the value is the running count for that category.
        """
        # 1. Generic Category level decay
        if isinstance(existing_categories, dict):
            cat_count = existing_categories.get(category, 0)
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

        # 2. Fine-grained tag/sub-category level decay
        tag_gain = 1.0
        if fine_grained_keys and existing_tags is not None:
            max_penalty = 0.0
            for key in fine_grained_keys:
                if isinstance(existing_tags, dict):
                    key_count = existing_tags.get(key, 0)
                else:
                    key_count = 1 if key in existing_tags else 0

                if key_count == 1:
                    penalty = 0.50  # 50% penalty for 2nd pagoda/tomb
                elif key_count >= 2:
                    penalty = 0.85  # 85% penalty for 3rd+ pagoda/tomb
                else:
                    penalty = 0.0
                max_penalty = max(max_penalty, penalty)
            tag_gain = 1.0 - max_penalty

        return min(cat_gain, tag_gain)
