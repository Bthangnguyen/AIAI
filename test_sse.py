"""Trace exactly what frontend sends to plan_trip_stream when user confirms."""
import urllib.request
import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SSE_URL = "http://localhost:8001/v1/trip/plan_trip_stream"

# Simulate the exact payload frontend sends after "xac nhan"
# rawPrompt = combined prompt, numDays from intent  
payload = {
    "user_prompt": "Hue 3 ngay, ngan sach 1 trieu xac nhan",
    "num_days": 3,
}

print(f"Calling: {SSE_URL}")
print(f"Payload: {json.dumps(payload)}")
t0 = time.time()

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(SSE_URL, data=data, headers={
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
    "Origin": "http://localhost:3000",
})

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        print(f"\nSTATUS: {resp.status} ({time.time()-t0:.1f}s)")
        body = resp.read().decode("utf-8")
        # Parse each SSE event
        for line in body.strip().split("\n"):
            if line.startswith("data: ") and line != "data: [DONE]":
                try:
                    obj = json.loads(line[6:])
                    if "days" in obj:
                        num_days = len(obj["days"])
                        total_stops = sum(len(d.get("stops",[])) for d in obj["days"])
                        print(f"  RESULT: {obj.get('status','?')} | {num_days} days | {total_stops} stops")
                    elif "step" in obj:
                        print(f"  EVENT: step={obj['step']}, extra={', '.join(f'{k}={v}' for k,v in obj.items() if k!='step')}")
                    elif "error_code" in obj or obj.get("step") == "error":
                        safe_msg = str(obj.get("message","?")).encode("ascii",errors="replace").decode()
                        print(f"  ERROR: {obj.get('error_code','?')} - {safe_msg}")
                except:
                    print(f"  RAW: {line[:100]}")
            elif line == "data: [DONE]":
                print(f"  [DONE]")
        print(f"\nTotal time: {time.time()-t0:.1f}s")
except urllib.error.HTTPError as e:
    print(f"\nHTTP ERROR: {e.code} ({time.time()-t0:.1f}s)")
    body = e.read().decode("utf-8")
    print(f"BODY: {body[:500]}")
except Exception as e:
    print(f"\nEXCEPTION: {e} ({time.time()-t0:.1f}s)")
