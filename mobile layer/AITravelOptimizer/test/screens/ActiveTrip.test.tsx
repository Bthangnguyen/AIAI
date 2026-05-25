import React from 'react';
import { render } from '@testing-library/react-native';
import { MapTimelineScreen } from '../../app/screens/MapTimelineScreen';
import { ThemeProvider } from '../../app/theme/context';
import { useTripStore } from '../../app/store/useTripStore';

describe('MapTimelineScreen Active Trip', () => {
  const mockItinerary = {
    status: "success",
    num_days: 1,
    total_pois_visited: 1,
    total_pois_dropped: 0,
    total_entrance_fee: 0,
    total_travel_min: 15,
    total_distance_km: 5,
    budget_used: 0,
    days: [
      {
        day_index: 0,
        date: "2026-05-10",
        hotel_name: "Pilgrimage Village",
        hotel_location: { latitude: 16.4637, longitude: 107.5909 },
        total_travel_min: 15,
        total_visit_min: 60,
        total_distance_km: 5,
        total_entrance_fee: 0,
        num_pois: 1,
        stops: [
          {
            poi_id: "poi_1",
            poi_name: "Hoan Kiem Lake",
            location: { latitude: 21.0285, longitude: 105.8523 },
            arrival_time_min: 540,
            departure_time_min: 600,
            visit_duration_min: 60,
            travel_time_from_prev_min: 15,
            entrance_fee: 0,
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    useTripStore.getState().resetTrip();
  });

  it('shows starts trip button when not locked', () => {
    useTripStore.getState().setIsLocked(false);
    const mockRoute = { params: { itinerary: mockItinerary } };
    const { getByText } = render(
      <ThemeProvider>
        <MapTimelineScreen route={mockRoute as any} navigation={{ setOptions: jest.fn() } as any} />
      </ThemeProvider>
    );
    
    // Initially not locked, shows "Khóa lộ trình"
    expect(getByText(/Khóa lộ trình/i)).toBeTruthy();
  });

  it('shows start trip button when locked', () => {
    useTripStore.getState().setIsLocked(true);
    const mockRoute = { params: { itinerary: mockItinerary } };
    const { getByText } = render(
      <ThemeProvider>
        <MapTimelineScreen route={mockRoute as any} navigation={{ setOptions: jest.fn() } as any} />
      </ThemeProvider>
    );

    // Locked, shows "Bắt đầu chuyến đi"
    expect(getByText(/Bắt đầu chuyến đi/i)).toBeTruthy();
  });
});
