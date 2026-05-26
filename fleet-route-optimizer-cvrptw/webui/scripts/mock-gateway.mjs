#!/usr/bin/env node
/**
 * Lightweight mock Gateway for web UI manual testing (P0–P8).
 * Run: npm run mock:gateway
 * Web:  NEXT_PUBLIC_GATEWAY_URL=http://localhost:8001 npm run dev
 */
import http from "node:http"

const PORT = Number(process.env.MOCK_GATEWAY_PORT ?? 8001)

const HUE_POIS = [
  { uuid: "dai-noi-hue", name: "Đại Nội Huế", category: "Di tích", latitude: 16.4678, longitude: 107.5784, visit_duration_min: 120, open_time: 480, close_time: 1260, entrance_fee: 200000, tags: ["lịch sử", "văn hóa"], has_embedding: true },
  { uuid: "chua-thien-mu", name: "Chùa Thiên Mụ", category: "Tâm linh", latitude: 16.4536, longitude: 107.5448, visit_duration_min: 75, open_time: 420, close_time: 1080, entrance_fee: 0, tags: ["chùa"], has_embedding: true },
  { uuid: "song-huong", name: "Sông Hương", category: "Cảnh quan", latitude: 16.4667, longitude: 107.59, visit_duration_min: 60, open_time: 0, close_time: 1440, entrance_fee: 0, tags: ["cảnh đẹp"], has_embedding: true },
  { uuid: "cau-truong-tien", name: "Cầu Trường Tiền", category: "Cảnh quan", latitude: 16.4689, longitude: 107.5886, visit_duration_min: 35, open_time: 480, close_time: 1320, entrance_fee: 0, tags: ["check-in"], has_embedding: true },
  { uuid: "lang-khai-dinh", name: "Lăng Khải Định", category: "Di tích", latitude: 16.3989, longitude: 107.5903, visit_duration_min: 90, open_time: 420, close_time: 1020, entrance_fee: 150000, tags: ["lịch sử"], has_embedding: true },
  { uuid: "lang-minh-mang", name: "Lăng Minh Mạng", category: "Di tích", latitude: 16.3875, longitude: 107.5694, visit_duration_min: 90, open_time: 420, close_time: 1020, entrance_fee: 150000, tags: ["lịch sử"], has_embedding: false },
  { uuid: "lang-tu-duc", name: "Lăng Tự Đức", category: "Di tích", latitude: 16.4326, longitude: 107.5658, visit_duration_min: 90, open_time: 420, close_time: 1020, entrance_fee: 150000, tags: ["lịch sử"], has_embedding: true },
  { uuid: "cho-dong-ba", name: "Chợ Đông Ba", category: "Ẩm thực", latitude: 16.4726, longitude: 107.5885, visit_duration_min: 75, open_time: 360, close_time: 1140, entrance_fee: 0, tags: ["chợ"], has_embedding: true },
  { uuid: "cafe-muoi", name: "Cafe Muối", category: "Cafe", latitude: 16.4645, longitude: 107.5746, visit_duration_min: 45, open_time: 420, close_time: 1260, entrance_fee: 45000, tags: ["cafe"], has_embedding: true },
  { uuid: "bun-bo-hue", name: "Bún bò Huế", category: "Ẩm thực", latitude: 16.4714, longitude: 107.5982, visit_duration_min: 45, open_time: 360, close_time: 840, entrance_fee: 60000, tags: ["bún bò"], has_embedding: false },
  { uuid: "quan-chay-thanh-lieu", name: "Quán chay Thanh Liễu", category: "Ăn chay", latitude: 16.4709, longitude: 107.5978, visit_duration_min: 60, open_time: 420, close_time: 1200, entrance_fee: 70000, tags: ["ăn chay"], has_embedding: true },
  { uuid: "doi-vong-canh", name: "Đồi Vọng Cảnh", category: "Cảnh quan", latitude: 16.4333, longitude: 107.565, visit_duration_min: 60, open_time: 360, close_time: 1080, entrance_fee: 0, tags: ["ngắm cảnh"], has_embedding: true },
  { uuid: "bien-thuan-an", name: "Biển Thuận An", category: "Biển", latitude: 16.5615, longitude: 107.6369, visit_duration_min: 120, open_time: 360, close_time: 1080, entrance_fee: 0, tags: ["biển"], has_embedding: true },
  { uuid: "pho-di-bo-hue", name: "Phố đi bộ Huế", category: "Giải trí", latitude: 16.4678, longitude: 107.5856, visit_duration_min: 90, open_time: 1020, close_time: 1380, entrance_fee: 0, tags: ["đi bộ"], has_embedding: true },
  { uuid: "nha-vuon-an-hien", name: "Nhà vườn An Hiên", category: "Văn hóa", latitude: 16.4678, longitude: 107.5677, visit_duration_min: 75, open_time: 480, close_time: 1020, entrance_fee: 70000, tags: ["nhà vườn"], has_embedding: false },
  { uuid: "qa-wrong-coords", name: "POI tọa độ sai (QA)", category: "Test", latitude: 0, longitude: 0, visit_duration_min: 30, open_time: 480, close_time: 1020, entrance_fee: 0, tags: ["qa"], has_embedding: true },
  { uuid: "qa-wrong-coords-2", name: "POI ngoài bbox (QA)", category: "Test", latitude: 16.62, longitude: 107.58, visit_duration_min: 30, open_time: 540, close_time: 1080, entrance_fee: 0, tags: ["qa"], has_embedding: true },
  { uuid: "qa-missing-embed", name: "POI thiếu embedding (QA)", category: "Test", latitude: 16.45, longitude: 107.55, visit_duration_min: 30, open_time: 480, close_time: 1020, entrance_fee: 0, tags: ["qa"], has_embedding: false },
  { uuid: "qa-bad-hours", name: "POI giờ mở sai (QA)", category: "Test", latitude: 16.451, longitude: 107.551, visit_duration_min: 30, open_time: 1200, close_time: 600, entrance_fee: 0, tags: ["qa"], has_embedding: true },
  { uuid: "qa-bad-duration", name: "POI thiếu duration (QA)", category: "Test", latitude: 16.452, longitude: 107.552, visit_duration_min: 0, open_time: 540, close_time: 1080, entrance_fee: 0, tags: ["qa"], has_embedding: true },
  { uuid: "dup-cafe-a", name: "Cafe Trung", category: "Cafe", latitude: 16.4645, longitude: 107.5746, visit_duration_min: 45, open_time: 420, close_time: 1200, entrance_fee: 45000, tags: ["cafe"], has_embedding: true },
  { uuid: "dup-cafe-b", name: "cafe trung", category: "Cafe", latitude: 16.46455, longitude: 107.57465, visit_duration_min: 45, open_time: 420, close_time: 1200, entrance_fee: 45000, tags: ["cafe"], has_embedding: true },
]

