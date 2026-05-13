/**
 * Mock POI data — 20 realistic points of interest in Huế, Vietnam.
 * Used as mock Layer 4 solver output when USE_MOCK_BACKEND = true.
 */
export interface MockPOI {
  id: string
  name: string
  category: "culture" | "nature" | "food" | "shopping" | "entertainment"
  lat: number
  lon: number
  visitDurationMin: number
  entranceFee: number // VND
  description: string
  photoUrl: string
  rating: number
  reviewCount: number
  openTime: string
  closeTime: string
  address: string
}

export const MOCK_POIS: MockPOI[] = [
  {
    id: "hue-001",
    name: "Đại Nội Huế (Imperial Citadel)",
    category: "culture",
    lat: 16.4698,
    lon: 107.5796,
    visitDurationMin: 120,
    entranceFee: 200000,
    description:
      "The Imperial City of Huế is a complex of monuments, temples, gardens, and palaces within a citadel built in the early 19th century. A UNESCO World Heritage Site.",
    photoUrl: "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    rating: 4.8,
    reviewCount: 12450,
    openTime: "07:00",
    closeTime: "17:30",
    address: "Huế, Thừa Thiên Huế",
  },
  {
    id: "hue-002",
    name: "Chùa Thiên Mụ",
    category: "culture",
    lat: 16.453,
    lon: 107.5487,
    visitDurationMin: 60,
    entranceFee: 0,
    description:
      "Thiên Mụ Pagoda is one of the oldest temples in Huế, standing on Ha Khe Hill by the Perfume River. Its iconic seven-story tower (Phước Duyên) is a symbol of the city.",
    photoUrl: "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&q=80",
    rating: 4.7,
    reviewCount: 8320,
    openTime: "08:00",
    closeTime: "17:00",
    address: "Kim Long, Huế",
  },
  {
    id: "hue-003",
    name: "Lăng Tự Đức",
    category: "culture",
    lat: 16.4578,
    lon: 107.5528,
    visitDurationMin: 90,
    entranceFee: 150000,
    description:
      "The tomb of Emperor Tự Đức is the largest royal mausoleum complex in Huế. Featuring a lake, pavilions, and gardens, it was also used as a residence during his reign.",
    photoUrl: "https://images.unsplash.com/photo-1603890037267-56d6c0b3c285?w=800&q=80",
    rating: 4.6,
    reviewCount: 5670,
    openTime: "07:00",
    closeTime: "17:30",
    address: "Thủy Xuân, Huế",
  },
  {
    id: "hue-004",
    name: "Lăng Khải Định",
    category: "culture",
    lat: 16.4039,
    lon: 107.5875,
    visitDurationMin: 75,
    entranceFee: 150000,
    description:
      "Khải Định Tomb is a unique blend of Vietnamese and European architectural styles. Its interior is lavishly decorated with elaborate mosaic inlays made from glass and porcelain.",
    photoUrl: "https://images.unsplash.com/photo-1559563458-527698bf5295?w=800&q=80",
    rating: 4.7,
    reviewCount: 6890,
    openTime: "07:00",
    closeTime: "17:00",
    address: "Châu Chữ, Huế",
  },
  {
    id: "hue-005",
    name: "Cầu Trường Tiền",
    category: "culture",
    lat: 16.4627,
    lon: 107.5996,
    visitDurationMin: 30,
    entranceFee: 0,
    description:
      "Trang Tien Bridge is the most iconic bridge in Huế, spanning the Perfume River. Built by the French in 1899, it's a symbol of the city and a popular spot for evening walks.",
    photoUrl: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80",
    rating: 4.5,
    reviewCount: 4210,
    openTime: "00:00",
    closeTime: "23:59",
    address: "Trung tâm, Huế",
  },
  {
    id: "hue-006",
    name: "Chợ Đông Ba",
    category: "shopping",
    lat: 16.4689,
    lon: 107.6018,
    visitDurationMin: 90,
    entranceFee: 0,
    description:
      "Dong Ba Market is the largest traditional market in Huế. A great place to experience local life and buy souvenirs, local specialties, and traditional handicrafts.",
    photoUrl: "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
    rating: 4.2,
    reviewCount: 3120,
    openTime: "06:00",
    closeTime: "18:00",
    address: "Trần Hưng Đạo, Huế",
  },
  {
    id: "hue-007",
    name: "Bún Bò Huế Mợ Tôn",
    category: "food",
    lat: 16.465,
    lon: 107.595,
    visitDurationMin: 45,
    entranceFee: 0,
    description:
      "Authentic Bún Bò Huế — the signature spicy beef noodle soup of Huế. This family-run restaurant has been serving the original recipe for over 30 years.",
    photoUrl: "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=800&q=80",
    rating: 4.9,
    reviewCount: 2890,
    openTime: "06:00",
    closeTime: "11:00",
    address: "Nguyễn Công Trứ, Huế",
  },
  {
    id: "hue-008",
    name: "Lăng Minh Mạng",
    category: "culture",
    lat: 16.4378,
    lon: 107.547,
    visitDurationMin: 90,
    entranceFee: 150000,
    description:
      "Minh Mang Tomb is considered one of the finest of the Nguyễn dynasty tombs. The complex features beautiful lakes, pine forests, and elegantly proportioned architecture.",
    photoUrl: "https://images.unsplash.com/photo-1549880338-65ddcdfd017b?w=800&q=80",
    rating: 4.6,
    reviewCount: 4560,
    openTime: "07:00",
    closeTime: "17:30",
    address: "Hương Thọ, Huế",
  },
  {
    id: "hue-009",
    name: "Vườn Cơ Hạ (Co Ha Garden)",
    category: "nature",
    lat: 16.4712,
    lon: 107.576,
    visitDurationMin: 45,
    entranceFee: 50000,
    description:
      "A hidden gem within the Imperial City — Co Ha Garden is a serene retreat with ancient trees, lotus ponds, and traditional Vietnamese landscaping.",
    photoUrl: "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=800&q=80",
    rating: 4.4,
    reviewCount: 1230,
    openTime: "07:00",
    closeTime: "17:30",
    address: "Hoàng thành Huế",
  },
  {
    id: "hue-010",
    name: "Nhà Hàng Tịnh Gia Viên",
    category: "food",
    lat: 16.462,
    lon: 107.583,
    visitDurationMin: 90,
    entranceFee: 0,
    description:
      "Experience authentic Royal Huế Cuisine in a beautifully restored heritage house. Famous for cơm hến, bánh khoái, and elaborate royal banquet sets.",
    photoUrl: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80",
    rating: 4.7,
    reviewCount: 1890,
    openTime: "10:00",
    closeTime: "21:00",
    address: "Lê Thánh Tôn, Huế",
  },
  {
    id: "hue-011",
    name: "Biển Thuận An",
    category: "nature",
    lat: 16.514,
    lon: 107.696,
    visitDurationMin: 120,
    entranceFee: 0,
    description:
      "Thuan An Beach is a serene stretch of white sand just 15km from Huế city center. Perfect for swimming and watching fishing boats along the peaceful lagoon.",
    photoUrl: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80",
    rating: 4.3,
    reviewCount: 3450,
    openTime: "00:00",
    closeTime: "23:59",
    address: "Phú Thuận, Huế",
  },
  {
    id: "hue-012",
    name: "Bảo Tàng Mỹ Thuật Cung Đình Huế",
    category: "culture",
    lat: 16.4685,
    lon: 107.5793,
    visitDurationMin: 60,
    entranceFee: 50000,
    description:
      "The Museum of Royal Fine Arts houses over 300 original royal objects including costumes, weapons, and porcelain from the Nguyễn dynasty.",
    photoUrl: "https://images.unsplash.com/photo-1580060839134-75a5edca2e99?w=800&q=80",
    rating: 4.5,
    reviewCount: 2100,
    openTime: "07:30",
    closeTime: "17:30",
    address: "3 Lê Trực, Huế",
  },
  {
    id: "hue-013",
    name: "Làng Hương Thủy Xuân",
    category: "culture",
    lat: 16.4456,
    lon: 107.5634,
    visitDurationMin: 60,
    entranceFee: 0,
    description:
      "Thủy Xuân Incense Village is famous for its colorful handmade incense sticks. A wonderful place for photography and to observe traditional Vietnamese craft.",
    photoUrl: "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80",
    rating: 4.6,
    reviewCount: 1560,
    openTime: "07:00",
    closeTime: "17:00",
    address: "Thủy Xuân, Huế",
  },
  {
    id: "hue-014",
    name: "Café Nón Lá",
    category: "food",
    lat: 16.467,
    lon: 107.598,
    visitDurationMin: 45,
    entranceFee: 0,
    description:
      "A charming rooftop café with panoramic views over the Perfume River and the city's rooftops. Known for its Huế-style cold drip coffee.",
    photoUrl: "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800&q=80",
    rating: 4.4,
    reviewCount: 980,
    openTime: "07:00",
    closeTime: "22:00",
    address: "Phạm Ngũ Lão, Huế",
  },
  {
    id: "hue-015",
    name: "Phá Tam Giang (Tam Giang Lagoon)",
    category: "nature",
    lat: 16.528,
    lon: 107.641,
    visitDurationMin: 180,
    entranceFee: 0,
    description:
      "Tam Giang Lagoon is the largest lagoon in Southeast Asia. Rent a boat and explore the fishing villages, wetlands, and incredible sunsets over the water.",
    photoUrl: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",
    rating: 4.8,
    reviewCount: 2340,
    openTime: "00:00",
    closeTime: "23:59",
    address: "Quảng Điền, Huế",
  },
]

/** Quick lookup by id */
export const getMockPOIById = (id: string): MockPOI | undefined =>
  MOCK_POIS.find((p) => p.id === id)

/** Filter by category */
export const getMockPOIsByCategory = (category: MockPOI["category"]): MockPOI[] =>
  MOCK_POIS.filter((p) => p.category === category)
