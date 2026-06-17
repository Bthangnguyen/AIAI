import { auth } from "@/lib/firebase"

export const GATEWAY_BASE_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001"

export async function getGatewayAuthHeader(): Promise<Record<string, string>> {
  if (typeof window === "undefined") return {}

  try {
    const token = auth?.currentUser
      ? await auth.currentUser.getIdToken()
      : window.localStorage.getItem("tripflow_auth_token")

    if (token) return { Authorization: `Bearer ${token}` }
  } catch (error) {
    console.warn("Unable to resolve Firebase auth token for gateway request", error)
  }

  return { Authorization: "Bearer mock-session-token-xyz-987" }
}

export async function gatewayFetch(path: string, init?: RequestInit) {
  const authHeader = await getGatewayAuthHeader()
  const res = await fetch(`${GATEWAY_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...authHeader,
      ...(init?.headers ?? {}),
    },
  })
  return res
}
