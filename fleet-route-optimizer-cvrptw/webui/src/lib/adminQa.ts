import type { AdminPoiRow, PoiQaIssueType, PoiQaSummary } from "@/types/admin"
import { mapBackendAdminPoi } from "@/lib/adminPois"
import { gatewayFetch } from "@/lib/client"

interface BackendPoiQaSummary {
  wrong_coords: number
  duplicates: number
  missing_hours: number
  missing_duration: number
  missing_embedding: number
}

interface BackendAdminPoiQaItem {
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
  duplicate_group?: string | null
}

interface BackendAdminPoiQaListResponse {
  issue: string
  items: BackendAdminPoiQaItem[]
  total: number
  limit: number
  offset: number
}

export interface AdminPoiQaRow extends AdminPoiRow {
  duplicateGroup?: string | null
}

export function mapBackendQaSummary(body: BackendPoiQaSummary): PoiQaSummary {
  return {
    wrong_coords: body.wrong_coords,
    duplicates: body.duplicates,
    missing_hours: body.missing_hours,
    missing_duration: body.missing_duration,
    missing_embedding: body.missing_embedding,
  }
}

export function mapBackendQaPoi(row: BackendAdminPoiQaItem): AdminPoiQaRow {
  return {
    ...mapBackendAdminPoi(row),
    duplicateGroup: row.duplicate_group ?? null,
  }
}

export function qaCardTone(count: number): "ok" | "warn" | "danger" {
  if (count <= 0) return "ok"
  if (count < 5) return "warn"
  return "danger"
}

export const QA_ISSUE_LABELS: Record<PoiQaIssueType, string> = {
  wrong_coords: "Tọa độ sai",
  duplicates: "Trùng POI",
  missing_hours: "Thiếu giờ mở cửa",
  missing_duration: "Thiếu visit duration",
  missing_embedding: "Thiếu embedding",
}

export async function fetchPoiQaSummary(signal?: AbortSignal): Promise<PoiQaSummary> {
  const res = await gatewayFetch("/v1/admin/pois/qa-summary", { signal })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(detail || `QA summary failed (${res.status})`)
  }
  return mapBackendQaSummary((await res.json()) as BackendPoiQaSummary)
}

export async function fetchPoiQaList(params: {
  issue: PoiQaIssueType
  limit?: number
  offset?: number
  signal?: AbortSignal
}): Promise<{ items: AdminPoiQaRow[]; total: number; issue: PoiQaIssueType }> {
  const search = new URLSearchParams({ issue: params.issue })
  if (params.limit != null) search.set("limit", String(params.limit))
  if (params.offset != null) search.set("offset", String(params.offset))

  const res = await gatewayFetch(`/v1/admin/pois/qa?${search.toString()}`, { signal: params.signal })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(detail || `QA list failed (${res.status})`)
  }

  const body = (await res.json()) as BackendAdminPoiQaListResponse
  return {
    issue: body.issue as PoiQaIssueType,
    total: body.total,
    items: body.items.map(mapBackendQaPoi),
  }
}

export function duplicateGroupClass(groupId: string | null | undefined): string {
  if (!groupId) return ""
  const palette = [
    "bg-yellow-100",
    "bg-sky-100",
    "bg-pink-100",
    "bg-lime-100",
    "bg-violet-100",
  ]
  const index = groupId.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0) % palette.length
  return palette[index] ?? "bg-yellow-100"
}
