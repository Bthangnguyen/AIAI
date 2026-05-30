# -*- coding: utf-8 -*-
"""Deterministic post-draft edit intent planner.

This module is intentionally lightweight: it turns common Vietnamese edit
phrases into atomic operations that the backend can preview, confirm, and apply.
The LLM can still be used, but this planner gives us a dependable fallback and
testable behavior for complex multi-intent edits.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from app.schemas.trip import EditIntent, OperationItem


TIME_WINDOWS = {
    "morning": {"start_min": 360, "end_min": 660},
    "lunch": {"start_min": 660, "end_min": 810},
    "afternoon": {"start_min": 840, "end_min": 1020},
    "evening": {"start_min": 1080, "end_min": 1320},
}

MICRO_TAG_RULES = [
    ("cafe_muoi", ("cafe muoi", "ca phe muoi", "cà phê muối", "cafe muối")),
    ("bun_bo", ("bun bo", "bún bò")),
    ("che", ("quan che", "quán chè", " che", "chè")),
    ("vegetarian", ("quan chay", "quán chay", "an chay", "ăn chay", "chay")),
    ("dai_noi", ("dai noi", "đại nội")),
    ("walking_street", ("di dao", "đi dạo", "pho di bo", "phố đi bộ")),
]

POI_ALIASES = {
    "dai noi": "Đại Nội",
    "đại nội": "Đại Nội",
    "cafe muoi": "cafe muối",
    "ca phe muoi": "cafe muối",
    "cà phê muối": "cafe muối",
    "nguyen hue": "Nguyễn Huệ",
    "nguyễn huệ": "Nguyễn Huệ",
}


def normalize(text: str | None) -> str:
    if not text:
        return ""
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    asciiish = asciiish.replace("đ", "d")
    asciiish = re.sub(r"[^a-z0-9\s:]+", " ", asciiish)
    return re.sub(r"\s+", " ", asciiish).strip()


def split_clauses(message: str) -> list[str]:
    parts = re.split(r"[,.;]|\brồi\b|\bsau đó\b|\band then\b", message, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p and p.strip()]


def extract_count(norm: str, default: int = 1) -> int:
    match = re.search(r"\b(\d+)\b", norm)
    if match:
        try:
            return max(1, int(match.group(1)))
        except ValueError:
            return default
    words = {"mot": 1, "một": 1, "hai": 2, "ba": 3}
    for key, val in words.items():
        if f" {key} " in f" {norm} ":
            return val
    return default


def extract_command_count(norm: str, verbs: tuple[str, ...], default: int = 1) -> int:
    for verb in verbs:
        match = re.search(rf"\b{re.escape(verb)}\s+(\d+)\b", norm)
        if match:
            return max(1, int(match.group(1)))
    return default


def extract_day(norm: str) -> int | None:
    match = re.search(r"ngay\s+(\d+)", norm)
    if match:
        return int(match.group(1))
    if "ngay mai" in norm:
        return 2
    if "ngay cuoi" in norm:
        return -1
    return None


def extract_time_min(norm: str) -> int | None:
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*h\b", norm)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return hour * 60 + minute
    return None


def extract_window(norm: str) -> dict[str, int] | None:
    if "buoi trua" in norm or "an trua" in norm or "trua" in norm:
        return TIME_WINDOWS["lunch"]
    if "buoi chieu" in norm or "chieu" in norm:
        return TIME_WINDOWS["afternoon"]
    if "buoi toi" in norm or "toi" in norm:
        return TIME_WINDOWS["evening"]
    if "buoi sang" in norm or "sang" in norm:
        return TIME_WINDOWS["morning"]
    return None


def micro_tags_for(text: str) -> list[str]:
    norm = normalize(text)
    tags: list[str] = []
    raw_lower = (text or "").lower()
    for tag, needles in MICRO_TAG_RULES:
        if tag == "che":
            if re.search(r"\bche\b", norm) or "quán chè" in raw_lower or " chè" in raw_lower:
                tags.append(tag)
            continue
        if any(needle in norm or needle in raw_lower for needle in needles):
            tags.append(tag)
    return tags


def category_for(tags: list[str], norm: str) -> str | None:
    if any(t in tags for t in ("bun_bo", "che", "vegetarian")):
        return "food"
    if "cafe_muoi" in tags or "cafe" in norm or "ca phe" in norm:
        return "cafe"
    if "walking_street" in tags or "di dao" in norm:
        return "nightlife"
    if "dai_noi" in tags:
        return "culture"
    return None


def display_target(text: str) -> str | None:
    norm = normalize(text)
    for key, value in POI_ALIASES.items():
        if key in norm or key in text.lower():
            return value
    return None


@dataclass
class EditIntentPlanner:
    """Builds pending edit plans from natural language edit requests."""

    def build(self, message: str) -> EditIntent:
        operations: list[OperationItem] = []
        for clause in split_clauses(message):
            op = self._operation_from_clause(clause)
            if op:
                operations.append(op)

        if not operations:
            action = "answer_question"
        elif len(operations) == 1:
            action = operations[0].type
        else:
            action = "modify_itinerary"

        target = operations[0].target if operations else message
        return EditIntent(
            action=action,
            target=target,
            target_count=operations[0].target_count if operations else None,
            constraints=self.pending_plan(message, operations),
            raw_message=message,
            operations=operations,
        )

    def pending_plan(self, message: str, operations: list[OperationItem]) -> dict[str, Any]:
        affected_days = sorted({
            op.target_day for op in operations
            if isinstance(op.target_day, int) and op.target_day > 0
        })
        return {
            "status": "pending_confirmation",
            "requires_confirmation": True,
            "operations": [op.model_dump(exclude_none=True) for op in operations],
            "affected_days": affected_days,
            "assistant_reply": self.reply_for(operations),
            "raw_message": message,
        }

    def reply_for(self, operations: list[OperationItem]) -> str:
        if not operations:
            return "Em chưa chắc mình muốn sửa gì trong lịch. Anh nói rõ điểm/ngày muốn sửa giúp em nhé?"
        parts = []
        for op in operations:
            if op.type == "move_place":
                time_text = f" vào {op.target_time_min // 60:02d}:{op.target_time_min % 60:02d}" if op.target_time_min is not None else ""
                day_text = f" ngày {op.target_day}" if op.target_day else ""
                parts.append(f"chuyển {op.target}{day_text}{time_text}")
            elif op.type == "add_place":
                day_text = f" ngày {op.target_day}" if op.target_day else ""
                pos_text = f" sau {op.relative_to}" if op.position == "after" and op.relative_to else ""
                parts.append(f"thêm {op.query or op.target}{pos_text}{day_text}")
            elif op.type == "remove_place":
                day_text = f" ngày {op.target_day}" if op.target_day else ""
                count_text = f"{op.target_count} " if op.target_count else ""
                parts.append(f"bỏ {count_text}{op.target or op.query}{day_text}")
            else:
                parts.append(op.type)
        return "Em sẽ " + ", ".join(parts) + ". Anh xác nhận em sửa một lượt nhé?"

    def _operation_from_clause(self, clause: str) -> OperationItem | None:
        norm = normalize(clause)
        tags = micro_tags_for(clause)
        day = extract_day(norm)
        exact_time = extract_time_min(norm)
        window = extract_window(norm)
        category = category_for(tags, norm)
        target = display_target(clause)

        if any(word in norm for word in ("dung tao lai", "khong tao lai", "dont rebuild", "do not rebuild")):
            return None

        if any(word in norm for word in ("tao lai", "lam lai", "reset", "rebuild")):
            return OperationItem(type="rebuild_requested", target=target, value=clause)

        if any(word in norm for word in ("tang len", "rut con", "them mot ngay", "bot ngay")):
            return OperationItem(type="change_duration", target=target, value=clause)

        if any(word in norm for word in ("doi cho", "swap")):
            return OperationItem(type="swap_places", target=target or clause, value=clause)

        if any(word in norm for word in ("chuyen", "dua ")) or ("sang" in norm and target):
            return OperationItem(
                type="move_place",
                target=target or clause,
                target_day=day,
                target_time_min=exact_time,
                time_window=window,
                target_category=category,
                target_micro_tags=tags,
                resolution_strategy="current_itinerary_match",
            )

        if any(word in norm for word in ("bo ", "xoa", "remove", "khong di")):
            return OperationItem(
                type="remove_place",
                target=target or self._query_from_clause(clause, tags),
                target_day=day,
                target_count=extract_command_count(norm, ("bo", "xoa", "remove"), default=1),
                target_category=category,
                target_micro_tags=tags,
                resolution_strategy="current_itinerary_match",
            )

        is_add = (
            any(word in norm for word in ("them", "chen", "bo sung"))
            or re.search(r"\b(an|di dao)\b", norm) is not None
        )
        if is_add:
            relative_to = None
            position = None
            if "sau khi" in norm or "sau " in norm:
                position = "after"
                relative_to = "Đại Nội" if "dai noi" in norm else None
                if relative_to:
                    tags = [tag for tag in tags if tag != "dai_noi"]
                    category = category_for(tags, norm)
            inferred_query = self._query_from_clause(clause, tags)
            query = inferred_query if inferred_query != clause.strip() else (target or inferred_query)
            return OperationItem(
                type="add_place",
                target=query,
                query=query,
                target_day=day,
                target_count=extract_command_count(norm, ("them", "chen", "bo sung"), default=1),
                target_category=category,
                target_micro_tags=tags,
                time_window=window,
                position=position or "best_gap",
                relative_to=relative_to,
                resolution_strategy="vector_search_then_suggest" if not target else "name_search",
            )

        return None

    def _query_from_clause(self, clause: str, tags: list[str]) -> str:
        if "che" in tags:
            return "quán chè"
        if "bun_bo" in tags:
            return "bún bò"
        if "vegetarian" in tags:
            return "quán chay"
        if "cafe_muoi" in tags:
            return "cafe muối"
        if "walking_street" in tags:
            target = display_target(clause)
            return target or clause
        return clause.strip()
