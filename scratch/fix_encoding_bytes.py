# -*- coding: utf-8 -*-
import sys

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

correct_strings = [
    "Lỗi",
    "Cần quyền truy cập vị trí để điều hướng",
    "Thành công",
    "Đang tính toán lại lộ trình từ vị trí hiện tại...",
    "Bỏ qua điểm hiện tại, đang Re-route từ vị trí:",
    "Xóa",
    "Ngày",
    "điểm",
    "Thêm địa điểm",
    "Bỏ qua điểm này",
    "Lưu Nháp",
    "Chốt Lịch Trình",
    "Đã xóa địa điểm",
    "Hoàn tác",
]

try:
    with open(file_path, "rb") as f:
        content_bytes = f.read()

    # Perform binary replacements for double-encoded UTF-8 strings
    for S in correct_strings:
        good_bytes = S.encode("utf-8")
        bad_bytes = S.encode("utf-8").decode("latin-1").encode("cp1252")
        content_bytes = content_bytes.replace(bad_bytes, good_bytes)

    # Manual byte replacement for punctuation symbols using cp1252 mapping
    # "â€”" -> "—" (em-dash)
    content_bytes = content_bytes.replace("â€”".encode("cp1252"), "—".encode("utf-8"))
    # "â€¢" -> "•" (bullet)
    content_bytes = content_bytes.replace("â€¢".encode("cp1252"), "•".encode("utf-8"))
    # "âœ•" -> "✕" (heavy multiplication x)
    content_bytes = content_bytes.replace("âœ•".encode("cp1252"), "✕".encode("utf-8"))
    # "Â·" -> "·" (middle dot)
    content_bytes = content_bytes.replace("Â·".encode("cp1252"), "·".encode("utf-8"))
    # "kâ‚«" -> "k₫" (dong symbol)
    content_bytes = content_bytes.replace("kâ‚«".encode("cp1252"), "k₫".encode("utf-8"))

    with open(file_path, "wb") as f:
        f.write(content_bytes)

    print("Success: MapTimelineScreen.tsx restored perfectly!")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
