import { load, save } from "./storage"
import { SyncQueue } from "./syncQueue"

// Mock storage functions
jest.mock("./storage", () => ({
  load: jest.fn(),
  save: jest.fn(),
}))

describe("SyncQueue", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("adds an action to the empty queue and saves it", () => {
    // Setup
    ;(load as jest.Mock).mockReturnValue(null)

    // Action
    const testAction = { type: "RE_ROUTE", payload: { id: 1 } }
    SyncQueue.enqueueAction(testAction)

    // Assert
    expect(load).toHaveBeenCalledWith("offline_sync_queue")
    expect(save).toHaveBeenCalledWith("offline_sync_queue", [testAction])
  })
})
