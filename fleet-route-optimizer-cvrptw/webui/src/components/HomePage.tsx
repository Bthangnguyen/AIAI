"use client"

import { Circle, Compass, MapPinned, Route, Sparkles } from "lucide-react"
import Link from "next/link"
import { useEffect, useState } from "react"
import { BuildProgressSteps } from "@/components/BuildProgressSteps"
import { ExamplePromptChips } from "@/components/ExamplePromptChips"
import { HomePromptBox } from "@/components/HomePromptBox"
import type { BuilderMode } from "@/types/trip"

interface HomePageProps {
  prompt: string
  mode: BuilderMode
  isLoading: boolean
  progressStep: number
  onPromptChange: (value: string) => void
  onModeChange: (mode: BuilderMode) => void
  onSubmit: () => void
  onAuthClick: () => void
  onNav: (target: "demo" | "saved" | "mobile") => void
}

const examples = [
  "Huế 3 ngày, ngân sách 1 triệu",
  "Đại Nội, cafe muối, ăn chay",
  "Food tour Huế cuối tuần",
  "Đi nhẹ nhàng cùng gia đình",
]

const dynamicLines = [
  "Hiểu nhu cầu bằng tiếng Việt",
  "Lọc địa điểm Huế theo sở thích",
  "Cân ngân sách và thời lượng mỗi ngày",
  "Đặt POI lên bản đồ OpenStreetMap",
  "Tạo timeline nháp có thể chỉnh sửa",
]

const sceneImages = [
  "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=2200&q=80",
  "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=2200&q=80",
  "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=2200&q=80",
  "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=2200&q=80",
]

