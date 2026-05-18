import React from 'react';
import { render } from '@testing-library/react-native';
import { HomeScreen } from '../../app/screens/HomeScreen';

describe('HomeScreen Conversational Entry', () => {
  it('renders chat input and prompt chips directly', () => {
    const { getByPlaceholderText, getByText } = render(<HomeScreen navigation={{ navigate: jest.fn() }} />);
    expect(getByPlaceholderText(/Bạn muốn đi đâu/i)).toBeTruthy();
    expect(getByText(/Đi Huế 3 ngày/i)).toBeTruthy();
  });
});
