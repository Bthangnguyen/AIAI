"""Deterministic distribution defaults for itinerary planning."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


DEFAULT_MIXED_DISTRIBUTION = {
    "culture": 0.35,
    "food": 0.30,
    "cafe": 0.15,
    "nightlife": 0.10,
    "nature": 0.10,
}


def normalize(text: str | None) -> str:
    if not text:
        return ""
    value = unicodedata.normalize("NFKD", text.lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("đ", "d")
    value = re.sub(r"[^a-z0-9\s_]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_distribution(distribution: dict[str, float] | None) -> dict[str, float]:
    allowed = {"food", "cafe", "culture", "nature", "nightlife", "shopping", "art", "wellness", "adventure"}
    cleaned = {
        normalize(key): max(0.0, float(value))
        for key, value in (distribution or {}).items()
        if normalize(key) in allowed and float(value or 0) > 0
    }
    total = sum(cleaned.values())
    if total <= 0:
        return dict(DEFAULT_MIXED_DISTRIBUTION)
    return {key: round(value / total, 4) for key, value in cleaned.items()}


def derive_distribution(contract: Any, raw_text: str | None = None) -> dict[str, float]:
    text_parts = [raw_text or ""]
    text_parts.extend(getattr(contract, "tags", None) or [])
    text_parts.extend(getattr(contract, "food_preferences", None) or [])
    text_parts.extend(getattr(contract, "locked_pois", None) or [])
    if getattr(contract, "trip_type", None):
        text_parts.append(contract.trip_type)
    if getattr(contract, "distribution_description", None):
        text_parts.append(contract.distribution_description)
    text = normalize(" ".join(str(x) for x in text_parts if x))

    existing = normalize_distribution(getattr(contract, "target_category_distribution", None))
    explicit = bool(getattr(contract, "target_category_distribution", None))

    has_food = any(token in text for token in ("am thuc", "an uong", "food", "foodie", "local_cuisine", "street food", "street_food"))
    has_culture = any(token in text for token in ("van hoa", "culture", "cultural", "lich su", "heritage"))
    has_cafe = any(token in text for token in ("cafe hopping", "cafe_hopping", "ca phe", "cafe"))
    has_night = any(token in text for token in ("buoi toi", "night", "nightlife", "di dao"))

    is_explicit_food_tour = any(token in text for token in ("food tour", "food_tour"))
    is_food_focused = has_food and not has_culture and not has_cafe
    if is_explicit_food_tour or is_food_focused:
        base = {"food": 0.70, "cafe": 0.15, "nightlife": 0.10, "culture": 0.05}
    elif any(token in text for token in ("cafe hopping", "cafe_hopping")) or (has_cafe and not has_culture and not has_food):
        base = {"cafe": 0.45, "food": 0.25, "culture": 0.15, "nightlife": 0.10, "nature": 0.05}
    elif has_culture and not has_food and not has_cafe:
        base = {"culture": 0.65, "food": 0.20, "cafe": 0.10, "nature": 0.05}
    elif explicit:
        base = existing
    elif has_culture and has_food:
        base = dict(DEFAULT_MIXED_DISTRIBUTION)
    else:
        base = dict(DEFAULT_MIXED_DISTRIBUTION)

    if has_cafe and "cafe" not in base:
        base["cafe"] = 0.15
    if has_night and "nightlife" not in base:
        base["nightlife"] = 0.10

    return normalize_distribution(base)


def apply_distribution_policy(contract: Any, raw_text: str | None = None) -> Any:
    contract.target_category_distribution = derive_distribution(contract, raw_text)
    if not getattr(contract, "distribution_description", None):
        dist = contract.target_category_distribution
        top = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(dist.items(), key=lambda item: item[1], reverse=True))
        contract.distribution_description = f"Stable distribution policy: {top}"
    return contract
