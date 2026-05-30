# -*- coding: utf-8 -*-
"""Stress test full build -> draft -> post-draft edit flows.

Runs through the public Gateway API so each case exercises:
chat_process collection/confirmation, plan_trip, deterministic edit intent,
edit confirmation, and in-memory itinerary mutation.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

BASE_URL = "http://127.0.0.1:8001"
OUT = Path("scratch/stress_outputs/build_edit_flows.json")


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
        timeout=180,
    )


def plan(prompt: str, contract: dict[str, Any]) -> dict[str, Any]:
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
        timeout=280,
    )


def build_flow(prompt: str, followups: list[str]) -> dict[str, Any]:
    history: list[dict[str, str]] = []
    turns = []
    first = chat(prompt)
    turns.append(first)
    history += [{"role": "user", "content": prompt}, {"role": "assistant", "content": first.get("reply", "")}]
    contract = first.get("updated_contract") or {}

    for followup in followups:
        if turns[-1].get("status") == "ready":
            break
        nxt = chat(followup, contract=contract, history=history)
        turns.append(nxt)
        history += [{"role": "user", "content": followup}, {"role": "assistant", "content": nxt.get("reply", "")}]
        contract = nxt.get("updated_contract") or contract

    if turns[-1].get("phase") == "confirming" and turns[-1].get("status") != "ready":
        ok = chat("ok tao di", contract=contract, history=history)
        turns.append(ok)
        history += [{"role": "user", "content": "ok tao di"}, {"role": "assistant", "content": ok.get("reply", "")}]
        contract = ok.get("updated_contract") or contract

    planned = None
    if turns[-1].get("status") == "ready":
        planned = plan(prompt, contract)

    return {"turns": turns, "contract": contract, "plan": planned, "history": history}


def apply_edit(
    edit_prompt: str,
    contract: dict[str, Any],
    itinerary: dict[str, Any],
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    first = chat(
        edit_prompt,
        contract=contract,
        history=history or [],
        has_draft=True,
        current_itinerary=itinerary,
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
        )
        turns.append(ok)
        updated = ok.get("updated_itinerary")

    return {"turns": turns, "updated_itinerary": updated}


def all_stops(itinerary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not itinerary:
        return []
    return [s for d in itinerary.get("days", []) for s in d.get("stops", [])]


def names(itinerary: dict[str, Any] | None) -> list[str]:
    return [str(s.get("poi_name") or s.get("name") or "") for s in all_stops(itinerary)]


def joined_names(itinerary: dict[str, Any] | None) -> str:
    return " | ".join(names(itinerary)).lower()


def count_real_stops(itinerary: dict[str, Any] | None) -> int:
    return sum(1 for s in all_stops(itinerary) if not str(s.get("poi_id", "")).startswith("__"))


def no_overlap(itinerary: dict[str, Any] | None) -> bool:
    if not itinerary:
        return False
    for day in itinerary.get("days", []):
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


def first_arrival(itinerary: dict[str, Any] | None) -> int | None:
    vals = [s.get("arrival_time_min") for s in all_stops(itinerary) if isinstance(s.get("arrival_time_min"), int)]
    return min(vals) if vals else None


def has_any(itinerary: dict[str, Any] | None, terms: list[str]) -> bool:
    text = joined_names(itinerary)
    return any(term.lower() in text for term in terms)


def removed_or_reduced(before: dict[str, Any], after: dict[str, Any], terms: list[str]) -> bool:
    before_count = sum(1 for n in names(before) if any(t.lower() in n.lower() for t in terms))
    after_count = sum(1 for n in names(after) if any(t.lower() in n.lower() for t in terms))
    return after_count < before_count


def summarize(itinerary: dict[str, Any] | None) -> list[dict[str, Any]]:
    summary = []
    if not itinerary:
        return summary
    for day in itinerary.get("days", []):
        summary.append({
            "day": (day.get("day_index") or 0) + 1,
            "stops": [
                {
                    "time": f"{s.get('arrival_time') or s.get('arrival_time_min')}->{s.get('departure_time') or s.get('departure_time_min')}",
                    "name": s.get("poi_name"),
                    "category": s.get("category"),
                    "travel_next": s.get("travel_time_to_next_min"),
                }
                for s in day.get("stops", [])
            ],
        })
    return summary


CASES = [
    {
        "name": "food_micro_edit_generic",
        "build": "Hue 1 ngay food tour duong pho, muon an bun bo, com hen, che Hue, cafe muoi, di chill tu 9h den 20h, 600k",
        "followups": ["chi tap trung am thuc, ok tao di"],
        "edit": "Bo bot 1 quan an nang bung, them 1 mon an vat buoi chieu, dung vuot 600k",
    },
    {
        "name": "culture_pending_then_day2_edit",
        "build": "Toi muon kham pha van hoa Hue 3 ngay, di nhe nhang, ngan sach 1 trieu",
        "followups": ["Di 8h den 20h moi ngay, co them mon an dia phuong va cafe, van hoa la chinh nhung dung qua day"],
        "edit": "Ngay 2 bo bot chua, them 1 diem ngoai troi nhe va 1 quan an toi dia phuong",
    },
    {
        "name": "afternoon_reorder_time",
        "build": "Hue 1 ngay buoi chieu thoi, tu 13h den 18h, muon Dai Noi, cafe muoi, them 1 mon dia phuong, di chill, 400k",
        "followups": [],
        "edit": "Chuyen Dai Noi len dau tien luc 13h, sau do moi cafe muoi, mon an de cuoi lich",
    },
    {
        "name": "two_day_mixed_edit",
        "build": "Hue 2 ngay, muon di Dai Noi, Lang Khai Dinh, lang huong Thuy Xuan, cafe dep, an bun bo va com hen, ngan sach 1.5 trieu, di 8h den 20h",
        "followups": [],
        "edit": "Ngay 1 bo cafe dep, them cafe muoi sau Dai Noi. Chuyen Lang Khai Dinh sang ngay 2, buoi toi ngay 2 them pho di bo hoac cho dem",
    },
    {
        "name": "tight_constraint_then_replace",
        "build": "Hue 1 ngay, di tu 16h den 19h, muon Dai Noi, Lang Minh Mang, Lang Khai Dinh, lang huong Thuy Xuan, an toi dia phuong, ngan sach 200k, di chill",
        "followups": ["Vay bo Lang Minh Mang, giu Dai Noi va lang huong, an toi don gian"],
        "edit": "Neu con gap qua thi bo lang huong, thay bang diem gan trung tam hon",
    },
]


def evaluate_case(name: str, build: dict[str, Any], edit: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    plan_data = build.get("plan") or {}
    itinerary = plan_data.get("layer4_result") if plan_data else None
    edited = edit.get("updated_itinerary")

    def check(cond: bool, msg: str) -> None:
        findings.append(("PASS: " if cond else "FAIL: ") + msg)

    check(plan_data.get("status") == "success", "build success")
    check(no_overlap(itinerary), "build no overlap")
    check(edited is not None, "edit returned updated_itinerary")
    if edited:
        check(no_overlap(edited), "edited no overlap")
        check(count_real_stops(edited) > 0, "edited kept real stops")

    if name == "food_micro_edit_generic":
        for label, terms in {
            "bun bo": ["bun bo", "bún bò"],
            "com hen": ["com hen", "cơm hến", "hen"],
            "che": ["che", "chè"],
            "cafe muoi": ["muoi", "muối"],
        }.items():
            check(has_any(itinerary, terms), f"build has {label}")
        if edited:
            check(count_real_stops(edited) >= count_real_stops(itinerary), "edit adds or preserves stop count")
    elif name == "culture_pending_then_day2_edit":
        contract = build.get("contract") or {}
        check(bool(contract.get("target_category_distribution")), "distribution present")
        check((contract.get("num_days") or 0) == 3, "3 day contract")
        if edited:
            check(len(edited.get("days", [])) == 3, "edit preserves 3 days")
            check(has_any(edited, ["an", "ăn", "bun", "com", "hến", "hen", "quan", "quán"]), "edit has food-ish stop")
    elif name == "afternoon_reorder_time":
        check(first_arrival(itinerary) is not None and first_arrival(itinerary) >= 780, "build starts after 13:00")
        if edited:
            first_name = names(edited)[0].lower() if names(edited) else ""
            check("dai noi" in first_name or "đại nội" in first_name, "edited Dai Noi first")
            check(first_arrival(edited) is not None and first_arrival(edited) >= 780, "edited still afternoon")
    elif name == "two_day_mixed_edit":
        check(len((itinerary or {}).get("days", [])) == 2, "build has 2 days")
        if edited:
            check(len(edited.get("days", [])) == 2, "edit preserves 2 days")
            check(has_any(edited, ["muoi", "muối"]), "edit adds cafe muoi")
            day2_text = " | ".join(str(s.get("poi_name") or "") for s in edited.get("days", [{}])[1].get("stops", [])).lower()
            check("khai dinh" in day2_text or "khải định" in day2_text, "Lang Khai Dinh on day 2")
    elif name == "tight_constraint_then_replace":
        contract = build.get("contract") or {}
        tw = contract.get("time_window") or {}
        check(tw.get("start_min") in (960, None) or (tw.get("start_min") or 0) >= 900, "late window captured")
        if edited:
            check(count_real_stops(edited) <= max(4, count_real_stops(itinerary)), "edited remains compact")
            check(no_overlap(edited), "edited feasible timing")

    return findings


def main() -> None:
    wait_health()
    results: dict[str, Any] = {}
    for case in CASES:
        name = case["name"]
        print(f"\nRUN {name}")
        try:
            build = build_flow(case["build"], case["followups"])
            itinerary = (build.get("plan") or {}).get("layer4_result")
            edit = {"turns": [], "updated_itinerary": None}
            if itinerary:
                edit = apply_edit(case["edit"], build.get("contract") or {}, itinerary, build.get("history") or [])
            findings = evaluate_case(name, build, edit)
            status = "PASS" if not any(f.startswith("FAIL") for f in findings) else "FAIL"
            print(status)
            for f in findings:
                print(" ", f)
            results[name] = {
                "status": status,
                "build_prompt": case["build"],
                "edit_prompt": case["edit"],
                "build_turns": build.get("turns"),
                "contract": build.get("contract"),
                "plan_status": (build.get("plan") or {}).get("status"),
                "locked_pois": (build.get("plan") or {}).get("locked_pois"),
                "build_summary": summarize(itinerary),
                "edit_turns": edit.get("turns"),
                "edit_summary": summarize(edit.get("updated_itinerary")),
                "findings": findings,
            }
        except Exception as exc:
            print("ERROR", repr(exc))
            results[name] = {
                "status": "ERROR",
                "build_prompt": case["build"],
                "edit_prompt": case["edit"],
                "error": repr(exc),
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWROTE {OUT}")


if __name__ == "__main__":
    main()
