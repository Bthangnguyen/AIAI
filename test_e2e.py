"""E2E Test: 5 different travel plan requests through the full pipeline."""
import urllib.request
import json
import sys
import io
import time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CHAT_URL = "http://localhost:8001/v1/trip/chat_process"
SSE_URL = "http://localhost:8001/v1/trip/plan_trip_stream"

def safe(s):
    return s.encode('ascii', errors='replace').decode('ascii') if s else ""

def call_chat(msg, history, contract):
    data = json.dumps({"message": msg, "history": history, "current_contract": contract}).encode("utf-8")
    req = urllib.request.Request(CHAT_URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def call_sse(prompt, num_days=None, budget=None):
    payload = {"user_prompt": prompt}
    if num_days: payload["num_days"] = num_days
    if budget: payload["budget"] = budget
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(SSE_URL, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        return resp.status, body

def parse_sse_result(body):
    """Extract the final result from SSE stream."""
    for line in body.strip().split("\n"):
        if line.startswith("data: ") and line != "data: [DONE]":
            try:
                obj = json.loads(line[6:])
                if "days" in obj:
                    return obj
                if obj.get("step") == "error" or obj.get("error_code"):
                    return {"error": obj.get("message", obj.get("error_code", "unknown"))}
            except: pass
    return None

TEST_CASES = [
    {
        "name": "Case 1: Basic Hue 2 days",
        "prompt": "Di Hue 2 ngay, ngan sach 1.5 trieu, thich lich su va am thuc",
        "num_days": 2,
    },
    {
        "name": "Case 2: Hue 1 day budget trip",  
        "prompt": "Mot ngay kham pha Hue, chi 500k, thich cafe va chup anh",
        "num_days": 1,
    },
    {
        "name": "Case 3: Hue 3 days family trip",
        "prompt": "Di Hue 3 ngay voi gia dinh 4 nguoi, ngan sach 3 trieu, tham Dai Noi va Chua Thien Mu",
        "num_days": 3,
    },
    {
        "name": "Case 4: Hue food tour",
        "prompt": "Food tour Hue 2 ngay, thich bun bo, com hen, che Hue, budget 2 trieu",
        "num_days": 2,
    },
    {
        "name": "Case 5: Hue chill trip",
        "prompt": "Di Hue 2 ngay, thu tha, thich thien nhien va song Huong, it di bo, 1.5 trieu",
        "num_days": 2,
    },
]

passed = 0
failed = 0

for i, tc in enumerate(TEST_CASES):
    print(f"\n{'='*60}")
    print(f"  {tc['name']}")
    print(f"  Prompt: {tc['prompt']}")
    print(f"{'='*60}")
    
    try:
        t0 = time.time()
        status, body = call_sse(tc["prompt"], tc.get("num_days"))
        elapsed = time.time() - t0
        
        result = parse_sse_result(body)
        
        if result and "days" in result:
            num_days = len(result["days"])
            total_stops = sum(len(d.get("stops", [])) for d in result["days"])
            status_field = result.get("status", "?")
            
            print(f"  STATUS: {status} | Solver: {status_field}")
            print(f"  Days: {num_days} | Total stops: {total_stops}")
            print(f"  Time: {elapsed:.1f}s")
            
            # Print first stop of each day
            for day in result["days"]:
                day_idx = day.get("day_index", "?")
                stops = day.get("stops", [])
                first_stop = stops[0].get("poi_name", "?") if stops else "no stops"
                print(f"    Day {day_idx}: {len(stops)} stops, starts with: {safe(first_stop)}")
            
            if total_stops > 0:
                print(f"  RESULT: PASS")
                passed += 1
            else:
                print(f"  RESULT: FAIL (no stops)")
                failed += 1
        elif result and "error" in result:
            print(f"  ERROR: {safe(str(result['error']))}")
            print(f"  Time: {time.time()-t0:.1f}s")
            print(f"  RESULT: FAIL")
            failed += 1
        else:
            print(f"  No valid result in SSE stream")
            print(f"  Body preview: {safe(body[:200])}")
            print(f"  RESULT: FAIL")
            failed += 1
    except Exception as e:
        print(f"  EXCEPTION: {safe(str(e))}")
        print(f"  RESULT: FAIL")
        failed += 1

print(f"\n{'='*60}")
print(f"  E2E RESULTS: {passed} PASSED / {failed} FAILED / {len(TEST_CASES)} TOTAL")
print(f"{'='*60}")
