/**
 * Tầng 1: Unit Tests — CategoryChip component
 */
import React from "react"
import { render, fireEvent } from "@testing-library/react-native"
import { CategoryChip } from "../../app/components/CategoryChip"
import { ThemeProvider } from "../../app/theme/context"

const wrap = (ui: React.ReactElement) => <ThemeProvider>{ui}</ThemeProvider>

describe("CategoryChip", () => {
  it("renders label", () => {
    const { getByText } = render(
      wrap(<CategoryChip label="Beach" onPress={() => {}} />),
    )
    expect(getByText("Beach")).toBeTruthy()
  })

  it("fires onPress when tapped", () => {
    const onPress = jest.fn()
    const { getByText } = render(
      wrap(<CategoryChip label="Mountain" onPress={onPress} />),
    )
    fireEvent.press(getByText("Mountain"))
    expect(onPress).toHaveBeenCalledTimes(1)
  })

  it("renders with active state without crash", () => {
    const { getByText } = render(
      wrap(<CategoryChip label="City" active onPress={() => {}} />),
    )
    expect(getByText("City")).toBeTruthy()
  })

  it("renders with inactive state without crash", () => {
    const { getByText } = render(
      wrap(<CategoryChip label="Heritage" active={false} onPress={() => {}} />),
    )
    expect(getByText("Heritage")).toBeTruthy()
  })
})
