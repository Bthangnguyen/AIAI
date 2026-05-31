"""Simulate multi-turn chat flow to verify no loop."""
import urllib.request
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://127.0.0.1:8001/v1/trip/chat_process"

def call_chat(msg, history, contract):
    data = json.dumps({
        "message": msg,
        "history": history,
        "current_contract": contract
    }).encode("utf-8")
    req = urllib.request.Request(
        BASE, 
        data=data, 
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer mock-session-token-xyz-987"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def safe(s):
    return s.encode('ascii', errors='replace').decode('ascii')

# Turn 1: Initial message
contract = {}
history = []
print("=== Turn 1: 'Toi muon di Hue 3 ngay' ===")
res = call_chat("Toi muon di Hue 3 ngay", history, contract)
print(f"  Status: {res['status']}")
print(f"  Reply: {safe(res['reply'][:120])}")
contract = res['updated_contract']
print(f"  dest={safe(str(contract.get('destination','?')))}, num_days={contract.get('num_days','?')}")
print(f"  confirmed={contract.get('confirmed_fields', [])}")
history.append({"role": "user", "content": "Toi muon di Hue 3 ngay"})
history.append({"role": "assistant", "content": res['reply']})

if res['status'] == 'ready':
    print("\n=== READY TO PLAN! No more questions needed. ===")
else:
    # Turn 2: Answer budget
    print("\n=== Turn 2: '2 trieu' ===")
    res = call_chat("2 trieu", history, contract)
    print(f"  Status: {res['status']}")
    print(f"  Reply: {safe(res['reply'][:120])}")
    contract = res['updated_contract']
    print(f"  dest={safe(str(contract.get('destination','?')))}, num_days={contract.get('num_days','?')}, budget={contract.get('budget_max','?')}")
    print(f"  confirmed={contract.get('confirmed_fields', [])}")
    history.append({"role": "user", "content": "2 trieu"})
    history.append({"role": "assistant", "content": res['reply']})

    if res['status'] == 'ready':
        print("\n=== READY TO PLAN! All 3 required fields collected. ===")
    else:
        # Turn 3
        print("\n=== Turn 3: 'ok' ===")
        res = call_chat("ok", history, contract)
        print(f"  Status: {res['status']}")
        print(f"  Reply: {safe(res['reply'][:120])}")
        if res['status'] == 'ready':
            print("\n=== READY TO PLAN! ===")
        else:
            print(f"\n=== STILL CLARIFYING ===")
            print(f"  confirmed={res['updated_contract'].get('confirmed_fields', [])}")

print("\n=== TEST COMPLETE ===")
