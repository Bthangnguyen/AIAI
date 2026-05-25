# -*- coding: utf-8 -*-
import re
import sys

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

def decode_segment(s):
    try:
        # Try to convert Latin-1 representation back to UTF-8
        b = s.encode("latin-1")
        return b.decode("utf-8")
    except Exception:
        # If encoding or decoding fails, return original
        return s

# Pattern to match sequences of characters where each is in Latin-1 range (ASCII + Latin-1 Supplement)
# but we specifically target sequences that contain garbage characters (like Ã, Ä, á, » etc.)
# range: \u0080 - \u00ff (Latin-1) and common Win-1252 extensions like em-dash, smart quotes
pattern = re.compile(r'([\u0080-\u024F\u2010-\u2030]+)')

try:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        # We find all matching segments on the line
        parts = pattern.split(line)
        fixed_parts = []
        for part in parts:
            if pattern.match(part):
                fixed_parts.append(decode_segment(part))
            else:
                fixed_parts.append(part)
        fixed_lines.append("".join(fixed_parts))

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)

    print("Success: MapTimelineScreen.tsx has been fully and cleanly restored to UTF-8!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
