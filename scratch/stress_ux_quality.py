# -*- coding: utf-8 -*-
"""Stress test: UX Quality – Kiểm tra lịch trình từ góc nhìn người dùng.

Không chỉ check API pass/fail, bộ test này đánh giá:
1. Thứ tự địa lý: Các điểm có gần nhau không, có đi vòng vèo không?
2. Đa dạng trải nghiệm: Không lặp quá nhiều cùng loại liên tiếp
3. Thời gian bữa ăn: Ăn trưa 11-14h, ăn tối 17-21h, không ăn sáng lúc 15h
4. Ngân sách: Tổng chi phí <= budget
5. Thời gian di chuyển: Không quá 30 phút liên tục trong nội thành
6. Thời lượng tham quan: Đủ thời gian cho từng điểm (không 10 phút cho Đại Nội)
7. Edit đúng ý: Thêm/bớt/đổi đúng chỗ, không phá hỏng phần còn lại
8. Tổng thể: Lịch trình trông có "ổn" không nếu bạn là du khách?

Chạy: python scratch/stress_ux_quality.py
Timeout dự kiến: ~5-8 phút (7 kịch bản, mỗi kịch bản ~45-60s)
"""

from __future__ import annotations

import json
import math
import time
import traceback
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE_URL = "http://127.0.0.1:8001"
OUT = Path("scratch/stress_outputs/ux_quality_results.json")

# ─── Thời gian hợp lý cho bữa ăn (phút từ 0h) ───
BREAKFAST_WINDOW = (360, 570)     # 6:00 – 9:30
LUNCH_WINDOW     = (660, 840)     # 11:00 – 14:00
DINNER_WINDOW    = (1020, 1260)   # 17:00 – 21:00
SNACK_WINDOW     = (840, 1080)    # 14:00 – 18:00

# Thời gian tham quan tối thiểu hợp lý (phút)
MIN_VISIT_BY_CATEGORY = {
    "culture": 30,
    "heritage": 45,
    "museum": 30,
    "pagoda": 20,
    "temple": 20,
    "food": 20,
    "cafe": 20,
    "park": 20,
    "market": 30,
    "shopping": 20,
}

# Khoảng cách tối đa hợp lý giữa 2 điểm liên tiếp (km) cho nội thành Huế
MAX_CONSECUTIVE_DISTANCE_KM = 12.0

# Tốc độ di chuyển trung bình (km/phút) – xe máy/taxi nội thành
AVG_SPEED_KM_PER_MIN = 0.5  # ~30km/h


# ═══════════════════════════════════════════════════════════════
# HTTP Helpers
# ═══════════════════════════════════════════════════════════════

def post_json(path: str, payload: dict[str, Any], timeout: int = 280) -> dict[str, Any]:
    import urllib.error
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
            data = json.loads(body)
            if "detail" in data:
                return data["detail"]
            return data
        except Exception:
            return {"status": "error", "error_code": "HTTP_ERROR", "message": f"HTTP {e.code}: {e.reason}"}



def wait_health() -> None:
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/v1/trip/health", timeout=5) as res:
                if res.status == 200:
                    return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Gateway không sẵn sàng")


def empty_contract() -> dict[str, Any]:
    return {
        "destination": None,
        "budget_max": None,
        "radius_km": 10.0,
        "num_days": 1,
        "tags": [],
        "locked_pois": [],
    }


