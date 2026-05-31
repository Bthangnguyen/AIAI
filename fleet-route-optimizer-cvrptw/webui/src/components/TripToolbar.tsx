"use client"

import { useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronLeft, Download, FolderOpen, Lock, MoreHorizontal, RefreshCw, RotateCcw, Save, Share2, Smartphone, Printer, Calendar as CalendarIcon, MapPin } from "lucide-react"
import { getPoi } from "@/lib/mockItineraryFallback"
import type { ItineraryDraft, PreviewMode, POI } from "@/types/trip"

interface TripToolbarProps {
  draft: ItineraryDraft | null
  viewMode: PreviewMode
  onViewModeChange: (mode: PreviewMode) => void
  onBack: () => void
  onSave: () => void
  onReset: () => void
  onRebuild: () => void
  onSavedTrips: () => void
  onMobilePhase: () => void
}

export function TripToolbar({ draft, viewMode, onViewModeChange, onBack, onSave, onReset, onRebuild, onSavedTrips, onMobilePhase }: TripToolbarProps) {
  const title = draft ? `${draft.destination} ${draft.days.length} ngày` : "Untitled Trip"
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false)
    }
    window.addEventListener("pointerdown", handlePointerDown)
    return () => window.removeEventListener("pointerdown", handlePointerDown)
  }, [menuOpen])

  const handleExportCalendar = () => {
    if (!draft) return
    let icsContent = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//TripFlow//Itinerary Planner//EN\r\nCALSCALE:GREGORIAN\r\nMETHOD:PUBLISH\r\n"
    
    const today = new Date()
    const startDate = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)
    
    draft.days.forEach((day, dayIndex) => {
      const currentDayDate = new Date(startDate.getTime())
      currentDayDate.setDate(startDate.getDate() + dayIndex)
      
      day.items.forEach((item, stopIndex) => {
        const poi = getPoi(item.poiId)
        if (!poi) return
        
        const timeStr = item.time || "08:00"
        let startH = 8
        let startM = 0
        
        if (timeStr.includes(":")) {
          const [h, m] = timeStr.split(":").map(Number)
          if (!isNaN(h)) startH = h
          if (!isNaN(m)) startM = m
        } else {
          const match = timeStr.match(/(\d+)/)
          if (match) startH = parseInt(match[0])
        }
        
        const start = new Date(currentDayDate.getTime())
        start.setHours(startH, startM, 0, 0)
        
        const durationMin = poi.estimatedDurationMinutes || 60
        const end = new Date(start.getTime() + durationMin * 60 * 1000)
        
        const formatICSDate = (date: Date) => {
          const pad = (n: number) => n.toString().padStart(2, '0')
          return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}T${pad(date.getHours())}${pad(date.getMinutes())}00`
        }
        
        const uid = `stop_${dayIndex}_${stopIndex}_${Date.now()}@tripflow`
        
        icsContent += "BEGIN:VEVENT\r\n"
        icsContent += `UID:${uid}\r\n`
        icsContent += `DTSTART:${formatICSDate(start)}\r\n`
        icsContent += `DTEND:${formatICSDate(end)}\r\n`
        icsContent += `SUMMARY:${poi.name || "Địa điểm"}\r\n`
        icsContent += `DESCRIPTION:${(item.note || poi.description || "").replace(/\r?\n/g, "\\n")}\r\n`
        icsContent += `LOCATION:${draft.destination || "Hue, Vietnam"}\r\n`
        icsContent += "END:VEVENT\r\n"
      })
    })
    icsContent += "END:VCALENDAR\r\n"
    
    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.setAttribute("download", `tripflow_itinerary_${draft.destination.toLowerCase()}.ics`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const openGoogleMapsRoute = (stops: POI[]) => {
    if (!draft || stops.length === 0) return
    
    const hotelLat = draft.llmContract?.hotel_lat
    const hotelLon = draft.llmContract?.hotel_lon
    const hasHotel = hotelLat !== undefined && hotelLon !== undefined
    
    let origin = ""
    let destination = ""
    let waypoints = ""
    
    if (hasHotel) {
      origin = `${hotelLat},${hotelLon}`
      destination = `${hotelLat},${hotelLon}`
      waypoints = stops.map(s => `${s.lat},${s.lng}`).join("|")
    } else {
      origin = `${stops[0].lat},${stops[0].lng}`
      destination = `${stops[stops.length - 1].lat},${stops[stops.length - 1].lng}`
      if (stops.length > 2) {
        waypoints = stops.slice(1, -1).map(s => `${s.lat},${s.lng}`).join("|")
      }
    }
    
    const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&waypoints=${encodeURIComponent(waypoints)}&travelmode=driving`
    window.open(mapsUrl, "_blank")
  }

  return (
    <div className="relative flex h-14 items-center border-b border-orange-200 bg-white px-4 text-orange-950 shadow-sm">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onBack} className="rounded-lg p-1.5 text-orange-950/60 transition hover:bg-orange-100 hover:text-orange-700" aria-label="Back">
          <ChevronLeft size={20} />
        </button>
        <button type="button" className="flex max-w-[220px] items-center gap-2 rounded-lg px-2.5 py-1.5 transition hover:bg-orange-50">
          <span className="truncate text-[15px] font-black text-orange-950">{title}</span>
          <Lock size={12} className="shrink-0 text-orange-500" />
          <ChevronDown size={14} className="shrink-0 text-orange-500" />
        </button>
      </div>

      <div className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 md:block">
        <div className="flex items-center rounded-xl border border-orange-200 bg-orange-50 p-1">
          {(["timeline", "map", "split"] as PreviewMode[]).map((mode) => (
            <button key={mode} type="button" onClick={() => onViewModeChange(mode)} className={`rounded-lg px-4 py-1.5 text-sm font-black transition ${viewMode === mode ? "bg-white text-orange-700 shadow-sm" : "text-orange-950/55 hover:text-orange-700"}`}>
              {mode === "timeline" ? "Preview" : mode === "map" ? "Map" : "Split"}
            </button>
          ))}
        </div>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button type="button" onClick={onSave} className="hidden items-center gap-2 rounded-lg border border-orange-300 px-4 py-2 text-sm font-black text-orange-700 transition hover:bg-orange-50 sm:flex">
          <Save size={14} /> Lưu nháp
        </button>
        <button type="button" disabled className="hidden items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-sm font-black text-white opacity-70 sm:flex">
          <Share2 size={14} /> Chia sẻ
        </button>
        <div ref={menuRef} className="relative">
          <button type="button" onClick={() => setMenuOpen((value) => !value)} className="rounded-lg p-2 text-orange-950/60 transition hover:bg-orange-100 hover:text-orange-700" aria-label="More actions" aria-expanded={menuOpen}>
            <MoreHorizontal size={20} />
          </button>
          {menuOpen ? (
            <div className="absolute right-0 top-full z-50 mt-2 w-64 rounded-xl border border-orange-200 bg-white py-1.5 shadow-2xl shadow-orange-950/10 max-h-96 overflow-y-auto custom-scrollbar">
              <button type="button" disabled={!draft} className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-40" onClick={() => { setMenuOpen(false); onRebuild() }}><RefreshCw size={16} /> Tạo option khác</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); console.log(JSON.stringify(draft, null, 2)) }}><Download size={16} /> Export JSON</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); onReset() }}><RotateCcw size={16} /> Reset Draft</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); onSavedTrips() }}><FolderOpen size={16} /> Saved Trips</button>
              <button type="button" className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50" onClick={() => { setMenuOpen(false); onMobilePhase() }}><Smartphone size={16} /> Mobile Phase</button>
              
              <div className="my-1 border-t border-orange-100" />
              
              <button type="button" disabled={!draft} className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-40" onClick={() => { setMenuOpen(false); window.print() }}><Printer size={16} /> Tải PDF lịch trình</button>
              <button type="button" disabled={!draft} className="flex w-full items-center gap-3 px-4 py-2.5 text-sm font-bold text-orange-950/65 hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-40" onClick={() => { setMenuOpen(false); handleExportCalendar() }}><CalendarIcon size={16} /> Đồng bộ Calendar (.ics)</button>
              
              {draft && (
                <>
                  <div className="my-1 border-t border-orange-100" />
                  <div className="px-4 py-1 text-[10px] uppercase tracking-wider font-extrabold text-orange-900/40">Dẫn đường Google Maps</div>
                  {draft.days.map((day) => {
                    const stops = day.items.map((item) => getPoi(item.poiId)).filter((p): p is POI => !!p)
                    if (stops.length === 0) return null
                    
                    return (
                      <button 
                        key={day.dayNumber}
                        type="button" 
                        className="flex w-full items-center gap-3 px-4 py-2.5 text-xs font-bold text-orange-950/65 hover:bg-orange-50" 
                        onClick={() => { 
                          setMenuOpen(false); 
                          openGoogleMapsRoute(stops);
                        }}
                      >
                        <MapPin size={14} className="text-orange-600" /> Bản đồ Ngày {day.dayNumber}
                      </button>
                    )
                  })}
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
