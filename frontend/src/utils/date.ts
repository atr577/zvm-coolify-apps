type DatePreset = 'datetime' | 'date' | 'weekday' | 'time'

const PRESETS: Record<DatePreset, Intl.DateTimeFormatOptions> = {
  datetime: { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' },
  date:     { year: 'numeric', month: 'short', day: 'numeric' },
  weekday:  { weekday: 'short', day: 'numeric', month: 'short' },
  time:     { hour: '2-digit', minute: '2-digit' },
}

export function formatDate(dateStr: string, preset: DatePreset = 'datetime'): string {
  return new Date(dateStr).toLocaleString(undefined, PRESETS[preset])
}

export function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  if (diffDay === 1) return 'yesterday'
  if (diffDay < 7) return `${diffDay}d ago`
  return formatDate(dateStr)
}
