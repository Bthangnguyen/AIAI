/**
 * Feature flags — toggle mock vs real backend.
 * Set USE_MOCK_BACKEND = false and configure travel.env to use real APIs.
 */
export const FeatureFlags = {
  /** When true, all API calls return mock data (no network required). */
  USE_MOCK_BACKEND: true,
  /** Enable/disable local push notifications during demo flow. */
  ENABLE_PUSH_NOTIFICATIONS: true,
  /** Enable share trip sheet. */
  ENABLE_SHARE: false,
  /** Enable re-route flow (requires L4 solver). */
  ENABLE_REROUTE: true,
} as const

export type FeatureFlagKey = keyof typeof FeatureFlags
