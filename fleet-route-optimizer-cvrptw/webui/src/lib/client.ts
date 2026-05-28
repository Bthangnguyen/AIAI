export const GATEWAY_BASE_URL =
  process.env.NEXT_PUBLIC_GATEWAY_URL ?? "http://localhost:8001"

export async function gatewayFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${GATEWAY_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      Authorization: "Bearer mock-session-token-xyz-987",
      ...(init?.headers ?? {}),
    },
  })
  return res
}
