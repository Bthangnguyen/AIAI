/**
 * Mock popular destination cards for ExploreScreen.
 * Covers top 6 destinations in Vietnam.
 */
export interface PopularLocation {
  id: string
  name: string
  country: string
  photoUrl: string
  photoUrl2?: string
  priceFrom: number // USD
  rating: number
  locationCount: number
  category: "beach" | "mountain" | "city" | "island" | "heritage"
  tagline: string
}

export const POPULAR_LOCATIONS: PopularLocation[] = [
  {
    id: "loc-001",
    name: "Hội An",
    country: "Vietnam",
    photoUrl: "https://images.unsplash.com/photo-1555921015-5532091f6026?w=800&q=80",
    photoUrl2: "https://images.unsplash.com/photo-1528127269322-539801943592?w=800&q=80",
    priceFrom: 199,
    rating: 4.9,
    locationCount: 36,
    category: "heritage",
    tagline: "Ancient Town Lanterns",
  },
  {
    id: "loc-002",
    name: "Đà Nẵng",
    country: "Vietnam",
    photoUrl: "https://images.unsplash.com/photo-1549887534-1541e9326642?w=800&q=80",
    photoUrl2: "https://images.unsplash.com/photo-1588668214407-6ea9a6d8c272?w=800&q=80",
    priceFrom: 299,
    rating: 4.7,
    locationCount: 22,
    category: "beach",
    tagline: "Golden Bridge & Dragon",
  },
  {
    id: "loc-003",
    name: "Huế",
    country: "Vietnam",
    photoUrl: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    photoUrl2: "https://images.unsplash.com/photo-1603890037267-56d6c0b3c285?w=800&q=80",
    priceFrom: 149,
    rating: 4.8,
    locationCount: 16,
    category: "heritage",
    tagline: "Imperial City & Royal Tombs",
  },
  {
    id: "loc-004",
    name: "Phú Quốc",
    country: "Vietnam",
    photoUrl: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80",
    photoUrl2: "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80",
    priceFrom: 499,
    rating: 4.8,
    locationCount: 28,
    category: "island",
    tagline: "Pearl Island Paradise",
  },
  {
    id: "loc-005",
    name: "Hà Nội",
    country: "Vietnam",
    photoUrl: "https://images.unsplash.com/photo-1583417267826-aebc4d1542e1?w=800&q=80",
    photoUrl2: "https://images.unsplash.com/photo-1510227272981-87123e259b17?w=800&q=80",
    priceFrom: 249,
    rating: 4.6,
    locationCount: 42,
    category: "city",
    tagline: "Old Quarter & Hoan Kiem",
  },
  {
    id: "loc-006",
    name: "Sa Pa",
    country: "Vietnam",
    photoUrl: "https://images.unsplash.com/photo-1571401835393-8c882e254a8b?w=800&q=80",
    photoUrl2: "https://images.unsplash.com/photo-1528127269322-539801943592?w=800&q=80",
    priceFrom: 179,
    rating: 4.7,
    locationCount: 18,
    category: "mountain",
    tagline: "Rice Terraces & Fansipan",
  },
]
