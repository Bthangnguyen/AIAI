"use client"

import { ArrowLeft, Lock, MapPin, Navigation, Route, SkipForward } from "lucide-react"

interface MobilePhasePageProps {
  onBack: () => void
}

const features = [
  { title: "Next Location", icon: MapPin, text: "Gợi ý điểm tiếp theo trong ngày." },
  { title: "Skip Stop", icon: SkipForward, text: "Bỏ qua một điểm đến khi kế hoạch thay đổi." },
  { title: "GPS Reroute", icon: Navigation, text: "Dùng vị trí mobile để mô phỏng reroute." },
  { title: "Reroute Current Day", icon: Route, text: "Tối ưu lại phần còn lại của ngày." },
]

export function MobilePhasePage({ onBack }: MobilePhasePageProps) {
  return (
    <div className="min-h-screen bg-orange-50 text-orange-950">
      <header className="border-b border-orange-200 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-6">
          <button type="button" onClick={onBack} className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-black text-orange-950/65 transition hover:bg-orange-100 hover:text-orange-700"><ArrowLeft className="h-4 w-4" />Back</button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-[36px] border border-orange-200 bg-white p-8 shadow-2xl shadow-orange-950/10">
          <div className="inline-flex items-center gap-2 rounded-full bg-orange-100 px-3 py-1 text-xs font-black text-orange-600"><Lock className="h-3.5 w-3.5" />Phase 2 · Mobile only</div>
          <h1 className="mt-5 text-4xl font-black tracking-tight text-orange-950">Active Trip Mode — Sắp ra mắt trên mobile</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-orange-950/65">Tính năng này dùng GPS trên app mobile để tối ưu lại phần còn lại của ngày khi người dùng bỏ qua một điểm đến. Đây chỉ là roadmap/demo UI, không triển khai GPS hoặc reroute thật.</p>
          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {features.map((feature) => {
              const Icon = feature.icon
              return (
                <article key={feature.title} className="rounded-[28px] border border-orange-200 bg-orange-50 p-5 opacity-90 shadow-xl shadow-orange-950/5">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-orange-600 shadow-lg shadow-orange-950/5"><Icon className="h-6 w-6" /></div>
                  <h2 className="mt-5 text-lg font-black text-orange-950">{feature.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-orange-950/62">{feature.text}</p>
                  <button type="button" disabled className="mt-5 w-full cursor-not-allowed rounded-2xl border border-orange-200 bg-white px-4 py-3 text-sm font-black text-orange-950/45">Locked</button>
                </article>
              )
            })}
          </div>
        </div>
      </main>
    </div>
  )
}
