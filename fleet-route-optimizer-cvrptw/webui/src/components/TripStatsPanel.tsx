"use client"

import { useEffect, useState } from "react"
import { Activity, Clock, MapPin, Route, Target, Wallet } from "lucide-react"
import type { OptimizationStats } from "@/types/stats"

interface TripStatsPanelProps {
  stats: OptimizationStats
}

function AnimatedNumber({ value, suffix = "", decimals = 0 }: { value: number; suffix?: string; decimals?: number }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    const duration = 1200
    const steps = 40
    const increment = value / steps
    let current = 0
    let step = 0
    const timer = setInterval(() => {
      step++
      current = Math.min(current + increment, value)
      setDisplay(current)
      if (step >= steps) clearInterval(timer)
    }, duration / steps)
    return () => clearInterval(timer)
  }, [value])
  return <span>{display.toFixed(decimals)}{suffix}</span>
}

function StatCard({ icon: Icon, label, children, accent = false }: { icon: any; label: string; children: React.ReactNode; accent?: boolean }) {
  return (
    <div className={`rounded-2xl border p-4 ${accent ? "border-orange-400 bg-orange-50" : "border-orange-200 bg-white"}`}>
      <div className="flex items-center gap-2 text-orange-500">
        <Icon className="h-4 w-4" />
        <span className="text-[10px] font-black uppercase tracking-[0.16em]">{label}</span>
      </div>
      <div className="mt-2 text-2xl font-black text-orange-950">{children}</div>
    </div>
  )
}

function ProgressBar({ value, max, color = "bg-orange-500" }: { value: number; max: number; color?: string }) {
  const percent = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-orange-100">
      <div className={`h-full rounded-full transition-all duration-1000 ease-out ${color}`} style={{ width: `${percent}%` }} />
    </div>
  )
}

export function TripStatsPanel({ stats }: TripStatsPanelProps) {
  return (
    <div className="rounded-2xl border border-orange-300 bg-gradient-to-br from-orange-50 to-white p-5 shadow-lg">
      <div className="mb-4 flex items-center gap-2">
        <Activity className="h-5 w-5 text-orange-600" />
        <h3 className="text-sm font-black text-orange-950">Thống kê Tối ưu hóa OR-Tools</h3>
        <span className="ml-auto rounded-full bg-green-100 px-2.5 py-0.5 text-[10px] font-bold text-green-700">
          Tối ưu {stats.saturationPercent}%
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Route} label="Tổng quãng đường">
          <AnimatedNumber value={stats.totalDistanceKm} suffix=" km" decimals={1} />
        </StatCard>
        <StatCard icon={MapPin} label="Địa điểm phục vụ">
          <AnimatedNumber value={stats.customersServed} />
          <span className="text-sm font-bold text-orange-400">/{stats.totalPoisAvailable}</span>
        </StatCard>
        <StatCard icon={Wallet} label="Chi phí ước tính" accent>
          <AnimatedNumber value={stats.budgetUsed} />
          <span className="text-sm font-bold text-orange-500">đ</span>
          {stats.budgetMax > 0 ? <ProgressBar value={stats.budgetUsed} max={stats.budgetMax} /> : null}
        </StatCard>
        <StatCard icon={Clock} label="Thời gian/ngày">
          <AnimatedNumber value={Math.floor(stats.avgTotalTimePerVehicleMin / 60)} suffix="h" />
          <span className="ml-1 text-sm font-bold text-orange-500">
            <AnimatedNumber value={stats.avgTotalTimePerVehicleMin % 60} suffix="m" />
          </span>
        </StatCard>
      </div>
      <div className="mt-3 flex items-center gap-4 rounded-xl bg-white/80 px-4 py-2.5 text-xs text-orange-950/60">
        <span>🔋 Bão hòa: <b className="text-orange-700">{stats.saturationPercent}%</b></span>
        <span>⏱️ Solver: <b className="text-orange-700">{stats.solverTimeSeconds}s</b></span>
        <span>🚗 Ngày: <b className="text-orange-700">{stats.vehiclesUsed}/{stats.totalVehicles}</b></span>
        <Target className="ml-auto h-3.5 w-3.5 text-green-500" />
      </div>
    </div>
  )
}
