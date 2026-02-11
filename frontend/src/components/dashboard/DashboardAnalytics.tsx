import { useState, useEffect, useMemo, useCallback } from 'react'
import { Film, Eye, TrendingUp, Calendar, AlertCircle } from 'lucide-react'
import { metricsApi } from '@/services/api'
import { formatRelativeDate } from '@/utils/date'
import type { DashboardSummaryResponse } from '@/types'

interface DashboardAnalyticsProps {
  onSelectProject: (id: number) => void
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

const HEALTH_COLORS: Record<string, string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-500',
  red: 'bg-red-500',
}

type SortField = 'project_name' | 'published_count' | 'total_views' | 'avg_views_per_video' | 'best_video_views' | 'last_published_at'
type SortOrder = 'asc' | 'desc'

export default function DashboardAnalytics({ onSelectProject }: DashboardAnalyticsProps) {
  const [data, setData] = useState<DashboardSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortField, setSortField] = useState<SortField>('total_views')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await metricsApi.getDashboardSummary()
      setData(res.data)
    } catch {
      setError('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const sortedProjects = useMemo(() => {
    if (!data) return []
    const sorted = [...data.projects]
    sorted.sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'project_name':
          cmp = a.project_name.localeCompare(b.project_name)
          break
        case 'published_count':
          cmp = a.published_count - b.published_count
          break
        case 'total_views':
          cmp = a.total_views - b.total_views
          break
        case 'avg_views_per_video':
          cmp = a.avg_views_per_video - b.avg_views_per_video
          break
        case 'best_video_views':
          cmp = a.best_video_views - b.best_video_views
          break
        case 'last_published_at': {
          const da = a.last_published_at ? new Date(a.last_published_at).getTime() : 0
          const db = b.last_published_at ? new Date(b.last_published_at).getTime() : 0
          cmp = da - db
          break
        }
      }
      return sortOrder === 'asc' ? cmp : -cmp
    })
    return sorted
  }, [data, sortField, sortOrder])

  if (loading) return <LoadingSkeleton />

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <AlertCircle className="h-12 w-12 text-red-400 mb-4" />
        <p className="text-gray-700 font-medium mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data || data.projects.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <Film className="h-16 w-16 text-gray-300 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Template projects yet</h3>
        <p className="text-gray-500">Create a Template project to start tracking analytics.</p>
      </div>
    )
  }

  const sortIcon = (field: SortField) => {
    if (sortField !== field) return null
    return <span className="ml-1 text-xs">{sortOrder === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <SummaryCard
          title="Total Published"
          value={String(data.total_published)}
          icon={<Film className="h-5 w-5 text-purple-600" />}
        />
        <SummaryCard
          title="Total Views"
          value={formatNumber(data.total_views)}
          icon={<Eye className="h-5 w-5 text-blue-600" />}
        />
        <SummaryCard
          title="Avg Views/Video"
          value={formatNumber(data.avg_views_per_video)}
          icon={<TrendingUp className="h-5 w-5 text-green-600" />}
        />
        <SummaryCard
          title="Publishing Cadence"
          value={`${data.publishing_cadence_actual.toFixed(1)}/day`}
          subtitle={`vs ${data.publishing_cadence_target.toFixed(1)}/day target`}
          icon={<Calendar className="h-5 w-5 text-orange-600" />}
        />
      </div>

      {/* Per-Project Table */}
      <div className="bg-white rounded-lg border mb-6">
        <h3 className="text-lg font-medium p-4 border-b">Projects Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-sm text-gray-500">
                <th className="px-4 py-3 cursor-pointer hover:text-gray-900" onClick={() => handleSort('project_name')}>
                  Project{sortIcon('project_name')}
                </th>
                <th className="px-4 py-3 cursor-pointer hover:text-gray-900 text-right" onClick={() => handleSort('published_count')}>
                  Published{sortIcon('published_count')}
                </th>
                <th className="px-4 py-3 cursor-pointer hover:text-gray-900 text-right" onClick={() => handleSort('total_views')}>
                  Total Views{sortIcon('total_views')}
                </th>
                <th className="px-4 py-3 cursor-pointer hover:text-gray-900 text-right" onClick={() => handleSort('avg_views_per_video')}>
                  Avg/Video{sortIcon('avg_views_per_video')}
                </th>
                <th className="px-4 py-3 cursor-pointer hover:text-gray-900 text-right" onClick={() => handleSort('best_video_views')}>
                  Best Video{sortIcon('best_video_views')}
                </th>
                <th className="px-4 py-3 cursor-pointer hover:text-gray-900 text-right" onClick={() => handleSort('last_published_at')}>
                  Last Published{sortIcon('last_published_at')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedProjects.map(p => (
                <tr
                  key={p.project_id}
                  className="border-b last:border-b-0 hover:bg-gray-50 cursor-pointer transition"
                  onClick={() => onSelectProject(p.project_id)}
                >
                  <td className="px-4 py-3 font-medium text-gray-900">{p.project_name}</td>
                  <td className="px-4 py-3 text-right text-gray-700">{p.published_count}</td>
                  <td className="px-4 py-3 text-right text-gray-700">{formatNumber(p.total_views)}</td>
                  <td className="px-4 py-3 text-right text-gray-700">{formatNumber(p.avg_views_per_video)}</td>
                  <td className="px-4 py-3 text-right text-gray-700">{p.best_video_views > 0 ? formatNumber(p.best_video_views) : '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-500 text-sm">{p.last_published_at ? formatRelativeDate(p.last_published_at) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Publishing Health */}
      <div className="bg-white rounded-lg border">
        <h3 className="text-lg font-medium p-4 border-b">Publishing Health</h3>
        <div className="divide-y">
          {data.health.map(h => (
            <div key={h.project_id} className="p-4 flex items-center gap-4">
              <span className={`w-3 h-3 rounded-full flex-shrink-0 ${HEALTH_COLORS[h.health_status]}`} />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900">{h.project_name}</div>
                <div className="text-sm text-gray-500">
                  {h.health_note || `Queue: ${h.queue_size} videos, ${h.queue_days?.toFixed(1) ?? '?'} days of content`}
                </div>
              </div>
              <div className="text-sm text-gray-600 whitespace-nowrap">
                {h.pending_moderation > 0 && (
                  <span className="mr-4 text-orange-600">{h.pending_moderation} awaiting review</span>
                )}
              </div>
              <div className="text-sm text-gray-600 whitespace-nowrap">
                {h.actual_cadence_last_7d.toFixed(1)}/day vs {h.target_cadence.toFixed(1)}/day
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function SummaryCard({ title, value, subtitle, icon }: {
  title: string
  value: string
  subtitle?: string
  icon: React.ReactNode
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 border">
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-sm text-gray-500">{title}</span>
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      {subtitle && <div className="text-xs text-gray-500 mt-1">{subtitle}</div>}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto p-6 animate-pulse">
      {/* Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="bg-gray-100 rounded-lg p-4 h-24" />
        ))}
      </div>
      {/* Table */}
      <div className="bg-white rounded-lg border mb-6 p-4">
        <div className="h-6 bg-gray-100 rounded w-48 mb-4" />
        {[1, 2, 3].map(i => (
          <div key={i} className="h-10 bg-gray-50 rounded mb-2" />
        ))}
      </div>
      {/* Health */}
      <div className="bg-white rounded-lg border p-4">
        <div className="h-6 bg-gray-100 rounded w-40 mb-4" />
        {[1, 2, 3].map(i => (
          <div key={i} className="h-12 bg-gray-50 rounded mb-2" />
        ))}
      </div>
    </div>
  )
}