const poiOverrides = new Map()

function getPoiRecord(base) {
  const override = poiOverrides.get(base.uuid) ?? {}
  return {
    ...base,
    category: override.category ?? base.category,
    tags: override.tags ?? base.tags ?? [],
  }
}

function toAdminPoiItem(p) {
  return {
    uuid: p.uuid,
    name: p.name,
    category: p.category,
    tags: p.tags ?? [],
    latitude: p.latitude,
    longitude: p.longitude,
    visit_duration_min: p.visit_duration_min,
    open_time: p.open_time ?? 480,
    close_time: p.close_time ?? 1260,
    has_embedding: p.has_embedding ?? true,
  }
}

function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*")
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Accept, X-Mock-Scenario")
}

function json(res, status, body) {
  cors(res)
  res.writeHead(status, { "Content-Type": "application/json" })
  res.end(JSON.stringify(body))
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    req.on("data", (c) => chunks.push(c))
    req.on("end", () => {
      try {
        resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString("utf8")) : {})
      } catch (e) {
        reject(e)
      }
    })
    req.on("error", reject)
  })
}

function detectScenario(message = "", headerScenario = "") {
  if (headerScenario) return headerScenario
  const m = message.toLowerCase()
  if (m.includes("mock-error") || m.includes("lỗi backend")) return "sse-error"
  if (m.includes("mock-partial") || m.includes("ngân sách thấp")) return "partial"
  if (m.includes("mock-walking") || m.includes("không muốn đi bộ")) return "walking-low"
  if (m.includes("3 ngày") && !/(triệu|tr|k|000)/.test(m)) return "clarifying-budget"
  if (/huế|hue/.test(m) && /(triệu|tr|500k|000)/.test(m) && !/\d+\s*ngày/.test(m)) return "clarifying-days"
  return "happy"
}

