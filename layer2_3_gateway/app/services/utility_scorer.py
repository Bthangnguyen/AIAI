"""Utility Scorer — computes per-POI utility score based on user intent + POI attributes.

Phase 0B: Bridges Layer 2/3's POI scoring with Layer 4's OR-Tools drop penalty.
Each POI gets a utility_score ∈ [0, 1] used as drop_penalty in AddDisjunction.
"""

from app.schemas.trip import POIResponse, POIScoreBreakdown, LLMDataContract


class UtilityScorer:
    """Computes per-POI utility score based on user intent + POI attributes."""

    WEIGHTS = {
        "semantic_score":  0.28,
        "quality_score":   0.18,
        "localness_score": 0.14,
        "novelty_score":   0.10,
        "budget_score":    0.10,
        "comfort_score":   0.10,
        "distance_score":  0.06,
        "diversity_gain":  0.04,
    }

    def score_poi(
        self,
        poi: POIResponse,
        contract: LLMDataContract,
        cosine_similarity: float,
        existing_categories: set,
    ) -> POIScoreBreakdown:
        """Score a single POI against user intent."""

        semantic = cosine_similarity  # from pgvector

        quality = min(1.0, poi.priority_score)  # existing field, 0-1

        localness = self._compute_localness(poi)  # from tags: "local", "hidden_gem"

        novelty = self._compute_novelty(poi)  # from tags: "unique", "off_beaten_path"

        comfort = self._compute_comfort(poi, contract)  # match pace/walking tolerance

        budget = self._compute_budget_fit(poi, contract)  # fee vs budget ratio

        distance = 0.5  # placeholder — computed in spatial filter

        diversity_gain = self._compute_diversity_gain(poi.category, existing_categories)

        return POIScoreBreakdown(
            semantic_score=semantic,
            quality_score=quality,
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

    def _compute_localness(self, poi: POIResponse) -> float:
        """Localness score based on POI tags."""
        if not poi.tags:
            return 0.5
        local_tags = {"local", "hidden_gem", "local_favorite", "off_beaten_path"}
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
        novelty_tags = {"unique", "off_beaten_path", "hidden_gem", "rare", "unusual"}
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
        """How well POI fits user budget."""
        if not contract.budget_max or poi.entrance_fee == 0:
            return 0.7
        ratio = poi.entrance_fee / contract.budget_max
        if ratio > 0.3:
            return 0.2  # Too expensive relative to total budget
        return max(0.1, 1.0 - ratio * 3)

    def _compute_diversity_gain(self, category: str, existing_categories: set) -> float:
        """Marginal gain: new category = high gain, repeated = low."""
        if category not in existing_categories:
            return 1.0
        count = sum(1 for c in existing_categories if c == category)
        return max(0.0, 1.0 - count * 0.3)
