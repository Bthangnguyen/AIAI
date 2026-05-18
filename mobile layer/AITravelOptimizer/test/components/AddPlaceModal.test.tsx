import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { AddPlaceModal } from '../../app/components/AddPlaceModal';

describe('AddPlaceModal Component', () => {
  it('allows user to search and add a place', () => {
    const mockOnAddPlaces = jest.fn();
    const { getByPlaceholderText, getByText } = render(
      <AddPlaceModal visible={true} onClose={jest.fn()} onAddPlaces={mockOnAddPlaces} />
    );

    const input = getByPlaceholderText(/VD: Thêm bún bò/i);
    fireEvent.changeText(input, 'Bún bò');

    const searchBtn = getByText('Tìm kiếm');
    fireEvent.press(searchBtn);

    // Assuming mock returns 'Bún Bò Huế'
    const resultItem = getByText('Bún Bò Huế');
    fireEvent.press(resultItem);

    const addBtn = getByText(/Thêm 1 điểm/i);
    fireEvent.press(addBtn);

    expect(mockOnAddPlaces).toHaveBeenCalledWith(expect.any(Array));
  });
});
