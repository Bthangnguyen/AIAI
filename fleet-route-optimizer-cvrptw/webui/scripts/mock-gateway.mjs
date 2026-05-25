#!/usr/bin/env node
/**
 * Lightweight mock Gateway for web UI manual testing (P0–P5).
 * Run: npm run mock:gateway
 * Web:  NEXT_PUBLIC_GATEWAY_URL=http://localhost:8001 npm run dev
 */
import http from "node:http"

const PORT = Number(process.env.MOCK_GATEWAY_PORT ?? 8001)

const HUE_POIS = [
  { uuid: "dai-noi-hue", name: "Đại Nội Huế", category: "Di tích", latitude: 16.4678, longitude: 107.5784, visit_duration_min: 120, entrance_fee: 200000, tags: ["lịch sử", "văn hóa"] },
  { uuid: "chua-thien-mu", name: "Chùa Thiên Mụ", category: "Tâm linh", latitude: 16.4536, longitude: 107.5448, visit_duration_min: 75, entrance_fee: 0, tags: ["chùa"] },
  { uuid: "cau-truong-tien", name: "Cầu Trường Tiền", category: "Cảnh quan", latitude: 16.4689, longitude: 107.5886, visit_duration_min: 35, entrance_fee: 0, tags: ["check-in"] },
  { uuid: "lang-khai-dinh", name: "Lăng Khải Định", category: "Di tích", latitude: 16.3989, longitude: 107.5903, visit_duration_min: 90, entrance_fee: 150000, tags: ["lịch sử"] },
  { uuid: "cafe-muoi", name: "Cafe Muối", category: "Cafe", latitude: 16.4645, longitude: 107.5746, visit_duration_min: 45, entrance_fee: 45000, tags: ["cafe"] },
  { uuid: "quan-chay-thanh-lieu", name: "Quán chay Thanh Liễu", category: "Ăn chay", latitude: 16.4709, longitude: 107.5978, visit_duration_min: 60, entrance_fee: 70000, tags: ["ăn chay"] },
]

function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*")
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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

    if (req.method === "POST" && url.pathname === "/v1/trip/chat_process") {
      const body = await readBody(req)
      return json(res, 200, handleChatProcess(body, scenarioHeader))
    }

    if (req.method === "POST" && url.pathname === "/v1/trip/plan_trip_stream") {
      const body = await readBody(req)
      return handlePlanTripStream(req, res, body, scenarioHeader)
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
  console.log(`\n   Web: cd webui && npm run dev\n`)
})
