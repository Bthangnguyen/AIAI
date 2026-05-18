import React from 'react';
import { render, fireEvent, act } from '@testing-library/react-native';
import { MapTimelineScreen } from '../../app/screens/MapTimelineScreen';

describe('MapTimelineScreen Draft Itinerary', () => {
  it('shows undo snackbar when removing POI', () => {
    // Mocking route params and navigation
    const mockRoute = { params: { itinerary: { days: [{ route: [{ poi: { name: 'Test' } }] }] } } };
    const { getByText, queryByText } = render(<MapTimelineScreen route={mockRoute} navigation={{ setOptions: jest.fn() }} />);
    
    // Snackbar should not be visible initially
    expect(queryByText(/Hoàn tác/i)).toBeNull();
    
    // Simulate removing a POI (assuming there's a Xóa button for each POI)
    // We will just look for the first Xóa button
    const deleteButton = getByText('Xóa');
    fireEvent.press(deleteButton);
    
    // Snackbar should appear
    expect(getByText(/Hoàn tác/i)).toBeTruthy();
  });
});
