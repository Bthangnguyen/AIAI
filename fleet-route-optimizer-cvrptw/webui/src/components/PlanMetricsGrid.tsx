"use client"

import { AlertTriangle, CloudSun, UtensilsCrossed } from "lucide-react"
import type { PlanMetrics } from "@/types/plan"
import { formatCurrency } from "@/lib/format"
import { diversityPercent, diversityTone, fatiguePercent, warningTooltip } from "@/lib/planMetricsDisplay"

interface PlanMetricsGridProps {
  metrics: PlanMetrics
}

export function PlanMetricsGrid({ metrics }: PlanMetricsGridProps) {
  const diversityClass =
    diversityTone(metrics.diversityScore) === "good"
      ? "text-green-700"
      : diversityTone(metrics.diversityScore) === "mid"
        ? "text-amber-700"
        : "text-red-600"

  const tooltip = warningTooltip(metrics)

  return (
    <div className="mt-4 space-y-3">
      <div className="grid grid-cols-2 gap-2 text-sm">
        <MetricCell label="Tổng chi phí" value={formatCurrency(metrics.totalCost)} />
        <MetricCell label="Thời gian di chuyển" value={formatTravel(metrics.totalTravelMin)} />
        <MetricCell label="Tổng số POI" value={`${metrics.poiCount}`} />
        <MetricCell label="Quãng đường" value={`${metrics.totalDistanceKm} km`} />
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between text-[10px] font-bold uppercase tracking-wide text-orange-950/45">
          <span>Fatigue</span>
          <span>{fatiguePercent(metrics.fatigueScore)}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-white/80">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-orange-500 transition-all"
            style={{ width: `${fatiguePercent(metrics.fatigueScore)}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold uppercase tracking-wide text-orange-950/45">Diversity</span>
        <span className={`text-sm font-black ${diversityClass}`}>{diversityPercent(metrics.diversityScore)}</span>
      </div>

      <div className="flex flex-wrap gap-1.5" title={tooltip}>
        <WarningBadge
          active={metrics.warnings.meal}
          tone="amber"
          icon={<UtensilsCrossed className="h-3 w-3" />}
          label="Meal"
          activeLabel="Thiếu bữa trưa"
        />
        <WarningBadge
          active={metrics.warnings.outdoor_heat}
          tone="orange"
          icon={<CloudSun className="h-3 w-3" />}
          label="Outdoor heat"
          activeLabel="Nắng nóng"
        />
        <WarningBadge
          active={metrics.warnings.budget}
          tone="red"
          icon={<AlertTriangle className="h-3 w-3" />}
          label="Budget OK"
          activeLabel="Ngân sách"
        />
      </div>
    </div>
  )
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/60 px-2 py-1.5">
      <p className="text-[10px] font-bold uppercase tracking-wide text-orange-950/45">{label}</p>
      <p className="font-black text-orange-950">{value}</p>
    </div>
  )
}

function WarningBadge({
  active,
  tone,
  icon,
  label,
  activeLabel,
}: {
  active: boolean
  tone: "amber" | "orange" | "red"
  icon: React.ReactNode
  label: string
  activeLabel: string
}) {
  const activeStyles = {
    amber: "border-amber-300 bg-amber-100 text-amber-900",
    orange: "border-orange-300 bg-orange-100 text-orange-900",
    red: "border-red-300 bg-red-100 text-red-900",
  }[tone]

  const idleStyle = "border-orange-200/80 bg-white/50 text-orange-950/35"

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-bold ${active ? activeStyles : idleStyle}`}
    >
      {icon}
      {active ? activeLabel : label}
    </span>
  )
}

function formatTravel(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `${m} phút`
  return `${h}h ${m}m`
}
