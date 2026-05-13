/**
 * Tầng 1: Unit Tests — HotelPicker component (Phase A new component)
 */
import React from "react"
import { render, fireEvent } from "@testing-library/react-native"
import { HotelPicker, HotelSelection } from "../../app/components/HotelPicker"
import { ThemeProvider } from "../../app/theme/context"
import { DEFAULT_HOTEL, HUE_PRESET_HOTELS } from "../../app/constants/presetHotels"

const wrap = (ui: React.ReactElement) => <ThemeProvider>{ui}</ThemeProvider>

describe("HotelPicker", () => {
  const defaultValue: HotelSelection = {
    name: DEFAULT_HOTEL.name,
    lat: DEFAULT_HOTEL.lat,
    lon: DEFAULT_HOTEL.lon,
  }

  it("renders with default hotel name displayed", () => {
    const { getAllByText } = render(
      wrap(<HotelPicker value={defaultValue} onChange={() => {}} />),
    )
    // Name appears in both selected display + chip
    const elements = getAllByText("Hue Heritage Hotel")
    expect(elements.length).toBeGreaterThanOrEqual(1)
  })

  it("renders all preset hotel chips", () => {
    const { getAllByText } = render(
      wrap(<HotelPicker value={defaultValue} onChange={() => {}} />),
    )
    HUE_PRESET_HOTELS.forEach((hotel) => {
      const elements = getAllByText(hotel.name)
      expect(elements.length).toBeGreaterThanOrEqual(1)
    })
  })

  it("renders 'Other...' search chip", () => {
    const { getByText } = render(
      wrap(<HotelPicker value={defaultValue} onChange={() => {}} />),
    )
    expect(getByText("Other...")).toBeTruthy()
  })

  it("calls onChange when a preset chip is tapped", () => {
    const onChange = jest.fn()
    const { getByText } = render(
      wrap(<HotelPicker value={defaultValue} onChange={onChange} />),
    )
    // Tap "Saigon Morin Hotel"
    fireEvent.press(getByText("Saigon Morin Hotel"))
    expect(onChange).toHaveBeenCalledWith({
      name: "Saigon Morin Hotel",
      lat: HUE_PRESET_HOTELS[1].lat,
      lon: HUE_PRESET_HOTELS[1].lon,
    })
  })

  it("shows search input when 'Other...' is tapped", () => {
    const { getByText, getByPlaceholderText } = render(
      wrap(<HotelPicker value={defaultValue} onChange={() => {}} />),
    )
    fireEvent.press(getByText("Other..."))
    expect(getByPlaceholderText("Search hotel or address...")).toBeTruthy()
  })
})
