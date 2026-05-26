"""
Test Analysis Module — Sprint 3A
Phân tích kết quả 100 prompt test pipeline.

Chức năng:
  1. Đọc results_summary.jsonl → Thống kê tỷ lệ lỗi theo ErrorCode
  2. Xác định bottlenecks: nhóm nào (A–J) có failure rate cao nhất
  3. Phân tích root cause: LLM sai vs. Solver infeasible vs. Budget conflict
  4. Xuất báo cáo markdown: testing/analysis_report.md
  5. Success Metrics: conversion rate, latency trung bình, score distribution
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

# ─── Constants ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(SCRIPT_DIR, "results_summary.jsonl")
REPORT_FILE = os.path.join(SCRIPT_DIR, "analysis_report.md")

GROUP_LABELS = {
    "A": "Basic Itinerary",
    "B": "Sở thích sâu / Persona",
    "C": "Food & Meal Timing",
    "D": "Pace / Comfort / Fatigue",
    "E": "Budget / Cost Conflict",
    "F": "Locked / Avoid POIs",
    "G": "Mâu thuẫn / Ambiguity",
    "H": "Narrative / Story",
    "I": "Multi-plan / Alternatives",
    "J": "Reroute / Dynamic Update",
}

SCORE_THRESHOLDS = {
    "excellent": 26,  # >= 26/30
    "good": 22,       # 22-25
    "needs_work": 18,  # 18-21
    "fail": 0,         # < 18
}

ERROR_CODE_LABELS = {
    "NO_FEASIBLE_ROUTE": "Solver không tìm được đường",
    "BUDGET_EXCEEDED": "Vượt ngân sách",
    "TOO_MANY_LOCKED": "Quá nhiều POI bị ghim",
    "OSRM_UNREACHABLE": "Lỗi kết nối OSRM",
    "LLM_EXTRACTION_FAILED": "LLM trích xuất thất bại",
    "LLM_PARSE_ERROR": "LLM không hiểu prompt",
    "TIMEOUT": "Hết thời gian xử lý",
    "UNKNOWN": "Lỗi không xác định",
}


# ─── Data Loading ────────────────────────────────────────────────────
def load_results(filepath: str = RESULTS_FILE) -> List[Dict[str, Any]]:
    """Load test results from JSONL file."""
    results = []
    if not os.path.exists(filepath):
        print(f"⚠️  File not found: {filepath}")
        print("   Hãy chạy run_pipeline_test.py trước để tạo kết quả.")
        return results

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️  Lỗi parse JSON ở dòng {line_num}: {e}")
    
    print(f"✓ Đã load {len(results)} kết quả test.")
    return results


# ─── Analysis Functions ────────────────────────────────────────────
def compute_overall_stats(results: List[Dict]) -> Dict[str, Any]:
    """Thống kê tổng quan: pass/fail rate, average score."""
    total = len(results)
    if total == 0:
        return {"total": 0, "pass_rate": 0, "avg_score": 0}

    passed = sum(1 for r in results if r.get("total_score", 0) >= SCORE_THRESHOLDS["good"])
    excellent = sum(1 for r in results if r.get("total_score", 0) >= SCORE_THRESHOLDS["excellent"])
    failed = sum(1 for r in results if r.get("total_score", 0) < SCORE_THRESHOLDS["fail"])
    errors = sum(1 for r in results if r.get("error_code"))

    scores = [r.get("total_score", 0) for r in results if not r.get("error_code")]
    avg_score = sum(scores) / len(scores) if scores else 0

    latencies = [r.get("duration_ms", 0) for r in results if r.get("duration_ms")]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    return {
        "total": total,
        "passed": passed,
        "excellent": excellent,
        "failed": failed,
        "errors": errors,
        "pass_rate": (passed / total) * 100 if total else 0,
        "excellent_rate": (excellent / total) * 100 if total else 0,
        "error_rate": (errors / total) * 100 if total else 0,
        "avg_score": round(avg_score, 1),
        "avg_latency_ms": round(avg_latency, 0),
        "conversion_rate": ((total - errors) / total) * 100 if total else 0,
    }


def analyze_errors_by_code(results: List[Dict]) -> Dict[str, int]:
    """Thống kê tỷ lệ lỗi theo ErrorCode."""
    error_counter = Counter()
    for r in results:
        code = r.get("error_code")
        if code:
            error_counter[code] += 1
    return dict(error_counter.most_common())


def analyze_by_group(results: List[Dict]) -> Dict[str, Dict]:
    """Phân tích kết quả theo nhóm A–J."""
    groups = defaultdict(list)
    for r in results:
        group = r.get("group", "?")
        groups[group].append(r)

    group_stats = {}
    for group_id in sorted(groups.keys()):
        group_results = groups[group_id]
        total = len(group_results)
        scores = [r.get("total_score", 0) for r in group_results if not r.get("error_code")]
        errors = sum(1 for r in group_results if r.get("error_code"))
        avg = sum(scores) / len(scores) if scores else 0
        
        # Latency per group
        latencies = [r.get("duration_ms", 0) for r in group_results if r.get("duration_ms")]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0

        group_stats[group_id] = {
            "label": GROUP_LABELS.get(group_id, "Unknown"),
            "total": total,
            "avg_score": round(avg, 1),
            "error_count": errors,
            "error_rate": round((errors / total) * 100, 1) if total else 0,
            "avg_latency_ms": round(avg_lat, 0),
            "worst_cases": [
                r["test_id"] for r in sorted(group_results, key=lambda x: x.get("total_score", 0))[:3]
                if r.get("total_score", 0) < SCORE_THRESHOLDS["good"]
            ],
        }

    return group_stats


def identify_bottlenecks(results: List[Dict]) -> List[Dict]:
    """Xác định các điểm nghẽn chính trong pipeline."""
    bottlenecks = []

    # 1. Layer phát sinh lỗi nhiều nhất
    layer_errors = Counter()
    for r in results:
        code = r.get("error_code") or ""
        if "LLM" in code:
            layer_errors["Layer 2 (LLM Extraction)"] += 1
        elif code in ("NO_FEASIBLE_ROUTE", "BUDGET_EXCEEDED", "TOO_MANY_LOCKED"):
            layer_errors["Layer 4 (Solver)"] += 1
        elif code == "OSRM_UNREACHABLE":
            layer_errors["OSRM (Routing)"] += 1
        elif code == "TIMEOUT":
            layer_errors["Timeout (Pipeline)"] += 1

    for layer, count in layer_errors.most_common():
        bottlenecks.append({
            "type": "layer_error",
            "layer": layer,
            "count": count,
            "recommendation": _get_recommendation(layer),
        })

    # 2. Nhóm test có điểm thấp nhất
    group_stats = analyze_by_group(results)
    weakest = sorted(group_stats.items(), key=lambda x: x[1]["avg_score"])[:3]
    for group_id, stats in weakest:
        if stats["avg_score"] < 25:
            bottlenecks.append({
                "type": "weak_group",
                "group": f"{group_id} ({stats['label']})",
                "avg_score": stats["avg_score"],
                "recommendation": f"Cần review lại logic xử lý nhóm {group_id}: {stats['label']}",
            })

    # 3. Score dimension analysis (which dimension is weakest overall)
    dimension_sums = defaultdict(list)
    for r in results:
        scores = r.get("dimension_scores", {})
        for dim, score in scores.items():
            dimension_sums[dim].append(score)

    for dim, scores_list in dimension_sums.items():
        avg = sum(scores_list) / len(scores_list) if scores_list else 0
        if avg < 4.0:
            bottlenecks.append({
                "type": "weak_dimension",
                "dimension": dim,
                "avg_score": round(avg, 2),
                "recommendation": f"Cần cải thiện khả năng {dim} của pipeline",
            })

    return bottlenecks


def _get_recommendation(layer: str) -> str:
    """Gợi ý cải thiện theo layer."""
    recs = {
        "Layer 2 (LLM Extraction)": "Cải thiện system prompt cho LLM Extractor. Thêm few-shot examples cho các trường hợp ambiguous.",
        "Layer 4 (Solver)": "Tăng time_limit cho OR-Tools solver. Thêm relaxation strategy khi constraint quá chặt.",
        "OSRM (Routing)": "Kiểm tra OSRM server status. Thêm fallback Haversine khi OSRM down.",
        "Timeout (Pipeline)": "Giảm số lượng POI candidates hoặc tăng solver timeout. Tối ưu spatial query.",
    }
    return recs.get(layer, "Cần investigation thêm.")


def analyze_score_distribution(results: List[Dict]) -> Dict[str, int]:
    """Phân bổ điểm theo thang đánh giá."""
    distribution = {"Xuất sắc (≥26)": 0, "Ổn (22-25)": 0, "Cần cải thiện (18-21)": 0, "Fail (<18)": 0, "Error": 0}
    for r in results:
        if r.get("error_code"):
            distribution["Error"] += 1
        elif r.get("total_score", 0) >= 26:
            distribution["Xuất sắc (≥26)"] += 1
        elif r.get("total_score", 0) >= 22:
            distribution["Ổn (22-25)"] += 1
        elif r.get("total_score", 0) >= 18:
            distribution["Cần cải thiện (18-21)"] += 1
        else:
            distribution["Fail (<18)"] += 1
    return distribution


# ─── ASCII Bar Chart ─────────────────────────────────────────────────
def ascii_bar(label: str, value: float, max_value: float, width: int = 30) -> str:
    """Generate ASCII bar chart line."""
    filled = int((value / max_value) * width) if max_value > 0 else 0
    bar = "█" * filled + "░" * (width - filled)
    return f"  {label:<30s} |{bar}| {value:.1f}"


# ─── Report Generation ──────────────────────────────────────────────
def generate_report(results: List[Dict], output_path: str = REPORT_FILE):
    """Xuất báo cáo phân tích toàn diện ra Markdown."""
    stats = compute_overall_stats(results)
    error_codes = analyze_errors_by_code(results)
    group_stats = analyze_by_group(results)
    bottlenecks = identify_bottlenecks(results)
    distribution = analyze_score_distribution(results)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = []
    lines.append(f"# 📊 Báo Cáo Phân Tích Test Pipeline — AIAI Travel Optimizer")
    lines.append(f"")
    lines.append(f"**Thời gian phân tích:** {now}")
    lines.append(f"**Tổng số test case:** {stats['total']}")
    lines.append(f"")

    # ─── 1. Overall Summary ─────
    lines.append("## 1. Tổng Quan Chất Lượng")
    lines.append("")
    lines.append("| Chỉ số | Giá trị |")
    lines.append("| :--- | :---: |")
    lines.append(f"| Tổng test case | {stats['total']} |")
    lines.append(f"| Pass (≥22/30) | {stats['passed']} ({stats['pass_rate']:.1f}%) |")
    lines.append(f"| Xuất sắc (≥26/30) | {stats['excellent']} ({stats['excellent_rate']:.1f}%) |")
    lines.append(f"| Lỗi hệ thống | {stats['errors']} ({stats['error_rate']:.1f}%) |")
    lines.append(f"| Điểm trung bình | {stats['avg_score']}/30 |")
    lines.append(f"| Conversion Rate | {stats['conversion_rate']:.1f}% |")
    lines.append(f"| Latency trung bình | {stats['avg_latency_ms']:.0f}ms |")
    lines.append("")

    # ─── 2. Score Distribution ─────
    lines.append("## 2. Phân Bổ Điểm Số")
    lines.append("")
    lines.append("```")
    max_val = max(distribution.values()) if distribution.values() else 1
    for label, count in distribution.items():
        lines.append(ascii_bar(label, count, max_val))
    lines.append("```")
    lines.append("")

    # ─── 3. Error Code Breakdown ─────
    lines.append("## 3. Thống Kê Lỗi Theo ErrorCode")
    lines.append("")
    if error_codes:
        lines.append("| ErrorCode | Số lần | Mô tả |")
        lines.append("| :--- | :---: | :--- |")
        for code, count in error_codes.items():
            desc = ERROR_CODE_LABELS.get(code, "Unknown")
            lines.append(f"| `{code}` | {count} | {desc} |")
    else:
        lines.append("> ✅ Không có lỗi hệ thống nào được ghi nhận.")
    lines.append("")

    # ─── 4. Group Analysis ─────
    lines.append("## 4. Phân Tích Theo Nhóm Test (A–J)")
    lines.append("")
    lines.append("| Nhóm | Tên | Số test | Điểm TB | Lỗi | Error Rate | Latency TB |")
    lines.append("| :---: | :--- | :---: | :---: | :---: | :---: | :---: |")
    for group_id, gs in sorted(group_stats.items()):
        status_emoji = "🟢" if gs["avg_score"] >= 26 else ("🟡" if gs["avg_score"] >= 22 else "🔴")
        lines.append(
            f"| {status_emoji} {group_id} | {gs['label']} | {gs['total']} | "
            f"{gs['avg_score']}/30 | {gs['error_count']} | {gs['error_rate']}% | {gs['avg_latency_ms']}ms |"
        )
    lines.append("")

    # ASCII chart for group scores
    lines.append("### Biểu Đồ Điểm Trung Bình Theo Nhóm")
    lines.append("```")
    max_score = 30
    for group_id, gs in sorted(group_stats.items()):
        lines.append(ascii_bar(f"{group_id}: {gs['label']}", gs["avg_score"], max_score))
    lines.append("```")
    lines.append("")

    # ─── 5. Bottleneck Analysis ─────
    lines.append("## 5. Điểm Nghẽn & Khuyến Nghị")
    lines.append("")
    if bottlenecks:
        for i, bn in enumerate(bottlenecks, 1):
            if bn["type"] == "layer_error":
                lines.append(f"### 5.{i}. {bn['layer']} — {bn['count']} lỗi")
                lines.append(f"> **Khuyến nghị:** {bn['recommendation']}")
            elif bn["type"] == "weak_group":
                lines.append(f"### 5.{i}. Nhóm {bn['group']} — Điểm TB: {bn['avg_score']}/30")
                lines.append(f"> **Khuyến nghị:** {bn['recommendation']}")
            elif bn["type"] == "weak_dimension":
                lines.append(f"### 5.{i}. Dimension \"{bn['dimension']}\" — Điểm TB: {bn['avg_score']}/5")
                lines.append(f"> **Khuyến nghị:** {bn['recommendation']}")
            lines.append("")
    else:
        lines.append("> ✅ Không phát hiện điểm nghẽn đáng kể.")
    lines.append("")

    # ─── 6. Feedback Loop ─────
    lines.append("## 6. Feedback Loop — Hướng Cải Thiện")
    lines.append("")
    lines.append("Dựa trên kết quả phân tích, các hướng cải thiện ưu tiên:")
    lines.append("")
    
    # Auto-generate feedback based on data
    if any(bn["type"] == "layer_error" and "LLM" in bn.get("layer", "") for bn in bottlenecks):
        lines.append("- [ ] **Layer 2 Prompt Tuning**: Cải thiện system prompt và thêm few-shot examples cho LLM Extractor")
    if any(bn["type"] == "layer_error" and "Solver" in bn.get("layer", "") for bn in bottlenecks):
        lines.append("- [ ] **Layer 4 Constraint Relaxation**: Thêm fallback strategy khi solver không tìm được feasible route")
    if stats["avg_latency_ms"] > 30000:
        lines.append("- [ ] **Performance**: Latency trung bình > 30s, cần tối ưu spatial query và solver time_limit")
    if stats["pass_rate"] < 80:
        lines.append("- [ ] **Quality Gate**: Pass rate < 80%, cần review lại toàn bộ pipeline")
    
    lines.append("- [ ] **Structured Logging**: Bổ sung duration_ms cho mỗi pipeline step (L2, L3, L4)")
    lines.append("- [ ] **Success Metrics Dashboard**: Tracking conversion_rate, latency, avg_score theo thời gian")
    lines.append("")

    # ─── 7. Worst Cases ─────
    lines.append("## 7. Các Test Case Cần Review")
    lines.append("")
    worst = [r for r in results if r.get("total_score", 30) < SCORE_THRESHOLDS["good"] or r.get("error_code")]
    if worst:
        lines.append("| Test ID | Nhóm | Điểm | Error | Prompt (rút gọn) |")
        lines.append("| :---: | :---: | :---: | :--- | :--- |")
        for r in sorted(worst, key=lambda x: x.get("total_score", 0))[:15]:
            prompt_short = r.get("prompt", "")[:60] + "..."
            score = r.get("total_score", "-")
            error = r.get("error_code", "-")
            lines.append(f"| {r['test_id']} | {r.get('group', '?')} | {score} | {error} | {prompt_short} |")
    else:
        lines.append("> ✅ Tất cả test case đều đạt chuẩn (≥22/30).")
    lines.append("")

    # Write report
    report_content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"✓ Báo cáo phân tích đã được lưu tại: {output_path}")
    return report_content


# ─── CLI Entry Point ────────────────────────────────────────────────
def main():
    """CLI entry point: python test_analysis.py [results_file]"""
    filepath = sys.argv[1] if len(sys.argv) > 1 else RESULTS_FILE
    
    print("=" * 60)
    print("  AIAI Travel Optimizer — Test Pipeline Analysis")
    print("=" * 60)
    
    results = load_results(filepath)
    if not results:
        print("\n❌ Không có dữ liệu để phân tích.")
        print("   Hãy chạy: python run_pipeline_test.py --batch 10")
        return

    # Print quick summary to console
    stats = compute_overall_stats(results)
    print(f"\n📊 Quick Summary:")
    print(f"   Total: {stats['total']} | Pass: {stats['passed']} | "
          f"Error: {stats['errors']} | Avg Score: {stats['avg_score']}/30")
    print(f"   Pass Rate: {stats['pass_rate']:.1f}% | "
          f"Conversion: {stats['conversion_rate']:.1f}% | "
          f"Avg Latency: {stats['avg_latency_ms']:.0f}ms")

    # Error breakdown
    error_codes = analyze_errors_by_code(results)
    if error_codes:
        print(f"\n⚠️  Error Breakdown:")
        for code, count in error_codes.items():
            print(f"   {code}: {count} occurrences")

    # Generate full report
    print(f"\n📝 Generating full analysis report...")
    generate_report(results)

    # Bottleneck summary
    bottlenecks = identify_bottlenecks(results)
    if bottlenecks:
        print(f"\n🔍 Top Bottlenecks:")
        for bn in bottlenecks[:5]:
            if bn["type"] == "layer_error":
                print(f"   ❗ {bn['layer']}: {bn['count']} errors")
            elif bn["type"] == "weak_group":
                print(f"   ❗ Group {bn['group']}: avg {bn['avg_score']}/30")

    print(f"\n✅ Analysis complete. Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
