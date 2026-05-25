import re

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

replacements = {
    "Lá»—i": "Lỗi",
    "Cáº§n quyá» n truy cáº\xadp vá»‹ trÃ­ Ä‘á»ƒ Ä‘iá» u hÆ°á»›ng": "Cần quyền truy cập vị trí để điều hướng",
    "ThÃ\xa0nh cÃ´ng": "Thành công",
    "Ä\x85ang tÃ\xadnh toÃ¡n láº¡i lá»™ trÃ¬nh tá»« vá»‹ trÃ­ hiá»‡n táº¡i...": "Đang tính toán lại lộ trình từ vị trí hiện tại...",
    "Bá»  qua Ä‘iá»ƒm hiá»‡n táº¡i, Ä‘ang Re-route tá»« vá»‹ trÃ­:": "Bỏ qua điểm hiện tại, đang Re-route từ vị trí:",
    "XÃ³a": "Xóa",
    "NgÃ\xa0y": "Ngày",
    "Ä‘iá»ƒm": "điểm",
    "ThÃªm Ä‘á»‹a Ä‘iá»ƒm": "Thêm địa điểm",
    "Bá»  qua Ä‘iá»ƒm nÃ\xa0y": "Bỏ qua điểm này",
    "LÆ°u NhÃ¡p": "Lưu Nháp",
    "Chá»‘t Lá»‹ch TrÃ¬nh": "Chốt Lịch Trình",
    "Ä\x90Ã£ xÃ³a Ä‘á»‹a Ä‘iá»ƒm": "Đã xóa địa điểm",
    "HoÃ\xa0n tÃ¡c": "Hoàn tác",
    "â€”": "—",
    "â€¢": "•",
    "âœ•": "✕",
    "Â·": "·",
    "kâ‚«": "k₫",
    "ðŸ“ ": "📍",
    "ðŸ ¨": "🏨",
    "ðŸ ›ï¸ ": "🏛️",
    "â›©ï¸ ": "🕌",
    "ðŸŒ³": "🌳",
    "ðŸ’": "🛒",
    "ðŸ œ": "🍛",
    "â˜•": "☕",
    "ðŸ –ï¸ ": "🏖️",
    "ðŸ’§": "💧",
    "ðŸ•": "🏮",
}

for src, dest in replacements.items():
    content = content.replace(src, dest)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✓ MapTimelineScreen.tsx encoding fixed successfully!")
