export type PoiQaIssueType =
  | "wrong_coords"
  | "duplicates"
  | "missing_hours"
  | "missing_duration"
  | "missing_embedding"

export interface PoiQaSummary {
  wrong_coords: number
  duplicates: number
  missing_hours: number
  missing_duration: number
  missing_embedding: number
}

export interface AdminPoiRow {
  uuid: string
  name: string
  category: string
  tags: string[]
  latitude: number
  longitude: number
  visitDurationMin: number
  openTime: number
  closeTime: number
  hasEmbedding: boolean
}
