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
    print(f"\n================ 📅 {title} ================")
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
            desc = stop.get("description") or ""
            print(f"  - [{arr_time}] {poi_name} ({category}, {duration} phút) - Giá vé/Bữa ăn: {fee:,.0f} ₫")
            total_cost += fee
            all_stop_names.append(poi_name)
            
    print(f"\n💰 Tổng chi phí lịch trình: {total_cost:,.0f} ₫")

async def main():
    print("🎬 KHỞI ĐỘNG KIỂM THỬ: GIẢ LẬP ĐÚNG CÂU LỆNH GHÉP PHỨC TẠP CỦA NGƯỜI DÙNG")
    print("Câu lệnh: 'giảm số lượng điểm bỏ nhà hàng cung đình thay bằng quán bún bò bỏ Đại nội huế bỏ Huế cooking class đi'\n")
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        # Step 1: Initialize Chat
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
        
        # Step 2: Send the complex compound unpunctuated edit message!
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
        
        # Step 3: Confirm the edit plan
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
            flat_stop_ids = [s.get("poi_id") for d in updated_itinerary.get("days", []) for s in d.get("stops", [])]
            
            print("\n🔬 KẾT QUẢ KIỂM TRA ĐỘ CHÍNH XÁC:")
            # Check 1: Cooking class is deleted
            has_cooking = any("cooking class" in name.lower() for name in flat_stops)
            print(f"  - Đã loại bỏ 'Hue Cooking Class'?: {'✅ ĐÚNG' if not has_cooking else '❌ SAI'}")
            
            # Check 2: Cung Đình is deleted
            has_cung_dinh = any("cung đình" in name.lower() for name in flat_stops)
            print(f"  - Đã loại bỏ 'Nhà hàng Cung Đình'?: {'✅ ĐÚNG' if not has_cung_dinh else '❌ SAI'}")
            
            # Check 3: Bún Bò is added
            has_bun_bo = any("bún bò" in name.lower() for name in flat_stops)
            print(f"  - Đã thêm 'Bún Bò Huế' vào?: {'✅ ĐÚNG' if has_bun_bo else '❌ SAI'}")
            
            # Check 4: Evening tour / Citadel is deleted
            has_citadel = any("citadel" in name.lower() or "đại nội" in name.lower() for name in flat_stops)
            print(f"  - Đã loại bỏ 'Hue Citadel Night Tour' / 'Đại Nội'?: {'✅ ĐÚNG' if not has_citadel else '❌ SAI'}")
            
        else:
            print("\n❌ Lập lịch sau khi sửa thất bại.")

if __name__ == "__main__":
    asyncio.run(main())
