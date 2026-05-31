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

async def run_stress_test():
    async with httpx.AsyncClient(timeout=180.0) as client:
        print("=== 🚀 KHỞI ĐỘNG E2E STRESS TEST TRIPFLOW ===")
        
        # --- TURN 1 ---
        msg1 = "Mình muốn đi Huế 3 ngày, ngân sách 1 triệu. Các điểm: Đại Nội, thích uống cafe muối và muốn ăn chay. Đây là một chuyến food tour Huế cuối tuần và đi nhẹ nhàng cùng gia đình."
        print(f"\n[User - Lượt 1]: {msg1}")
        
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
        
        payload1 = {
            "message": msg1,
            "history": [],
            "current_contract": current_contract,
            "has_draft": False
        }
        
        resp = await client.post(f"{GW_URL}/chat_process", json=payload1, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Lỗi ở Lượt 1: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)
            
        res1 = resp.json()
        print(f"\n[AI - Phản hồi 1]: {res1['reply']}")
        print(f"Status: {res1['status']}")
        print(f"Missing fields: {res1['missing_fields']}")
        print(f"Current Destination: {res1['updated_contract'].get('destination')}")
        print(f"Current Days: {res1['updated_contract'].get('num_days')}")
        print(f"Current Tags: {res1['updated_contract'].get('tags')}")
        print(f"Target Distribution: {res1['updated_contract'].get('target_category_distribution')}")
        
        # Reconstruct history and contract for Turn 2
        history = [
            {"role": "user", "content": msg1},
            {"role": "assistant", "content": res1["reply"]}
        ]
        current_contract = res1["updated_contract"]
        
        # --- TURN 2 (Follow-up) ---
        # AI will ask about missing fields (usually times or hotel preferences)
        # We reply with travel times, central hotel preference, and confirm the default.
        msg2 = "Chúng mình đi cả ngày từ 8h đến 21h hàng ngày nhé, khách sạn ở gần trung tâm, bạn cứ chọn khách sạn trung tâm mặc định giúp mình nhé."
        print(f"\n[User - Lượt 2]: {msg2}")
        
        payload2 = {
            "message": msg2,
            "history": history,
            "current_contract": current_contract,
            "has_draft": False
        }
        
        resp = await client.post(f"{GW_URL}/chat_process", json=payload2, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Lỗi ở Lượt 2: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)
            
        res2 = resp.json()
        print(f"\n[AI - Phản hồi 2]: {res2['reply']}")
        print(f"Status: {res2['status']}")
        print(f"Missing fields: {res2['missing_fields']}")
        
        history.append({"role": "user", "content": msg2})
        history.append({"role": "assistant", "content": res2["reply"]})
        current_contract = res2["updated_contract"]
        
        # --- TURN 3 (Confirmation if needed) ---
        if res2["status"] == "clarifying" or res2.get("requires_confirmation") or current_contract.get("confirmation_pending"):
            msg3 = "Đúng rồi, mình xác nhận tất cả thông tin, bạn tạo lịch trình giúp mình."
            print(f"\n[User - Lượt 3]: {msg3}")
            
            payload3 = {
                "message": msg3,
                "history": history,
                "current_contract": current_contract,
                "has_draft": False
            }
            
            resp = await client.post(f"{GW_URL}/chat_process", json=payload3, headers=HEADERS)
            if resp.status_code != 200:
                print(f"❌ Lỗi ở Lượt 3: HTTP {resp.status_code} - {resp.text}")
                sys.exit(1)
                
            res3 = resp.json()
            print(f"\n[AI - Phản hồi 3]: {res3['reply']}")
            print(f"Status: {res3['status']}")
            
            history.append({"role": "user", "content": msg3})
            history.append({"role": "assistant", "content": res3["reply"]})
            current_contract = res3["updated_contract"]
            
        # Ensure contract is marked ready
        current_contract["ready_to_plan"] = True
        
        # --- PLAN TRIP ---
        print("\n--- 🧭 GỌI API LẬP LỊCH TRÌNH (PLAN TRIP) ---")
        plan_payload = {
            "user_prompt": msg1,
            "num_days": current_contract["num_days"],
            "budget": current_contract["budget_max"],
            "destination": current_contract["destination"],
            "contract": current_contract
        }
        
        resp = await client.post(f"{GW_URL}/plan_trip", json=plan_payload, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Lỗi Lập lịch trình: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)
            
        plan_res = resp.json()
        print(f"Trạng thái lập lịch trình: {plan_res['status']}")
        
        itinerary = plan_res.get("layer4_result")
        if not itinerary:
            print("❌ Lập lịch trình thất bại hoặc không có kết quả Layer 4.")
            sys.exit(1)
            
        print("\n=== 📊 ĐÁNH GIÁ LỊCH TRÌNH BAN ĐẦU ===")
        llm_c = plan_res.get("llm_contract") or {}
        print(f"Khách sạn: {llm_c.get('hotel_name')} ({llm_c.get('hotel_lat')}, {llm_c.get('hotel_lon')})")
        print(f"Số ngày: {len(itinerary.get('days', []))}")
        
        all_stop_names = []
        category_counts = {}
        for day in itinerary["days"]:
            day_num = day.get("day_index", 0) + 1
            print(f"\n📅 Ngày {day_num}:")
            for stop in day.get("stops", []):
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
        for cat, cnt in category_counts.items():
            print(f"  - {cat}: {cnt} điểm ({cnt / len(all_stop_names) * 100:.1f}%)")
            
        # Verify required items
        print("\n🔍 Kiểm tra sự hiện diện của các điểm/món yêu cầu:")
        contains_dainoi = any("Đại Nội" in name for name in all_stop_names)
        contains_saltcoffee = any("muối" in name.lower() or "salt" in name.lower() for name in all_stop_names)
        contains_veg = any("chay" in name.lower() or "vegetarian" in name.lower() or "vegan" in name.lower() for name in all_stop_names)
        
        print(f"  - Có Đại Nội: {contains_dainoi}")
        print(f"  - Có Cafe muối: {contains_saltcoffee}")
        print(f"  - Có Quán Chay: {contains_veg}")
        
        # --- EDIT INTENT SIMULATION ---
        # Real user wants to replace/add something. E.g., replace the vegetarian restaurant with a che Hue place
        edit_msg = "Thay đổi quán chay ở ngày 1 thành quán chè Huế giúp mình"
        print(f"\n[User - Sửa lịch trình]: {edit_msg}")
        
        edit_payload = {
            "message": edit_msg,
            "history": history,
            "current_contract": current_contract,
            "has_draft": True,
            "current_itinerary": itinerary
        }
        
        resp = await client.post(f"{GW_URL}/chat_process", json=edit_payload, headers=HEADERS)
        if resp.status_code != 200:
            print(f"❌ Lỗi khi sửa lịch trình: HTTP {resp.status_code} - {resp.text}")
            sys.exit(1)
            
        edit_res = resp.json()
        print(f"\n[AI - Phản hồi sửa]: {edit_res['reply']}")
        print(f"Status sửa: {edit_res['status']}")
        
        if edit_res.get("requires_confirmation") or edit_res.get("pending_edit_plan"):
            print("AI yêu cầu xác nhận thay đổi...")
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
                sys.exit(1)
                
            edit_res = resp.json()
            print(f"\n[AI - Phản hồi sau xác nhận]: {edit_res['reply']}")
            print(f"Status cuối cùng: {edit_res['status']}")
            
        updated_itinerary = edit_res.get("updated_itinerary")
        if updated_itinerary:
            print("\n=== 📊 ĐÁNH GIÁ LỊCH TRÌNH SAU KHI SỬA ===")
            all_updated_stop_names = []
            for day in updated_itinerary["days"]:
                day_num = day.get("day_index", 0) + 1
                print(f"\n📅 Ngày {day_num} (Đã cập nhật):")
                for stop in day.get("stops", []):
                    poi_id = stop.get("poi_id", "")
                    if poi_id.startswith("hotel_day_") or poi_id == "__rest_break__":
                        continue
                    poi_name = stop.get("poi_name") or "Unknown POI"
                    arr_min = stop.get("arrival_time_min", 480)
                    arr_time = minutes_to_time(arr_min)
                    all_updated_stop_names.append(poi_name)
                    print(f"  - [{arr_time}] {poi_name} ({stop.get('category')})")
                    
            # Check the edits
            print("\n🔍 Đánh giá kết quả sửa:")
            contains_che = any("chè" in name.lower() or "sweet" in name.lower() for name in all_updated_stop_names)
            print(f"  - Có quán Chè Huế sau khi sửa: {contains_che}")
        else:
            print("\n⚠️ Không nhận được itinerary cập nhật từ API (in-memory hoặc solver).")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
