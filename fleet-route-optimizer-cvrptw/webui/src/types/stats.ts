export interface OptimizationStats {
  totalDistanceKm: number
  customersServed: number
  totalPoisAvailable: number
  totalLoadUsed: number
  totalLoadCapacity: number
  saturationPercent: number
  vehiclesUsed: number
  totalVehicles: number
  budgetUsed: number
  budgetMax: number
  avgTravelTimePerVehicleMin: number
  avgTotalTimePerVehicleMin: number
  solverTimeSeconds: number
}
