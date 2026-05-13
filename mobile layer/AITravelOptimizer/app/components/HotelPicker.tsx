/**
 * HotelPicker — Hotel selection component with:
 * 1. Preset hotel chips (quick select)
 * 2. Mapbox Geocoding search (type hotel name → autocomplete suggestions)
 *
 * Uses Mapbox Geocoding API v5 — no Google Maps needed.
 */
import React, { useState, useCallback, useRef } from "react"
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  ScrollView,
} from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { HUE_PRESET_HOTELS, PresetHotel } from "@/constants/presetHotels"

// ─── Types ──────────────────────────────────────────────────────
export interface HotelSelection {
  name: string
  lat: number
  lon: number
}

interface HotelPickerProps {
  value: HotelSelection
  onChange: (hotel: HotelSelection) => void
}

interface GeocodingFeature {
  id: string
  place_name: string
  center: [number, number] // [lon, lat]
  text: string
}

// ─── Mapbox Geocoding ───────────────────────────────────────────
const MAPBOX_TOKEN = process.env.EXPO_PUBLIC_MAPBOX_TOKEN || ""

const searchMapbox = async (query: string): Promise<GeocodingFeature[]> => {
  if (!query.trim() || query.length < 3 || !MAPBOX_TOKEN) return []

  try {
    // Bias search towards Huế, Vietnam (bbox + proximity)
    const url =
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json` +
      `?access_token=${MAPBOX_TOKEN}` +
      `&types=poi,address` +
      `&proximity=107.59,16.46` + // Huế center
      `&bbox=107.45,16.30,107.75,16.60` + // Huế bounding box
      `&limit=5` +
      `&language=vi`

    const res = await fetch(url)
    const data = await res.json()
    return data.features || []
  } catch (e) {
    console.error("Mapbox Geocoding error:", e)
    return []
  }
}

// ─── Component ──────────────────────────────────────────────────
export const HotelPicker: React.FC<HotelPickerProps> = ({ value, onChange }) => {
  const [searchText, setSearchText] = useState("")
  const [suggestions, setSuggestions] = useState<GeocodingFeature[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // ─── Preset selection ─────────────────────────────────────────
  const handlePresetSelect = useCallback((preset: PresetHotel) => {
    onChange({ name: preset.name, lat: preset.lat, lon: preset.lon })
    setShowSearch(false)
    setSearchText("")
    setSuggestions([])
  }, [onChange])

  // ─── Mapbox search with debounce ──────────────────────────────
  const handleSearchChange = useCallback((text: string) => {
    setSearchText(text)
    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (text.length < 3) {
      setSuggestions([])
      return
    }

    debounceRef.current = setTimeout(async () => {
      setIsSearching(true)
      const results = await searchMapbox(text)
      setSuggestions(results)
      setIsSearching(false)
    }, 400)
  }, [])

  const handleSuggestionSelect = useCallback((feature: GeocodingFeature) => {
    onChange({
      name: feature.text || feature.place_name,
      lat: feature.center[1], // Mapbox returns [lon, lat]
      lon: feature.center[0],
    })
    setSearchText("")
    setSuggestions([])
    setShowSearch(false)
  }, [onChange])

  // ─── Selected indicator ───────────────────────────────────────
  const selectedPreset = HUE_PRESET_HOTELS.find(
    (h) => h.name === value.name
  )

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Starting point (Hotel)</Text>

      {/* Selected hotel display */}
      <View style={styles.selectedRow}>
        <Text style={styles.selectedEmoji}>{selectedPreset?.emoji || "📍"}</Text>
        <Text style={styles.selectedName} numberOfLines={1}>{value.name}</Text>
      </View>

      {/* Preset chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.chipsRow}
      >
        {HUE_PRESET_HOTELS.map((hotel) => {
          const isActive = hotel.name === value.name
          return (
            <TouchableOpacity
              key={hotel.id}
              style={[styles.chip, isActive && styles.chipActive]}
              onPress={() => handlePresetSelect(hotel)}
              activeOpacity={0.7}
            >
              <Text style={styles.chipEmoji}>{hotel.emoji}</Text>
              <Text style={[styles.chipText, isActive && styles.chipTextActive]} numberOfLines={1}>
                {hotel.name}
              </Text>
            </TouchableOpacity>
          )
        })}

        {/* Custom search chip */}
        <TouchableOpacity
          style={[styles.chip, showSearch && styles.chipActive]}
          onPress={() => setShowSearch(!showSearch)}
          activeOpacity={0.7}
        >
          <Text style={styles.chipEmoji}>🔍</Text>
          <Text style={[styles.chipText, showSearch && styles.chipTextActive]}>
            Other...
          </Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Mapbox search input */}
      {showSearch && (
        <View style={styles.searchSection}>
          <TextInput
            style={styles.searchInput}
            value={searchText}
            onChangeText={handleSearchChange}
            placeholder="Search hotel or address..."
            placeholderTextColor={colors.palette.figmaGrayMedium}
            autoFocus
          />

          {isSearching && (
            <ActivityIndicator
              size="small"
              color={colors.tint}
              style={styles.spinner}
            />
          )}

          {/* Suggestions dropdown */}
          {suggestions.length > 0 && (
            <View style={styles.suggestionsContainer}>
              {suggestions.map((feature) => (
                <TouchableOpacity
                  key={feature.id}
                  style={styles.suggestionItem}
                  onPress={() => handleSuggestionSelect(feature)}
                >
                  <Text style={styles.suggestionText} numberOfLines={2}>
                    {feature.place_name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>
      )}
    </View>
  )
}

// ─── Styles ─────────────────────────────────────────────────────
const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.md,
  },
  label: {
    fontFamily: typography.primary.semiBold,
    fontSize: 15,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.xs,
  },
  selectedRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  selectedEmoji: {
    fontSize: 20,
    marginRight: spacing.sm,
  },
  selectedName: {
    fontFamily: typography.primary.medium,
    fontSize: 15,
    color: colors.palette.figmaBlack,
    flex: 1,
  },
  chipsRow: {
    gap: spacing.xs,
    paddingBottom: spacing.xs,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderWidth: 1.5,
    borderColor: "transparent",
  },
  chipActive: {
    borderColor: colors.palette.figmaPrimaryBlack,
    backgroundColor: colors.palette.figmaGrayLight,
  },
  chipEmoji: {
    fontSize: 14,
    marginRight: 6,
  },
  chipText: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.figmaGrayDark,
    maxWidth: 120,
  },
  chipTextActive: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaPrimaryBlack,
  },
  searchSection: {
    marginTop: spacing.sm,
  },
  searchInput: {
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
    padding: spacing.md,
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
    borderWidth: 1,
    borderColor: colors.palette.figmaGrayLight,
  },
  spinner: {
    position: "absolute",
    right: 16,
    top: 14,
  },
  suggestionsContainer: {
    marginTop: spacing.xs,
    backgroundColor: colors.palette.figmaWhite,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: colors.palette.figmaGrayLight,
    overflow: "hidden",
    // Shadow
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 4,
  },
  suggestionItem: {
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.palette.figmaGrayLight,
  },
  suggestionText: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayDark,
    lineHeight: 18,
  },
})
