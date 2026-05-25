import type { ReRouteResult } from "@/lib/api"

export type ReRouteOutcome = "success" | "warning" | "infeasible" | "error"

export interface InterpretedReRoute {
  outcome: ReRouteOutcome
  message: string
  day?: ReRouteResult["day"]
}

export function interpretReRoute(result: ReRouteResult): InterpretedReRoute {
  const stops =
    result.day?.stops?.filter((stop) => !stop.poi_id?.startsWith("hotel_day_")) ?? []

  if (result.status === "error") {
    return {
      outcome: "error",
      message: result.message ?? "Lỗi re-route.",
    }
  }

  if (result.status === "success" || result.status === "optimized_with_warning") {
    if (stops.length === 0) {
      return {
        outcome: "infeasible",
        message: "Không thể xếp thêm — thử bớt điểm hoặc tăng thời gian trong ngày.",
      }
    }
    if (result.status === "optimized_with_warning") {
      return {
        outcome: "warning",
        message: result.message ?? "Lịch trình tối ưu một phần — xem ghi chú trước khi áp dụng.",
        day: result.day,
      }
    }
    return {
      outcome: "success",
      message: result.message ?? "Đã tối ưu lại lịch trình.",
      day: result.day,
    }
  }

  if (result.status === "infeasible" || !result.day) {
    return {
      outcome: "infeasible",
      message: result.message ?? "Không thể thêm điểm này vào lịch trình (hết thời gian).",
    }
  }

  return {
    outcome: "error",
    message: result.message ?? "Lỗi re-route.",
  }
}
