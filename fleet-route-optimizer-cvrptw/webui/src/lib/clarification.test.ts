import { describe, expect, it } from "vitest"
import { buildFollowUpQuestion, inferMissingField } from "@/lib/clarification"

describe("inferMissingField", () => {
  it("asks destination when missing or not Huế", () => {
    expect(inferMissingField({ destination: null, num_days: 3 })).toBe("destination")
    expect(inferMissingField({ destination: "Đà Nẵng", num_days: 2 })).toBe("destination")
  })

  it("asks days when num_days is zero or negative", () => {
    expect(inferMissingField({ destination: "Huế", num_days: 0 })).toBe("days")
  })

  it('asks budget for "Đi Huế 3 ngày" contract (P1 acceptance)', () => {
    expect(
      inferMissingField({
        destination: "Huế",
        num_days: 3,
        budget_max: null,
      }),
    ).toBe("budget")
  })
})

describe("buildFollowUpQuestion", () => {
  it("wraps backend reply with inferred field", () => {
    const result = buildFollowUpQuestion(
      { destination: "Huế", num_days: 3, budget_max: null },
      "Bạn dự kiến ngân sách bao nhiêu?",
    )
    expect(result.field).toBe("budget")
    expect(result.question).toBe("Bạn dự kiến ngân sách bao nhiêu?")
  })
})
