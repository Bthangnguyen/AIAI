import type { PlanMetrics } from "@/types/plan"

export function diversityTone(score: number): "good" | "mid" | "low" {
  if (score >= 0.7) return "good"
  if (score >= 0.5) return "mid"
  return "low"
}

export function diversityPercent(score: number): string {
  return `${Math.round(score * 100)}%`
}

export function fatiguePercent(score: number): number {
  return Math.round(Math.min(1, Math.max(0, score)) * 100)
}

export function warningLabels(metrics: PlanMetrics): string[] {
  const labels: string[] = []
  if (metrics.warnings.meal) labels.push("Thiếu bữa trưa")
  if (metrics.warnings.outdoor_heat) labels.push("Nắng nóng ngoài trời")
  if (metrics.warnings.budget) labels.push("Vượt / sát ngân sách")
  return labels
}

export function warningTooltip(metrics: PlanMetrics): string | undefined {
  if (metrics.validationMessages?.length) {
    return metrics.validationMessages.join("\n")
  }
  const labels = warningLabels(metrics)
  return labels.length ? labels.join(" · ") : undefined
}
