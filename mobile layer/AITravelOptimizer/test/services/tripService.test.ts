/**
 * Tầng 1: Unit Tests — TripService (checkHealth + planTripStream SSE)
 */

// Mock react-native-sse before import
jest.mock("react-native-sse", () => {
  return jest.fn().mockImplementation(() => ({
    addEventListener: jest.fn(),
    close: jest.fn(),
  }))
})

// Mock apisauce
jest.mock("../../app/services/api/index", () => ({
  api: {
    apisauce: {
      post: jest.fn(),
    },
  },
}))

import { TripService } from "../../app/services/api/tripService"

// Save original fetch
const originalFetch = global.fetch

describe("TripService", () => {
  afterEach(() => {
    jest.clearAllMocks()
    global.fetch = originalFetch
  })

  describe("checkHealth", () => {
    it("returns ready when server responds with status ready", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: "ready" }),
      }) as any

      const result = await TripService.checkHealth()
      expect(result.ready).toBe(true)
      expect(result.message).toBe("ready")
    })

    it("returns not ready on HTTP error", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: () => Promise.resolve({}),
      }) as any

      const result = await TripService.checkHealth()
      expect(result.ready).toBe(false)
      expect(result.message).toContain("503")
    })

    it("returns not ready on network error", async () => {
      global.fetch = jest.fn().mockRejectedValue(new Error("Network error")) as any

      const result = await TripService.checkHealth()
      expect(result.ready).toBe(false)
      expect(result.message).toBe("Network error")
    })

    it("returns not ready when server returns busy status", async () => {
      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: "busy" }),
      }) as any

      const result = await TripService.checkHealth()
      expect(result.ready).toBe(false)
    })
  })

  describe("planTripStream", () => {
    it("creates EventSource with correct URL and payload", () => {
      const EventSource = require("react-native-sse")

      TripService.planTripStream(
        "3 days in Hue",
        16.46, 107.59,
        "Test Hotel", 3,
        jest.fn(), jest.fn(), jest.fn(),
      )

      expect(EventSource).toHaveBeenCalledWith(
        expect.stringContaining("/v1/trip/plan_trip_stream"),
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "1",
          },
          body: JSON.stringify({
            user_prompt: "3 days in Hue",
            hotel_lat: 16.46,
            hotel_lon: 107.59,
            hotel_name: "Test Hotel",
            num_days: 3,
          }),
        }),
      )
    })

    it("registers message and error event listeners", () => {
      const EventSource = require("react-native-sse")
      const mockInstance = {
        addEventListener: jest.fn(),
        close: jest.fn(),
      }
      EventSource.mockImplementation(() => mockInstance)

      TripService.planTripStream(
        "test", 0, 0, "H", 1,
        jest.fn(), jest.fn(), jest.fn(),
      )

      expect(mockInstance.addEventListener).toHaveBeenCalledWith("message", expect.any(Function))
      expect(mockInstance.addEventListener).toHaveBeenCalledWith("error", expect.any(Function))
    })
  })

  describe("processChat", () => {
    it("calls /chat_process with message, history, contract and returns updated data", async () => {
      const mockResponse = {
        status: "clarifying",
        reply: "Dạ mình muốn đi Huế mấy ngày ạ?",
        updated_contract: { destination: "Huế", num_days: 1, tags: [] },
      }

      global.fetch = jest.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      }) as any

      const history = [{ role: "user", content: "Hi" }]
      const contract = { destination: "Huế", num_days: 1, tags: [] }

      const result = await TripService.processChat("Tôi muốn đi Huế", history as any, contract)

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/v1/trip/chat_process"),
        expect.objectContaining({
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "ngrok-skip-browser-warning": "1",
          },
          body: JSON.stringify({
            message: "Tôi muốn đi Huế",
            history,
            current_contract: contract,
          }),
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })
})
