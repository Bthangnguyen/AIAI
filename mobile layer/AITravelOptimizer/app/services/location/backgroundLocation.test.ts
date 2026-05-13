import * as Location from "expo-location"

import { BackgroundLocationService } from "./backgroundLocation"

jest.mock("expo-task-manager", () => ({
  defineTask: jest.fn(),
}))

jest.mock("expo-location", () => ({
  requestForegroundPermissionsAsync: jest.fn(),
  requestBackgroundPermissionsAsync: jest.fn(),
  startLocationUpdatesAsync: jest.fn(),
  stopLocationUpdatesAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}))

jest.mock("expo-notifications", () => ({
  scheduleNotificationAsync: jest.fn(),
}))

describe("BackgroundLocationService", () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it("requests permissions and starts tracking if granted", async () => {
    ;(Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
      status: "granted",
    })
    ;(Location.requestBackgroundPermissionsAsync as jest.Mock).mockResolvedValue({
      status: "granted",
    })

    await BackgroundLocationService.startTracking()

    expect(Location.startLocationUpdatesAsync).toHaveBeenCalledWith(
      "BACKGROUND_LOCATION_TASK",
      expect.any(Object),
    )
  })
})
