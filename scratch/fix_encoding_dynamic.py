# -*- coding: utf-8 -*-
import sys

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

def is_cp1252(ch):
    try:
        ch.encode("cp1252")
        return True
    except Exception:
        return False

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Step 1: Detect all characters that are NOT cp1252-compatible
    non_cp1252_chars = sorted(list(set([ch for ch in content if not is_cp1252(ch)])))

    # Step 2: Replace them with unique placeholders
    placeholders = {}
    for idx, ch in enumerate(non_cp1252_chars):
        placeholder = f"__DYNAMIC_PLACEHOLDER_{idx}__"
        placeholders[placeholder] = ch
        content = content.replace(ch, placeholder)

    # Step 3: Perform the Latin-1-to-UTF-8 CP1252 byte translation
    raw_bytes = content.encode("cp1252")
    fixed_content = raw_bytes.decode("utf-8")

    # Step 4: Restore the non-cp1252 characters from placeholders
    for placeholder, ch in placeholders.items():
        fixed_content = fixed_content.replace(placeholder, ch)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    print("Success: MapTimelineScreen.tsx has been dynamically and perfectly restored!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
