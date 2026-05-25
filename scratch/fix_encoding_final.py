# -*- coding: utf-8 -*-
import sys

file_path = r"d:\Workspaces\AI travel optimizer\Routing Engine\mobile layer\AITravelOptimizer\app\screens\MapTimelineScreen.tsx"

# List of all strings and symbols we want to restore from double-encoded UTF-8
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
    "—",
    "•",
    "✕",
    "·",
    "₫",
]

try:
    with open(file_path, "rb") as f:
        content_bytes = f.read()

    for S in correct_strings:
        # good_bytes is the correct UTF-8 byte sequence
        good_bytes = S.encode("utf-8")
        # bad_bytes is the double-encoded UTF-8 byte sequence
        bad_bytes = S.encode("utf-8").decode("latin-1").encode("utf-8")
        content_bytes = content_bytes.replace(bad_bytes, good_bytes)

    with open(file_path, "wb") as f:
        f.write(content_bytes)

    print("Success: MapTimelineScreen.tsx restored perfectly!")
except Exception as e:
    print(f"Error: {e}")
