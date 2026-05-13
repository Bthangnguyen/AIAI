/**
 * Preset hotels in Huế — quick-select options for the ItineraryFormScreen.
 * Coordinates verified against Mapbox/OSM data.
 */
export interface PresetHotel {
  id: string
  name: string
  lat: number
  lon: number
  emoji: string
}

export const HUE_PRESET_HOTELS: PresetHotel[] = [
  { id: "hue-heritage",  name: "Hue Heritage Hotel",   lat: 16.4637, lon: 107.5909, emoji: "🏨" },
  { id: "saigon-morin",  name: "Saigon Morin Hotel",   lat: 16.4614, lon: 107.5969, emoji: "🏛️" },
  { id: "pilgrimage",    name: "Pilgrimage Village",    lat: 16.4386, lon: 107.5726, emoji: "🌿" },
  { id: "imperial-hue",  name: "Imperial Hotel Hue",    lat: 16.4599, lon: 107.5922, emoji: "👑" },
  { id: "azerai-la-res", name: "Azerai La Residence",   lat: 16.4583, lon: 107.5942, emoji: "✨" },
]

/** Default hotel for when no selection is made */
export const DEFAULT_HOTEL = HUE_PRESET_HOTELS[0]
