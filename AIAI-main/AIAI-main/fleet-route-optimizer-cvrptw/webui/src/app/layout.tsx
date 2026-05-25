import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "TripFlow AI",
  description: "Vietnamese AI itinerary planner MVP for Hue travel drafts.",
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  )
}
