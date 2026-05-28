import Link from "next/link"
import { AdminGuard } from "@/components/AdminGuard"

const navItems = [
  { href: "/admin/pois", label: "POI" },
  { href: "/admin/qa", label: "QA" },
]

export default function AdminLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <AdminGuard>
      <div className="flex min-h-screen bg-[#fff7ed] text-orange-950">
      <aside className="flex w-56 shrink-0 flex-col border-r border-orange-200 bg-white">
        <div className="border-b border-orange-200 px-4 py-5">
          <p className="text-xs font-black uppercase tracking-[0.2em] text-orange-400">Admin</p>
          <h1 className="mt-1 text-lg font-black">TripFlow QA</h1>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-xl px-3 py-2.5 text-sm font-bold text-orange-950/70 transition hover:bg-orange-50 hover:text-orange-950"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-auto border-t border-orange-200 p-3">
          <Link
            href="/"
            className="inline-flex w-full items-center justify-center rounded-xl border border-orange-200 bg-orange-50 px-3 py-2.5 text-sm font-bold text-orange-700 transition hover:bg-orange-100"
          >
            ← Quay Builder
          </Link>
        </div>
      </aside>
      <main className="min-w-0 flex-1 p-6">{children}</main>
      </div>
    </AdminGuard>
  )
}