export function HomePage({ prompt, mode, isLoading, progressStep, onPromptChange, onModeChange, onSubmit, onAuthClick, onNav }: HomePageProps) {
  const [activeLine, setActiveLine] = useState(0)
  const [activeScene, setActiveScene] = useState(0)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveLine((value) => (value + 1) % dynamicLines.length)
    }, 2200)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActiveScene((value) => (value + 1) % sceneImages.length)
    }, 5200)
    return () => window.clearInterval(timer)
  }, [])

  function fillRandomExample() {
    onPromptChange(examples[Math.floor(Math.random() * examples.length)])
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#fff7ed] text-[#1f1308]">
      {sceneImages.map((image, index) => (
        <div
          key={image}
          className={`absolute inset-0 bg-cover bg-center transition-opacity duration-1000 ${activeScene === index ? "opacity-100" : "opacity-0"}`}
          style={{ backgroundImage: `url(${image})` }}
          aria-hidden="true"
        />
      ))}
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(255,247,237,0.94)_0%,rgba(255,247,237,0.82)_48%,rgba(255,255,255,0.48)_100%)]" aria-hidden="true" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_24%_18%,rgba(249,115,22,0.24),transparent_30rem)]" aria-hidden="true" />

      <header className="relative z-10 border-b border-orange-200/70 bg-white/60 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-6">
          <button type="button" onClick={() => onNav("demo")} className="flex items-center gap-2 text-2xl font-black tracking-tight text-orange-950">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-orange-500 text-white shadow-lg shadow-orange-500/25">
              <Circle className="h-3.5 w-3.5 fill-current" />
            </span>
            <span className="text-[34px] leading-none">TripFlow</span>
          </button>
          <nav className="hidden items-center gap-8 text-sm font-bold text-orange-950/65 md:flex">
            <button type="button" onClick={() => onNav("demo")} className="transition hover:text-orange-600">Demo</button>
            <button type="button" onClick={() => onNav("saved")} className="transition hover:text-orange-600">Saved Trips</button>
            <button type="button" onClick={() => onNav("mobile")} className="transition hover:text-orange-600">Mobile Phase</button>
            <Link href="/admin" className="transition hover:text-orange-600">Admin</Link>
          </nav>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onAuthClick} className="hidden rounded-full border border-orange-200 bg-white/70 px-4 py-2 text-sm font-black text-orange-950 transition hover:border-orange-400 sm:inline-flex">
              Login
            </button>
            <button type="button" onClick={onAuthClick} className="rounded-full bg-orange-500 px-4 py-2 text-sm font-black text-white shadow-lg shadow-orange-500/25 transition hover:bg-orange-600">
              Sign up
            </button>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto w-full max-w-6xl px-6 pb-16 pt-12 sm:pt-16">
        <section className="mx-auto max-w-4xl text-center">
          <p className="mb-5 inline-flex rounded-full bg-white/80 px-4 py-2 text-xs font-black uppercase tracking-[0.28em] text-orange-600 shadow-lg shadow-orange-950/5">AI travel builder</p>
          <h1 className="text-5xl font-black tracking-tight text-orange-950 sm:text-7xl">Build your trip in minutes.</h1>
          <h2 className="mt-3 text-3xl font-black tracking-tight text-orange-700 sm:text-4xl">Tạo lịch trình du lịch trong vài phút.</h2>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-orange-950/72 sm:text-xl">
            Mô tả chuyến đi bằng tiếng Việt. TripFlow AI sẽ tạo lịch trình nháp theo ngày, ngân sách và sở thích của bạn.
          </p>

          <div className="mx-auto mt-7 flex max-w-fit flex-wrap items-center gap-3 rounded-full border border-orange-200 bg-white/80 px-4 py-2 text-sm shadow-2xl shadow-orange-950/10 backdrop-blur">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-orange-500 text-white">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <span className="text-orange-950/65">TripFlow đang</span>
            <span key={dynamicLines[activeLine]} className="dynamic-hero-text font-black text-orange-700">
              {dynamicLines[activeLine]}
            </span>
            <span className="h-4 w-px animate-pulse bg-orange-500" aria-hidden="true" />
          </div>

          <HomePromptBox
            prompt={prompt}
            mode={mode}
            isLoading={isLoading}
            onPromptChange={onPromptChange}
            onModeChange={onModeChange}
            onSubmit={onSubmit}
            onExample={fillRandomExample}
          />
          <ExamplePromptChips onPick={onPromptChange} />
          {isLoading ? <BuildProgressSteps activeIndex={progressStep} /> : null}
        </section>

        <section className="mt-10 grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="rounded-[32px] border border-orange-200 bg-white/82 p-6 shadow-2xl shadow-orange-950/10 backdrop-blur-xl">
            <p className="text-xs font-black uppercase tracking-[0.22em] text-orange-500">Mô tả dự án</p>
            <h3 className="mt-3 text-2xl font-black text-orange-950">TripFlow AI là MVP lập lịch trình du lịch có bản đồ trực quan.</h3>
            <p className="mt-3 text-sm leading-7 text-orange-950/70">
              Dự án mô phỏng trải nghiệm “AI travel builder”: người dùng nhập nhu cầu, hệ thống hỏi bổ sung thông tin còn thiếu, tạo lịch trình nháp theo ngày, hiển thị POI trên OpenStreetMap, cho phép thêm/xóa địa điểm, undo và lưu bản nháp bằng localStorage.
            </p>
          </article>
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            {[
              { icon: Compass, title: "Intent", text: "Nhận diện điểm đến, số ngày, ngân sách và sở thích." },
              { icon: Route, title: "Timeline", text: "Tạo lịch trình ngày-by-ngày với chi phí và thời lượng." },
              { icon: MapPinned, title: "OSM Preview", text: "Đặt marker mock và nối route line theo thứ tự POI." },
            ].map((item) => {
              const Icon = item.icon
              return (
                <article key={item.title} className="rounded-[24px] border border-orange-200 bg-white/78 p-4 shadow-xl shadow-orange-950/5 backdrop-blur-xl">
                  <div className="flex items-start gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-orange-100 text-orange-600"><Icon className="h-5 w-5" /></span>
                    <div>
                      <h4 className="font-black text-orange-950">{item.title}</h4>
                      <p className="mt-1 text-sm leading-6 text-orange-950/65">{item.text}</p>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        </section>
      </main>
    </div>
  )
}

