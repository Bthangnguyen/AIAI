"""Diversity scoring — Shannon Entropy + Target Distribution Fit.

Measures how diverse a set of POIs is across categories,
and how well the distribution matches a target profile for the trip type.
"""

import math
from typing import Dict, List, Optional, Tuple
from collections import Counter


# Default target distributions by trip type
DEFAULT_DISTRIBUTIONS: Dict[str, Dict[str, float]] = {
    "sightseeing": {
        "culture": 0.35, "nature": 0.20, "food": 0.15,
        "cafe": 0.10, "shopping": 0.10, "rest": 0.10,
    },
    "food_tour": {
        "food": 0.45, "cafe": 0.20, "culture": 0.10,
        "shopping": 0.10, "nature": 0.10, "rest": 0.05,
    },
    "cafe_hopping": {
        "cafe": 0.50, "food": 0.20, "shopping": 0.10,
        "culture": 0.10, "nature": 0.05, "rest": 0.05,
    },
    "cultural": {
        "culture": 0.50, "food": 0.15, "nature": 0.10,
        "cafe": 0.10, "shopping": 0.10, "rest": 0.05,
    },
    "nightlife": {
        "food": 0.30, "cafe": 0.25, "shopping": 0.15,
        "culture": 0.10, "nature": 0.05, "rest": 0.15,
    },
    "mixed": {
        "culture": 0.25, "food": 0.20, "nature": 0.15,
        "cafe": 0.15, "shopping": 0.15, "rest": 0.10,
    },
}

# Threshold by trip type specificity
THRESHOLDS = {
    "mixed": 0.65,
    "sightseeing": 0.50,
    "cultural": 0.50,
    "food_tour": 0.40,
    "cafe_hopping": 0.40,
    "nightlife": 0.50,
}
DEFAULT_THRESHOLD = 0.50


class DiversityScorer:
    """Scores category diversity of POIs using entropy + target distribution fit."""

    def score(
        self,
        categories: List[str],
        trip_type: str = "mixed",
        target_distribution: Optional[Dict[str, float]] = None,
    ) -> float:
        """Compute diversity score in [0, 1].
        
        Combined = 0.5 * normalized_entropy + 0.5 * target_distribution_fit
        
        Args:
            categories: List of POI category strings
            trip_type: Trip type for default target distribution
            target_distribution: Override target distribution
            
        Returns:
            Float 0.0-1.0 diversity score
        """
        if not categories or len(categories) <= 1:
            return 0.0

        entropy = self._shannon_entropy(categories)
        target = target_distribution or DEFAULT_DISTRIBUTIONS.get(
            trip_type, DEFAULT_DISTRIBUTIONS["mixed"]
        )
        target_fit = self._target_distribution_fit(categories, target)

        return round(0.5 * entropy + 0.5 * target_fit, 4)

    def get_threshold(self, trip_type: str = "mixed") -> float:
        """Get diversity threshold for a trip type."""
        return THRESHOLDS.get(trip_type, DEFAULT_THRESHOLD)

    def is_diverse_enough(
        self,
        categories: List[str],
        trip_type: str = "mixed",
        target_distribution: Optional[Dict[str, float]] = None,
    ) -> bool:
        """Check if category set meets diversity threshold."""
        return self.score(categories, trip_type, target_distribution) >= self.get_threshold(trip_type)

    def suggest_swaps(
        self,
        categories: List[str],
        trip_type: str = "mixed",
        target_distribution: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[str, str]]:
        """Suggest category swaps: (over-represented, under-represented) pairs.
        
        Returns list of (remove_category, add_category) suggestions.
        """
        target = target_distribution or DEFAULT_DISTRIBUTIONS.get(
            trip_type, DEFAULT_DISTRIBUTIONS["mixed"]
        )
        n = len(categories)
        if n == 0:
            return []

        actual = Counter(categories)
        actual_dist = {cat: count / n for cat, count in actual.items()}

        # Find over-represented and under-represented categories
        over = []  # (excess, category)
        under = []  # (deficit, category)

        all_cats = set(list(actual_dist.keys()) + list(target.keys()))
        for cat in all_cats:
            actual_pct = actual_dist.get(cat, 0.0)
            target_pct = target.get(cat, 0.0)
            diff = actual_pct - target_pct
            if diff > 0.1:
                over.append((diff, cat))
            elif diff < -0.1:
                under.append((-diff, cat))

        over.sort(reverse=True)
        under.sort(reverse=True)

        swaps = []
        for (_, over_cat), (_, under_cat) in zip(over, under):
            swaps.append((over_cat, under_cat))

        return swaps

    @staticmethod
    def _shannon_entropy(categories: List[str]) -> float:
        """Normalized Shannon entropy in [0, 1]."""
        n = len(categories)
        if n <= 1:
            return 0.0

        counts = Counter(categories)
        num_unique = len(counts)
        if num_unique <= 1:
            return 0.0

        max_entropy = math.log2(num_unique)
        if max_entropy == 0:
            return 0.0

        entropy = -sum(
            (c / n) * math.log2(c / n)
            for c in counts.values()
        )
        return min(1.0, entropy / max_entropy)

    @staticmethod
    def _target_distribution_fit(
        categories: List[str],
        target: Dict[str, float],
    ) -> float:
        """Fit score: 1 - 0.5 * Σ|actual_i - target_i|. In [0, 1]."""
        n = len(categories)
        if n == 0:
            return 0.0

        actual = Counter(categories)
        actual_dist = {cat: count / n for cat, count in actual.items()}

        all_cats = set(list(actual_dist.keys()) + list(target.keys()))
        total_diff = sum(
            abs(actual_dist.get(cat, 0.0) - target.get(cat, 0.0))
            for cat in all_cats
        )

        return max(0.0, 1.0 - 0.5 * total_diff)
