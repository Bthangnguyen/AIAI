import requests
import json

url = "http://localhost:8001/v1/trip/chat_process"
payload = {
    "message": "Huế",
    "history": [
        {"role": "user", "content": "Tôi muốn đi du lịch 2 ngày, ăn bún bò và thích Đại Nội."},
        {"role": "assistant", "content": "Dạ anh/chị muốn đi du lịch ở đâu ạ?"}
    ],
    "current_contract": {
        "destination": None,
        "budget_max": None,
        "radius_km": 10.0,
        "num_days": 2,
        "tags": ["food", "culture"],
        "locked_pois": ["Đại Nội"]
    }
}

headers = {"Content-Type": "application/json"}
response = requests.post(url, json=payload, headers=headers)
print("Status:", response.status_code)
with open("scratch/test_chat_process_output.json", "w", encoding="utf-8") as f:
    json.dump(response.json(), f, indent=2, ensure_ascii=False)
print("Saved response to scratch/test_chat_process_output.json")

