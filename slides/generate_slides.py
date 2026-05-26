"""
Main runner — Generates the full 22-slide PPTX presentation.
"""
from pptx import Presentation
from pptx.util import Inches

from slides_part1 import (
    build_slide_01_cover, build_slide_02_problem, build_slide_03_gap,
    build_slide_04_objectives, build_slide_05_overview,
    build_slide_06_users, build_slide_07_nlp,
)
from slides_part2 import (
    build_slide_08_poi_filter, build_slide_09_optimization,
    build_slide_10_solving, build_slide_11_reroute,
    build_slide_12_realtime, build_slide_13_ui,
)
from slides_part3 import (
    build_slide_14_architecture, build_slide_15_pipeline,
    build_slide_16_techstack, build_slide_17_fallback,
    build_slide_18_demo, build_slide_19_evaluation,
    build_slide_20_contribution, build_slide_21_limitations,
    build_slide_22_qa,
)

OUTPUT_FILE = "AI_Itinerary_Optimizer_POC.pptx"


def main():
    prs = Presentation()
    # Set 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    print("Building slides...")

    # PHẦN 1 — MỞ ĐẦU
    build_slide_01_cover(prs);          print("  ✅ Slide 01 — Cover")
    build_slide_02_problem(prs);        print("  ✅ Slide 02 — Problem Statement")
    build_slide_03_gap(prs);            print("  ✅ Slide 03 — Market Gap")
    build_slide_04_objectives(prs);     print("  ✅ Slide 04 — Research Objectives")

    # PHẦN 2 — TỔNG QUAN
    build_slide_05_overview(prs);       print("  ✅ Slide 05 — System Overview")
    build_slide_06_users(prs);          print("  ✅ Slide 06 — Target Users")

    # PHẦN 3 — DEEP DIVE FEATURES
    build_slide_07_nlp(prs);            print("  ✅ Slide 07 — NLP Generation")
    build_slide_08_poi_filter(prs);     print("  ✅ Slide 08 — POI Filtering")
    build_slide_09_optimization(prs);   print("  ✅ Slide 09 — Optimization Engine")
    build_slide_10_solving(prs);        print("  ✅ Slide 10 — Solving Logic")
    build_slide_11_reroute(prs);        print("  ✅ Slide 11 — Dynamic Re-route")
    build_slide_12_realtime(prs);       print("  ✅ Slide 12 — Realtime UX")
    build_slide_13_ui(prs);             print("  ✅ Slide 13 — MapTimeline UI")

    # PHẦN 4 — TECHNICAL
    build_slide_14_architecture(prs);   print("  ✅ Slide 14 — Architecture")
    build_slide_15_pipeline(prs);       print("  ✅ Slide 15 — Data Pipeline")
    build_slide_16_techstack(prs);      print("  ✅ Slide 16 — Tech Stack")
    build_slide_17_fallback(prs);       print("  ✅ Slide 17 — Fallback Strategy")

    # PHẦN 5 — DEMO + EVALUATION
    build_slide_18_demo(prs);           print("  ✅ Slide 18 — Demo Scenario")
    build_slide_19_evaluation(prs);     print("  ✅ Slide 19 — Evaluation")
    build_slide_20_contribution(prs);   print("  ✅ Slide 20 — Contributions")
    build_slide_21_limitations(prs);    print("  ✅ Slide 21 — Limitations & Future")
    build_slide_22_qa(prs);             print("  ✅ Slide 22 — Q&A")

    prs.save(OUTPUT_FILE)
    print(f"\n🎉 Done! File saved: {OUTPUT_FILE}")
    print(f"   Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    main()