function buildLayer4(scenario) {
  const baseStops = [
    { poi_id: "dai-noi-hue", poi_name: "Đại Nội Huế", arrival_time_min: 480 },
    { poi_id: "chua-thien-mu", poi_name: "Chùa Thiên Mụ", arrival_time_min: 630 },
    { poi_id: "cau-truong-tien", poi_name: "Cầu Trường Tiền", arrival_time_min: 780 },
  ]
  if (scenario === "partial") {
    return {
      status: "success",
      num_days: 2,
      days: [
        { day_index: 0, narrative_title: "Ngày văn hóa", stops: baseStops },
        { day_index: 1, narrative_title: "Ngày ẩm thực", stops: [{ poi_id: "cafe-muoi", poi_name: "Cafe Muối", arrival_time_min: 540 }] },
      ],
      total_distance_km: 18.4,
      total_pois_visited: 3,
      total_pois_dropped: 2,
      budget_used: 980000,
      budget_total: 800000,
      validation_notes: ["[warning] Ngân sách thấp — 2 POI bị bỏ qua", "[info] Cân nhắc giảm số điểm mỗi ngày"],
    }
  }
  return {
    status: "success",
    num_days: 2,
    days: [
      { day_index: 0, narrative_title: "Khám phá trung tâm", stops: baseStops },
      { day_index: 1, narrative_title: "Ẩm thực & cafe", stops: [{ poi_id: "quan-chay-thanh-lieu", poi_name: "Quán chay Thanh Liễu", arrival_time_min: 720 }] },
    ],
    total_distance_km: 22.1,
    total_pois_visited: 4,
    total_pois_dropped: 0,
    budget_used: 650000,
    budget_total: 1000000,
    validation_notes: [],
  }
}

function handleChatProcess(body, scenarioHeader) {
  const message = body.message ?? ""
  const scenario = detectScenario(message, scenarioHeader)

  if (scenario === "clarifying-budget") {
    return {
      status: "clarifying",
      reply: "Bạn dự kiến ngân sách khoảng bao nhiêu cho chuyến đi Huế 3 ngày?",
      updated_contract: { destination: "Huế", num_days: 3, budget_max: null, radius_km: 10, tags: [], locked_pois: [] },
    }
  }
  if (scenario === "clarifying-days") {
    return {
      status: "clarifying",
      reply: "Bạn muốn đi Huế mấy ngày?",
      updated_contract: { destination: "Huế", num_days: 1, budget_max: 1000000, radius_km: 10, tags: [], locked_pois: [] },
    }
  }
  return {
    status: "ready",
    reply: "Dạ em đã nhận đủ thông tin. Đang lên lịch trình khám phá Huế!",
    updated_contract: {
      destination: "Huế",
      num_days: message.match(/(\d+)\s*ngày/) ? Number(message.match(/(\d+)\s*ngày/)[1]) : 2,
      budget_max: 1000000,
      radius_km: 10,
      tags: ["văn hóa"],
      locked_pois: [],
    },
  }
}

async function handlePlanTripStream(req, res, body, scenarioHeader) {
  const message = body.user_prompt ?? ""
  const scenario = detectScenario(message, scenarioHeader)

  cors(res)
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  })

  const send = (payload) => {
    res.write(`data: ${JSON.stringify(payload)}\n\n`)
  }

  send({ stage: "intent_extraction_started" })
  await delay(200)
  const walkingContract =
    scenario === "walking-low"
      ? { destination: "Huế", num_days: 2, walking_tolerance: "low", transport_modes: ["taxi"] }
      : { destination: "Huế", num_days: 2 }
  send({ stage: "intent_extraction_completed", contract: walkingContract })
  await delay(200)
  send({ stage: "poi_search_started" })
  await delay(200)
  send({ stage: "poi_search_completed", pois_found: 4, locked_count: 0 })
  await delay(200)
  send({ stage: "optimization_started" })
  await delay(300)

  if (scenario === "sse-error") {
    send({ stage: "error", message: "Mock: LLM timeout — thử lại sau" })
    res.write("data: [DONE]\n\n")
    res.end()
    return
  }

  send({ stage: "optimization_completed" })
  const layer4 = buildLayer4(scenario)
  send({ stage: "validation_completed", validation_notes: layer4.validation_notes ?? [] })
  await delay(150)
  send({ stage: "narrative_completed", result: layer4 })
  res.write("data: [DONE]\n\n")
  res.end()
}

