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
    ("bun_bo", ("bun bo", "bún bò", "bunboplaceholder")),
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
    parts = re.split(r"(?<!\d)[,.]|[,.](?!\d)|;|(?:\brồi\b)|(?:\bsau đó\b)|(?:\band then\b)", message, flags=re.IGNORECASE)
    clauses = []
    
    verb_pattern = re.compile(
        r"\b(bỏ|xóa|thêm|chèn|thay\s+bằng|thay\s+thế|đổi\s+bằng|chuyển|đưa|bo|xoa|them|chen|thay\s+bang|thay\s+the|doi\s+bang|chuyen|dua|swap|doi\s+cho)\b",
        flags=re.IGNORECASE
    )
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        matches = list(verb_pattern.finditer(part))
        if len(matches) <= 1:
            clauses.append(part)
        else:
            indices = []
            if matches[0].start() > 0:
                indices.append(0)
            indices.extend(m.start() for m in matches)
            indices.append(len(part))
            for i in range(len(indices) - 1):
                sub = part[indices[i]:indices[i+1]].strip()
                if sub:
                    clauses.append(sub)
                    
    return [c for c in clauses if c]


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


def extract_budget_amount(text: str) -> float | None:
    if not text:
        return None
    # Lowercase and normalize unicode, keeping dots and commas
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFKD", lowered)
    cleaned = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    cleaned = cleaned.replace("đ", "d")
    # Replace commas with dots for decimal representation
    cleaned = re.sub(r'(\d+)\s*,\s*(\d+)', r'\1.\2', cleaned)
    cleaned = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', cleaned)
    
    # Match patterns like "1.5 trieu", "2 tr", "500k", "2 cu"
    match = re.search(r'\b(\d+(?:\.\d+)?)\s*(trieu|tr|cu)\b', cleaned)
    if match:
        val = float(match.group(1))
        return val * 1_000_000
        
    match = re.search(r'\b(\d+(?:\.\d+)?)\s*k\b', cleaned)
    if match:
        val = float(match.group(1))
        return val * 1_000
        
    match = re.search(r'\b(\d+(?:\.\d+)?)\s*(d|vnd|dong)\b', cleaned)
    if match:
        val = float(match.group(1))
        if val < 1000:
            return val * 1_000_000
        return val
        
    # Fallback to plain number if we mention budget keywords
    if any(k in cleaned for k in ("ngan sach", "budget", "chi phi", "gia ca", "kinh phi")):
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', cleaned)
        if match:
            val = float(match.group(1))
            if val <= 100:  # Assumed to be in millions if <= 100
                return val * 1_000_000
            return val
            
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


def preprocess_message(msg: str) -> str:
    text = msg
    text = re.sub(r"\bb[uú]n\s+b[oò]\b", "BUNBOPLACEHOLDER", text, flags=re.IGNORECASE)
    text = re.sub(r"\bb[oổ]\s+sung\b", "BOSUNGPLACEHOLDER", text, flags=re.IGNORECASE)
    text = re.sub(r"\bth[iị]t\s+b[oò]\b", "THITBOPLACEHOLDER", text, flags=re.IGNORECASE)
    text = re.sub(r"\bph[oở]\s+b[oò]\b", "PHOBOPLACEHOLDER", text, flags=re.IGNORECASE)
    text = re.sub(r"\bb[oò]\s+kho\b", "BOKHOPLACEHOLDER", text, flags=re.IGNORECASE)
    text = re.sub(r"\bb[oò]\s+n[eé]\b", "BONEPLACEHOLDER", text, flags=re.IGNORECASE)
    text = re.sub(r"\bqu[aá]n\s+b[oò]\b", "QUANBOPLACEHOLDER", text, flags=re.IGNORECASE)
    return text


def restore_placeholders(text: str) -> str:
    if not text:
        return ""
    text = text.replace("BUNBOPLACEHOLDER", "bún bò").replace("bunboplaceholder", "bún bò")
    text = text.replace("BOSUNGPLACEHOLDER", "bổ sung").replace("bosungplaceholder", "bổ sung")
    text = text.replace("THITBOPLACEHOLDER", "thịt bò").replace("thitboplaceholder", "thịt bò")
    text = text.replace("PHOBOPLACEHOLDER", "phở bò").replace("phoboplaceholder", "phở bò")
    text = text.replace("BOKHOPLACEHOLDER", "bò kho").replace("bokhoplaceholder", "bò kho")
    text = text.replace("BONEPLACEHOLDER", "bò né").replace("boneplaceholder", "bò né")
    text = text.replace("QUANBOPLACEHOLDER", "quán bò").replace("quanboplaceholder", "quán bò")
    return text


