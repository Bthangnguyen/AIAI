# Full Experience UI/UX Redesign — AI Travel Optimizer

## 1. Overview

Clone the Figma "Travel App UI Kit" design language into the existing React Native / Expo app. Deliver a **Full Experience** (10+ screens) with **mock backend** so the complete user flow can be tested on Android Emulator without any real API dependency.

**Source Figma**: `N0odA22MkrdhMcXxnMIivY` — Travel App UI Kits (Community)

---

## 2. Design System (Extracted from Figma)

### 2.1 Color Palette

```
Primary Black:    #0D0D0D  — CTA buttons, headings
White:            #FFFFFF  — Background, cards
Off-White:        #F5F5F5  — Section backgrounds
Gray Light:       #E7E7E7  — Borders, dividers
Gray Medium:      #858585  — Subtitle text
Gray Dark:        #272727  — Body text
Accent Teal:      #68D6CA  — Gradient start, tags
Accent Blue:      #2E60F4  — Gradient end, links
Accent Orange:    #FF6B35  — Warnings, weather
Star Yellow:      #FFD700  — Rating stars
Success Green:    #4CAF50  — Active states
Error Red:        #E74C3C  — Error states
```

### 2.2 Typography

```
Font Family: Poppins (Google Fonts)
  - Heading XL:   Poppins SemiBold 600, 36px, lineHeight 164.5%
  - Heading L:    Poppins SemiBold 600, 24px
  - Heading M:    Poppins SemiBold 600, 18px
  - Body:         Poppins Regular 400, 14px
  - Caption:      Poppins Regular 400, 12px
  - Button:       Poppins SemiBold 600, 16px
  - Tab:          Poppins Medium 500, 12px
```

### 2.3 Spacing

```
xs:   4px
sm:   8px
md:  16px
lg:  24px
xl:  32px
xxl: 48px
```

### 2.4 Border Radius

```
sm:     8px   — Small tags, chips
md:    15px   — Cards, images
lg:    25px   — Search bars, inputs
xl:    36px   — CTA buttons
full:  999px  — Avatars, dots
```

### 2.5 Shadows

```
Card:    0 2px 10px rgba(0,0,0,0.08)
Elevated: 0 4px 20px rgba(0,0,0,0.12)
Tab Bar: 0 -2px 10px rgba(0,0,0,0.06)
```

---

## 3. Screen Inventory

### 3.1 Screens to REFACTOR (existing)

| Screen | Current Issue | Target State |
|--------|-------------|--------------|
| `OnboardingScreen` | Placeholder images, wrong font | 3-slide carousel with Poppins, SVG illustrations, dot indicators |
| `LoginScreen` | Basic form | Email/password + social login (Facebook, Apple, Google icons), rounded 36px buttons |
| `HomeScreen` | Glassmorphism over photo | Clean white bg, search bar, popular locations cards, greeting header |
| `MapTimelineScreen` | Functional but raw | Map + bottom sheet with day tabs, weather badges, timeline cards |

### 3.2 Screens to CREATE (new)

| Screen | Description | Figma Reference |
|--------|-------------|-----------------|
| `RegisterScreen` | Sign up form: email, password, repeat, ToS checkbox | "Login registration page" (sign up variant) |
| `ExploreScreen` | Popular locations grid, search, category filters (Island/Beach/Resort) | "Front page" |
| `POIDetailScreen` | Full-width hero image, rating stars, description, "Plan trip" CTA | "Attraction details page" + "Attraction introduction page" |
| `ItineraryFormScreen` | Calendar picker, date range selection, query input, "Next step" CTA | "Schedule page" |
| `TripSummaryScreen` | Day-by-day itinerary list, weather forecast per day, cost breakdown | "Weather query page" |
| `ProfileScreen` | Avatar, trip stats, settings access, social links | Derived from Figma patterns |
| `SettingsScreen` | Language, theme, notifications, API URL (dev), logout | Standard patterns |
| `TripHistoryScreen` | List of past/saved trips, tap to re-open | Standard list pattern |
| `ShareTripScreen` | Trip preview card + share actions (copy link, social) | Derived |

### 3.3 Navigation Architecture

```
RootStack
├── Auth Flow (unauthenticated)
│   ├── OnboardingScreen
│   ├── LoginScreen
│   └── RegisterScreen
│
└── Main Flow (authenticated)
    ├── BottomTabNavigator
    │   ├── HomeTab → ExploreScreen (Home)
    │   ├── GuideTab → TripHistoryScreen
    │   ├── WalletTab → TripSummaryScreen (current trip)
    │   └── ProfileTab → ProfileScreen
    │
    └── Modal/Push Screens
        ├── POIDetailScreen
        ├── ItineraryFormScreen (from Home)
        ├── LoadingScreen (SSE pipeline)
        ├── MapTimelineScreen (result)
        ├── ShareTripScreen
        └── SettingsScreen
```