function handlePlanAlternatives() {
  const baseStops = [
    { poi_id: "dai-noi-hue", poi_name: "Đại Nội Huế", arrival_time_min: 480 },
    { poi_id: "chua-thien-mu", poi_name: "Chùa Thiên Mụ", arrival_time_min: 630 },
    { poi_id: "cau-truong-tien", poi_name: "Cầu Trường Tiền", arrival_time_min: 780 },
    { poi_id: "lang-khai-dinh", poi_name: "Lăng Khải Định", arrival_time_min: 900 },
  ]
  const chillStops = baseStops.slice(0, 2)
  const budgetStops = baseStops.slice(0, 3)

  const mkPlan = (style, label, description, stops, metrics) => ({
    style,
    label,
    description,
    days: [
      { day_index: 0, narrative_title: `${label} — Ngày 1`, stops },
      {
        day_index: 1,
        narrative_title: `${label} — Ngày 2`,
        stops: [{ poi_id: "cafe-muoi", poi_name: "Cafe Muối", arrival_time_min: 540 }],
      },
    ],
    total_pois: metrics.poi_count,
    metrics,
  })

  return {
    status: "success",
    num_plans: 3,
    plans: [
      mkPlan("balanced", "Cân bằng", "Kết hợp tham quan, ăn uống, và nghỉ ngơi hài hòa", baseStops, {
        total_cost: 650000,
        total_travel_min: 180,
        poi_count: 12,
        total_distance_km: 45,
        fatigue_score: 0.72,
        diversity_score: 0.81,
        warnings: { meal: false, outdoor_heat: true, budget: false },
        validation_messages: ["[warning] Ngày 1: POI ngoài trời trong khung 12h–14h"],
      }),
      mkPlan("budget", "Tiết kiệm", "Ưu tiên trải nghiệm miễn phí và giá rẻ", budgetStops, {
        total_cost: 420000,
        total_travel_min: 150,
        poi_count: 10,
        total_distance_km: 38,
        fatigue_score: 0.65,
        diversity_score: 0.74,
        warnings: { meal: false, outdoor_heat: false, budget: true },
        validation_messages: ["[warning] Tổng chi phí sát ngân sách"],
      }),
      mkPlan("chill", "Thoải mái", "Ít điểm, nhiều thời gian thư giãn", chillStops, {
        total_cost: 380000,
        total_travel_min: 95,
        poi_count: 7,
        total_distance_km: 28,
        fatigue_score: 0.45,
        diversity_score: 0.68,
        warnings: { meal: true, outdoor_heat: false, budget: false },
        validation_messages: ["[warning] Ngày 1: thiếu quán ăn trưa"],
      }),
    ],
  }
}

function handleReRoute(body) {
  const remaining = body.remaining_poi_ids ?? []
  if (remaining.includes("force-error")) {
    return { status: "error", message: "Mock: solver crash" }
  }
  if (remaining.length >= 6) {
    return { status: "infeasible", message: "Mock: ngày đã đầy — không thể thêm POI" }
  }
  if (remaining.includes("force-warning")) {
    return {
      status: "optimized_with_warning",
      message: "Mock: tối ưu một phần — một số POI bị dồn sát nhau",
      day: {
        day_index: body.day_index ?? 0,
        stops: [
          { poi_id: "hotel_day_0", arrival_time_min: 420 },
          ...remaining.slice(0, 5).map((id, i) => {
            const poi = HUE_POIS.find((p) => p.uuid === id)
            return { poi_id: id, poi_name: poi?.name ?? id, arrival_time_min: 480 + i * 90 }
          }),
        ],
      },
    }
  }
  return {
    status: "success",
    message: "Mock: đã tối ưu lại lịch trình",
    day: {
      day_index: body.day_index ?? 0,
      stops: [
        { poi_id: "hotel_day_0", arrival_time_min: 420 },
        ...remaining.map((id, i) => {
          const poi = HUE_POIS.find((p) => p.uuid === id)
          return { poi_id: id, poi_name: poi?.name ?? id, arrival_time_min: 480 + i * 90 }
        }),
      ],
    },
  }
}

function handleSearchPois(url) {
  const query = (url.searchParams.get("query") ?? "").toLowerCase()
  const limit = Number(url.searchParams.get("limit") ?? 8)
  const filtered = query
    ? HUE_POIS.filter((p) => [p.name, p.category, ...(p.tags ?? [])].join(" ").toLowerCase().includes(query))
    : HUE_POIS
  return filtered.slice(0, limit).map((p) => ({
    uuid: p.uuid,
    name: p.name,
    category: p.category,
    description: `${p.name} (mock)`,
    latitude: p.latitude,
    longitude: p.longitude,
    visit_duration_min: p.visit_duration_min,
    price: p.entrance_fee,
    entrance_fee: p.entrance_fee,
    tags: p.tags,
    is_locked: false,
  }))
}

