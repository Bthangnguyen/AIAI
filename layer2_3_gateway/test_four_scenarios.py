import asyncio
import httpx
import json
import sys

GW_URL = "http://localhost:8001/v1/trip"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer mock-session-token-xyz-987"
}

def minutes_to_time(minutes: int) -> str:
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def print_itinerary(title: str, itinerary: dict, llm_c: dict):
    print(f"\n================ 📅 {title} ================")
    print(f"Khách sạn: {llm_c.get('hotel_name')} ({llm_c.get('hotel_lat')}, {llm_c.get('hotel_lon')})")
    print(f"Số ngày: {len(itinerary.get('days', []))}")
    
    all_stop_names = []
    category_counts = {}
    
    for day in itinerary.get("days", []):
        day_num = day.get("day_index", 0) + 1
        print(f"\n📅 Ngày {day_num}:")
        stops = day.get("stops", [])
        if not stops:
            print("  (Không có địa điểm nào)")
            continue
        for stop in stops:
            poi_id = stop.get("poi_id", "")
            if poi_id.startswith("hotel_day_") or poi_id == "__rest_break__":
                continue
            poi_name = stop.get("poi_name") or "Unknown POI"
            arr_min = stop.get("arrival_time_min", 480)
            arr_time = minutes_to_time(arr_min)
            duration = stop.get("visit_duration_min", 60)
            category = stop.get("category") or "unknown"
            all_stop_names.append(poi_name)
            category_counts[category] = category_counts.get(category, 0) + 1
            desc = stop.get("description") or ""
            print(f"  - [{arr_time}] {poi_name} ({category}, {duration} phút) - {desc[:60]}...")
            
    print("\n📈 Phân bổ Category thực tế:")
    if all_stop_names:
        for cat, cnt in category_counts.items():
            print(f"  - {cat}: {cnt} điểm ({cnt / len(all_stop_names) * 100:.1f}%)")
    else:
        print("  - Trống")

