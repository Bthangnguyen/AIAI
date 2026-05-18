import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { MapTimelineScreen } from '../../app/screens/MapTimelineScreen';

describe('MapTimelineScreen Active Trip', () => {
  it('shows skip stop button when locked', () => {
    const mockRoute = { params: { itinerary: { days: [{ route: [{ poi: { name: 'Test' } }] }] } } };
    const { getByText, queryByText } = render(<MapTimelineScreen route={mockRoute} navigation={{ setOptions: jest.fn() }} />);
    
    // Initially not locked, shows Confirm Trip
    expect(getByText(/Chốt Lịch Trình/i)).toBeTruthy();
    expect(queryByText(/Bỏ qua điểm này/i)).toBeNull();

    // Lock the trip
    fireEvent.press(getByText(/Chốt Lịch Trình/i));

    // Should now show Skip Stop
    expect(getByText(/Bỏ qua điểm này/i)).toBeTruthy();
  });
});
