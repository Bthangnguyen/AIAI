"use client"

import { useEffect, useRef } from "react"
import type { ItineraryDay, POI } from "@/types/trip"
import { getPoi } from "@/lib/mockItineraryFallback"

interface JourneyPlaybackProps {
  days: ItineraryDay[]
  isPlaying: boolean
  onStepChange: (poiId: string, stepIndex: number) => void
  onFinish: () => void
  selectedDay: number | "all"
  map: mapboxgl.Map | null
}

interface PlaybackMarker {
  poi: POI
  dayNumber: number
  time: string
}

export function JourneyPlayback({ days, isPlaying, onStepChange, onFinish, selectedDay, map }: JourneyPlaybackProps) {
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
    if (!isPlaying || markers.length === 0 || !map) {
      playingRef.current = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      return
    }

    playingRef.current = true
    stepRef.current = 0

    function playStep() {
      if (!playingRef.current || !map) return
      const index = stepRef.current
      if (index >= markers.length) {
        onFinish()
        return
      }

      const marker = markers[index]
      const zoom = index === 0 ? 13 : 15

      map.flyTo({
        center: [marker.poi.lng, marker.poi.lat],
        zoom,
        essential: true,
        duration: 1500
      })
      onStepChange(marker.poi.id, index)

      stepRef.current++
      timeoutRef.current = setTimeout(playStep, 3000)
    }

    // Start: zoom out first to show all points
    const bounds = markers.reduce(
      (acc, m) => {
        return [
          [Math.min(acc[0][0], m.poi.lng), Math.min(acc[0][1], m.poi.lat)],
          [Math.max(acc[1][0], m.poi.lng), Math.max(acc[1][1], m.poi.lat)]
        ]
      },
      [[markers[0].poi.lng, markers[0].poi.lat], [markers[0].poi.lng, markers[0].poi.lat]]
    )
    map.fitBounds(bounds as [[number, number], [number, number]], { padding: 50, maxZoom: 13 })

    timeoutRef.current = setTimeout(playStep, 1500)

    return () => {
      playingRef.current = false
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, map])

  return null
}
