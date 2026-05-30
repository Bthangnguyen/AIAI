# -*- coding: utf-8 -*-
"""Focused E2E checks after time-window, semantic, and travel-time fixes."""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "http://127.0.0.1:8001"
OUT = Path("scratch/stress_outputs/focused_after_fixes.json")


def post_json(path: str, payload: dict[str, Any], timeout: int = 260) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_health() -> None:
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/v1/trip/health", timeout=5) as res:
                if res.status == 200:
                    return
        except Exception:
            time.sleep(2)
    raise RuntimeError("gateway not healthy")


def empty_contract() -> dict[str, Any]:
    return {"destination": None, "budget_max": None, "radius_km": 10.0, "num_days": 1, "tags": [], "locked_pois": []}


def chat(message: str, contract: dict[str, Any] | None = None, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return post_json("/v1/trip/chat_process", {
        "message": message,
        "history": history or [],
        "current_contract": contract or empty_contract(),
        "has_draft": False,
    }, timeout=160)


def plan(prompt: str, contract: dict[str, Any]) -> dict[str, Any]:
    return post_json("/v1/trip/plan_trip", {
        "user_prompt": prompt,
        "num_days": contract.get("num_days"),
        "budget": contract.get("budget_max"),
        "destination": contract.get("destination") or "Huế",
        "preferences": contract.get("tags") or [],
        "contract": contract,
    }, timeout=280)


def complete_flow(prompt: str, followup: str | None = None) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    first = chat(prompt)
    history += [{"role": "user", "content": prompt}, {"role": "assistant", "content": first.get("reply", "")}]
    contract = first.get("updated_contract") or {}
    turns = [first]

    if first.get("phase") == "collecting" and followup:
        second = chat(followup, contract=contract, history=history)
        history += [{"role": "user", "content": followup}, {"role": "assistant", "content": second.get("reply", "")}]
        contract = second.get("updated_contract") or contract
        turns.append(second)

    if turns[-1].get("phase") == "confirming":
        ok = chat("ok tạo đi", contract=contract, history=history)
        contract = ok.get("updated_contract") or contract
        turns.append(ok)

    planned = None
    if turns[-1].get("status") == "ready":
        planned = plan(prompt, contract)

    return {"prompt": prompt, "turns": turns, "contract": contract, "plan": planned}


def stops(layer4: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not layer4:
        return []
    return [s for d in layer4.get("days", []) for s in d.get("stops", [])]


def category_counts(layer4: dict[str, Any] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in stops(layer4):
        if str(s.get("poi_id", "")).startswith("__"):
            continue
        cat = (s.get("category") or "none").lower()
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def no_overlap(layer4: dict[str, Any] | None) -> bool:
    if not layer4:
        return False
    for day in layer4.get("days", []):
        prev = -1
        for s in sorted(day.get("stops", []), key=lambda x: x.get("arrival_time_min", 0)):
            arr = s.get("arrival_time_min")
            dep = s.get("departure_time_min")
            if not isinstance(arr, int) or not isinstance(dep, int):
                return False
            if arr < prev:
                return False
            prev = max(prev, dep)
    return True


def travel_not_all_zero(layer4: dict[str, Any] | None) -> bool:
    vals = [s.get("travel_time_to_next_min") for s in stops(layer4) if s.get("travel_time_to_next_min") is not None]
    return bool(vals) and not all(int(v or 0) == 0 for v in vals)


def first_arrival(layer4: dict[str, Any] | None) -> int | None:
    arrs = [s.get("arrival_time_min") for s in stops(layer4) if isinstance(s.get("arrival_time_min"), int)]
    return min(arrs) if arrs else None


def contains_name(layer4: dict[str, Any] | None, terms: tuple[str, ...]) -> bool:
    joined = " | ".join((s.get("poi_name") or "").lower() for s in stops(layer4))
    return any(t.lower() in joined for t in terms)


def evaluate(name: str, data: dict[str, Any]) -> dict[str, Any]:
    planned = data.get("plan") or {}
    layer4 = planned.get("layer4_result") if planned else None
    contract = data.get("contract") or {}
    findings: list[str] = []

    def check(cond: bool, msg: str) -> None:
        findings.append(("PASS: " if cond else "FAIL: ") + msg)

    check(bool(contract.get("target_category_distribution")), "distribution present")
    check(planned is not None and planned.get("status") == "success", "plan_trip success")
    if layer4:
        check(no_overlap(layer4), "no overlap")
        check(travel_not_all_zero(layer4), "travel_time_to_next not all zero")

    if name == "afternoon":
        tw = contract.get("time_window") or {}
        check(contract.get("time_slot") == "afternoon", "time_slot afternoon")
        check(tw.get("start_min") == 780 and tw.get("end_min") == 1080, "time_window 13:00-18:00")
        fa = first_arrival(layer4)
        check(fa is not None and fa >= 780, "first stop after 13:00")
    elif name == "food_tour":
        counts = category_counts(layer4)
        total = sum(counts.values()) or 1
        check((counts.get("food", 0) + counts.get("cafe", 0) + counts.get("nightlife", 0)) / total >= 0.75, "food/cafe/nightlife ratio >= 75%")
        check(counts.get("culture", 0) == 0, "no culture in food tour")
    elif name == "two_cafes":
        counts = category_counts(layer4)
        check(first_arrival(layer4) is not None and first_arrival(layer4) >= 780, "first stop after 13:00")
        check(counts.get("cafe", 0) >= 1, "has cafe")
        check(counts.get("culture", 0) <= 1, "culture not dominant")
    elif name == "specific_food":
        check(contains_name(layer4, ("bún bò", "bun bo")), "has bun bo")
        check(contains_name(layer4, ("cơm hến", "com hen", "hến")), "has com hen")
        check(contains_name(layer4, ("chè", "che")), "has che")
    elif name == "travel_time":
        check(travel_not_all_zero(layer4), "travel times exposed")
        check(no_overlap(layer4), "arrival respects previous departure")

    data["category_counts"] = category_counts(layer4)
    data["findings"] = findings
    data["status"] = "PASS" if not any(f.startswith("FAIL") for f in findings) else "FAIL"
    return data


def main() -> None:
    wait_health()
    cases = {
        "afternoon": ("Huế 1 ngày buổi chiều, chill, đi Đại Nội, uống cafe muối, ăn món địa phương, 500k", None),
        "food_tour": ("Food tour Huế 1 ngày, chill, đường phố, ngon bổ rẻ, 500k", "cả ngày, bắt đầu 9h sáng đến khoảng 9h tối"),
        "two_cafes": ("Huế 1 ngày buổi chiều, tôi muốn 2 quán cafe đẹp, 1 món ăn địa phương, đi chill, 400k", None),
        "specific_food": ("Huế 1 ngày, tôi muốn ăn bún bò, cơm hến, chè Huế, cafe muối, đi từ 9h đến 20h, 600k", None),
        "travel_time": ("Huế 1 ngày, đi Lăng Khải Định, Làng Hương Thủy Xuân, Đại Nội, cafe muối, ăn tối địa phương, đi 8h-20h", "ngân sách 1 triệu"),
    }

    results = {}
    for name, (prompt, followup) in cases.items():
        print(f"RUN {name}")
        data = complete_flow(prompt, followup)
        results[name] = evaluate(name, data)
        print(results[name]["status"])
        for f in results[name]["findings"]:
            print(" ", f)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE {OUT}")


if __name__ == "__main__":
    main()
