import sys
import asyncio
import httpx
import json

sys.stdout.reconfigure(encoding='utf-8')

GW_URL = "http://localhost:8001/v1/trip"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer mock-session-token-xyz-987"
}

def minutes_to_time(minutes: int) -> str:
    h = (minutes // 60) % 24
    m = minutes % 60
    return f"{h:02d}:{m:02d}"

def print_itinerary(title: str, itinerary: dict):
    print(f"\n================ 📅 {title} ==================")
    print(f"Số ngày: {len(itinerary.get('days', []))}")
    
    total_cost = 0
    all_stop_names = []
    
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
            fee = stop.get("entrance_fee", 0)
            print(f"  - [{arr_time}] {poi_name} ({category}, {duration} phút) - Giá vé/Bữa ăn: {fee:,.0f} ₫")
            total_cost += fee
            all_stop_names.append(poi_name)
            
    print(f"\n💰 Tổng chi phí lịch trình: {total_cost:,.0f} ₫")

async def test_scenario_1(client: httpx.AsyncClient):
    print("\n" + "="*80)
    print("🎬 KỊCH BẢN 1: GIẢ LẬP CÂU LỆNH GHÉP PHỨC TẠP KHÔNG DẤU CỦA NGƯỜI DÙNG")
    print("Câu lệnh: 'giảm số lượng điểm bỏ nhà hàng cung đình thay bằng quán bún bò bỏ Đại nội huế bỏ Huế cooking class đi'")
    print("="*80)
    
    # ── Step 1: Initialize Chat ──
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
    
    # Turn 1
    payload = {
        "message": "Mình muốn đi Huế 3 ngày, ngân sách 1 triệu.",
        "history": history,
        "current_contract": current_contract,
        "has_draft": False
    }
    resp = await client.post(f"{GW_URL}/chat_process", json=payload, headers=HEADERS)
    res = resp.json()
    current_contract = res["updated_contract"]
    history.append({"role": "user", "content": payload["message"]})
    history.append({"role": "assistant", "content": res["reply"]})
    
    # Turn 2
    payload = {
        "message": "mình đi kết hợp luôn, mình đi cả ngày, khách sạn ở trung tâm.",
        "history": history,
        "current_contract": current_contract,
        "has_draft": False
    }
    resp = await client.post(f"{GW_URL}/chat_process", json=payload, headers=HEADERS)
    res = resp.json()
    current_contract = res["updated_contract"]
    history.append({"role": "user", "content": payload["message"]})
    history.append({"role": "assistant", "content": res["reply"]})
    
    # Turn 3: Confirm
    payload = {
        "message": "đồng ý, lên lịch đi.",
        "history": history,
        "current_contract": current_contract,
        "has_draft": False
    }
    resp = await client.post(f"{GW_URL}/chat_process", json=payload, headers=HEADERS)
    res = resp.json()
    current_contract = res["updated_contract"]
    
    # Call plan_trip to get the original draft
    current_contract["ready_to_plan"] = True
    plan_payload = {
        "user_prompt": "Mình muốn đi Huế 3 ngày, ngân sách 1 triệu.",
        "num_days": current_contract["num_days"],
        "budget": current_contract["budget_max"],
        "destination": current_contract["destination"],
        "contract": current_contract
    }
    resp = await client.post(f"{GW_URL}/plan_trip", json=plan_payload, headers=HEADERS)
    plan_res = resp.json()
    itinerary = plan_res.get("layer4_result")
    
    print_itinerary("LỊCH TRÌNH GỐC BAN ĐẦU", itinerary)
    
    # ── Step 2: Send the complex compound unpunctuated edit message! ──
    edit_msg = "giảm số lượng điểm bỏ nhà hàng cung đình thay bằng quán bún bò bỏ Đại nội huế bỏ Huế cooking class đi"
    print(f"\n[User - Yêu cầu sửa lịch trình]: {edit_msg}")
    
    edit_payload = {
        "message": edit_msg,
        "history": history,
        "current_contract": current_contract,
        "has_draft": True,
        "current_itinerary": itinerary
    }
    resp = await client.post(f"{GW_URL}/chat_process", json=edit_payload, headers=HEADERS)
    edit_res = resp.json()
    
    print(f"\n[AI - Phản hồi sửa]: {edit_res['reply']}")
    print(f"Status sửa: {edit_res['status']}")
    
    # ── Step 3: Confirm the edit plan ──
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
    final_res = resp.json()
    
    updated_itinerary = final_res.get("updated_itinerary")
    if updated_itinerary:
        print_itinerary("LỊCH TRÌNH SAU KHI SỬA LỘ TRÌNH (EDIT INTENT)", updated_itinerary)
        
        # Post-checks
        flat_stops = [s.get("poi_name") for d in updated_itinerary.get("days", []) for s in d.get("stops", [])]
        
        print("\n🔬 KẾT QUẢ KIỂM TRA ĐỘ CHÍNH XÁC KỊCH BẢN 1:")
        
        # Check 1: Cooking class is deleted
        has_cooking = any("cooking class" in name.lower() for name in flat_stops)
        print(f"  - Đã loại bỏ 'Hue Cooking Class'?: {'✅ ĐÚNG' if not has_cooking else '❌ SAI'}")
        
        # Check 2: Cung Đình is deleted
        has_cung_dinh = any("cung đình" in name.lower() for name in flat_stops)
        print(f"  - Đã loại bỏ 'Nhà hàng Cung Đình'?: {'✅ ĐÚNG' if not has_cung_dinh else '❌ SAI'}")
        
        # Check 3: Other food stops (e.g. Phố Cổ or Hương Giang) remain untouched (no loose matching bugs)
        orig_food_stops = [s.get("poi_name") for s in itinerary.get("days", [])[0].get("stops", []) if s.get("category") == "food" or "nhà hàng" in s.get("poi_name", "").lower()]
        flat_stops_lower = [name.lower() for name in flat_stops]
        preserved_all = True
        for name in orig_food_stops:
            if "cooking" in name.lower() or "cung đình" in name.lower():
                continue
            if name.lower() not in flat_stops_lower:
                preserved_all = False
                print(f"  ❌ Lỗi: {name} đã bị xóa hoặc thay thế nhầm!")
        print(f"  - Đã giữ lại các nhà hàng khác (không xóa nhầm)?: {'✅ ĐÚNG' if preserved_all else '❌ SAI'}")
        
        # Check 4: Bún Bò is added
        has_bun_bo = any("bún bò" in name.lower() for name in flat_stops)
        print(f"  - Đã thêm 'Bún Bò Huế' vào?: {'✅ ĐÚNG' if has_bun_bo else '❌ SAI'}")
        
        # Check 5: Evening tour / Citadel is deleted completely
        has_citadel = any("citadel" in name.lower() or "đại nội" in name.lower() for name in flat_stops)
        print(f"  - Đã loại bỏ cả 'Hue Citadel Night Tour' & 'Đại Nội Huế'?: {'✅ ĐÚNG' if not has_citadel else '❌ SAI'}")
        
        assert not has_cooking, "Hue Cooking Class should be removed"
        assert not has_cung_dinh, "Cung Dinh should be removed"
        assert preserved_all, "Other generic food stops should not be removed"
        assert not has_citadel, "Citadel and Citadel Night Tour should both be removed"
        print("\n👉 KỊCH BẢN 1 HOÀN TOÀN THÀNH CÔNG! HỆ THỐNG ĐÃ HOẠT ĐỘNG HOÀN HẢO!")
    else:
        print("\n❌ Lập lịch sau khi sửa thất bại.")
        assert False, "Scenario 1 failed to apply edit"

async def test_scenario_2(client: httpx.AsyncClient):
    print("\n" + "="*80)
    print("🎬 KỊCH BẢN 2: TÁI HIỆN LỊCH CŨ CHỈ CÓ DUY NHẤT TOUR ĐÊM (EVENING CITADEL NIGHT TOUR ONLY)")
    print("Yêu cầu: 'bỏ Đại nội huế' khi lịch trình chỉ có duy nhất 'Hue Citadel Night Tour'")
    print("="*80)
    
    # ── Step 1: Create a mock itinerary that has only 'Hue Citadel Night Tour' ──
    mock_itinerary = {
        "destination": "Huế",
        "num_days": 3,
        "total_entrance_fee": 350000.0,
        "budget_used": 350000.0,
        "days": [
            {
                "day_index": 0,
                "date": "Day 1",
                "start_time_min": 540,
                "start_hotel_name": "Hue Default Hotel",
                "start_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "end_hotel_name": "Hue Default Hotel",
                "end_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "stops": [
                    {
                        "poi_id": "stop_1_1",
                        "poi_name": "Trường Quốc Học Huế",
                        "category": "history",
                        "arrival_time_min": 540,
                        "departure_time_min": 600,
                        "visit_duration_min": 60,
                        "entrance_fee": 0
                    }
                ]
            },
            {
                "day_index": 1,
                "date": "Day 2",
                "start_time_min": 540,
                "stops": [
                    {
                        "poi_id": "stop_2_1",
                        "poi_name": "Chùa Thiên Mụ",
                        "category": "culture",
                        "arrival_time_min": 600,
                        "departure_time_min": 660,
                        "visit_duration_min": 60,
                        "entrance_fee": 0
                    }
                ]
            },
            {
                "day_index": 2,
                "date": "Day 3",
                "start_time_min": 540,
                "stops": [
                    {
                        "poi_id": "stop_3_1",
                        "poi_name": "Hue Citadel Night Tour",
                        "category": "culture",
                        "arrival_time_min": 1140,
                        "departure_time_min": 1230,
                        "visit_duration_min": 90,
                        "entrance_fee": 150000
                    }
                ]
            }
        ]
    }
    
    print_itinerary("MOCK LỊCH TRÌNH BAN ĐẦU (CHỈ CÓ TOUR ĐÊM)", mock_itinerary)
    
    current_contract = {
        "destination": "Huế",
        "budget_max": 1000000,
        "radius_km": 10.0,
        "num_days": 3,
        "tags": ["culture"],
        "locked_pois": [],
        "excluded_pois": [],
        "confirmed_fields": [],
    }
    history = []
    
    # ── Step 2: Request deletion of 'Đại nội Huế' ──
    edit_msg = "bỏ Đại nội huế"
    print(f"\n[User - Yêu cầu sửa lịch trình]: {edit_msg}")
    
    edit_payload = {
        "message": edit_msg,
        "history": history,
        "current_contract": current_contract,
        "has_draft": True,
        "current_itinerary": mock_itinerary
    }
    resp = await client.post(f"{GW_URL}/chat_process", json=edit_payload, headers=HEADERS)
    edit_res = resp.json()
    
    print(f"\n[AI - Phản hồi sửa]: {edit_res['reply']}")
    print(f"Status sửa: {edit_res['status']}")
    
    # ── Step 3: Confirm deletion ──
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
        "current_itinerary": mock_itinerary,
        "pending_edit_plan": edit_res.get("pending_edit_plan")
    }
    resp = await client.post(f"{GW_URL}/chat_process", json=confirm_payload, headers=HEADERS)
    final_res = resp.json()
    
    updated_itinerary = final_res.get("updated_itinerary")
    if updated_itinerary:
        print_itinerary("LỊCH TRÌNH MOCK SAU KHI SỬA LỘ TRÌNH (EDIT INTENT)", updated_itinerary)
        
        flat_stops = [s.get("poi_name") for d in updated_itinerary.get("days", []) for s in d.get("stops", [])]
        
        print("\n🔬 KẾT QUẢ KIỂM TRA ĐỘ CHÍNH XÁC KỊCH BẢN 2:")
        
        # Check 1: Evening tour 'Hue Citadel Night Tour' is successfully deleted
        has_night_tour = any("citadel" in name.lower() or "đại nội" in name.lower() for name in flat_stops)
        print(f"  - Đã loại bỏ thành công 'Hue Citadel Night Tour'?: {'✅ ĐÚNG' if not has_night_tour else '❌ SAI'}")
        
        assert not has_night_tour, "Hue Citadel Night Tour should be deleted in the evening-only case"
        print("\n👉 KỊCH BẢN 2 HOÀN TOÀN THÀNH CÔNG! HỆ THỐNG ĐÃ XÓA KHỚP TOUR ĐÊM HOÀN HẢO!")
    else:
        print("\n❌ Lập lịch sau khi sửa thất bại.")
        assert False, "Scenario 2 failed to apply edit"

async def main():
    print("🔥 KHỞI CHẠY BỘ KIỂM THỬ STRESS TEST TOÀN DIỆN MỚI QUA GATEWAY & LLM 🔥")
    async with httpx.AsyncClient(timeout=180.0) as client:
        await test_scenario_1(client)
        await test_scenario_2(client)
    print("\n🏆 TẤT CẢ CÁC KỊCH BẢN KIỂM THỬ ĐÃ THÀNH CÔNG MỸ MÃN! 🏆")

if __name__ == "__main__":
    asyncio.run(main())
