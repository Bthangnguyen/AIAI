"use client"

import Link from "next/link"
import { useAuth } from "@/lib/auth"

function adminEmails(): string[] {
  return (process.env.NEXT_PUBLIC_ADMIN_EMAILS ?? "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean)
}

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, loading, configured, signInWithGoogle, signOut } = useAuth()
  const allowedEmails = adminEmails()
  const email = user?.email?.toLowerCase() ?? ""
  const isAllowed = !!email && allowedEmails.includes(email)

  if (loading) {
    return <AdminShell><p className="text-sm font-bold text-orange-950/65">Checking admin session...</p></AdminShell>
  }

  if (!configured) {
    return (
      <AdminShell>
        <h1 className="text-2xl font-black">Admin is locked</h1>
        <p className="mt-2 text-sm text-orange-950/65">Firebase env is not configured for this build.</p>
      </AdminShell>
    )
  }

  if (!user) {
    return (
      <AdminShell>
        <h1 className="text-2xl font-black">Admin login</h1>
        <p className="mt-2 text-sm text-orange-950/65">Sign in with an allowed Google account.</p>
        <button type="button" onClick={() => void signInWithGoogle()} className="mt-5 rounded-xl bg-orange-500 px-4 py-2 text-sm font-black text-white">Continue with Google</button>
      </AdminShell>
    )
  }

  if (!isAllowed) {
    return (
      <AdminShell>
        <h1 className="text-2xl font-black">No admin access</h1>
        <p className="mt-2 text-sm text-orange-950/65">{user.email} is not in NEXT_PUBLIC_ADMIN_EMAILS.</p>
        <button type="button" onClick={() => void signOut()} className="mt-5 rounded-xl border border-orange-200 bg-white px-4 py-2 text-sm font-black text-orange-700">Sign out</button>
      </AdminShell>
    )
  }

  return <>{children}</>
}

function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-orange-50 p-6 text-orange-950">
      <section className="w-full max-w-md rounded-2xl border border-orange-200 bg-white p-6 shadow-xl shadow-orange-950/10">
        {children}
        <Link href="/" className="mt-5 inline-flex text-sm font-black text-orange-700">Back to TripFlow</Link>
      </section>
    </div>
  )
}
