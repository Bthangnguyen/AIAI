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


def test_change_duration_breakdown_requires_rebuild_path():
    planner = EditIntentPlanner()
    intent = planner.build("thêm một ngày nữa cho lịch trình")

    assert intent.action == "change_duration"
    assert len(intent.operations) == 1
    assert intent.operations[0].type == "change_duration"
    assert intent.constraints["status"] == "pending_confirmation"
    assert intent.constraints["requires_confirmation"] is True


def test_new_edit_intents():
    planner = EditIntentPlanner()
    
    # 1. Budget changes
    i1 = planner.build("giảm ngân sách xuống 1.5 triệu")
    assert i1.action == "change_budget"
    assert len(i1.operations) == 1
    assert i1.operations[0].type == "change_budget"
    assert i1.operations[0].amount == 1500000.0
    assert "ngân sách thành 1,5 triệu" in i1.constraints["assistant_reply"]

    i2 = planner.build("tăng ngân sách lên 3tr")
    assert i2.operations[0].amount == 3000000.0
    
    i3 = planner.build("đổi ngân sách thành 500k")
    assert i3.operations[0].amount == 500000.0
    assert "ngân sách thành 500k" in i3.constraints["assistant_reply"]

    i4 = planner.build("đổi ngân sách")
    assert i4.operations[0].amount is None

    # 2. Pace changes
    p1 = planner.build("đi thong thả hơn nhé")
    assert p1.action == "change_pace"
    assert p1.operations[0].type == "change_pace"
    assert p1.operations[0].value == "chill"
    assert "thong thả" in p1.constraints["assistant_reply"]

    p2 = planner.build("lịch trình dày đặc hơn")
    assert p2.operations[0].value == "intense"
    assert "dày đặc" in p2.constraints["assistant_reply"]

    p3 = planner.build("đi bình thường cân bằng thôi")
    assert p3.operations[0].value == "balanced"
    assert "vừa phải" in p3.constraints["assistant_reply"]

    # 3. Time changes
    t1 = planner.build("bắt đầu trễ hơn chút")
    assert t1.action == "change_time"
    assert t1.operations[0].type == "change_time"
    assert t1.operations[0].value == "later"

    t2 = planner.build("kết thúc sớm hơn")
    assert t2.operations[0].value == "earlier"

    t3 = planner.build("đổi giờ khởi hành thành 8h sáng")
    assert t3.operations[0].target_time_min == 480

    # 4. Add Preference
    pref1 = planner.build("tôi thích ăn hải sản")
    assert pref1.action == "add_preference"
    assert pref1.operations[0].type == "add_preference"
    assert pref1.operations[0].target == "ăn hải sản"

    pref2 = planner.build("thêm sở thích ngắm cảnh thiên nhiên")
    assert pref2.action == "add_preference"
    assert pref2.operations[0].target == "ngắm cảnh thiên nhiên"

    # 5. Avoid Preference
    av1 = planner.build("không thích đi bộ nhiều")
    assert av1.action == "avoid_preference"
    assert av1.operations[0].type == "avoid_preference"
    assert av1.operations[0].target == "đi bộ nhiều"

    av2 = planner.build("tránh các điểm đông đúc")
    assert av2.action == "avoid_preference"
    assert av2.operations[0].target == "các điểm đông đúc"
