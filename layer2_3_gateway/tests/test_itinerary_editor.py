# -*- coding: utf-8 -*-
"""Unit tests for JIT Itinerary Editor Service."""

import pytest
from app.services.itinerary_editor import ItineraryEditorService, haversine_distance, estimate_travel_time
from app.schemas.trip import POIResponse
from uuid import uuid4

def test_haversine_distance():
    loc1 = {"latitude": 16.4637, "longitude": 107.5905}
    loc2 = {"latitude": 16.4677, "longitude": 107.5953}
    dist = haversine_distance(loc1, loc2)
    assert dist > 0
    assert dist < 2.0  # these two points are very close in Hue

def test_estimate_travel_time():
    loc1 = {"latitude": 16.4637, "longitude": 107.5905}
    loc2 = {"latitude": 16.4677, "longitude": 107.5953}
    minutes = estimate_travel_time(loc1, loc2)
    assert minutes >= 5  # minimum travel time fallback is 5 mins

def test_jit_remove_stop():
    editor = ItineraryEditorService()
    
    itinerary = {
        "status": "success",
        "num_days": 1,
        "days": [
            {
                "day_index": 0,
                "date": "day-0",
                "start_hotel_name": "Hotel Mora",
                "start_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "end_hotel_name": "Hotel Mora",
                "end_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "start_time_min": 480,
                "stops": [
                    {
                        "poi_id": "uuid-1111",
                        "poi_name": "Đại Nội Huế",
                        "location": {"latitude": 16.4677, "longitude": 107.5953},
                        "visit_duration_min": 90,
                        "entrance_fee": 200000.0,
                        "category": "culture"
                    },
                    {
                        "poi_id": "uuid-2222",
                        "poi_name": "Café Muối",
                        "location": {"latitude": 16.4622, "longitude": 107.5899},
                        "visit_duration_min": 45,
                        "entrance_fee": 0.0,
                        "category": "cafe"
                    }
                ]
            }
        ]
    }
    
    # Recalculate original timings first
    editor._recalculate_day_timings(itinerary["days"][0])
    
    # Verify pre-remove stops count and time
    assert len(itinerary["days"][0]["stops"]) == 2
    orig_total_travel = itinerary["days"][0]["total_travel_min"]
    
    # Remove Cafe Muoi
    res = editor.remove_stop(itinerary, "Café Muối")
    
    assert len(res["days"][0]["stops"]) == 1
    assert res["days"][0]["stops"][0]["poi_id"] == "uuid-1111"
    
    # Verify sequential propagation of time
    stop = res["days"][0]["stops"][0]
    expected_arrival = 480 + stop["travel_time_from_prev_min"]
    assert stop["arrival_time_min"] == expected_arrival
    assert stop["departure_time_min"] == expected_arrival + 90
    
    # Total travel min should have decreased since one stop was removed
    assert res["days"][0]["total_travel_min"] < orig_total_travel
    assert res["total_pois_visited"] == 1

def test_jit_add_stop():
    editor = ItineraryEditorService()
    
    itinerary = {
        "status": "success",
        "num_days": 1,
        "days": [
            {
                "day_index": 0,
                "date": "day-0",
                "start_hotel_name": "Hotel Mora",
                "start_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "end_hotel_name": "Hotel Mora",
                "end_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "start_time_min": 480,
                "stops": [
                    {
                        "poi_id": "uuid-1111",
                        "poi_name": "Đại Nội Huế",
                        "location": {"latitude": 16.4677, "longitude": 107.5953},
                        "visit_duration_min": 90,
                        "entrance_fee": 200000.0,
                        "category": "culture"
                    }
                ]
            }
        ]
    }
    
    poi_to_add = POIResponse(
        uuid=uuid4(),
        name="Chùa Thiên Mụ",
        category="culture",
        latitude=16.4522,
        longitude=107.5432,
        visit_duration_min=60,
        entrance_fee=0.0,
        open_time=420,
        close_time=1080
    )
    
    # Add Chùa Thiên Mụ at index 0 (as the first stop)
    res = editor.add_stop(itinerary, day_index=0, poi=poi_to_add, insert_index=0)
    
    assert len(res["days"][0]["stops"]) == 2
    assert res["days"][0]["stops"][0]["poi_name"] == "Chùa Thiên Mụ"
    assert res["days"][0]["stops"][1]["poi_name"] == "Đại Nội Huế"
    
    # Chùa Thiên Mụ timing propagation
    first_stop = res["days"][0]["stops"][0]
    second_stop = res["days"][0]["stops"][1]
    
    # first_stop arrival should be 480 + travel from hotel
    assert first_stop["arrival_time_min"] == 480 + first_stop["travel_time_from_prev_min"]
    # second_stop arrival should be first_stop departure + travel time between them
    assert second_stop["arrival_time_min"] == first_stop["departure_time_min"] + second_stop["travel_time_from_prev_min"]


def test_move_stop_honors_preferred_time_before_default_day_start():
    editor = ItineraryEditorService()
    itinerary = {
        "status": "success",
        "days": [
            {
                "day_index": 0,
                "start_time_min": 480,
                "start_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "end_hotel_location": {"latitude": 16.4637, "longitude": 107.5905},
                "stops": [
                    {
                        "poi_id": "uuid-1111",
                        "poi_name": "Dai Noi Hue",
                        "location": {"latitude": 16.4677, "longitude": 107.5953},
                        "visit_duration_min": 90,
                        "category": "culture",
                    }
                ],
            }
        ],
    }

    res = editor.move_stop(itinerary, "Dai Noi", target_day=1, preferred_time_min=420)
    stop = res["days"][0]["stops"][0]

    assert stop["arrival_time_min"] == 420
    assert stop["preferred_time_min"] == 420
