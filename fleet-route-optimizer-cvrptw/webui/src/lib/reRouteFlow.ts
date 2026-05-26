import { interpretReRoute } from "@/lib/reroute"
import { reRouteStopsToItems } from "@/lib/rerouteHelpers"
import type { ReRouteResult } from "@/lib/api"
import type { ItineraryItem } from "@/types/trip"

export type ReRouteToastVariant = "success" | "warning" | "error"

export type ProcessReRouteSuccess = {
  ok: true
  items: ItineraryItem[]
  toastVariant: ReRouteToastVariant
  message: string
}

export type ProcessReRouteFailure = {
  ok: false
  toastVariant: ReRouteToastVariant
  message: string
}

export type ProcessReRouteResult = ProcessReRouteSuccess | ProcessReRouteFailure

export function processReRouteResult(dayIndex: number, result: ReRouteResult): ProcessReRouteResult {
  const interpreted = interpretReRoute(result)

  if (interpreted.outcome === "infeasible" || interpreted.outcome === "error" || !interpreted.day) {
    return {
      ok: false,
      toastVariant: interpreted.outcome === "error" ? "error" : "warning",
      message: interpreted.message,
    }
  }

  return {
    ok: true,
    items: reRouteStopsToItems(dayIndex, interpreted.day),
    toastVariant: interpreted.outcome === "warning" ? "warning" : "success",
    message: interpreted.message,
  }
}
