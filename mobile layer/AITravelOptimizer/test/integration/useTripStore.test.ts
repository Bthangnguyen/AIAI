import { act } from '@testing-library/react-native';
import { useTripStore } from '../../app/store/useTripStore';

describe('Trip Store State', () => {
  beforeEach(() => {
    // Reset store before each test
    useTripStore.getState().resetTrip();
  });

  it('should update sseStage correctly', () => {
    expect(useTripStore.getState().sseStage).toBe('idle');
    
    act(() => {
      useTripStore.getState().setSseStage('intent_extraction_started');
    });

    expect(useTripStore.getState().sseStage).toBe('intent_extraction_started');
  });

  it('should store extracted constraints', () => {
    const mockConstraints = {
      num_days: 2,
      tags: ['văn hóa'],
      locked_pois: [],
      food_preferences: ['chay'],
    };

    act(() => {
      useTripStore.getState().setExtractedConstraints(mockConstraints);
    });

    expect(useTripStore.getState().extractedConstraints).toEqual(mockConstraints);
  });
});
