/**
 * Tầng 1: Unit Tests — SearchBar component
 */
import React from "react"
import { render, fireEvent } from "@testing-library/react-native"
import { SearchBar } from "../../app/components/SearchBar"
import { ThemeProvider } from "../../app/theme/context"

const wrap = (ui: React.ReactElement) => <ThemeProvider>{ui}</ThemeProvider>

describe("SearchBar", () => {
  it("renders with placeholder text", () => {
    const { getByPlaceholderText } = render(
      wrap(<SearchBar value="" onChangeText={() => {}} placeholder="Search here..." />),
    )
    expect(getByPlaceholderText("Search here...")).toBeTruthy()
  })

  it("fires onChangeText when typing", () => {
    const onChangeText = jest.fn()
    const { getByPlaceholderText } = render(
      wrap(<SearchBar value="" onChangeText={onChangeText} placeholder="Type..." />),
    )
    fireEvent.changeText(getByPlaceholderText("Type..."), "Hue")
    expect(onChangeText).toHaveBeenCalledWith("Hue")
  })

  it("displays current value", () => {
    const { getByDisplayValue } = render(
      wrap(<SearchBar value="Da Nang" onChangeText={() => {}} />),
    )
    expect(getByDisplayValue("Da Nang")).toBeTruthy()
  })
})