def clean_query(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(
        r"^(them|chen|bo\s+sung|thay\s+bang|thay\s+the|doi\s+bang|chuyen|dua|bo|xoa|thêm|chèn|bổ\s+sung|thay\s+bằng|thay\s+thế|đổi\s+bằng|chuyển|đưa|bỏ|xóa)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"\s+(di|giup|ho|nhe|nha|dum|ho|thoi|thôi|đi|giúp|hộ|nhé|nha|dùm)$",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"\s+(vao\s+)?ngay\s+\d+\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(
        r"\s+(vào\s+)?ngày\s+\d+\b",
        "",
        cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return restore_placeholders(cleaned)


@dataclass
class EditIntentPlanner:
    """Builds pending edit plans from natural language edit requests."""

    def build(self, message: str) -> EditIntent:
        preprocessed = preprocess_message(message)
        operations: list[OperationItem] = []
        for clause in split_clauses(preprocessed):
            op = self._operation_from_clause(clause)
            if op:
                if op.target:
                    op.target = restore_placeholders(op.target)
                if op.query:
                    op.query = restore_placeholders(op.query)
                if op.value:
                    op.value = restore_placeholders(op.value)
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
            elif op.type == "replace_place":
                parts.append(f"thay thế {op.target} bằng {op.query}")
            elif op.type == "swap_places":
                parts.append(f"đổi chỗ {op.target}")
            elif op.type == "change_duration":
                parts.append("thay đổi số ngày đi")
            elif op.type == "rebuild_requested":
                parts.append("tạo lại lịch trình")
            elif op.type == "change_budget":
                if op.amount is not None:
                    # helper inline formatting
                    amount_str = ""
                    amount = op.amount
                    if amount >= 1_000_000:
                        val = amount / 1_000_000
                        val_str = str(int(val) if val.is_integer() else val).replace(".", ",")
                        amount_str = f"{val_str} triệu"
                    elif amount >= 1_000:
                        val = amount / 1_000
                        val_str = str(int(val) if val.is_integer() else val).replace(".", ",")
                        amount_str = f"{val_str}k"
                    else:
                        amount_str = f"{int(amount)}đ"
                    parts.append(f"thay đổi ngân sách thành {amount_str}")
                else:
                    parts.append("thay đổi ngân sách")
            elif op.type == "change_pace":
                pace_desc = "vừa phải"
                if op.value == "chill":
                    pace_desc = "thong thả"
                elif op.value == "intense":
                    pace_desc = "dày đặc"
                parts.append(f"đổi nhịp độ di chuyển thành {pace_desc}")
            elif op.type == "change_time":
                if op.target_time_min is not None:
                    parts.append(f"đổi giờ khởi hành thành {op.target_time_min // 60:02d}:{op.target_time_min % 60:02d}")
                elif op.value == "later":
                    parts.append("điều chỉnh thời gian đi trễ hơn")
                elif op.value == "earlier":
                    parts.append("điều chỉnh thời gian đi sớm hơn")
                else:
                    parts.append("điều chỉnh khung giờ hoạt động")
            elif op.type == "add_preference":
                parts.append(f"thêm sở thích: {op.target}")
            elif op.type == "avoid_preference":
                parts.append(f"hạn chế/tránh: {op.target}")
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

        if any(word in norm for word in ("ngan sach", "budget", "chi phi", "gia ca", "tien ", "kinh phi")):
            amount = extract_budget_amount(clause)
            return OperationItem(
                type="change_budget",
                amount=amount,
                value=clause.strip()
            )

        if any(word in norm for word in ("nhip do", "toc do", "pace", "thong tha", "chill", "cham", "tu tu", "it diem", "gian ra", "nhe nhang", "thu gian", "nhanh", "day", "nhieu diem", "don dap", "gap", "voi", "nhieu hon", "vua phai", "binh thuong", "can bang")):
            val = "balanced"
            if any(word in norm for word in ("thong tha", "chill", "cham", "tu tu", "it diem", "gian ra", "nhe nhang", "thu gian")):
                val = "chill"
            elif any(word in norm for word in ("nhanh", "day", "nhieu diem", "don dap", "gap", "voi", "nhieu hon")):
                val = "intense"
            return OperationItem(
                type="change_pace",
                value=val,
                target=val
            )

        if any(word in norm for word in ("thoi gian", "gio giac", "khung gio", "tre hon", "muon hon", "som hon", "time", "bat dau", "ket thuc", "gio di", "gio ve", "gio ", "khoi hanh")):
            val_dir = None
            if "muon hon" in norm or "tre hon" in norm or "later" in norm:
                val_dir = "later"
            elif "som hon" in norm or "earlier" in norm:
                val_dir = "earlier"
            return OperationItem(
                type="change_time",
                target_time_min=exact_time,
                time_window=window,
                value=val_dir or clause.strip(),
                target=clause.strip()
            )

        if any(word in norm for word in ("khong thich", "tranh", "ghet", "khong muon", "avoid", "dont like", "han che", "cam")):
            if not target:
                avoid_val = clean_query(clause)
                avoid_val = re.sub(r"^(?:tôi|toi|minh|mình|em|ta)?\s*(khong thich|không thích|tranh|tránh|ghet|ghét|khong muon|không muốn|avoid|dont like|han che|hạn chế|cam|cấm)\s+", "", avoid_val, flags=re.IGNORECASE).strip()
                return OperationItem(
                    type="avoid_preference",
                    target=avoid_val,
                    value=avoid_val
                )

        if "so thich" in norm or "preference" in norm:
            pref_val = clean_query(clause)
            pref_val = re.sub(r"^(?:them|chen|bo sung|thêm|chèn|bổ sung|so thich|sở thích|preference)\s+", "", pref_val, flags=re.IGNORECASE).strip()
            return OperationItem(
                type="add_preference",
                target=pref_val,
                value=pref_val
            )

        if any(word in norm for word in ("thich", "muon", "uu tien", "me", "khoai", "yeu thich", "prefer", "like")):
            is_specific_place = any(word in norm for word in ("them ", "chen ", "bo sung ", "thay bang", "thay the")) or (target is not None)
            if not is_specific_place:
                pref_val = clean_query(clause)
                pref_val = re.sub(r"^(?:tôi|toi|minh|mình|em|ta)?\s*(thich|thích|muon|muốn|uu tien|ưu tiên|me|mê|khoai|khoái|yeu thich|yêu thích|prefer|like)\s+", "", pref_val, flags=re.IGNORECASE).strip()
                return OperationItem(
                    type="add_preference",
                    target=pref_val,
                    value=pref_val
                )

        is_replace = any(word in norm for word in ("thay bang", "thay the", "doi bang"))
        if is_replace:
            match = re.search(r"thay\s+(.+?)\s+bang\s+(.+)", norm)
            if match:
                target_place = match.group(1).strip()
                new_place = match.group(2).strip()
                new_place = re.sub(r"\b(di|giup|ho|nhe|dum|nay)\b", "", new_place).strip()
                return OperationItem(
                    type="replace_place",
                    target=display_target(target_place) or target_place,
                    query=new_place,
                    target_day=day,
                    target_category=category,
                    target_micro_tags=tags,
                    resolution_strategy="name_search",
                )


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

        if (
            re.search(r"\b(bo|xoa|remove)\b", norm) is not None
            or "khong di" in norm
        ):
            target_val = target or self._query_from_clause(clause, tags)
            target_val = clean_query(target_val)
            return OperationItem(
                type="remove_place",
                target=target_val,
                target_day=day,
                target_count=extract_command_count(norm, ("bo", "xoa", "remove"), default=999),
                target_category=category,
                target_micro_tags=tags,
                resolution_strategy="current_itinerary_match",
            )

        is_add = (
            any(word in norm for word in ("them", "chen", "bo sung", "thay bang", "thay the"))
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
            query = clean_query(query)
            return OperationItem(
                type="add_place",
                target=query,
                query=query,
                target_day=day,
                target_count=extract_command_count(norm, ("them", "chen", "bo sung", "thay bang", "thay the"), default=1),
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
