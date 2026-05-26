import type { AdminPoiRow } from "@/types/admin"
import { gatewayFetch } from "@/lib/client"

export const POI_CATEGORY_OPTIONS = [
  "Di tích",
  "Tâm linh",
  "Cảnh quan",
  "Ẩm thực",
  "Cafe",
  "Ăn chay",
  "Văn hóa",
  "Giải trí",
  "Biển",
  "culture",
  "food",
  "cafe",
  "nature",
] as const

export interface AdminPoiListResult {
  items: AdminPoiRow[]
  total: number
  limit: number
  offset: number
}

export interface AdminPoiPatch {
  category?: string
  tags?: string[]
}

interface BackendAdminPoiItem {
  uuid: string
  name: string
  category: string
  tags?: string[]
  latitude: number
  longitude: number
  visit_duration_min: number
  open_time: number
  close_time: number
  has_embedding: boolean
}

interface BackendAdminPoiListResponse {
  items: BackendAdminPoiItem[]
  total: number
  limit: number
  offset: number
}

export function parseTagsInput(raw: string): string[] {
  const seen = new Set<string>()
  const tags: string[] = []
  for (const part of raw.split(",")) {
    const tag = part.trim()
    if (!tag) continue
    const key = tag.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    tags.push(tag)
  }
  return tags
}

export function mapBackendAdminPoi(row: BackendAdminPoiItem): AdminPoiRow {
  return {
    uuid: row.uuid,
    name: row.name,
    category: row.category,
    tags: row.tags ?? [],
    latitude: row.latitude,
    longitude: row.longitude,
    visitDurationMin: row.visit_duration_min,
    openTime: row.open_time,
    closeTime: row.close_time,
    hasEmbedding: row.has_embedding,
  }
}

export async function fetchAdminPois(params: {
  limit?: number
  offset?: number
  q?: string
  signal?: AbortSignal
}): Promise<AdminPoiListResult> {
  const search = new URLSearchParams()
  if (params.limit != null) search.set("limit", String(params.limit))
  if (params.offset != null) search.set("offset", String(params.offset))
  if (params.q?.trim()) search.set("q", params.q.trim())

  const res = await gatewayFetch(`/v1/admin/pois?${search.toString()}`, { signal: params.signal })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(detail || `Admin POI list failed (${res.status})`)
  }

  const body = (await res.json()) as BackendAdminPoiListResponse
  return {
    items: body.items.map(mapBackendAdminPoi),
    total: body.total,
    limit: body.limit,
    offset: body.offset,
  }
}

export async function updateAdminPoi(uuid: string, patch: AdminPoiPatch): Promise<AdminPoiRow> {
  const res = await gatewayFetch(`/v1/admin/pois/${encodeURIComponent(uuid)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(detail || `Admin POI update failed (${res.status})`)
  }
  const body = (await res.json()) as BackendAdminPoiItem
  return mapBackendAdminPoi(body)
}
