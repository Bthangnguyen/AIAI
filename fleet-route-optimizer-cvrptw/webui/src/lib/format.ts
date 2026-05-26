export function formatCurrency(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return "Chưa rõ"
  return `${Math.round(value).toLocaleString("vi-VN")} ₫`
}

export function formatDateTime(iso: string | undefined | null): string {
  if (!iso) return "--"
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
