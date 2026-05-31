"use client"

import { useState } from "react"
import { X, Mail, Lock, User, ArrowRight, Sparkles } from "lucide-react"
import { useAuth } from "@/lib/auth"

interface MockAuthModalProps {
  isOpen: boolean
  onClose: () => void
  onContinue: () => void
  configured?: boolean
  isLoading?: boolean
}

type AuthTab = "signin" | "signup" | "forgot"

export function MockAuthModal({ isOpen, onClose, onContinue, configured = true, isLoading: parentLoading = false }: MockAuthModalProps) {
  const { signInWithGoogle, signInWithEmail, signUpWithEmail, sendPasswordReset, signInAsGuest } = useAuth()
  
  const [tab, setTab] = useState<AuthTab>("signin")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [name, setName] = useState("")
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const activeLoading = loading || parentLoading

  if (!isOpen) return null

  const handleGoogleLogin = async () => {
    setError(null)
    setLoading(true)
    try {
      const u = await signInWithGoogle()
      if (u) {
        onContinue()
      }
    } catch (err: any) {
      setError(err?.message || "Đăng nhập Google thất bại.")
    } finally {
      setLoading(false)
    }
  }

  const handleGuestLogin = async () => {
    setError(null)
    setLoading(true)
    try {
      const u = await signInAsGuest()
      if (u) {
        onContinue()
      }
    } catch (err: any) {
      setError(err?.message || "Không thể vào chế độ khách.")
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccessMessage(null)

    if (!email.trim()) {
      setError("Vui lòng nhập Email.")
      return
    }

    setLoading(true)
    try {
      if (tab === "signin") {
        if (!password) {
          setError("Vui lòng nhập Mật khẩu.")
          setLoading(false)
          return
        }
        const u = await signInWithEmail(email, password)
        if (u) {
          onContinue()
        }
      } else if (tab === "signup") {
        if (!name.trim()) {
          setError("Vui lòng nhập Họ và tên.")
          setLoading(false)
          return
        }
        if (password.length < 6) {
          setError("Mật khẩu phải chứa ít nhất 6 ký tự.")
          setLoading(false)
          return
        }
        const u = await signUpWithEmail(email, password, name)
        if (u) {
          onContinue()
        }
      } else if (tab === "forgot") {
        await sendPasswordReset(email)
        setSuccessMessage("Một liên kết khôi phục mật khẩu đã được gửi đến Email của anh!")
      }
    } catch (err: any) {
      console.error(err)
      setError(err?.message || "Có lỗi xảy ra, vui lòng thử lại.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[1200] flex items-center justify-center bg-orange-950/50 p-4 backdrop-blur-sm">
      <section className="w-full max-w-md rounded-[32px] border border-orange-200 bg-white p-6 text-orange-950 shadow-2xl shadow-orange-950/25 flex flex-col relative overflow-hidden">
        {/* Glow decoration */}
        <div className="absolute -top-12 -right-12 w-32 h-32 bg-orange-200/40 rounded-full blur-2xl pointer-events-none" />

        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-5 top-5 rounded-full bg-orange-50 p-2 text-orange-700 transition hover:bg-orange-100"
          aria-label="Đóng"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Header Title */}
        <div className="mb-5">
          <div className="flex items-center gap-1.5 text-xs font-black uppercase tracking-[0.22em] text-orange-600">
            <Sparkles className="h-3.5 w-3.5" />
            <span>TripFlow Account</span>
          </div>
          <h2 className="mt-2 text-2xl font-black leading-tight">
            {tab === "signin" && "Chào mừng anh quay lại"}
            {tab === "signup" && "Khởi hành cùng TripFlow"}
            {tab === "forgot" && "Khôi phục mật khẩu"}
          </h2>
          <p className="mt-1.5 text-xs leading-5 text-orange-950/60">
            {tab === "signin" && "Đăng nhập để lưu trữ lịch trình và đồng bộ hành trình thông minh."}
            {tab === "signup" && "Đăng ký tài khoản để bắt đầu thiết kế các chuyến đi thấu cảm."}
            {tab === "forgot" && "Nhập email của anh để nhận liên kết đặt lại mật khẩu mới."}
          </p>
        </div>

        {/* Quick Guest Bypass (MVP Focus!) */}
        {tab !== "forgot" && (
          <button
            type="button"
            onClick={handleGuestLogin}
            disabled={activeLoading}
            className="mb-5 flex items-center justify-center gap-2 w-full rounded-2xl bg-orange-50 border border-orange-200 px-4 py-3.5 text-xs font-black text-orange-950 transition hover:bg-orange-100 active:scale-[0.98]"
          >
            👤 Vào nhanh với vai trò Khách (Guest Mode)
          </button>
        )}

        {/* Separator */}
        {tab !== "forgot" && (
          <div className="flex items-center gap-2 mb-4 text-[10px] font-black uppercase text-orange-950/40 tracking-wider">
            <div className="h-[1px] bg-orange-100 flex-1" />
            <span>Hoặc sử dụng tài khoản</span>
            <div className="h-[1px] bg-orange-100 flex-1" />
          </div>
        )}

        {/* Auth Tabs */}
        {tab !== "forgot" && (
          <div className="flex bg-orange-50 p-1 rounded-xl mb-4 text-xs font-bold shrink-0">
            <button
              type="button"
              onClick={() => { setTab("signin"); setError(null); }}
              className={`flex-1 py-2 text-center rounded-lg transition ${tab === "signin" ? "bg-white text-orange-950 shadow-sm" : "text-orange-950/60 hover:text-orange-950"}`}
            >
              Đăng nhập
            </button>
            <button
              type="button"
              onClick={() => { setTab("signup"); setError(null); }}
              className={`flex-1 py-2 text-center rounded-lg transition ${tab === "signup" ? "bg-white text-orange-950 shadow-sm" : "text-orange-950/60 hover:text-orange-950"}`}
            >
              Đăng ký Email
            </button>
          </div>
        )}

        {/* Form Alerts */}
        {error && (
          <div className="mb-4 rounded-xl bg-red-50 border border-red-200 px-3.5 py-2.5 text-xs font-bold text-red-600">
            ⚠️ {error}
          </div>
        )}

        {successMessage && (
          <div className="mb-4 rounded-xl bg-green-50 border border-green-200 px-3.5 py-2.5 text-xs font-bold text-green-700">
            ✅ {successMessage}
          </div>
        )}

        {/* Main Auth Form */}
        <form onSubmit={handleSubmit} className="grid gap-3.5">
          {tab === "signup" && (
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-orange-400" />
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Họ và tên của anh"
                className="w-full rounded-2xl border border-orange-200 bg-white pl-10 pr-4 py-3 text-xs font-semibold text-orange-950 outline-none transition focus:border-orange-400 focus:bg-orange-50/10"
                required
              />
            </div>
          )}

          <div className="relative">
            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-orange-400" />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Địa chỉ Email"
              className="w-full rounded-2xl border border-orange-200 bg-white pl-10 pr-4 py-3 text-xs font-semibold text-orange-950 outline-none transition focus:border-orange-400 focus:bg-orange-50/10"
              required
            />
          </div>

          {tab !== "forgot" && (
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-orange-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mật khẩu"
                className="w-full rounded-2xl border border-orange-200 bg-white pl-10 pr-4 py-3 text-xs font-semibold text-orange-950 outline-none transition focus:border-orange-400 focus:bg-orange-50/10"
                required
              />
            </div>
          )}

          {tab === "signin" && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => { setTab("forgot"); setError(null); }}
                className="text-[11px] font-black text-orange-600 hover:underline"
              >
                Quên mật khẩu?
              </button>
            </div>
          )}

          <button
            type="submit"
            disabled={activeLoading}
            className="mt-2 flex items-center justify-center gap-2 w-full rounded-2xl bg-orange-600 px-4 py-3 text-xs font-black text-white shadow-lg shadow-orange-600/20 transition hover:bg-orange-700 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
          >
            {activeLoading ? (
              <span className="h-4.5 w-4.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            ) : (
              <>
                {tab === "signin" && "Đăng nhập"}
                {tab === "signup" && "Đăng ký tài khoản mới"}
                {tab === "forgot" && "Gửi yêu cầu khôi phục"}
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>

        {/* Forgot password go back */}
        {tab === "forgot" && (
          <button
            type="button"
            onClick={() => { setTab("signin"); setError(null); setSuccessMessage(null); }}
            className="mt-4 text-center text-xs font-black text-orange-600 hover:underline"
          >
            Quay lại Đăng nhập
          </button>
        )}

        {/* SSO Social Logins */}
        {tab !== "forgot" && (
          <>
            <div className="flex items-center gap-2 my-4 text-[10px] font-black uppercase text-orange-950/40 tracking-wider shrink-0">
              <div className="h-[1px] bg-orange-100 flex-1" />
              <span>Hoặc liên kết nhanh</span>
              <div className="h-[1px] bg-orange-100 flex-1" />
            </div>

            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={activeLoading}
              className="flex items-center justify-center gap-2 w-full rounded-2xl bg-white border border-orange-200 px-4 py-3 text-xs font-black text-orange-950 hover:bg-orange-50 transition active:scale-[0.98]"
            >
              <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24">
                <path fill="#EA4335" d="M12.24 10.285V14.4h6.887c-.648 2.41-2.519 4.114-5.136 4.114A5.99 5.99 0 0 1 8 12.527a5.99 5.99 0 0 1 5.99-5.99 5.86 5.86 0 0 1 4.027 1.583l3.08-3.08A9.87 9.87 0 0 0 13.99 2 9.99 9.99 0 0 0 4 12a9.99 9.99 0 0 0 9.99 10c5.38 0 9.87-4.22 9.87-10 0-.677-.078-1.32-.198-1.715H12.24Z" />
              </svg>
              Đăng nhập với Google
            </button>
          </>
        )}

        {!configured && (
          <p className="mt-4 rounded-xl border border-orange-100 bg-orange-50/50 p-3 text-[10px] leading-relaxed font-semibold text-orange-700/80">
            ℹ️ Firebase chưa được cấu hình ở môi trường hiện tại. Hệ thống sẽ tự động giả lập Đăng nhập & Đăng ký thành công để anh trải nghiệm tức thì.
          </p>
        )}
      </section>
    </div>
  )
}