function handleAdminPois(url) {
  const q = (url.searchParams.get("q") ?? "").toLowerCase()
  const limit = Number(url.searchParams.get("limit") ?? 50)
  const offset = Number(url.searchParams.get("offset") ?? 0)
  const all = HUE_POIS.map(getPoiRecord)
  const filtered = q
    ? all.filter((p) => [p.name, p.category, ...(p.tags ?? [])].join(" ").toLowerCase().includes(q))
    : all
  const slice = filtered.slice(offset, offset + limit)
  return {
    items: slice.map(toAdminPoiItem),
    total: filtered.length,
    limit,
    offset,
  }
}

function handleAdminPoiPatch(uuid, body) {
  const base = HUE_POIS.find((p) => p.uuid === uuid)
  if (!base) {
    return { status: 404, body: { detail: "POI not found" } }
  }
  if (body.category == null && body.tags == null) {
    return { status: 422, body: { detail: "No fields to update" } }
  }
  const current = getPoiRecord(base)
  const next = {
    category: body.category ?? current.category,
    tags: body.tags ?? current.tags,
  }
  poiOverrides.set(uuid, next)
  return { status: 200, body: toAdminPoiItem({ ...base, ...next }) }
}

const HUE_LAT_MIN = 16.3
const HUE_LAT_MAX = 16.6
const HUE_LNG_MIN = 107.4
const HUE_LNG_MAX = 107.8

function normalizePoiName(name) {
  return name.trim().toLowerCase().replace(/\s+/g, " ")
}

function haversineMeters(lat1, lon1, lat2, lon2) {
  const radius = 6371000
  const phi1 = (lat1 * Math.PI) / 180
  const phi2 = (lat2 * Math.PI) / 180
  const dPhi = ((lat2 - lat1) * Math.PI) / 180
  const dLambda = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(dPhi / 2) ** 2 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLambda / 2) ** 2
  return 2 * radius * Math.asin(Math.sqrt(a))
}

function isWrongCoords(p) {
  if (p.latitude === 0 && p.longitude === 0) return true
  return (
    p.latitude < HUE_LAT_MIN ||
    p.latitude > HUE_LAT_MAX ||
    p.longitude < HUE_LNG_MIN ||
    p.longitude > HUE_LNG_MAX
  )
}

function isMissingHours(p) {
  if (p.open_time >= p.close_time) return true
  return p.open_time === 480 && p.close_time === 1260
}

function isMissingDuration(p) {
  return p.visit_duration_min <= 0
}

function duplicateGroupMap(pois) {
  const groups = {}
  const byName = new Map()
  for (const poi of pois) {
    const key = normalizePoiName(poi.name)
    if (!key) continue
    if (!byName.has(key)) byName.set(key, [])
    byName.get(key).push(poi)
  }

  let groupIndex = 0
  for (const entries of byName.values()) {
    if (entries.length < 2) continue
    const visited = new Set()
    for (const seed of entries) {
      if (visited.has(seed.uuid)) continue
      const cluster = [seed]
      visited.add(seed.uuid)
      let expanded = true
      while (expanded) {
        expanded = false
        for (const candidate of entries) {
          if (visited.has(candidate.uuid)) continue
          if (
            cluster.some(
              (member) =>
                haversineMeters(candidate.latitude, candidate.longitude, member.latitude, member.longitude) <
                50,
            )
          ) {
            cluster.push(candidate)
            visited.add(candidate.uuid)
            expanded = true
          }
        }
      }
      if (cluster.length >= 2) {
        const groupId = `dup-${groupIndex++}`
        for (const member of cluster) groups[member.uuid] = groupId
      }
    }
  }
  return groups
}

function allAdminPois() {
  return HUE_POIS.map(getPoiRecord)
}

function computeMockQaSummary(pois) {
  const dupMap = duplicateGroupMap(pois)
  return {
    wrong_coords: pois.filter(isWrongCoords).length,
    duplicates: Object.keys(dupMap).length,
    missing_hours: pois.filter(isMissingHours).length,
    missing_duration: pois.filter(isMissingDuration).length,
    missing_embedding: pois.filter((p) => !p.has_embedding).length,
  }
}

