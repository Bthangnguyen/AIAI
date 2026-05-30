"use client"

import { X } from "lucide-react"

interface MockAuthModalProps {
  isOpen: boolean
  onClose: () => void
  onContinue: () => void
  configured?: boolean
  isLoading?: boolean
}

export function MockAuthModal({ isOpen, onClose, onContinue, configured = true, isLoading = false }: MockAuthModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center bg-orange-950/45 p-4 backdrop-blur-sm">
      <section className="w-full max-w-md rounded-[32px] border border-orange-200 bg-white p-6 text-orange-950 shadow-2xl shadow-orange-950/25">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.22em] text-orange-500">TripFlow account</p>
            <h2 className="mt-2 text-3xl font-black">Dang nhap de luu lich trinh</h2>
            <p className="mt-2 text-sm leading-6 text-orange-950/65">Su dung Google account. Draft se duoc luu rieng theo user trong Firestore.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-full bg-orange-50 p-2 text-orange-700 transition hover:bg-orange-100" aria-label="Đóng">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 grid gap-3">
          {configured ? (
            <button type="button" onClick={onContinue} disabled={isLoading} className="rounded-2xl bg-orange-500 px-4 py-3 text-sm font-black text-white shadow-lg shadow-orange-500/25 transition hover:bg-orange-600">
              {isLoading ? "Dang xu ly..." : "Tiep tuc voi Google"}
            </button>
          ) : (
            <button type="button" onClick={onContinue} disabled={isLoading} className="rounded-2xl bg-orange-500 px-4 py-3 text-sm font-black text-white shadow-lg shadow-orange-500/25 transition hover:bg-orange-600">
              {isLoading ? "Dang xu ly..." : "Dang nhap tai khoan Guest (Local Dev)"}
            </button>
          )}
          {!configured ? (
            <p className="rounded-2xl border border-orange-200 bg-orange-50 px-4 py-3 text-xs font-bold text-orange-700">
              Firebase chưa được cấu hình. Hệ thống sẽ sử dụng Tài khoản Guest local để chạy thử nghiệm đầy đủ tính năng.
            </p>
          ) : null}
        </div>

        <p className="mt-4 text-center text-xs text-orange-950/50">Login va signup deu dung Google provider.</p>
      </section>
    </div>
  )
}
