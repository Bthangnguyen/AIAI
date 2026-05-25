# -*- coding: utf-8 -*-
import sys

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

# The 8 specific Vietnamese characters that are in UTF-8 but not in CP1252
viet_chars = {
    chr(0x110): "__VIET_110__", # Đ
    chr(0x1b0): "__VIET_1b0__", # ư
    chr(0x1ea1): "__VIET_1ea1__", # ạ
    chr(0x1ea7): "__VIET_1ea7__", # ầ
    chr(0x1ead): "__VIET_1ead__", # ậ
    chr(0x1ec1): "__VIET_1ec1__", # ề
    chr(0x1ecf): "__VIET_1ecf__", # ỉ
    chr(0x1eeb): "__VIET_1eeb__", # ứ
}

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Step 1: Replace the correct Vietnamese characters with placeholders
    for char, placeholder in viet_chars.items():
        content = content.replace(char, placeholder)

    # Step 2: Encode to cp1252 (reconstructing raw bytes) and decode as utf-8
    # Since only cp1252-compatible chars remain, this is guaranteed to succeed!
    raw_bytes = content.encode("cp1252")
    fixed_content = raw_bytes.decode("utf-8")

    # Step 3: Restore the correct Vietnamese characters from placeholders
    for char, placeholder in viet_chars.items():
        fixed_content = fixed_content.replace(placeholder, char)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    print("Success: MapTimelineScreen.tsx has been magically and perfectly restored!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
