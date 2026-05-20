"use client"

import { useEffect, useRef } from "react"
import L from "leaflet"
import { useMap } from "react-leaflet"
import type { ItineraryDay, POI } from "@/types/trip"
import { getPoi } from "@/lib/mockItineraryFallback"

interface JourneyPlaybackProps {
  days: ItineraryDay[]
  isPlaying: boolean
  onStepChange: (poiId: string, stepIndex: number) => void
  onFinish: () => void
  selectedDay: number | "all"
}

interface PlaybackMarker {
  poi: POI
  dayNumber: number
  time: string
}

export function JourneyPlayback({ days, isPlaying, onStepChange, onFinish, selectedDay }: JourneyPlaybackProps) {
  const map = useMap()
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const stepRef = useRef(0)
  const playingRef = useRef(false)

  const markers: PlaybackMarker[] = days
    .filter(day => selectedDay === "all" || day.dayNumber === selectedDay)
    .flatMap(day =>
      day.items
        .map(item => {
          const poi = getPoi(item.poiId)
          return poi ? { poi, dayNumber: day.dayNumber, time: item.time } : null
        })
        .filter((m): m is PlaybackMarker => m !== null)
    )

  useEffect(() => {
    if (!isPlaying || markers.length === 0) {
      playingRef.current = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      return
    }

    playingRef.current = true
    stepRef.current = 0

    function playStep() {
      if (!playingRef.current) return
      const index = stepRef.current
      if (index >= markers.length) {
        onFinish()
        return
      }

      const marker = markers[index]
      const zoom = index === 0 ? 13 : 15

      map.flyTo([marker.poi.lat, marker.poi.lng], zoom, { duration: 1.5 })
      onStepChange(marker.poi.id, index)

      stepRef.current++
      timeoutRef.current = setTimeout(playStep, 3000)
    }

    // Start: zoom out first to show all points
    const bounds = L.latLngBounds(markers.map(m => [m.poi.lat, m.poi.lng]))
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 13 })

    timeoutRef.current = setTimeout(playStep, 1500)

    return () => {
      playingRef.current = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [isPlaying])

  return null
}
