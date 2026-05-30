"""POI tag normalization and semantic text helpers.

The POI table can receive tags from CSV, OSM, or JSON-like exports. This module
turns those sources into stable micro-tags that are useful for retrieval.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable


GENERIC_TAGS = {
    "am_thuc",
    "ẩm_thực",
    "dia_phuong",
    "địa_phương",
    "local",
    "local_food",
    "hue",
    "huế",
    "thu_gian",
    "thư_giãn",
    "do_uong",
    "đồ_uống",
    "restaurant",
    "nha_hang",
    "nhà_hàng",
    "diem_tham_quan",
    "điểm_tham_quan",
    "du_lich",
    "tourism",
}


PATTERN_TAGS: list[tuple[str, str]] = [
    (r"\bcafe muoi\b|\bca phe muoi\b|\bcà phê muối\b|\bsalt coffee\b", "cafe_muoi"),
    (r"\bcafe\b|\bcoffee\b|\bcà phê\b|\bca phe\b", "cafe"),
    (r"\bbun bo\b|\bbún bò\b", "bun_bo"),
    (r"\bcom hen\b|\bcơm hến\b", "com_hen"),
    (r"\bbanh khoai\b|\bbánh khoái\b", "banh_khoai"),
    (r"\bbanh beo\b|\bbánh bèo\b", "banh_beo"),
    (r"\bbanh nam\b|\bbánh nậm\b", "banh_nam"),
    (r"\bbanh loc\b|\bbánh lọc\b", "banh_loc"),
    (r"\bnem lui\b|\bnem lụi\b", "nem_lui"),
    (r"\bche\b|\bchè\b|\bdessert\b|\bsweet soup\b", "che_hue"),
    (r"\bchay\b|\bvegetarian\b|\bvegan\b", "vegetarian"),
    (r"\bstreet food\b|\bstreetfood\b|\bduong pho\b|\bđường phố\b", "street_food"),
    (r"\bnight food\b|\blate night\b|\ban dem\b|\băn đêm\b|\bam thuc dem\b|\bẩm thực đêm\b", "night_food"),
    (r"\bwalking street\b|\bpho di bo\b|\bphố đi bộ\b", "walking_street"),
    (r"\bdai noi\b|\bđại nội\b|\bcitadel\b|\bhoang thanh\b|\bhoàng thành\b", "citadel"),
    (r"\bpalace\b|\bhoang cung\b|\bhoàng cung\b", "imperial_palace"),
    (r"\blang vua\b|\blăng vua\b|\btomb\b|\bmausoleum\b", "royal_tomb"),
    (r"\bchua\b|\bchùa\b|\bpagoda\b|\btemple\b|\btam linh\b|\btâm linh\b", "pagoda"),
    (r"\bmuseum\b|\bbao tang\b|\bbảo tàng\b", "museum"),
    (r"\blang nghe\b|\blàng nghề\b|\bcraft\b|\bworkshop\b", "craft_village"),
    (r"\briver\b|\bsong huong\b|\bsông hương\b", "riverfront"),
    (r"\bnature\b|\blake\b|\briver\b|\bgarden\b|\bpark\b|\bnui\b|\bnúi\b", "nature"),
    (r"\bspa\b|\bmassage\b|\bwellness\b", "wellness"),
    (r"\bmarket\b|\bcho\b|\bchợ\b|\bshopping\b", "market"),
]


GROUP_BASE_TAGS = {
    "food": ["food"],
    "cafe": ["cafe"],
    "culture": ["culture"],
    "nature": ["nature"],
    "nightlife": ["nightlife"],
    "shopping": ["shopping"],
    "wellness": ["wellness"],
    "adventure": ["adventure"],
}


def strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.replace("đ", "d").replace("Đ", "D")


def canonical_tag(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip().lower()
    text = strip_accents(text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def _flatten_raw_tags(raw_tags) -> list[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, str):
        candidates = [raw_tags]
    elif isinstance(raw_tags, Iterable):
        candidates = [str(item) for item in raw_tags if item is not None]
    else:
        candidates = [str(raw_tags)]

    joined = ",".join(candidates).strip()
    cleaned_joined = joined.replace('\\"', '"')
    if cleaned_joined.startswith("[") and cleaned_joined.endswith("]"):
        try:
            parsed = json.loads(cleaned_joined)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except Exception:
            pass

    values: list[str] = []
    for item in candidates:
        token = item.strip()
        token = token.strip("{}[]")
        token = token.strip().strip('"').strip("'")
        if not token:
            continue
        if token.startswith("[") or token.endswith("]") or '","' in token:
            try:
                parsed = json.loads(token if token.startswith("[") else f"[{token}]")
                if isinstance(parsed, list):
                    values.extend(str(v) for v in parsed if str(v).strip())
                    continue
            except Exception:
                pass
        values.append(token)
    return values


def normalize_tags(
    *,
    name: str,
    category: str | None,
    category_group: str | None,
    description: str | None,
    raw_tags,
) -> list[str]:
    """Return stable retrieval tags for a POI.

    Generic filler tags are removed unless they are the macro group. Specific
    micro-tags are derived from the name, category, description, and source tags.
    """

    source_text = " ".join(
        part for part in [
            name or "",
            category or "",
            category_group or "",
            description or "",
            " ".join(_flatten_raw_tags(raw_tags)),
        ] if part
    ).lower()
    ascii_text = strip_accents(source_text)
    combined_text = f"{source_text} {ascii_text}"

    tags: list[str] = []
    group = canonical_tag(category_group)
    tags.extend(GROUP_BASE_TAGS.get(group, []))

    for raw in _flatten_raw_tags(raw_tags):
        tag = canonical_tag(raw)
        if tag and tag not in GENERIC_TAGS:
            tags.append(tag)

    for pattern, tag in PATTERN_TAGS:
        if re.search(pattern, combined_text):
            tags.append(tag)

    if group == "food" and not any(t in tags for t in ["street_food", "bun_bo", "com_hen", "banh_khoai", "banh_beo", "vegetarian"]):
        tags.append("local_eatery")
    if group == "cafe" and "cafe_muoi" not in tags:
        tags.append("local_cafe")

    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        clean = canonical_tag(tag)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        deduped.append(clean)
    return deduped[:16]


def build_embedding_text(
    *,
    name: str,
    category: str | None,
    category_group: str | None,
    description: str | None,
    tags: list[str],
) -> str:
    """Build concise text for semantic retrieval."""

    parts = [
        f"name: {name}",
        f"group: {category_group or category or 'poi'}",
    ]
    if category and category != category_group:
        parts.append(f"category: {category}")
    if tags:
        parts.append("micro_tags: " + ", ".join(tags))
    if description:
        parts.append("description: " + description[:500])
    return " | ".join(parts)
