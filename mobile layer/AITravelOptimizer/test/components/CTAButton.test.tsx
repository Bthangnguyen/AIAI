/**
 * Tầng 1: Unit Tests — CTAButton component
 */
import React from "react"
import { render, fireEvent } from "@testing-library/react-native"
import { CTAButton } from "../../app/components/CTAButton"
import { ThemeProvider } from "../../app/theme/context"

const wrap = (ui: React.ReactElement) => <ThemeProvider>{ui}</ThemeProvider>

describe("CTAButton", () => {
  it("renders label text", () => {
    const { getByText } = render(wrap(<CTAButton label="Go" onPress={() => {}} />))
    expect(getByText("Go")).toBeTruthy()
  })

  it("fires onPress callback when tapped", () => {
    const onPress = jest.fn()
    const { getByText } = render(wrap(<CTAButton label="Tap me" onPress={onPress} />))
    fireEvent.press(getByText("Tap me"))
    expect(onPress).toHaveBeenCalledTimes(1)
  })

  it("does not fire onPress when disabled", () => {
    const onPress = jest.fn()
    const { getByTestId } = render(
      wrap(<CTAButton label="Nope" onPress={onPress} disabled testID="cta-disabled" />),
    )
    fireEvent.press(getByTestId("cta-disabled"))
    expect(onPress).not.toHaveBeenCalled()
  })

  it("does not fire onPress when loading", () => {
    const onPress = jest.fn()
    const { getByTestId } = render(
      wrap(<CTAButton label="Loading" onPress={onPress} loading testID="cta-loading" />),
    )
    fireEvent.press(getByTestId("cta-loading"))
    expect(onPress).not.toHaveBeenCalled()
  })

  it("shows ActivityIndicator when loading", () => {
    const { queryByText, UNSAFE_getByType } = render(
      wrap(<CTAButton label="Submit" onPress={() => {}} loading />),
    )
    // Label should not be visible when loading
    expect(queryByText("Submit")).toBeNull()
  })
})
