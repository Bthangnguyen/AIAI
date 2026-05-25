import type { FollowUpQuestion, MissingIntentField } from "@/types/trip"

export interface ChatContractSlice {
  destination?: string | null
  budget_max?: number | null
  num_days?: number
}

export function inferMissingField(contract: ChatContractSlice): MissingIntentField {
  const dest = (contract.destination ?? "").toLowerCase()
  if (!dest || (!dest.includes("huế") && !dest.includes("hue"))) {
    return "destination"
  }
  if (!contract.num_days || contract.num_days < 1) {
    return "days"
  }
  if (contract.budget_max == null) {
    return "budget"
  }
  return "budget"
}

export function buildFollowUpQuestion(
  contract: ChatContractSlice,
  reply: string,
): FollowUpQuestion {
  return {
    field: inferMissingField(contract),
    question: reply,
  }
}