function filterMockQaPois(pois, issue) {
  const dupMap = duplicateGroupMap(pois)
  if (issue === "wrong_coords") return { items: pois.filter(isWrongCoords), dupMap }
  if (issue === "duplicates") return { items: pois.filter((p) => dupMap[p.uuid]), dupMap }
  if (issue === "missing_hours") return { items: pois.filter(isMissingHours), dupMap }
  if (issue === "missing_duration") return { items: pois.filter(isMissingDuration), dupMap }
  if (issue === "missing_embedding") return { items: pois.filter((p) => !p.has_embedding), dupMap }
  return { items: [], dupMap }
}

function handleAdminQaSummary() {
  return computeMockQaSummary(allAdminPois())
}

function handleAdminQaList(url) {
  const issue = url.searchParams.get("issue") ?? "wrong_coords"
  const limit = Number(url.searchParams.get("limit") ?? 50)
  const offset = Number(url.searchParams.get("offset") ?? 0)
  const { items, dupMap } = filterMockQaPois(allAdminPois(), issue)
  const slice = items.slice(offset, offset + limit)
  return {
    issue,
    items: slice.map((p) => ({ ...toAdminPoiItem(p), duplicate_group: dupMap[p.uuid] ?? null })),
    total: items.length,
    limit,
    offset,
  }
}

function delay(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://localhost:${PORT}`)
  const scenarioHeader = req.headers["x-mock-scenario"] ?? ""

  if (req.method === "OPTIONS") {
    cors(res)
    res.writeHead(204)
    res.end()
    return
  }

  try {
    if (req.method === "GET" && url.pathname === "/v1/trip/health") {
      return json(res, 200, { status: "ready", service: "Mock Gateway (Web1 manual test)" })
    }

    if (req.method === "GET" && url.pathname === "/v1/trip/search_pois") {
      return json(res, 200, handleSearchPois(url))
    }

    if (req.method === "GET" && url.pathname === "/v1/admin/pois") {
      return json(res, 200, handleAdminPois(url))
    }

    if (req.method === "GET" && url.pathname === "/v1/admin/pois/qa-summary") {
      return json(res, 200, handleAdminQaSummary())
    }

    if (req.method === "GET" && url.pathname === "/v1/admin/pois/qa") {
      return json(res, 200, handleAdminQaList(url))
    }

    if (req.method === "PATCH" && url.pathname.startsWith("/v1/admin/pois/")) {
      const uuid = decodeURIComponent(url.pathname.replace("/v1/admin/pois/", ""))
      const body = await readBody(req)
      const result = handleAdminPoiPatch(uuid, body)
      return json(res, result.status, result.body)
    }

    if (req.method === "POST" && url.pathname === "/v1/trip/chat_process") {
      const body = await readBody(req)
      return json(res, 200, handleChatProcess(body, scenarioHeader))
    }

    if (req.method === "POST" && url.pathname === "/v1/trip/plan_trip_stream") {
      const body = await readBody(req)
      return handlePlanTripStream(req, res, body, scenarioHeader)
    }

    if (req.method === "POST" && url.pathname === "/v1/trip/plan_alternatives") {
      return json(res, 200, handlePlanAlternatives())
    }

    if (req.method === "POST" && url.pathname === "/v1/trip/re_route") {
      const body = await readBody(req)
      return json(res, 200, handleReRoute(body))
    }

    json(res, 404, { error: "Not found", path: url.pathname })
  } catch (e) {
    json(res, 500, { error: String(e) })
  }
})

server.listen(PORT, () => {
  console.log(`\n🧪 Mock Gateway → http://localhost:${PORT}`)
  console.log(`   Health: GET /v1/trip/health`)
  console.log(`\n📋 Prompt scenarios (type on home page):`)
  console.log(`   P1 clarifying budget : "Đi Huế 3 ngày"`)
  console.log(`   P1 clarifying days    : "Đi Huế 1 triệu"`)
  console.log(`   P3 happy path         : "Đi Huế 2 ngày ngân sách 1 triệu"`)
  console.log(`   P3+P4 partial/warning : "mock-partial Đi Huế 2 ngày 800k"`)
  console.log(`   P6 walking (mock)     : "mock-walking Đi Huế 2 ngày 1 triệu"`)
  console.log(`   P2+P3 build error     : "mock-error Đi Huế 2 ngày"`)
  console.log(`   Web2 compare          : tab Compare sau khi build (plan_alternatives mock)`)
  console.log(`\n   Web: cd webui && npm run dev\n`)
})
