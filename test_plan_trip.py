"""Test plan_trip (non-streaming) endpoint - what frontend now uses."""
import urllib.request
import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

URL = "http://localhost:8001/v1/trip/plan_trip"

payload = {
    "user_prompt": "Hue 3 ngay, ngan sach 1 trieu",
    "num_days": 3,
    "budget": 1000000,
    "destination": "Hue",
}

print(f"Calling: {URL}")
print(f"Payload: {json.dumps(payload)}")
t0 = time.time()

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(URL, data=data, headers={
    "Content-Type": "application/json",
    "Origin": "http://localhost:3000",
})

try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        elapsed = time.time() - t0
        body = resp.read().decode("utf-8")
        result = json.loads(body)
        print(f"\nSTATUS: {resp.status} ({elapsed:.1f}s)")
        print(f"Result status: {result.get('status')}")
        print(f"Message: {result.get('message','')[:100].encode('ascii',errors='replace').decode()}")
        l4 = result.get("layer4_result")
        if l4 and "days" in l4:
            days = l4["days"]
            total = sum(len(d.get("stops",[])) for d in days)
            print(f"Days: {len(days)} | Total stops: {total}")
            for d in days:
                stops = d.get("stops", [])
                first = stops[0]["poi_name"] if stops else "?"
                print(f"  Day {d['day_index']}: {len(stops)} stops, first={first.encode('ascii',errors='replace').decode()}")
            print(f"\nRESULT: PASS")
        elif l4 and "error_code" in l4:
            print(f"Error: {l4.get('error_code')} - {l4.get('message','')}")
            print(f"\nRESULT: FAIL (solver error)")
        else:
            print(f"No layer4_result")
            print(f"Body preview: {body[:300]}")
            print(f"\nRESULT: FAIL")
except urllib.error.HTTPError as e:
    elapsed = time.time() - t0
    print(f"\nHTTP ERROR: {e.code} ({elapsed:.1f}s)")
    body = e.read().decode("utf-8")
    print(f"BODY: {body[:500].encode('ascii',errors='replace').decode()}")
except Exception as e:
    elapsed = time.time() - t0
    print(f"\nEXCEPTION: {e} ({elapsed:.1f}s)")
