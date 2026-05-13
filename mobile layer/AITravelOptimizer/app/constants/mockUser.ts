/** Mock user profile data for ProfileScreen. */
export interface MockUser {
  id: string
  name: string
  firstName: string
  email: string
  avatarUrl: string
  joinedDate: string
  tripCount: number
  reviewCount: number
  savedCount: number
  bio: string
  location: string
}

export const MOCK_USER: MockUser = {
  id: "user-001",
  name: "Nguyễn Thắng",
  firstName: "Thắng",
  email: "nguyen.thang@example.com",
  avatarUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&q=80",
  joinedDate: "2024-01-15",
  tripCount: 7,
  reviewCount: 23,
  savedCount: 14,
  bio: "Travel enthusiast exploring the hidden gems of Vietnam 🇻🇳",
  location: "Hà Nội, Vietnam",
}

export interface MockTripHistory {
  id: string
  destination: string
  photoUrl: string
  startDate: string
  endDate: string
  poiCount: number
  status: "completed" | "upcoming" | "draft"
  totalDays: number
}

export const MOCK_TRIP_HISTORY: MockTripHistory[] = [
  {
    id: "trip-001",
    destination: "Huế",
    photoUrl: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    startDate: "2026-03-14",
    endDate: "2026-03-17",
    poiCount: 8,
    status: "completed",
    totalDays: 3,
  },
  {
    id: "trip-002",
    destination: "Hội An",
    photoUrl: "https://images.unsplash.com/photo-1555921015-5532091f6026?w=800&q=80",
    startDate: "2026-01-20",
    endDate: "2026-01-23",
    poiCount: 10,
    status: "completed",
    totalDays: 3,
  },
  {
    id: "trip-003",
    destination: "Đà Nẵng",
    photoUrl: "https://images.unsplash.com/photo-1549887534-1541e9326642?w=800&q=80",
    startDate: "2026-07-01",
    endDate: "2026-07-05",
    poiCount: 0,
    status: "upcoming",
    totalDays: 4,
  },
]
