import { create } from 'zustand';
import { persist, StateStorage, createJSONStorage } from 'zustand/middleware';
import { MMKV } from 'react-native-mmkv';
import { LLMDataContract, SSEStage } from '../types/api';

// Khởi tạo MMKV instance
const storage = new MMKV({
  id: 'trip-storage'
});

// Tạo adapter để Zustand có thể lưu vào MMKV
const zustandStorage: StateStorage = {
  setItem: (name, value) => {
    return storage.set(name, value);
  },
  getItem: (name) => {
    const value = storage.getString(name);
    return value ?? null;
  },
  removeItem: (name) => {
    return storage.delete(name);
  },
};

interface TripState {
  // 1. Input từ User
  originalPrompt: string;
  setOriginalPrompt: (prompt: string) => void;
  
  // 2. Trạng thái Loading (SSE)
  sseStage: SSEStage;
  setSseStage: (stage: SSEStage) => void;

  // 3. Dữ liệu Lộ trình & Reroute
  extractedConstraints: LLMDataContract | null;
  currentItinerary: any | null; // Có thể thay bằng kiểu cụ thể sau khi API hoàn thiện
  currentLocation: { lat: number; lon: number } | null;
  
  // Các hàm cập nhật
  setExtractedConstraints: (constraints: LLMDataContract) => void;
  setCurrentItinerary: (itinerary: any) => void;
  updateCurrentLocation: (lat: number, lon: number) => void;
  
  // Hàm reset
  resetTrip: () => void;
}

export const useTripStore = create<TripState>()(
  persist(
    (set) => ({
      originalPrompt: '',
      setOriginalPrompt: (prompt) => set({ originalPrompt: prompt }),
      
      sseStage: 'idle',
      setSseStage: (stage) => set({ sseStage: stage }),
      
      extractedConstraints: null,
      setExtractedConstraints: (c) => set({ extractedConstraints: c }),
      
      currentItinerary: null,
      setCurrentItinerary: (data) => set({ currentItinerary: data }),
      
      currentLocation: null,
      updateCurrentLocation: (lat, lon) => set({ currentLocation: { lat, lon } }),

      resetTrip: () => set({
        originalPrompt: '',
        sseStage: 'idle',
        extractedConstraints: null,
        currentItinerary: null
      })
    }),
    {
      name: 'ai-travel-trip-storage',
      storage: createJSONStorage(() => zustandStorage),
      // Bỏ qua không lưu sseStage (vì trạng thái loading chỉ có ý nghĩa trong một phiên làm việc)
      partialize: (state) => ({ 
        originalPrompt: state.originalPrompt,
        extractedConstraints: state.extractedConstraints,
        currentItinerary: state.currentItinerary
      })
    }
  )
);