---

## 4. Mock Data Architecture

### 4.1 Mock Service Layer

Replace real API calls with a `MockTripService` that returns realistic data with artificial delays (500-2000ms) to simulate SSE streaming.

```typescript
// app/services/mock/mockTripService.ts
export const MockTripService = {
  planTripStream: (prompt, hotelLat, hotelLon, hotelName, numDays) => {
    // Returns an EventSource-like emitter with fake SSE events:
    // 1. l2_done (500ms) — LLM extraction
    // 2. l3_done (1500ms) — Spatial filter
    // 3. l4_result (3000ms) — Solver output with full itinerary
  }
}
```

### 4.2 Mock Data Files

```
app/constants/
├── mockItinerary.ts      (existing — expand to multi-day)
├── mockPOIs.ts           (new — 20+ POIs with photos, ratings)
├── mockPopularLocations.ts (new — destination cards)
├── mockWeather.ts        (new — per-day weather data)
└── mockUser.ts           (new — profile data)
```

### 4.3 Feature Flags

```typescript
// app/config/features.ts
export const USE_MOCK_BACKEND = true  // Toggle mock vs real API
```

---

## 5. Bottom Tab Bar Design

Following Figma's tab bar pattern:

```
┌──────────────────────────────────────┐
│  🏠 Home    💼 Wallet    📖 Guide   📊 Chart │
│  (active)                             │
└──────────────────────────────────────┘
```

- White background (#FFFFFF)
- Rounded top corners (24px)
- Active tab: primary black icon + bold label
- Inactive tab: gray (#858585) icon + regular label
- Shadow: `0 -2px 10px rgba(0,0,0,0.06)`

Map to our app:
- **Home** → ExploreScreen (search + popular)
- **Wallet** → Current trip / TripSummaryScreen
- **Guide** → TripHistoryScreen
- **Chart** → ProfileScreen + Stats

---

## 6. Component Library

### 6.1 Shared Components to Build

| Component | Description |
|-----------|-------------|
| `SearchBar` | Rounded input with search icon, placeholder "Search..." |
| `LocationCard` | Image + title + price + rating + locations count |
| `POICard` | Compact card: image, name, time, description |
| `DayTabBar` | Horizontal scroll: Day 1 / Day 2 / Day 3 with active indicator |
| `WeatherBadge` | Circle with weather icon + temperature |
| `TimelineItem` | Time + vertical line + stop name + activity |
| `RatingStars` | 5-star display with score and review count |
| `CategoryChip` | Rounded pill: Island / Beach / Resort with active state |
| `CTAButton` | Full-width black/gradient rounded button |
| `SocialLoginButton` | Icon + text button for Facebook/Apple/Google |
| `BottomTabBar` | Custom tab bar matching Figma design |
| `AvatarBadge` | Circular avatar with online indicator |
| `CalendarPicker` | Month view calendar with date range selection |

---

## 7. Push Notifications (Mock)

For demo purposes, implement local push notifications using `expo-notifications`:
- **Trip reminder**: "Your trip to Huế starts tomorrow!"
- **Weather alert**: "Rain expected at 2 PM, consider indoor activities"
- **Re-route suggestion**: "Traffic detected, want to re-route?"

All triggered locally with `timeInterval` triggers during demo flow.

---

## 8. Development Workflow

### 8.1 Android Emulator Setup
- Install Android Studio + create Pixel 6 Pro AVD (API 34)
- Use `npx expo run:android` for native module support (Mapbox)
- Hot reload enabled for rapid iteration

### 8.2 Test-Driven Development
- **Unit tests**: Each mock service function
- **Component tests**: React Native Testing Library for each new component
- **Navigation tests**: Verify screen transitions
- **Snapshot tests**: Visual regression for key screens

---

## 9. Success Criteria

1. ✅ All 13 screens render correctly on Android Emulator
2. ✅ Complete user flow: Onboarding → Login → Home → Plan Trip → Loading → MapTimeline → POI Detail
3. ✅ Bottom tab navigation works with smooth transitions
4. ✅ Mock SSE pipeline shows realistic loading animation
5. ✅ Design matches Figma reference (Poppins font, white bg, rounded corners)
6. ✅ Push notifications trigger locally
7. ✅ Feature flag toggles mock/real backend
