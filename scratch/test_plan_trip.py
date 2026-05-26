import requests
import json

url = "http://localhost:8001/v1/trip/plan_trip"
payload = {
    "user_prompt": "Tôi muốn đi du lịch 2 ngày, ăn bún bò và thích Đại Nội. Huế",
    "num_days": 2,
    "destination": "Huế",
    "preferences": ["food", "culture"]
}

headers = {"Content-Type": "application/json"}
response = requests.post(url, json=payload, headers=headers)
print("Status:", response.status_code)
with open("scratch/test_plan_trip_output.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=2, ensure_ascii=False)
print("Saved response to scratch/test_plan_trip_output.json")
