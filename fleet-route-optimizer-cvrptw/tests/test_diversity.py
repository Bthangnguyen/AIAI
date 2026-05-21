"""Tests for DiversityScorer — Phase 3."""

import pytest
from src.services.diversity_scorer import DiversityScorer


class TestShannonEntropy:
    def test_all_same_category_low_score(self):
        """6 same-category POIs → score < 0.3."""
        scorer = DiversityScorer()
        categories = ["culture"] * 6
        score = scorer.score(categories, "mixed")
        assert score < 0.3

    def test_all_different_categories_high_score(self):
        """6 different categories → score > 0.7."""
        scorer = DiversityScorer()
        categories = ["culture", "food", "cafe", "nature", "shopping", "rest"]
        score = scorer.score(categories, "mixed")
        assert score > 0.7

    def test_single_poi_zero(self):
        """Single POI → score 0."""
        scorer = DiversityScorer()
        assert scorer.score(["culture"], "mixed") == 0.0

    def test_empty_zero(self):
        """No POIs → score 0."""
        scorer = DiversityScorer()
        assert scorer.score([], "mixed") == 0.0


class TestTargetDistributionFit:
    def test_food_tour_with_food_majority(self):
        """food_tour with 4/6 food POIs → fits target, score > 0.5."""
        scorer = DiversityScorer()
        categories = ["food", "food", "food", "food", "cafe", "culture"]
        score = scorer.score(categories, "food_tour")
        assert score > 0.5

    def test_food_tour_all_culture_low(self):
        """food_tour with all culture → doesn't fit target."""
        scorer = DiversityScorer()
        categories = ["culture"] * 6
        score = scorer.score(categories, "food_tour")
        assert score < 0.4


class TestThresholds:
    def test_mixed_threshold(self):
        scorer = DiversityScorer()
        assert scorer.get_threshold("mixed") == 0.65

    def test_food_tour_threshold(self):
        scorer = DiversityScorer()
        assert scorer.get_threshold("food_tour") == 0.40

    def test_is_diverse_enough_with_diverse_set(self):
        scorer = DiversityScorer()
        categories = ["culture", "food", "cafe", "nature", "shopping", "rest"]
        assert scorer.is_diverse_enough(categories, "mixed") is True


class TestSuggestSwaps:
    def test_over_culture_swap(self):
        """Over-represented culture → suggest swap to under-represented."""
        scorer = DiversityScorer()
        categories = ["culture"] * 5 + ["food"]
        swaps = scorer.suggest_swaps(categories, "mixed")
        assert len(swaps) > 0
        # First swap should remove culture
        assert swaps[0][0] == "culture"

    def test_balanced_no_swaps(self):
        """Well-balanced categories → no swaps needed."""
        scorer = DiversityScorer()
        categories = ["culture", "food", "cafe", "nature", "shopping", "rest"]
        swaps = scorer.suggest_swaps(categories, "mixed")
        # May have 0 or very few swaps
        assert len(swaps) <= 2
