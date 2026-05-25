import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { MapTimelineScreen } from '../../app/screens/MapTimelineScreen';
import { ThemeProvider } from '../../app/theme/context';
import { useTripStore } from '../../app/store/useTripStore';

describe('MapTimelineScreen Draft Itinerary', () => {
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

  it('shows undo snackbar when removing POI', () => {
    const mockRoute = { params: { itinerary: mockItinerary } };
    const { getByText, queryByText } = render(
      <ThemeProvider>
        <MapTimelineScreen route={mockRoute as any} navigation={{ setOptions: jest.fn() } as any} />
      </ThemeProvider>
    );
    
    // Snackbar should not be visible initially
    expect(queryByText(/Hoàn tác/i) || queryByText(/HoÃ n tÃ¡c/i)).toBeNull();
    
    // Simulate removing a POI (assuming there's a Xóa button for each POI - matched by regex for robustness)
    const deleteButton = queryByText(/Xóa/i) || getByText(/XÃ³a/i);
    fireEvent.press(deleteButton);
    
    // Snackbar should appear
    const undoButton = queryByText(/Hoàn tác/i) || getByText(/HoÃ n tÃ¡c/i);
    expect(undoButton).toBeTruthy();
  });
});
