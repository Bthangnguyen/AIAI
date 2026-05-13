import { TravelItinerary } from "@/navigators/navigationTypes"

export const MOCK_ITINERARY: TravelItinerary = {
  status: "success",
  num_days: 2,
  total_pois_visited: 4,
  total_pois_dropped: 0,
  total_entrance_fee: 100000,
  total_travel_min: 60,
  total_distance_km: 15.5,
  budget_used: 100000,
  days: [
    {
      day_index: 1,
      date: "2026-05-10",
      hotel_name: "Hanoi Old Quarter Hotel",
      hotel_location: { latitude: 21.0333, longitude: 105.85 },
      total_travel_min: 30,
      total_visit_min: 120,
      total_distance_km: 5.5,
      total_entrance_fee: 50000,
      num_pois: 2,
      stops: [
        {
          poi_id: "poi_1",
          poi_name: "Hoan Kiem Lake",
          location: { latitude: 21.0285, longitude: 105.8523 },
          arrival_time_min: 540, // 9:00 AM
          departure_time_min: 600, // 10:00 AM
          visit_duration_min: 60,
          travel_time_from_prev_min: 15,
          entrance_fee: 0,
        },
        {
          poi_id: "poi_2",
          poi_name: "Temple of Literature",
          location: { latitude: 21.0294, longitude: 105.8355 },
          arrival_time_min: 615, // 10:15 AM
          departure_time_min: 675, // 11:15 AM
          visit_duration_min: 60,
          travel_time_from_prev_min: 15,
          entrance_fee: 50000,
        },
      ],
    },
    {
      day_index: 2,
      date: "2026-05-11",
      hotel_name: "Hanoi Old Quarter Hotel",
      hotel_location: { latitude: 21.0333, longitude: 105.85 },
      total_travel_min: 30,
      total_visit_min: 120,
      total_distance_km: 10,
      total_entrance_fee: 50000,
      num_pois: 2,
      stops: [
        {
          poi_id: "poi_3",
          poi_name: "Ho Chi Minh Mausoleum",
          location: { latitude: 21.0367, longitude: 105.8336 },
          arrival_time_min: 540,
          departure_time_min: 600,
          visit_duration_min: 60,
          travel_time_from_prev_min: 15,
          entrance_fee: 0,
        },
        {
          poi_id: "poi_4",
          poi_name: "Vietnam Museum of Ethnology",
          location: { latitude: 21.0406, longitude: 105.7983 },
          arrival_time_min: 620,
          departure_time_min: 680,
          visit_duration_min: 60,
          travel_time_from_prev_min: 20,
          entrance_fee: 50000,
        },
      ],
    },
  ],
}