async def run_scenario(client: httpx.AsyncClient, scenario_num: int, prompt_turns: list):
    print(f"\n\n#################################################################")
    print(f"### 🎬 SCENARIO {scenario_num}: {prompt_turns[0]} ###")
    print(f"#################################################################")
    
    current_contract = {
        "destination": None,
        "budget_max": None,
        "radius_km": 10.0,
        "num_days": 1,
        "tags": [],
        "locked_pois": [],
        "excluded_pois": [],
        "confirmed_fields": [],
    }
    history = []
    last_response = None
    
    # Converse dynamically until ready
    for turn_idx, user_msg in enumerate(prompt_turns[:-1]): # The last message is the edit request, handled after planning
        print(f"\n[User - Lượt {turn_idx+1}]: {user_msg}")
        
        payload = {
            "message": user_msg,
            "history": history,
            "current_contract": current_contract,
            "has_draft": False
        }
        
        resp = await client.post(f"{GW_URL}/chat_process", json=payload, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Lỗi ở Lượt {turn_idx+1}: HTTP {resp.status_code} - {resp.text}")
            return
            
        last_response = resp.json()
        print(f"\n[AI - Phản hồi {turn_idx+1}]: {last_response['reply']}")
        print(f"Status: {last_response['status']}")
        current_contract = last_response["updated_contract"]
        print(f"🎯 Distribution Rate ở lượt này: {current_contract.get('target_category_distribution')}")
        
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": last_response["reply"]})
        
        # If AI says ready but we have more turns, we keep going; if AI is ready and we are at the end, we break.
        if last_response["status"] == "ready" and turn_idx == len(prompt_turns) - 2:
            break
            
    # If the conversational status is still clarifying, force confirm
    if last_response and last_response["status"] == "clarifying":
        confirm_msg = "Đúng rồi, mình xác nhận tất cả thông tin, bạn tạo lịch trình giúp mình."
        print(f"\n[User - Xác nhận Cuối]: {confirm_msg}")
        payload = {
            "message": confirm_msg,
            "history": history,
            "current_contract": current_contract,
            "has_draft": False
        }
        resp = await client.post(f"{GW_URL}/chat_process", json=payload, headers=HEADERS)
        if resp.status_code == 200:
            last_response = resp.json()
            current_contract = last_response["updated_contract"]
            print(f"\n[AI]: {last_response['reply']}")
            print(f"Status: {last_response['status']}")
            print(f"🎯 Final Distribution Rate: {current_contract.get('target_category_distribution')}")
            
    # Mark ready and plan
    current_contract["ready_to_plan"] = True
    print(f"\n--- 🧭 GỌI API LẬP LỊCH TRÌNH BAN ĐẦU (PLAN TRIP) ---")
    plan_payload = {
        "user_prompt": prompt_turns[0],
        "num_days": current_contract["num_days"],
        "budget": current_contract["budget_max"],
        "destination": current_contract["destination"],
        "contract": current_contract
    }
    
    resp = await client.post(f"{GW_URL}/plan_trip", json=plan_payload, headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ Lỗi Lập lịch trình: HTTP {resp.status_code} - {resp.text}")
        return
        
    plan_res = resp.json()
    itinerary = plan_res.get("layer4_result")
    if not itinerary:
        print("❌ Lập lịch trình thất bại hoặc không có kết quả Layer 4.")
        return
        
    print_itinerary("LỊCH TRÌNH BAN ĐẦU", itinerary, plan_res.get("llm_contract") or {})
    
    # --- EDIT INTENT PHASE ---
    edit_msg = prompt_turns[-1]
    print(f"\n[User - Yêu cầu sửa lịch trình]: {edit_msg}")
    
    edit_payload = {
        "message": edit_msg,
        "history": history,
        "current_contract": current_contract,
        "has_draft": True,
        "current_itinerary": itinerary
    }
    
    resp = await client.post(f"{GW_URL}/chat_process", json=edit_payload, headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ Lỗi khi yêu cầu sửa lịch trình: HTTP {resp.status_code} - {resp.text}")
        return
        
    edit_res = resp.json()
    print(f"\n[AI - Phản hồi sửa]: {edit_res['reply']}")
    print(f"Status sửa: {edit_res['status']}")
    
    # Confirm edit if required
    if edit_res.get("requires_confirmation") or edit_res.get("pending_edit_plan"):
        confirm_edit_msg = "Đồng ý sửa nhé."
        print(f"\n[User - Xác nhận sửa]: {confirm_edit_msg}")
        
        confirm_payload = {
            "message": confirm_edit_msg,
            "history": history + [
                {"role": "user", "content": edit_msg},
                {"role": "assistant", "content": edit_res["reply"]}
            ],
            "current_contract": edit_res["updated_contract"],
            "has_draft": True,
            "current_itinerary": itinerary,
            "pending_edit_plan": edit_res.get("pending_edit_plan")
        }
        
        resp = await client.post(f"{GW_URL}/chat_process", json=confirm_payload, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Lỗi khi xác nhận sửa: HTTP {resp.status_code} - {resp.text}")
            return
            
        edit_res = resp.json()
        print(f"\n[AI - Phản hồi sau xác nhận]: {edit_res['reply']}")
        print(f"Status cuối cùng: {edit_res['status']}")
        
    updated_itinerary = edit_res.get("updated_itinerary")
    if updated_itinerary:
        print_itinerary("LỊCH TRÌNH SAU KHI SỬA (EDIT INTENT)", updated_itinerary, edit_res.get("updated_contract") or {})
    else:
        print("\n⚠️ Không nhận được lịch trình cập nhật sau khi sửa (JIT-edit).")

async def main():
    # Define 4 distinct conversational scenarios corresponding to the user's 4 test cases
    scenarios = [
        # SCENARIO 1: "Huế 3 ngày, ngân sách 1 triệu"
        [
            "Mình muốn đi Huế 3 ngày, ngân sách 1 triệu.",
            "Mình muốn đi chill chill ngắm cảnh sông Hương, Đại Nội và ăn uống nhẹ nhàng thôi. Thời gian đi cả ngày từ 8h đến 20h nhé. Khách sạn ở trung tâm mặc định giúp mình.",
            "Đúng rồi, bạn tạo lịch trình giúp mình nhé.",
            "Thay đổi địa điểm thứ hai ở ngày 1 thành quán cafe muối giúp mình." # Edit intent
        ],
        # SCENARIO 2: "Đại Nội, cafe muối, ăn chay"
        [
            "Mình muốn đi Huế ghé Đại Nội, uống cafe muối và ăn chay.",
            "Chuyến này mình đi 2 ngày nhé. Ngân sách khoảng 1.5 triệu. Mình đi từ 8h sáng đến 21h đêm. Khách sạn ở trung tâm mặc định nha.",
            "Đúng rồi, tạo lịch trình giúp mình.",
            "Thay đổi quán chay ở ngày 1 thành quán chè Huế giúp mình." # Edit intent
        ],
        # SCENARIO 3: "Food tour Huế cuối tuần"
        [
            "Mình muốn đi Food tour Huế cuối tuần.",
            "Đúng rồi đi 2 ngày cuối tuần nhé, ngân sách khoảng 2 triệu, muốn ăn bún bò, cơm hến và bánh bèo nậm lọc. Đi từ 9h sáng đến 22h đêm nha.",
            "Đồng ý, bạn lên lịch đi.",
            "Thay đổi địa điểm ăn lúc 14h30 ngày 2 thành đi dạo sông Hương giúp mình." # Edit intent
        ],
        # SCENARIO 4: "Đi nhẹ nhàng cùng gia đình"
        [
            "Mình muốn đi Huế nhẹ nhàng cùng gia đình.",
            "Chuyến này đi 3 ngày, ngân sách 3 triệu cho cả nhà nhé. Đi chậm chill chill từ 8h30 đến 18h30 hàng ngày để gia đình không bị mệt. Muốn đi chùa Thiên Mụ và Đại Nội.",
            "Đúng rồi, bạn tạo lịch trình đi.",
            "Thay đổi điểm cuối cùng ngày 2 thành một tiệm chè Huế ngon giúp mình." # Edit intent
        ]
    ]
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        for idx, prompt_turns in enumerate(scenarios):
            await run_scenario(client, idx + 1, prompt_turns)

if __name__ == "__main__":
    asyncio.run(main())
