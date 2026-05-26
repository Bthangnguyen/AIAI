import { getPoi } from "@/lib/mockItineraryFallback"
import type { ItineraryDay, POI } from "@/types/trip"

export interface RouteStats {
  totalDistanceKm: number
  orderedPois: POI[]
}

function haversineKm(a: POI, b: POI): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLng = toRad(b.lng - a.lng)
  const lat1 = toRad(a.lat)
  const lat2 = toRad(b.lat)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2
  return 6371 * 2 * Math.asin(Math.sqrt(h))
}

function routeDistance(pois: POI[]): number {
  if (pois.length < 2) return 0
  let total = 0
  for (let i = 1; i < pois.length; i += 1) {
    total += haversineKm(pois[i - 1], pois[i])
  }
  return Math.round(total * 10) / 10
}

function collectPois(days: ItineraryDay[]): POI[] {
  return days
    .flatMap((day) => day.items.map((item) => getPoi(item.poiId)))
    .filter((poi): poi is POI => Boolean(poi))
}

export function getOptimizedRoute(days: ItineraryDay[]): RouteStats {
  const orderedPois = collectPois(days)
  return {
    totalDistanceKm: routeDistance(orderedPois),
    orderedPois,
  }
}

export function getRandomRoute(days: ItineraryDay[]): RouteStats {
  const pois = collectPois(days)
  const shuffled = [...pois].sort(() => Math.random() - 0.5)
  return {
    totalDistanceKm: routeDistance(shuffled),
    orderedPois: shuffled,
  }
}
