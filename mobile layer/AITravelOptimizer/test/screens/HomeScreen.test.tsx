import React from 'react';
import { render } from '@testing-library/react-native';
import { HomeScreen } from '../../app/screens/HomeScreen';
import { ThemeProvider } from '../../app/theme/context';

describe('HomeScreen Conversational Entry', () => {
  it('renders chat input and prompt chips directly', () => {
    const { getByPlaceholderText, getByText } = render(
      <ThemeProvider>
        <HomeScreen navigation={{ navigate: jest.fn() } as any} />
      </ThemeProvider>
    );
    expect(getByPlaceholderText(/Nhập lịch trình bạn mơ ước/i)).toBeTruthy();
    expect(getByText(/🏯 Đại Nội Huế 1 ngày/i)).toBeTruthy();
  });
});
