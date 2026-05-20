"use client"

import { ArrowLeft, FolderOpen, Plus } from "lucide-react"
import { draftTotals } from "@/lib/mockItineraryFallback"
import { formatCurrency, formatDateTime } from "@/lib/format"
import type { ItineraryDraft } from "@/types/trip"

interface SavedTripsPageProps {
  drafts: ItineraryDraft[]
  onOpenDraft: (draft: ItineraryDraft) => void
  onCreateNew: () => void
  onBack: () => void
}

export function SavedTripsPage({ drafts, onOpenDraft, onCreateNew, onBack }: SavedTripsPageProps) {
  return (
    <div className="min-h-screen bg-orange-50 text-orange-950">
      <header className="border-b border-orange-200 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <button type="button" onClick={onBack} className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-black text-orange-950/65 transition hover:bg-orange-100 hover:text-orange-700"><ArrowLeft className="h-4 w-4" />Back</button>
          <button type="button" onClick={onCreateNew} className="inline-flex items-center gap-2 rounded-full bg-orange-500 px-4 py-2 text-sm font-black text-white shadow-lg shadow-orange-500/25"><Plus className="h-4 w-4" />Tạo lịch trình đầu tiên</button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="text-xs font-black uppercase tracking-[0.22em] text-orange-500">Saved workspace</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-orange-950">Lịch trình đã lưu</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-orange-950/65">Mở lại các bản nháp đã lưu trong localStorage. Không có cloud database, auth hoặc đồng bộ tài khoản.</p>

        {drafts.length === 0 ? (
          <section className="mt-10 flex min-h-[360px] items-center justify-center rounded-[32px] border border-dashed border-orange-300 bg-white/85 p-10 text-center shadow-2xl shadow-orange-950/10">
            <div>
              <FolderOpen className="mx-auto h-12 w-12 text-orange-400" />
              <h2 className="mt-4 text-2xl font-black text-orange-950">Chưa có lịch trình nào</h2>
              <p className="mt-2 text-sm text-orange-950/60">Tạo và lưu bản nháp đầu tiên để nó xuất hiện ở đây.</p>
              <button type="button" onClick={onCreateNew} className="mt-5 rounded-full bg-orange-500 px-5 py-3 text-sm font-black text-white shadow-lg shadow-orange-500/25">Tạo lịch trình đầu tiên</button>
            </div>
          </section>
        ) : (
          <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {drafts.map((draft) => {
              const totals = draftTotals(draft)
              return (
                <article key={draft.id} className="rounded-[28px] border border-orange-200 bg-white p-5 shadow-2xl shadow-orange-950/10 transition hover:-translate-y-1 hover:border-orange-400">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-2xl font-black text-orange-950">{draft.destination}</h2>
                      <p className="mt-1 text-sm text-orange-950/60">{draft.days.length} ngày · {totals.poiCount} địa điểm</p>
                    </div>
                    <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-black text-orange-600">Draft</span>
                  </div>
                  <div className="mt-4 grid gap-2 text-sm text-orange-950/62">
                    <span>Created: {formatDateTime(draft.createdAt)}</span>
                    <span>Updated: {formatDateTime(draft.updatedAt)}</span>
                    <span>Estimated cost: {formatCurrency(totals.estimatedCost)}</span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {(draft.tags.length ? draft.tags : ["balanced"]).slice(0, 4).map((tag) => <span key={tag} className="rounded-full bg-orange-100 px-3 py-1 text-xs font-bold text-orange-700">{tag}</span>)}
                  </div>
                  <button type="button" onClick={() => onOpenDraft(draft)} className="mt-5 w-full rounded-2xl bg-orange-500 px-4 py-3 text-sm font-black text-white transition hover:bg-orange-600">Mở lại</button>
                </article>
              )
            })}
          </section>
        )}
      </main>
    </div>
  )
}
