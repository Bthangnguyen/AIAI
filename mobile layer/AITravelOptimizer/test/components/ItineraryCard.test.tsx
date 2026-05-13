import { render } from "@testing-library/react-native"

import { ItineraryCard } from "../../app/components/ItineraryCard"
import { ThemeProvider } from "../../app/theme/context"

describe("ItineraryCard", () => {
  it("hiển thị emoji, tiêu đề và thời gian", () => {
    const { getByText } = render(
      <ThemeProvider>
        <ItineraryCard
          timeString="12:30 — 14:00"
          title="Golden beach"
          emoji="🏖️"
          visitDurationMin={90}
          entranceFee={0}
          travelTimeMin={0}
        />
      </ThemeProvider>,
    )
    expect(getByText("12:30 — 14:00")).toBeTruthy()
    expect(getByText("Golden beach")).toBeTruthy()
    expect(getByText("🏖️")).toBeTruthy()
  })
})
