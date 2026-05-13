/**
 * Mock weather data per day for TripSummaryScreen and MapTimelineScreen.
 */
export type WeatherCondition =
  | "sunny"
  | "partly_cloudy"
  | "cloudy"
  | "rainy"
  | "stormy"
  | "windy"

export interface DayWeather {
  day: number // 1-based
  date: string // YYYY-MM-DD
  condition: WeatherCondition
  tempHigh: number // Celsius
  tempLow: number
  humidity: number // percent
  icon: string // emoji
  description: string
}

export const MOCK_WEATHER: DayWeather[] = [
  {
    day: 1,
    date: "2026-06-14",
    condition: "sunny",
    tempHigh: 34,
    tempLow: 26,
    humidity: 65,
    icon: "☀️",
    description: "Clear sunny day, perfect for sightseeing",
  },
  {
    day: 2,
    date: "2026-06-15",
    condition: "partly_cloudy",
    tempHigh: 32,
    tempLow: 25,
    humidity: 70,
    icon: "⛅",
    description: "Partly cloudy, comfortable for outdoor activities",
  },
  {
    day: 3,
    date: "2026-06-16",
    condition: "rainy",
    tempHigh: 28,
    tempLow: 23,
    humidity: 88,
    icon: "🌧️",
    description: "Rain expected in the afternoon, bring an umbrella",
  },
  {
    day: 4,
    date: "2026-06-17",
    condition: "cloudy",
    tempHigh: 30,
    tempLow: 24,
    humidity: 75,
    icon: "☁️",
    description: "Overcast but dry, good for temple visits",
  },
  {
    day: 5,
    date: "2026-06-18",
    condition: "sunny",
    tempHigh: 35,
    tempLow: 27,
    humidity: 60,
    icon: "☀️",
    description: "Hot and sunny, stay hydrated",
  },
]

/** Get weather for a specific day (1-based) */
export const getWeatherForDay = (day: number): DayWeather | undefined =>
  MOCK_WEATHER.find((w) => w.day === day)

/** Weather icon map for UI */
export const WEATHER_ICONS: Record<WeatherCondition, string> = {
  sunny: "☀️",
  partly_cloudy: "⛅",
  cloudy: "☁️",
  rainy: "🌧️",
  stormy: "⛈️",
  windy: "💨",
}
