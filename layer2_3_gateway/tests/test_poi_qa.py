"""Tests for POI QA pure logic."""
from app.services.poi_qa import (
    PoiQaRecord,
    compute_qa_summary,
    duplicate_group_map,
    filter_pois_by_issue,
    is_missing_duration,
    is_missing_hours,
    is_wrong_coords,
)


def _poi(**kwargs) -> PoiQaRecord:
    defaults = {
        "uuid": "x",
        "name": "Test",
        "category": "Test",
        "tags": [],
        "latitude": 16.47,
        "longitude": 107.58,
        "visit_duration_min": 60,
        "open_time": 540,
        "close_time": 1080,
        "has_embedding": True,
    }
    defaults.update(kwargs)
    return PoiQaRecord(**defaults)


def test_wrong_coords_flags_null_island_and_outside_bbox():
    assert is_wrong_coords(0, 0) is True
    assert is_wrong_coords(16.47, 107.58) is False
    assert is_wrong_coords(15.0, 107.58) is True


def test_missing_hours_invalid_window_and_default_pair():
    assert is_missing_hours(1200, 600) is True
    assert is_missing_hours(480, 1260) is True
    assert is_missing_hours(540, 1080) is False


def test_missing_duration_non_positive():
    assert is_missing_duration(0) is True
    assert is_missing_duration(30) is False


def test_duplicate_group_map_groups_nearby_same_name():
    pois = [
        _poi(uuid="a", name="Cafe Trung", latitude=16.4645, longitude=107.5746),
        _poi(uuid="b", name="cafe trung", latitude=16.4646, longitude=107.5747),
        _poi(uuid="c", name="Đại Nội", latitude=16.4678, longitude=107.5784),
    ]
    groups = duplicate_group_map(pois)
    assert groups["a"] == groups["b"]
    assert "c" not in groups


def test_compute_qa_summary_counts_issues():
    pois = [
        _poi(uuid="bad-coords", name="Null Island", latitude=0, longitude=0),
        _poi(uuid="bad-hours", name="Bad Hours", open_time=1200, close_time=600),
        _poi(uuid="bad-duration", name="Bad Duration", visit_duration_min=0),
        _poi(uuid="bad-embed", name="Bad Embed", has_embedding=False),
        _poi(uuid="dup-1", name="Cafe Trung", latitude=16.4645, longitude=107.5746),
        _poi(uuid="dup-2", name="Cafe Trung", latitude=16.4646, longitude=107.5747),
    ]
    summary = compute_qa_summary(pois)
    assert summary.wrong_coords == 1
    assert summary.missing_hours == 1
    assert summary.missing_duration == 1
    assert summary.missing_embedding == 1
    assert summary.duplicates == 2


def test_filter_pois_by_issue_wrong_coords():
    pois = [_poi(uuid="ok"), _poi(uuid="bad", latitude=0, longitude=0)]
    filtered, groups = filter_pois_by_issue(pois, "wrong_coords")
    assert [p.uuid for p in filtered] == ["bad"]
    assert groups == {}
