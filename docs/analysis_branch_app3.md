# Branch Analysis Report: `origin/app3`

## 1. Exact Functionality
The `origin/app3` branch focuses on frontend UI styling experiments and introduces a massive **frontend mock backend pipeline** for testing the JIT rerouting feature in the offline/mock sandbox:
- **Visual Regression (Light Theme UI)**: 
  - Regresses the Glassmorphic Dark UI of the baseline branch back to an older, flat layout containing a semi-transparent screen overlay and static background photo (from Unsplash).
  - Lacks the high-fidelity interactive elements (voice pulse animations, gold orb accents, custom linear gradients, and state-driven progress bars).
- **Hardcoded Coordinates**:
  - Chat sending logic bypasses dynamic coordinates, hardcoding coordinates to Hanoi's Mường Thanh Hotel (`latitude: 21.0285`, `longitude: 105.8542`) instead of retrieving from the extracted L2 contract.
- **Reanimated-Based Spinner**:
  - LoadingScreen uses a `react-native-reanimated` shared value spinner rotation (`useSharedValue`, `useAnimatedStyle`) rather than standard `Animated` API.
  - Implements a flat timeline progress display (4 old pipeline steps) with a white/grey card look.
- **Client-Side Mock Backend (Inside `tripService.ts`)**:
  - Leverages `FeatureFlags.USE_MOCK_BACKEND` to intercept all re-route requests and execute a fully simulated routing engine purely inside the phone's JavaScript runtime:
    - **Tired / Foot Sore State**: Splices Cafe Stop ("The Note Coffee") at the very beginning of the daily itinerary, modifying durations and entrance fees.
    - **Hungry State**: Splices Restaurant Stop ("Phở 10 Lý Quốc Sư") into the day.
    - **Rainy / Weather State**: Identifies the next outdoor stop and swaps it out for an indoor stop ("Bảo tàng Mỹ thuật VN").
    - **Cafe State**: Splices Cafe Stop ("Giảng Café") at the beginning.
    - **Emergency Stop**: Inserts "Circle K / Pharmacity (Tạt ngang)" on user requests for pharmacy/marts.
    - **Extend Time State**: Extends the last POI visit duration by 30 minutes.
    - **Prioritize Free State**: Searches and expels the most expensive POI in the day's itinerary to enforce strict budget caps.

## 2. File Structure Changes
The repository architecture remains flat and identical to `main`, but introduces several frontend test utilities:
- **`mobile layer/AITravelOptimizer/app/config/features.ts`**: Holds the feature flags toggle schema (`FeatureFlags.USE_MOCK_BACKEND`).
- **`mobile layer/AITravelOptimizer/app/hooks/useMockPlanTrip.ts`**: Contains obsolete client-side plan mocks.
- **`mobile layer/AITravelOptimizer/app/services/api/rerouteService.ts`**: Standalone service wrapping mock payloads.

## 3. Dependencies Introduced
- **`react-native-reanimated`**: Leveraged heavily in screens for layout transitions, shared values, and rotation easing.

## 4. Database Changes
- *None* — Since this branch uses a mock frontend interceptor, no PostGIS database schema migrations or changes were implemented.

## 5. Modified Files
- `mobile layer/AITravelOptimizer/app/screens/HomeScreen.tsx`
- `mobile layer/AITravelOptimizer/app/screens/LoadingScreen.tsx`
- `mobile layer/AITravelOptimizer/app/services/api/tripService.ts`
- `mobile layer/AITravelOptimizer/app/config/features.ts`
- `mobile layer/AITravelOptimizer/app/hooks/useMockPlanTrip.ts`
- `mobile layer/AITravelOptimizer/app/services/api/rerouteService.ts`
