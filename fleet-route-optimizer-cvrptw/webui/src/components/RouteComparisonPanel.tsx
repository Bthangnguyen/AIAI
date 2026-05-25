"use client"

import { Check, Leaf, Scale, Wallet } from "lucide-react"
import { PlanMetricsGrid } from "@/components/PlanMetricsGrid"
import type { PlanStyle, PlanVariant } from "@/types/plan"
import { formatCurrency } from "@/lib/format"

interface RouteComparisonPanelProps {
  variants: PlanVariant[] | null
  loading: boolean
  error?: string | null
  selectedPlanStyle?: PlanStyle
  onApply?: (variant: PlanVariant) => void
}

const STYLE_META: Record<PlanStyle, { icon: typeof Scale; accent: string; border: string; bg: string }> = {
  balanced: {
    icon: Scale,
    accent: "text-green-700",
    border: "border-green-300",
    bg: "bg-green-50/60",
  },
  budget: {
    icon: Wallet,
    accent: "text-blue-700",
    border: "border-blue-300",
    bg: "bg-blue-50/60",
  },
  chill: {
    icon: Leaf,
    accent: "text-emerald-700",
    border: "border-emerald-300",
    bg: "bg-emerald-50/60",
  },
}

export function RouteComparisonPanel({ variants, loading, error, selectedPlanStyle, onApply }: RouteComparisonPanelProps) {
  if (loading) {
    return (
      <div className="mx-auto w-full max-w-6xl space-y-6">
        <CompareHeader />
        <div className="grid gap-4 md:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-orange-200 bg-white/80 p-5">
              <div className="h-5 w-28 rounded bg-orange-100" />
              <div className="mt-4 h-10 w-20 rounded bg-orange-100" />
              <div className="mt-4 space-y-2">
                <div className="h-3 w-full rounded bg-orange-50" />
                <div className="h-3 w-4/5 rounded bg-orange-50" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto w-full max-w-3xl rounded-2xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="font-black text-red-800">Không tải được phương án so sánh</p>
        <p className="mt-2 text-sm text-red-600">{error}</p>
      </div>
    )
  }

  if (!variants?.length) {
    return (
      <div className="mx-auto w-full max-w-3xl rounded-2xl border border-dashed border-orange-200 bg-white/80 p-8 text-center">
        <p className="font-black text-orange-950">Chưa có dữ liệu so sánh</p>
        <p className="mt-2 text-sm text-orange-950/60">Tạo lịch trình trước, sau đó quay lại tab Compare.</p>
      </div>
    )
  }

  const minPoiCount = Math.min(...variants.map((v) => v.metrics.poiCount))
  const minFatigue = Math.min(...variants.map((v) => v.metrics.fatigueScore))

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <CompareHeader />

      <div className="grid gap-4 md:grid-cols-3">
        {variants.map((variant) => {
          const meta = STYLE_META[variant.style]
          const Icon = meta.icon
          const isChillHighlight = variant.style === "chill" && variant.metrics.poiCount === minPoiCount
          const isApplied = selectedPlanStyle === variant.style
          const isLowestFatigue = variant.metrics.fatigueScore === minFatigue

          return (
            <article
              key={variant.style}
              className={`flex flex-col rounded-2xl border-2 p-5 ${meta.border} ${meta.bg} ${isChillHighlight ? "ring-2 ring-emerald-300/70" : ""} ${isApplied ? "ring-2 ring-orange-400" : ""}`}
            >
              <div className={`flex items-center gap-2 ${meta.accent}`}>
                <Icon className="h-5 w-5" />
                <h3 className="text-lg font-black">{variant.label}</h3>
                {isApplied ? (
                  <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-orange-500 px-2 py-0.5 text-[10px] font-black text-white">
                    <Check className="h-3 w-3" /> Đang dùng
                  </span>
                ) : null}
              </div>
              <p className="mt-1 text-xs text-orange-950/55">{variant.description}</p>

              <PlanMetricsGrid metrics={variant.metrics} />

              {isLowestFatigue && variant.style === "chill" ? (
                <p className="mt-2 text-[10px] font-bold text-emerald-700">Fatigue thấp nhất trong 3 phương án</p>
              ) : null}

              <div className="mt-3 space-y-1">
                {variant.days.flatMap((day) => day.items).slice(0, 4).map((item, i) => (
                  <div key={`${variant.style}-${item.id}`} className="flex items-center gap-2 text-xs text-orange-950/60">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/80 text-[10px] font-bold">{i + 1}</span>
                    <span className="truncate">{item.note || item.poiId}</span>
                  </div>
                ))}
                {variant.metrics.poiCount > 4 ? (
                  <p className="text-xs text-orange-400">+{variant.metrics.poiCount - 4} điểm · {formatCurrency(variant.metrics.totalCost)}</p>
                ) : null}
              </div>

              {variant.overlapWarning ? (
                <p className="mt-2 rounded-lg bg-amber-100/80 px-2 py-1 text-[10px] font-bold text-amber-800">{variant.overlapWarning}</p>
              ) : null}

              {onApply ? (
                <button
                  type="button"
                  onClick={() => onApply(variant)}
                  className="mt-4 w-full rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-black text-white shadow transition hover:bg-orange-600 disabled:opacity-50"
                  disabled={isApplied}
                >
                  {isApplied ? "Đã áp dụng" : "Áp dụng phương án này"}
                </button>
              ) : null}
            </article>
          )
        })}
      </div>
    </div>
  )
}

function CompareHeader() {
  return (
    <div className="text-center">
      <h2 className="text-2xl font-black text-orange-950">So sánh 3 phương án lộ trình</h2>
      <p className="mt-1 text-sm text-orange-950/60">8 chỉ số Validator · Cân bằng · Tiết kiệm · Thoải mái</p>
    </div>
  )
}
