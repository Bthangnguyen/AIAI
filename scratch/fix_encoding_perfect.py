import sys

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

targets = [
    "Lá»—i",
    "Cáº§n quyá» n truy cáº­p vá»‹ trÃ­ Ä‘á»ƒ Ä‘iá» u hÆ°á»›ng",
    "ThÃ nh cÃ´ng",
    "Äang tÃ­nh toÃ¡n láº¡i lá»™ trÃ¬nh tá»« vá»‹ trÃ­ hiá»‡n táº¡i...",
    "Bá»  qua Ä‘iá»ƒm hiá»‡n táº¡i, Ä‘ang Re-route tá»« vá»‹ trÃ­:",
    "XÃ³a",
    "NgÃ y",
    "Ä‘iá»ƒm",
    "ThÃªm Ä‘á»‹a Ä‘iá»ƒm",
    "Bá»  qua Ä‘iá»ƒm nÃ y",
    "LÆ°u NhÃ¡p",
    "Chá»‘t Lá»‹ch TrÃ¬nh",
    "ÄÃ£ xÃ³a Ä‘á»‹a Ä‘iá»ƒm",
    "HoÃ n tÃ¡c",
    "â€”",
    "â€¢",
    "âœ•",
    "Â·",
    "kâ‚«",
]

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    for target in targets:
        # Safely convert Latin-1 string representations of UTF-8 back to clean UTF-8
        try:
            fixed = target.encode("latin-1").decode("utf-8")
            content = content.replace(target, fixed)
        except Exception as err:
            print(f"Skipping target '{target}': {err}")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Success: MapTimelineScreen.tsx has been cleanly fixed!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
