import * as Location from "expo-location"
import * as Notifications from "expo-notifications"
import * as TaskManager from "expo-task-manager"

const LOCATION_TASK_NAME = "BACKGROUND_LOCATION_TASK"

TaskManager.defineTask(LOCATION_TASK_NAME, async ({ data, error }: any) => {
  if (error) {
    console.error("Background Location Error:", error)
    return
  }
  if (data) {
    const isLate = false
    if (isLate) {
      await Notifications.scheduleNotificationAsync({
        content: {
          title: "Bạn sắp trễ lịch trình!",
          body: "Có muốn hệ thống tự động tìm đường thay thế không?",
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
          seconds: 1,
          repeats: false,
        },

      })
    }
  }
})

export const BackgroundLocationService = {
  async startTracking() {
    const { status: foregroundStatus } = await Location.requestForegroundPermissionsAsync()
    if (foregroundStatus !== "granted") return

    const { status: backgroundStatus } = await Location.requestBackgroundPermissionsAsync()
    if (backgroundStatus !== "granted") return

    await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
      accuracy: Location.Accuracy.Balanced,
      timeInterval: 60000,
      distanceInterval: 100,
      deferredUpdatesInterval: 60000,
    })
  },

  async stopTracking() {
    await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME)
  },
}
