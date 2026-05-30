# -*- coding: utf-8 -*-
"""Tests for deterministic post-draft edit intent planning."""

from app.services.edit_intent_planner import EditIntentPlanner


def test_add_che_afternoon_day_2_breakdown():
    planner = EditIntentPlanner()
    intent = planner.build("thêm 1 quán chè vào buổi chiều ngày 2")

    assert intent.action == "add_place"
    assert len(intent.operations) == 1
    op = intent.operations[0]
    assert op.type == "add_place"
    assert op.query == "quán chè"
    assert op.target_day == 2
    assert op.target_count == 1
    assert op.target_category == "food"
    assert op.target_micro_tags == ["che"]
    assert op.time_window == {"start_min": 840, "end_min": 1020}
    assert op.resolution_strategy == "vector_search_then_suggest"


def test_complex_multi_edit_breakdown():
    planner = EditIntentPlanner()
    message = (
        "chuyển Đại Nội sang 7h sáng ngày mai, rồi chèn quán cà phê muối sau khi đi Đại Nội. "
        "Rồi buổi trưa ăn bún bò, buổi chiều ăn quán chay, buổi tối đi dạo Nguyễn Huệ"
    )
    intent = planner.build(message)

    assert intent.action == "modify_itinerary"
    assert [op.type for op in intent.operations] == [
        "move_place",
        "add_place",
        "add_place",
        "add_place",
        "add_place",
    ]

    move = intent.operations[0]
    assert move.target == "Đại Nội"
    assert move.target_day == 2
    assert move.target_time_min == 420
    assert move.time_window == {"start_min": 360, "end_min": 660}

    cafe = intent.operations[1]
    assert cafe.query == "cafe muối"
    assert cafe.position == "after"
    assert cafe.relative_to == "Đại Nội"
    assert cafe.target_micro_tags == ["cafe_muoi"]

    lunch = intent.operations[2]
    assert lunch.query == "bún bò"
    assert lunch.time_window == {"start_min": 660, "end_min": 810}
    assert lunch.target_micro_tags == ["bun_bo"]

    vegetarian = intent.operations[3]
    assert vegetarian.query == "quán chay"
    assert vegetarian.time_window == {"start_min": 840, "end_min": 1020}
    assert vegetarian.target_micro_tags == ["vegetarian"]

    evening = intent.operations[4]
    assert evening.query == "Nguyễn Huệ"
    assert evening.target_category == "nightlife"
    assert evening.time_window == {"start_min": 1080, "end_min": 1320}

    plan = intent.constraints
    assert plan["status"] == "pending_confirmation"
    assert plan["requires_confirmation"] is True
    assert len(plan["operations"]) == 5
