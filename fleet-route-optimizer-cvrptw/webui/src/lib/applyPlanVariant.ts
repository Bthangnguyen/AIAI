import type { ItineraryDraft } from "@/types/trip"
import type { PlanStyle, PlanVariant } from "@/types/plan"

export function applyPlanVariant(draft: ItineraryDraft, variant: PlanVariant): ItineraryDraft {
  return {
    ...draft,
    days: variant.days.map((day) => ({
      ...day,
      items: day.items.map((item) => ({ ...item })),
    })),
    updatedAt: new Date().toISOString(),
    selectedPlanStyle: variant.style,
  }
}

export function planStyleLabel(style: PlanStyle): string {
  const labels: Record<PlanStyle, string> = {
    balanced: "Cân bằng",
    budget: "Tiết kiệm",
    chill: "Thoải mái",
  }
  return labels[style]
}
