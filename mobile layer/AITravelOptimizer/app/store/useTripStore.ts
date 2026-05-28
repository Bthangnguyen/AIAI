import { create } from 'zustand';
import { persist, StateStorage, createJSONStorage } from 'zustand/middleware';
import { MMKV } from 'react-native-mmkv';
import { LLMDataContract, SSEStage } from '../types/api';
import type { TravelItinerary } from '../navigators/navigationTypes';

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

export interface LockedTripHistoryItem {
  id: string;
  destination: string;
  startDate: string;
  totalDays: number;
  poiCount: number;
  itinerary: TravelItinerary;
  lockedAt: string;
}

interface TripState {
  // 1. Input từ User
  originalPrompt: string;
  setOriginalPrompt: (prompt: string) => void;
  
  // 2. Trạng thái Loading (SSE)
  sseStage: SSEStage;
  setSseStage: (stage: SSEStage) => void;

  // 3. Dữ liệu Lộ trình & Reroute
  extractedConstraints: LLMDataContract | null;
  currentItinerary: TravelItinerary | null;
  currentLocation: { lat: number; lon: number } | null;
  
  // 4. Trip mode: Draft (chưa khóa) vs Live (đã khóa)
  isLocked: boolean;
  setIsLocked: (locked: boolean) => void;
  lockedTripHistory: LockedTripHistoryItem[];
  saveLockedTrip: (itinerary: TravelItinerary) => void;

  // 5. Visited POIs — persisted across app restarts
  visitedPOIIds: string[];
  markVisited: (poiId: string) => void;
  unmarkVisited: (poiId: string) => void;
  clearVisited: () => void;
  
  // Các hàm cập nhật
  setExtractedConstraints: (constraints: LLMDataContract) => void;
  setCurrentItinerary: (itinerary: TravelItinerary) => void;
  updateCurrentLocation: (lat: number, lon: number) => void;
  
  // Hàm reset
  resetTrip: () => void;
}

export const useTripStore = create<TripState>()(
  persist(
    (set, get) => ({
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

      // Trip mode
      isLocked: false,
      setIsLocked: (locked) => set({ isLocked: locked }),
      lockedTripHistory: [],
      saveLockedTrip: (itinerary) => {
        const destination = itinerary.days?.[0]?.start_hotel_name || "Chuyến đi đã khóa";
        const firstDate = itinerary.days?.[0]?.date || new Date().toISOString().slice(0, 10);
        const poiCount = itinerary.days?.reduce((sum, day) => sum + (day.stops?.length || 0), 0) || 0;
        const id = `${firstDate}-${destination}-${itinerary.num_days || itinerary.days?.length || 1}`;
        const item: LockedTripHistoryItem = {
          id,
          destination,
          startDate: firstDate,
          totalDays: itinerary.num_days || itinerary.days?.length || 1,
          poiCount,
          itinerary,
          lockedAt: new Date().toISOString(),
        };
        const withoutDuplicate = get().lockedTripHistory.filter((trip) => trip.id !== id);
        set({ lockedTripHistory: [item, ...withoutDuplicate] });
      },

      // Visited POIs (persisted via MMKV)
      visitedPOIIds: [],
      markVisited: (poiId) => {
        const current = get().visitedPOIIds;
        if (!current.includes(poiId)) {
          set({ visitedPOIIds: [...current, poiId] });
        }
      },
      unmarkVisited: (poiId) => {
        set({ visitedPOIIds: get().visitedPOIIds.filter(id => id !== poiId) });
      },
      clearVisited: () => set({ visitedPOIIds: [] }),

      resetTrip: () => set({
        originalPrompt: '',
        sseStage: 'idle',
        extractedConstraints: null,
        currentItinerary: null,
        isLocked: false,
        visitedPOIIds: [],
      })
    }),
    {
      name: 'ai-travel-trip-storage-v2',
      storage: createJSONStorage(() => zustandStorage),
      // Persist: prompt, constraints, itinerary, lock state, visited POIs
      // Skip: sseStage, currentLocation (transient)
      partialize: (state) => ({ 
        originalPrompt: state.originalPrompt,
        extractedConstraints: state.extractedConstraints,
        currentItinerary: state.currentItinerary,
        isLocked: state.isLocked,
        lockedTripHistory: state.lockedTripHistory,
        visitedPOIIds: state.visitedPOIIds,
      })
    }
  )
);
