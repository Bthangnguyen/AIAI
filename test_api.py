import urllib.request
import json
import sys

url = "http://localhost:8001/v1/trip/chat_process"
data = json.dumps({
    "message": "Toi muon di Hue 2 ngay",
    "history": [],
    "current_contract": {}
}).encode("utf-8")

req = urllib.request.Request(url, data=data, headers={
    "Content-Type": "application/json",
    "Origin": "http://localhost:3000"
})

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        print(f"STATUS: {resp.status}")
        # Safe print for Windows console
        safe = body.encode("ascii", errors="replace").decode("ascii")
        print(f"BODY: {safe[:2000]}")
        # Also parse JSON to check structure
        parsed = json.loads(body)
        print(f"\nRESPONSE KEYS: {list(parsed.keys())}")
        print(f"STATUS FIELD: {parsed.get('status')}")
except urllib.error.HTTPError as e:
    print(f"HTTP ERROR: {e.code}")
    body = e.read().decode("utf-8")
    safe = body.encode("ascii", errors="replace").decode("ascii")
    print(f"BODY: {safe[:2000]}")
except Exception as e:
    print(f"ERROR: {e}")
