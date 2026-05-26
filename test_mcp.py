import sys
import json
import subprocess
import threading
import time

def read_messages(process):
    for line in iter(process.stdout.readline, b''):
        try:
            msg = json.loads(line.decode('utf-8').strip())
            print(f"\n[SERVER RESPONSE ID {msg.get('id', 'N/A')}]")
            print(json.dumps(msg, indent=2))
        except Exception as e:
            # Maybe not json
            pass

print("🚀 Khởi động MCP Server...")
process = subprocess.Popen(
    ["npx.cmd", "-y", "@henkey/postgres-mcp-server", "postgresql://travel:travel_secret@localhost:5432/travel"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL  # Ignore npm logs
)

thread = threading.Thread(target=read_messages, args=(process,))
thread.daemon = True
thread.start()

def send_msg(msg):
    process.stdin.write((json.dumps(msg) + "\n").encode('utf-8'))
    process.stdin.flush()

time.sleep(2)  # Wait for npm to download and start

# 1. Initialize
print("\n➡️ Gửi yêu cầu: initialize")
send_msg({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
})
time.sleep(1)

send_msg({
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
})

# 2. List Tools
print("\n➡️ Gửi yêu cầu: tools/list (Lấy danh sách công cụ)")
send_msg({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
})
time.sleep(1)

# 3. Test Tool: query
print("\n➡️ Gửi yêu cầu: tools/call (Chạy câu lệnh SQL)")
send_msg({
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
        "name": "query",
        "arguments": {
            "sql": "SELECT version(), current_database();"
        }
    }
})
time.sleep(2)

process.terminate()
print("\n✅ Hoàn tất kiểm tra!")