def chat(
    message: str,
    contract: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
    *,
    has_draft: bool = False,
    current_itinerary: dict[str, Any] | None = None,
    pending_edit_plan: dict[str, Any] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    return post_json(
        "/v1/trip/chat_process",
        {
            "message": message,
            "history": history or [],
            "current_contract": contract or empty_contract(),
            "has_draft": has_draft,
            "current_itinerary": current_itinerary,
            "pending_edit_plan": pending_edit_plan,
        },
        timeout=timeout,
    )


def plan(prompt: str, contract: dict[str, Any], timeout: int = 280) -> dict[str, Any]:
    return post_json(
        "/v1/trip/plan_trip",
        {
            "user_prompt": prompt,
            "num_days": contract.get("num_days"),
            "budget": contract.get("budget_max"),
            "destination": contract.get("destination") or "Hue",
            "preferences": contract.get("tags") or [],
            "contract": contract,
        },
        timeout=timeout,
    )


# ═══════════════════════════════════════════════════════════════
# Build + Edit Flow
# ═══════════════════════════════════════════════════════════════

def build_flow(prompt: str, followups: list[str], timeout: int = 180, plan_timeout: int = 280) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    turns = []
    first = chat(prompt, timeout=timeout)
    turns.append(first)
    history += [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": first.get("reply", "")},
    ]
    contract = first.get("updated_contract") or {}

    for followup in followups:
        if turns[-1].get("status") == "ready":
            break
        nxt = chat(followup, contract=contract, history=history, timeout=timeout)
        turns.append(nxt)
        history += [
            {"role": "user", "content": followup},
            {"role": "assistant", "content": nxt.get("reply", "")},
        ]
        contract = nxt.get("updated_contract") or contract

    if turns[-1].get("phase") == "confirming" and turns[-1].get("status") != "ready":
        ok = chat("ok tao di", contract=contract, history=history, timeout=timeout)
        turns.append(ok)
        history += [
            {"role": "user", "content": "ok tao di"},
            {"role": "assistant", "content": ok.get("reply", "")},
        ]
        contract = ok.get("updated_contract") or contract

    planned = None
    if turns[-1].get("status") == "ready":
        planned = plan(prompt, contract, timeout=plan_timeout)

    return {"turns": turns, "contract": contract, "plan": planned, "history": history}


def apply_edit(
    edit_prompt: str,
    contract: dict[str, Any],
    itinerary: dict[str, Any],
    history: list[dict[str, str]] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    first = chat(
        edit_prompt,
        contract=contract,
        history=history or [],
        has_draft=True,
        current_itinerary=itinerary,
        timeout=timeout,
    )
    turns = [first]
    pending = first.get("pending_edit_plan")
    updated = first.get("updated_itinerary")

    if pending and not updated:
        ok = chat(
            "ok",
            contract=contract,
            history=(history or []) + [
                {"role": "user", "content": edit_prompt},
                {"role": "assistant", "content": first.get("reply", "")},
            ],
            has_draft=True,
            current_itinerary=itinerary,
            pending_edit_plan=pending,
            timeout=timeout,
        )
        turns.append(ok)
        updated = ok.get("updated_itinerary")

    return {"turns": turns, "updated_itinerary": updated}


# ═══════════════════════════════════════════════════════════════
# Itinerary Extraction Helpers
# ═══════════════════════════════════════════════════════════════

def all_stops(itinerary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not itinerary:
        return []
    return [s for d in itinerary.get("days", []) for s in d.get("stops", [])]


def real_stops(itinerary: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [s for s in all_stops(itinerary) if not str(s.get("poi_id", "")).startswith("__")]


def stops_by_day(itinerary: dict[str, Any] | None) -> list[list[dict[str, Any]]]:
    if not itinerary:
        return []
    result = []
    for d in itinerary.get("days", []):
        day_stops = [s for s in d.get("stops", []) if not str(s.get("poi_id", "")).startswith("__")]
        result.append(day_stops)
    return result


def stop_name(s: dict[str, Any]) -> str:
    return str(s.get("poi_name") or s.get("name") or "").strip()


def stop_category(s: dict[str, Any]) -> str:
    return str(s.get("category") or s.get("category_group") or "").lower().strip()


def stop_lat_lon(s: dict[str, Any]) -> tuple[float, float] | None:
    lat = s.get("latitude") or s.get("lat")
    lon = s.get("longitude") or s.get("lon")
    if lat is not None and lon is not None:
        return (float(lat), float(lon))
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def total_cost(itinerary: dict[str, Any] | None) -> float:
    return sum(float(s.get("price") or s.get("entrance_fee") or 0) for s in real_stops(itinerary))


# ═══════════════════════════════════════════════════════════════
# UX Quality Checks
# ═══════════════════════════════════════════════════════════════

@dataclass
class Finding:
    category: str  # geography, variety, meal_timing, budget, travel_time, visit_duration, edit_accuracy, coherence
    severity: str  # PASS, WARN, FAIL
    message: str


@dataclass
class UXReport:
    case_name: str
    findings: list[Finding] = field(default_factory=list)
    score: float = 0.0  # 0-100

    def add(self, category: str, severity: str, message: str):
        self.findings.append(Finding(category, severity, message))

    def pass_(self, cat: str, msg: str):
        self.add(cat, "PASS", msg)

    def warn(self, cat: str, msg: str):
        self.add(cat, "WARN", msg)

    def fail(self, cat: str, msg: str):
        self.add(cat, "FAIL", msg)

    def compute_score(self):
        if not self.findings:
            self.score = 0.0
            return
        weights = {"PASS": 1.0, "WARN": 0.5, "FAIL": 0.0}
        total = sum(weights.get(f.severity, 0) for f in self.findings)
        self.score = round(100 * total / len(self.findings), 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_name": self.case_name,
            "score": self.score,
            "pass": sum(1 for f in self.findings if f.severity == "PASS"),
            "warn": sum(1 for f in self.findings if f.severity == "WARN"),
            "fail": sum(1 for f in self.findings if f.severity == "FAIL"),
            "findings": [
                {"category": f.category, "severity": f.severity, "message": f.message}
                for f in self.findings
            ],
        }


def check_no_time_overlap(report: UXReport, itinerary: dict[str, Any] | None, label: str = ""):
    """Kiểm tra không có 2 điểm nào bị trùng giờ."""
    prefix = f"[{label}] " if label else ""
    if not itinerary:
        report.fail("coherence", f"{prefix}Không có lịch trình")
        return
    for day in itinerary.get("days", []):
        day_idx = (day.get("day_index") or 0) + 1
        prev_dep = -1
        for s in sorted(day.get("stops", []), key=lambda x: x.get("arrival_time_min", 0)):
            arr = s.get("arrival_time_min")
            dep = s.get("departure_time_min")
            if isinstance(arr, int) and arr < prev_dep:
                report.fail("coherence", f"{prefix}Ngày {day_idx}: {stop_name(s)} (đến {arr}p) trùng giờ với điểm trước (rời {prev_dep}p)")
                return
            if isinstance(dep, int):
                prev_dep = dep
    report.pass_("coherence", f"{prefix}Không trùng giờ giữa các điểm")


def check_geographic_clustering(report: UXReport, day_stops: list[dict[str, Any]], day_idx: int):
    """Kiểm tra các điểm trong ngày có gần nhau không, không đi vòng vèo."""
    coords = [(stop_lat_lon(s), stop_name(s)) for s in day_stops]
    coords = [(c, n) for c, n in coords if c is not None]
    if len(coords) < 2:
        return

    max_dist = 0.0
    total_dist = 0.0
    zigzag_count = 0
    for i in range(len(coords) - 1):
        (lat1, lon1), name1 = coords[i]
        (lat2, lon2), name2 = coords[i + 1]
        d = haversine_km(lat1, lon1, lat2, lon2)
        total_dist += d
        if d > max_dist:
            max_dist = d
        if d > MAX_CONSECUTIVE_DISTANCE_KM:
            report.warn("geography", f"Ngày {day_idx}: {name1} → {name2} xa {d:.1f}km (>{MAX_CONSECUTIVE_DISTANCE_KM}km)")

    # Check zigzag: nếu đi A→B→C mà AC < AB thì có thể đi vòng
    if len(coords) >= 3:
        for i in range(len(coords) - 2):
            (lat_a, lon_a), _ = coords[i]
            (lat_b, lon_b), name_b = coords[i + 1]
            (lat_c, lon_c), name_c = coords[i + 2]
            ab = haversine_km(lat_a, lon_a, lat_b, lon_b)
            bc = haversine_km(lat_b, lon_b, lat_c, lon_c)
            ac = haversine_km(lat_a, lon_a, lat_c, lon_c)
            if ab > 2.0 and bc > 2.0 and ac < min(ab, bc) * 0.5:
                zigzag_count += 1

    if zigzag_count == 0:
        report.pass_("geography", f"Ngày {day_idx}: Tuyến đường hợp lý, không đi vòng vèo (tổng {total_dist:.1f}km)")
    else:
        report.warn("geography", f"Ngày {day_idx}: Có {zigzag_count} đoạn đi vòng, tuyến đường chưa tối ưu")


def check_variety(report: UXReport, day_stops: list[dict[str, Any]], day_idx: int):
    """Kiểm tra đa dạng trải nghiệm: không quá 3 điểm cùng loại liên tiếp."""
    if len(day_stops) < 2:
        return
    cats = [stop_category(s) for s in day_stops]
    # Check liên tiếp cùng loại
    consecutive = 1
    max_consecutive = 1
    repeated_cat = ""
    for i in range(1, len(cats)):
        if cats[i] and cats[i] == cats[i - 1]:
            consecutive += 1
            if consecutive > max_consecutive:
                max_consecutive = consecutive
                repeated_cat = cats[i]
        else:
            consecutive = 1

    if max_consecutive >= 4:
        report.fail("variety", f"Ngày {day_idx}: {max_consecutive} điểm liên tiếp cùng loại '{repeated_cat}' – quá đơn điệu")
    elif max_consecutive >= 3:
        report.warn("variety", f"Ngày {day_idx}: {max_consecutive} điểm liên tiếp cùng loại '{repeated_cat}'")
    else:
        report.pass_("variety", f"Ngày {day_idx}: Trải nghiệm đa dạng ({dict(Counter(cats))})")


def check_meal_timing(report: UXReport, day_stops: list[dict[str, Any]], day_idx: int):
    """Kiểm tra bữa ăn đúng giờ: trưa ~11-14h, tối ~17-21h."""
    food_cats = {"food", "restaurant", "street_food", "quán ăn", "nhà hàng", "ẩm thực"}
    food_tags = {"food", "bun_bo", "com_hen", "che_hue", "street_food", "an_vat", "breakfast", "lunch", "dinner"}

    food_stops = []
    for s in day_stops:
        cat = stop_category(s)
        tags = {str(t).lower() for t in (s.get("tags") or [])}
        name_lower = stop_name(s).lower()
        is_food = (
            cat in food_cats
            or bool(tags & food_tags)
            or any(kw in cat for kw in ["food", "ăn", "quán", "nhà hàng", "ẩm thực"])
            or any(kw in name_lower for kw in ["bún", "bun", "cơm", "com", "phở", "pho", "chè", "che", "bánh", "banh"])
        )
        if is_food:
            arr = s.get("arrival_time_min")
            if isinstance(arr, int):
                food_stops.append((arr, stop_name(s)))

    if not food_stops:
        # Không có bữa ăn nào – có thể ok cho trip ngắn
        return

    meal_issues = []
    for arr_min, name in food_stops:
        h = arr_min // 60
        m = arr_min % 60
        time_str = f"{h:02d}:{m:02d}"

        in_breakfast = BREAKFAST_WINDOW[0] <= arr_min <= BREAKFAST_WINDOW[1]
        in_lunch = LUNCH_WINDOW[0] <= arr_min <= LUNCH_WINDOW[1]
        in_dinner = DINNER_WINDOW[0] <= arr_min <= DINNER_WINDOW[1]
        in_snack = SNACK_WINDOW[0] <= arr_min <= SNACK_WINDOW[1]

        if not (in_breakfast or in_lunch or in_dinner or in_snack):
            meal_issues.append(f"{name} lúc {time_str} – giờ ăn bất thường")

    if not meal_issues:
        times = ", ".join(f"{n} ({t // 60}:{t % 60:02d})" for t, n in food_stops)
        report.pass_("meal_timing", f"Ngày {day_idx}: Bữa ăn đúng giờ – {times}")
    else:
        for issue in meal_issues:
            report.warn("meal_timing", f"Ngày {day_idx}: {issue}")


def check_budget(report: UXReport, itinerary: dict[str, Any] | None, budget_max: float | None):
    """Kiểm tra tổng chi phí <= ngân sách."""
    if budget_max is None or budget_max <= 0:
        return
    cost = total_cost(itinerary)
    if cost <= budget_max:
        report.pass_("budget", f"Tổng chi phí {cost:,.0f}đ <= ngân sách {budget_max:,.0f}đ")
    elif cost <= budget_max * 1.15:
        report.warn("budget", f"Tổng chi phí {cost:,.0f}đ vượt nhẹ ngân sách {budget_max:,.0f}đ (+{((cost / budget_max) - 1) * 100:.0f}%)")
    else:
        report.fail("budget", f"Tổng chi phí {cost:,.0f}đ VƯỢT ngân sách {budget_max:,.0f}đ (+{((cost / budget_max) - 1) * 100:.0f}%)")


def check_travel_time(report: UXReport, day_stops: list[dict[str, Any]], day_idx: int):
    """Kiểm tra thời gian di chuyển hợp lý giữa các điểm."""
    for i in range(len(day_stops) - 1):
        s = day_stops[i]
        dep = s.get("departure_time_min")
        next_arr = day_stops[i + 1].get("arrival_time_min")
        travel_time = s.get("travel_time_to_next_min")

        if isinstance(travel_time, (int, float)) and travel_time > 40:
            report.warn(
                "travel_time",
                f"Ngày {day_idx}: {stop_name(s)} → {stop_name(day_stops[i + 1])}: di chuyển {travel_time:.0f} phút – hơi xa"
            )
        elif isinstance(dep, int) and isinstance(next_arr, int):
            gap = next_arr - dep
            if gap > 60:
                report.warn(
                    "travel_time",
                    f"Ngày {day_idx}: Khoảng trống {gap} phút giữa {stop_name(s)} → {stop_name(day_stops[i + 1])}"
                )

    # Tổng kết
    total_travel = sum(float(s.get("travel_time_to_next_min") or 0) for s in day_stops)
    total_visit = sum(
        max(0, (s.get("departure_time_min") or 0) - (s.get("arrival_time_min") or 0))
        for s in day_stops
    )
    if total_visit > 0:
        ratio = total_travel / total_visit
        if ratio > 0.6:
            report.warn("travel_time", f"Ngày {day_idx}: Tỉ lệ di chuyển/tham quan cao ({ratio:.1%})")
        else:
            report.pass_("travel_time", f"Ngày {day_idx}: Tỉ lệ di chuyển/tham quan ổn ({ratio:.1%})")


def check_visit_duration(report: UXReport, day_stops: list[dict[str, Any]], day_idx: int):
    """Kiểm tra thời gian tham quan đủ cho từng loại điểm."""
    for s in day_stops:
        arr = s.get("arrival_time_min")
        dep = s.get("departure_time_min")
        if not isinstance(arr, int) or not isinstance(dep, int):
            continue
        duration = dep - arr
        cat = stop_category(s)
        name = stop_name(s)

        # Đại Nội cần ít nhất 60 phút
        if any(kw in name.lower() for kw in ["đại nội", "dai noi", "imperial city", "hoàng thành"]):
            if duration < 60:
                report.warn("visit_duration", f"Ngày {day_idx}: {name} chỉ {duration}p – nên ≥60p")
                continue

        # Lăng tẩm cần ít nhất 40 phút
        if any(kw in name.lower() for kw in ["lăng", "lang", "tomb", "mausoleum"]):
            if duration < 35:
                report.warn("visit_duration", f"Ngày {day_idx}: {name} chỉ {duration}p – nên ≥40p")
                continue

        # Check chung theo category
        for cat_key, min_dur in MIN_VISIT_BY_CATEGORY.items():
            if cat_key in cat and duration < min_dur * 0.7:
                report.warn("visit_duration", f"Ngày {day_idx}: {name} ({cat}) chỉ {duration}p – nên ≥{min_dur}p")
                break


def check_time_window_respected(report: UXReport, itinerary: dict[str, Any] | None, start_min: int | None, end_min: int | None, label: str = ""):
    """Kiểm tra lịch trình nằm trong khung giờ yêu cầu."""
    prefix = f"[{label}] " if label else ""
    stops = real_stops(itinerary)
    if not stops:
        return

    first_arr = min((s.get("arrival_time_min") or 9999) for s in stops)
    last_dep = max((s.get("departure_time_min") or 0) for s in stops)

    if start_min is not None and first_arr < start_min - 15:
        report.fail("coherence", f"{prefix}Bắt đầu lúc {first_arr // 60}:{first_arr % 60:02d} trước giờ yêu cầu {start_min // 60}:{start_min % 60:02d}")
    elif start_min is not None:
        report.pass_("coherence", f"{prefix}Bắt đầu đúng giờ ({first_arr // 60}:{first_arr % 60:02d} >= {start_min // 60}:{start_min % 60:02d})")

    if end_min is not None and last_dep > end_min + 30:
        report.warn("coherence", f"{prefix}Kết thúc lúc {last_dep // 60}:{last_dep % 60:02d} muộn hơn {end_min // 60}:{end_min % 60:02d}")
    elif end_min is not None:
        report.pass_("coherence", f"{prefix}Kết thúc đúng giờ ({last_dep // 60}:{last_dep % 60:02d} <= {end_min // 60}:{end_min % 60:02d})")


def check_has_keywords(report: UXReport, itinerary: dict[str, Any] | None, keywords: list[str], label: str):
    """Kiểm tra lịch trình có chứa các keyword quan trọng."""
    if not itinerary:
        report.fail("coherence", f"Không tìm thấy '{label}' – lịch trình trống")
        return False
    all_text = " ".join(stop_name(s).lower() for s in all_stops(itinerary))
    all_text += " " + " ".join(
        " ".join(str(t).lower() for t in (s.get("tags") or []))
        for s in all_stops(itinerary)
    )
    found = any(kw.lower() in all_text for kw in keywords)
    if found:
        report.pass_("coherence", f"Có '{label}' trong lịch trình")
    else:
        report.fail("coherence", f"Thiếu '{label}' trong lịch trình")
    return found


def run_full_ux_checks(report: UXReport, itinerary: dict[str, Any] | None, budget: float | None = None, start_min: int | None = None, end_min: int | None = None, label: str = ""):
    """Chạy toàn bộ UX checks trên 1 itinerary."""
    if not itinerary:
        report.fail("coherence", f"[{label}] Lịch trình trống")
        return

    check_no_time_overlap(report, itinerary, label)
    check_budget(report, itinerary, budget)
    check_time_window_respected(report, itinerary, start_min, end_min, label)

    for di, day_stops_list in enumerate(stops_by_day(itinerary)):
        day_idx = di + 1
        if not day_stops_list:
            report.warn("coherence", f"[{label}] Ngày {day_idx}: Không có điểm tham quan nào")
            continue
        check_geographic_clustering(report, day_stops_list, day_idx)
        check_variety(report, day_stops_list, day_idx)
        check_meal_timing(report, day_stops_list, day_idx)
        check_travel_time(report, day_stops_list, day_idx)
        check_visit_duration(report, day_stops_list, day_idx)


# ═══════════════════════════════════════════════════════════════
# Test Scenarios
# ═══════════════════════════════════════════════════════════════

SCENARIOS = [
    {
        "name": "01_couple_romantic_1day",
        "description": "Cặp đôi đi Huế 1 ngày lãng mạn, chill nhẹ, muốn check-in đẹp",
        "build": "Tôi và bạn gái đi Huế 1 ngày, muốn lịch trình lãng mạn, check-in đẹp, ăn uống ngon, cafe view sông Hương, tối đi dạo phố cổ, ngân sách 800k, di 8h den 21h",
        "followups": ["ok tao di"],
        "edit": "Bỏ bớt 1 điểm tham quan, thêm 1 quán cafe view đẹp buổi chiều",
        "checks": {
            "budget": 800000,
            "start_min": 480,
            "end_min": 1260,
            "must_have": [
                (["cafe", "cà phê", "coffee"], "cafe/cà phê"),
            ],
        },
    },
    {
        "name": "02_family_culture_2days",
        "description": "Gia đình 4 người đi Huế 2 ngày, thiên văn hóa lịch sử, có trẻ nhỏ",
        "build": "Gia dinh 4 nguoi di Hue 2 ngay, co tre nho 5 tuoi, muon tham quan di tich lich su, Dai Noi, lang tam, an trua dia phuong moi ngay, nghi ngoi nhieu, ngan sach 2 trieu, di 8h den 19h",
        "followups": [],
        "edit": "Ngày 1 bỏ 1 lăng, thêm 1 công viên hoặc điểm vui chơi cho trẻ em",
        "checks": {
            "budget": 2000000,
            "start_min": 480,
            "end_min": 1140,
            "must_have": [
                (["đại nội", "dai noi", "imperial", "hoàng thành"], "Đại Nội"),
                (["lăng", "lang", "tomb"], "Lăng tẩm"),
            ],
        },
    },
    {
        "name": "03_backpacker_food_1day",
        "description": "Phượt thủ 1 ngày, ưu tiên ẩm thực đường phố, ngân sách thấp",
        "build": "Di Hue 1 ngay kieu phuot, chi muon an uong duong pho la chinh, bun bo, com hen, che Hue, banh beo, cafe muoi, toi di pho di bo, ngan sach 400k, tu 7h den 22h",
        "followups": ["chi tap trung am thuc"],
        "edit": "Thêm 1 món ăn vặt buổi chiều, bỏ 1 quán nào đắt nhất",
        "timeout": 300,
        "plan_timeout": 360,
        "checks": {
            "budget": 400000,
            "start_min": 420,
            "end_min": 1320,
            "must_have": [
                (["bún bò", "bun bo"], "Bún bò"),
                (["cơm hến", "com hen", "hến"], "Cơm hến"),
            ],
        },
    },
    {
        "name": "04_afternoon_only",
        "description": "Chỉ có buổi chiều rảnh, 13h-18h, muốn trải nghiệm nhanh",
        "build": "Toi chi co buoi chieu 13h den 18h o Hue, muon di 1-2 diem van hoa noi bat nhat, 1 cafe nghi chan, ngan sach 300k",
        "followups": [],
        "edit": "Đổi thứ tự: cafe trước, rồi mới đi tham quan",
        "checks": {
            "budget": 300000,
            "start_min": 780,
            "end_min": 1080,
        },
    },
    {
        "name": "05_3day_mixed_deep",
        "description": "3 ngày khám phá sâu Huế: văn hóa, ẩm thực, thiên nhiên",
        "build": "Di Hue 3 ngay, ngay 1 van hoa di tich, ngay 2 thien nhien va lang tam xa, ngay 3 am thuc va mua sam, ngan sach 3 trieu, di 8h den 20h",
        "followups": [],
        "edit": "Ngày 2 thêm 1 quán ăn trưa địa phương. Ngày 3 bỏ mua sắm, thay bằng 1 quán cafe view đẹp",
        "checks": {
            "budget": 3000000,
            "start_min": 480,
            "end_min": 1200,
        },
    },
    {
        "name": "06_evening_night_only",
        "description": "Đã đi cả ngày rồi, tối muốn ăn uống và đi dạo 18h-22h",
        "build": "Toi o Hue toi nay, tu 18h den 22h muon an toi ngon, di dao song Huong, co the ghe cho dem hoac pho di bo, ngan sach 500k",
        "followups": [],
        "edit": "Thêm 1 quán kem hoặc chè tráng miệng sau ăn tối",
        "checks": {
            "budget": 500000,
            "start_min": 1080,
            "end_min": 1320,
        },
    },
    {
        "name": "07_edit_reorder_complex",
        "description": "Lịch 2 ngày, edit phức tạp: đổi điểm giữa các ngày",
        "build": "Hue 2 ngay, muon Dai Noi, Lang Khai Dinh, lang huong Thuy Xuan, cafe muoi, bun bo, com hen, di 8h den 20h, ngan sach 1.5 trieu",
        "followups": [],
        "edit": "Chuyển Lăng Khải Định sang ngày 2, thêm 1 quán cafe buổi sáng ngày 1",
        "timeout": 300,
        "plan_timeout": 360,
        "checks": {
            "budget": 1500000,
            "start_min": 480,
            "end_min": 1200,
            "must_have": [
                (["đại nội", "dai noi", "imperial"], "Đại Nội"),
                (["khải định", "khai dinh"], "Lăng Khải Định"),
            ],
        },
    },
    {
        "name": "08_healing_zen_vegan_glutenfree_2days",
        "description": "Chuyến đi thiền định chữa lành 2 ngày, thuần chay dị ứng gluten nghiêm ngặt, đi sớm 5h sáng",
        "build": "Tôi muốn đi Huế 2 ngày để thiền định và chữa lành tâm hồn (healing). Tôi chỉ muốn tham quan các ngôi chùa thiền cổ cực kỳ yên tĩnh (không ồn ào du lịch thương mại) và học thiền. Đặc biệt, tôi bị dị ứng gluten nặng và ăn chay trường nghiêm ngặt (chỉ ăn thuần chay - vegan), không được có tỏi, hành (ngũ vị tân). Lịch trình từ 5h sáng (để ngắm bình minh/thiền sớm) đến 19h tối. Ngân sách 1.5 triệu.",
        "followups": [],
        "edit": "Ngày 2 bỏ bớt 1 chùa thiền xa, thêm 1 quán trà chiều thảo mộc tĩnh lặng",
        "timeout": 300,
        "plan_timeout": 360,
        "checks": {
            "budget": 1500000,
            "start_min": 300,
            "end_min": 1140,
            "must_have": [
                (["chùa", "zen", "thiền", "từ hiếu", "huyền không"], "Chùa/Thiền định"),
                (["chay", "vegan", "vegetari", "không gluten"], "Món chay thuần"),
            ],
        },
    },
    {
        "name": "09_indoor_stormy_day_craft_1day",
        "description": "Lịch trình 1 ngày tránh bão cực đoan (indoor-only), làm đồ thủ công truyền thống và bảo tàng cung đình",
        "build": "Thời tiết Huế hôm nay dự báo bão mưa cực kỳ to cả ngày, tôi không muốn bị ướt. Hãy lên lịch trình 1 ngày hoàn toàn TRONG NHÀ (indoor-only) ở Huế, có hoạt động trải nghiệm làm đồ thủ công truyền thống, ăn uống tại các nhà hàng có mái che ấm cúng, có bảo tàng trưng bày cổ vật. Ngân sách 1 triệu.",
        "followups": [],
        "edit": "Thêm 1 quán cafe sách yên tĩnh buổi chiều để đọc sách tránh mưa",
        "checks": {
            "budget": 1000000,
            "must_have": [
                (["bảo tàng", "museum", "cổ vật", "trong nhà", "cung đình"], "Bảo tàng/Trong nhà"),
                (["thủ công", "craft", "làm tranh", "hoa giấy", "trải nghiệm"], "Trải nghiệm thủ công"),
            ],
        },
    },
    {
        "name": "10_wheelchair_accessible_slow_elderly_1day",
        "description": "Lịch trình 1 ngày cho người khuyết tật/người già di chuyển xe lăn dốc dẹp, nhịp độ cực chậm",
        "build": "Tôi dẫn bà ngoại 85 tuổi đi xe lăn du lịch Huế 1 ngày. Lịch trình phải đi cực kỳ chậm, các điểm đến bắt buộc phải hỗ trợ lối đi xe lăn hoặc không phải leo bậc thang dốc. Không đi quá 3 điểm một ngày để tránh mệt, nghỉ trưa kéo dài ít nhất 2.5 tiếng ở nơi mát mẻ, yên tĩnh. Ngân sách 800k.",
        "followups": [],
        "edit": "Đổi điểm tham quan buổi chiều bằng đi thuyền chill trên sông Hương ngắm cảnh hoàng hôn",
        "checks": {
            "budget": 800000,
            "must_have": [
                (["thuyền", "sông hương", "boat", "cruise", "rồng"], "Thuyền sông Hương"),
            ],
        },
    },
    {
        "name": "11_semantic_exotic_food_1day",
        "description": "Blogger ẩm thực săn lùng món ngon dân dã độc lạ Huế (bánh bèo, rau má, bánh căn, vả trộn, chè bột lọc heo quay)",
        "build": "Tôi là blogger ẩm thực muốn đi Huế 1 ngày để săn lùng các món ăn dân dã và đặc sản cực kỳ lạ. Tôi muốn ăn bánh bèo chén chuẩn vị, uống nước rau má đậu xanh dừa, ăn bánh căn hoặc bánh khoái, vả trộn xúc bánh tráng, và kết thúc bằng món chè bột lọc heo quay trứ danh. Lập cho tôi lịch trình từ 8h đến 21h, ngân sách 500k.",
        "followups": [],
        "edit": "Đổi chỗ quán Chè Hẻm xuống cuối ngày sau bữa bánh bèo Bà Nga để làm món tráng miệng ngọt, và dời Bánh Bèo Bà Đỏ lên làm bữa ăn sáng mặn lúc 8h30",
        "checks": {
            "budget": 500000,
            "start_min": 480,
            "end_min": 1260,
            "must_have": [
                (["bánh bèo", "bèo"], "Bánh bèo"),
                (["rau má", "rau ma"], "Rau má"),
                (["bánh căn", "bánh khoái", "khoái"], "Bánh căn/Bánh khoái"),
                (["vả trộn", "vả", "va tron"], "Vả trộn"),
                (["heo quay", "chè heo quay"], "Chè bột lọc heo quay"),
            ],
        },
    },
]


# ═══════════════════════════════════════════════════════════════
# Main Runner
# ═══════════════════════════════════════════════════════════════

def run_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    name = scenario["name"]
    checks = scenario.get("checks", {})
    report = UXReport(case_name=name)

    print(f"\n{'='*60}")
    print(f"🔍 {name}: {scenario['description']}")
    print(f"{'='*60}")

    t0 = time.time()

    # 1. Build
    print(f"  📋 Building itinerary...")
    scenario_timeout = scenario.get("timeout", 180)
    scenario_plan_timeout = scenario.get("plan_timeout", 280)
    build = build_flow(
        scenario["build"],
        scenario.get("followups", []),
        timeout=scenario_timeout,
        plan_timeout=scenario_plan_timeout,
    )
    plan_data = build.get("plan") or {}
    itinerary = plan_data.get("layer4_result") if plan_data else None
    contract = build.get("contract") or {}

    build_elapsed = time.time() - t0
    print(f"  ⏱ Build done in {build_elapsed:.1f}s")

    if not itinerary:
        status_val = plan_data.get("status")
        if status_val == "error" or "error_code" in plan_data:
            report.fail("coherence", f"Build thất bại: {plan_data.get('message') or plan_data.get('error_code', 'unknown')}")
        elif not plan_data:
            report.fail("coherence", "Không nhận được plan_trip response – có thể contract chưa ready")
        else:
            report.fail("coherence", f"Build trả về nhưng không có itinerary (status={status_val})")
        report.compute_score()
        return {
            "status": "BUILD_FAILED",
            "scenario": scenario,
            "report": report.to_dict(),
            "elapsed_s": round(time.time() - t0, 1),
            "build_turns": build.get("turns"),
            "contract": contract,
        }

    # Check build quality
    num_real = len(real_stops(itinerary))
    num_days = len(itinerary.get("days", []))
    report.pass_("coherence", f"Build thành công: {num_real} điểm, {num_days} ngày")
    print(f"  ✅ {num_real} stops, {num_days} days")

    # Print itinerary summary
    for di, ds in enumerate(stops_by_day(itinerary)):
        day_idx = di + 1
        for s in ds:
            arr = s.get("arrival_time_min", 0)
            dep = s.get("departure_time_min", 0)
            print(f"    Ngày {day_idx}: {arr // 60}:{arr % 60:02d}-{dep // 60}:{dep % 60:02d} {stop_name(s)} [{stop_category(s)}]")

    # Run UX checks on build
    run_full_ux_checks(
        report, itinerary,
        budget=checks.get("budget"),
        start_min=checks.get("start_min"),
        end_min=checks.get("end_min"),
        label="Build",
    )

    # Check must_have keywords
    for keywords, label in checks.get("must_have", []):
        check_has_keywords(report, itinerary, keywords, label)

    # 2. Edit
    edited_itinerary = None
    if scenario.get("edit"):
        print(f"\n  ✏️  Editing: {scenario['edit']}")
        t_edit = time.time()
        edit_result = apply_edit(
            scenario["edit"],
            contract,
            itinerary,
            build.get("history") or [],
            timeout=scenario_timeout,
        )
        edit_elapsed = time.time() - t_edit
        print(f"  ⏱ Edit done in {edit_elapsed:.1f}s")

        edited_itinerary = edit_result.get("updated_itinerary")
        if edited_itinerary:
            edit_real = len(real_stops(edited_itinerary))
            report.pass_("edit_accuracy", f"Edit thành công: {edit_real} điểm sau chỉnh sửa")
            print(f"  ✅ Edited: {edit_real} stops")

            # Print edited summary
            for di, ds in enumerate(stops_by_day(edited_itinerary)):
                day_idx = di + 1
                for s in ds:
                    arr = s.get("arrival_time_min", 0)
                    dep = s.get("departure_time_min", 0)
                    print(f"    Ngày {day_idx}: {arr // 60}:{arr % 60:02d}-{dep // 60}:{dep % 60:02d} {stop_name(s)} [{stop_category(s)}]")

            # Run UX checks on edited itinerary
            run_full_ux_checks(
                report, edited_itinerary,
                budget=checks.get("budget"),
                start_min=checks.get("start_min"),
                end_min=checks.get("end_min"),
                label="Edited",
            )

            # Edit should not destroy existing good content
            before_names = {stop_name(s).lower() for s in real_stops(itinerary)}
            after_names = {stop_name(s).lower() for s in real_stops(edited_itinerary)}
            lost = before_names - after_names
            gained = after_names - before_names
            if len(lost) > len(real_stops(itinerary)) * 0.5:
                report.fail("edit_accuracy", f"Edit phá hủy quá nhiều: mất {len(lost)}/{len(before_names)} điểm")
            elif lost:
                report.pass_("edit_accuracy", f"Edit bỏ {len(lost)} điểm, thêm {len(gained)} điểm – hợp lý")
        else:
            report.warn("edit_accuracy", "Edit không trả về updated_itinerary")
            print(f"  ⚠️ No updated_itinerary returned")

    elapsed = round(time.time() - t0, 1)
    report.compute_score()

    # Summary
    print(f"\n  📊 Score: {report.score}/100 ({sum(1 for f in report.findings if f.severity == 'PASS')}P / {sum(1 for f in report.findings if f.severity == 'WARN')}W / {sum(1 for f in report.findings if f.severity == 'FAIL')}F)")

    return {
        "status": "DONE",
        "scenario": {"name": name, "description": scenario["description"]},
        "report": report.to_dict(),
        "elapsed_s": elapsed,
        "build_summary": _summarize(itinerary),
        "edit_summary": _summarize(edited_itinerary) if edited_itinerary else None,
        "contract": contract,
    }


def _summarize(itinerary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not itinerary:
        return []
    summary = []
    for d in itinerary.get("days", []):
        summary.append({
            "day": (d.get("day_index") or 0) + 1,
            "stops": [
                {
                    "time": f"{s.get('arrival_time_min', 0) // 60}:{s.get('arrival_time_min', 0) % 60:02d} → {s.get('departure_time_min', 0) // 60}:{s.get('departure_time_min', 0) % 60:02d}",
                    "name": stop_name(s),
                    "category": stop_category(s),
                    "price": s.get("price") or s.get("entrance_fee") or 0,
                }
                for s in d.get("stops", [])
                if not str(s.get("poi_id", "")).startswith("__")
            ],
        })
    return summary


def main() -> None:
    wait_health()
    print(f"\n{'#'*60}")
    print(f"# UX QUALITY STRESS TEST – {len(SCENARIOS)} kịch bản")
    print(f"# Bắt đầu: {time.strftime('%H:%M:%S')}")
    print(f"{'#'*60}")

    results: dict[str, Any] = {}
    scores: list[float] = []
    t_total = time.time()

    for scenario in SCENARIOS:
        try:
            result = run_scenario(scenario)
            results[scenario["name"]] = result
            scores.append(result["report"]["score"])
        except Exception as exc:
            print(f"\n  ❌ ERROR: {repr(exc)}")
            traceback.print_exc()
            results[scenario["name"]] = {
                "status": "ERROR",
                "scenario": {"name": scenario["name"], "description": scenario["description"]},
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            scores.append(0.0)

    total_elapsed = round(time.time() - t_total, 1)

    # Final summary
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    print(f"\n{'#'*60}")
    print(f"# KẾT QUẢ TỔNG HỢP")
    print(f"# Thời gian: {total_elapsed}s")
    print(f"# Điểm trung bình: {avg_score}/100")
    print(f"{'#'*60}")

    for name, result in results.items():
        status = result.get("status", "?")
        score = result.get("report", {}).get("score", 0)
        emoji = "✅" if score >= 70 else "⚠️" if score >= 40 else "❌"
        print(f"  {emoji} {name}: {score}/100 ({status})")

    # Write results
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results["_summary"] = {
        "total_scenarios": len(SCENARIOS),
        "avg_score": avg_score,
        "total_elapsed_s": total_elapsed,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📁 Kết quả chi tiết: {OUT}")


if __name__ == "__main__":
    main()
