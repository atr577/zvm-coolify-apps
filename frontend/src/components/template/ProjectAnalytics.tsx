import { useState, useEffect, useCallback, useRef, Fragment } from 'react'
import {
  Eye,
  TrendingUp,
  Share2,
  Bookmark,
  AlertCircle,
  RefreshCw,
  ArrowUpDown,
} from 'lucide-react'
import { metricsApi } from '@/services/api'
import { formatDate } from '@/utils/date'
import type {
  ProjectMetricsResponse,
  GenerationMetrics,
  GenerationPlatformMetrics,
} from '@/types'
import axios from 'axios'

interface ProjectAnalyticsProps {
  projectId: number
}

const PERIODS = ['30m', '6h', '24h', '7d'] as const
type Period = (typeof PERIODS)[number]

type SortField = 'published_at' | 'views' | 'engagement_rate' | 'virality_rate' | 'saves'

const PLATFORM_ICONS: Record<string, string> = {
  instagram: 'IG',
  tiktok: 'TT',
  youtube: 'YT',
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function formatRate(rate: number | null): string {
  if (rate === null) return '--'
  return `${rate.toFixed(1)}%`
}

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'pending':
      return (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700"
          title="First metrics will be available ~30 min after publishing."
        >
          Collecting...
        </span>
      )
    case 'no_post_id':
      return (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500"
          title="Published before metrics tracking was enabled."
        >
          Metrics unavailable
        </span>
      )
    case 'not_collected':
      return (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700"
          title="Data for this period not yet collected."
        >
          --
        </span>
      )
    default:
      return null
  }
}

function PlatformMetricsRow({ platform, metrics }: { platform: string; metrics: GenerationPlatformMetrics }) {
  return (
    <div className="flex items-center gap-4 text-xs text-gray-600 py-1">
      <span className="w-6 font-medium text-gray-400">{PLATFORM_ICONS[platform] || platform}</span>
      <span className="w-16 text-right">{formatNumber(metrics.views)}</span>
      <span className="w-14 text-right">{formatRate(metrics.engagement_rate)}</span>
      <span className="w-14 text-right">{formatRate(metrics.virality_rate)}</span>
      <span className="w-14 text-right">{formatNumber(metrics.saves)}</span>
      <span className="w-14 text-right">{formatNumber(metrics.reach)}</span>
    </div>
  )
}

export function ProjectAnalytics({ projectId }: ProjectAnalyticsProps) {
  const [data, setData] = useState<ProjectMetricsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState<Period | undefined>(undefined)
  const [sortBy, setSortBy] = useState<SortField>('published_at')
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set())

  // Refresh state (T44)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null)
  const [cooldownUntil, setCooldownUntil] = useState<Date | null>(null)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const cooldownTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const [, setTick] = useState(0) // force re-render for cooldown countdown

  const cooldownActive = cooldownUntil ? cooldownUntil > new Date() : false

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownActive) {
      cooldownTimer.current = setInterval(() => setTick((t) => t + 1), 10_000)
    } else if (cooldownTimer.current) {
      clearInterval(cooldownTimer.current)
      cooldownTimer.current = null
    }
    return () => {
      if (cooldownTimer.current) clearInterval(cooldownTimer.current)
    }
  }, [cooldownActive])

  const fetchData = useCallback(async () => {
    try {
      setError(null)
      setLoading(true)
      const { data: result } = await metricsApi.getProjectMetrics(projectId, {
        period,
        sort_by: sortBy,
      })
      setData(result)
    } catch (err) {
      console.error('Failed to load analytics:', err)
      setError('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }, [projectId, period, sortBy])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    setRefreshError(null)
    try {
      const { data: result } = await metricsApi.refreshProjectMetrics(projectId)
      setLastRefreshedAt(new Date())
      if (result.cooldown_until) {
        setCooldownUntil(new Date(result.cooldown_until))
      }
      // Re-fetch table data with fresh metrics
      await fetchData()
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        const detail = err.response.data?.detail
        if (detail?.cooldown_until) {
          setCooldownUntil(new Date(detail.cooldown_until))
        }
        setRefreshError('Cooldown active')
      } else if (axios.isAxiosError(err) && err.response?.status === 400) {
        setRefreshError(err.response.data?.detail || 'Too many videos')
      } else {
        setRefreshError('Failed to refresh')
      }
    } finally {
      setRefreshing(false)
    }
  }, [projectId, fetchData])

  const toggleRow = (id: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSort = (field: SortField) => {
    setSortBy(field)
  }

  // Cooldown tooltip text
  const cooldownTooltip = cooldownActive && cooldownUntil
    ? `Available in ${Math.max(1, Math.ceil((cooldownUntil.getTime() - Date.now()) / 60_000))} min`
    : 'Refresh from YouTube'

  // Loading state
  if (loading && !data) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Analytics</h3>
        <div className="animate-pulse space-y-4">
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-20 bg-gray-100 rounded-lg" />
            ))}
          </div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-gray-50 rounded" />
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Analytics</h3>
        <div className="flex flex-col items-center py-8 text-gray-500">
          <AlertCircle className="w-8 h-8 mb-2 text-red-400" />
          <p className="text-sm mb-3">{error}</p>
          <button
            onClick={fetchData}
            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-gray-100 rounded hover:bg-gray-200 transition"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      </div>
    )
  }

  // Empty state
  if (!data || data.generations.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Analytics</h3>
        <div className="text-center py-8 text-gray-500">
          <Eye className="w-8 h-8 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">No published videos yet.</p>
          <p className="text-xs text-gray-400 mt-1">
            Approve and schedule videos to see analytics here.
          </p>
        </div>
      </div>
    )
  }

  const { totals, generations } = data

  // Sum metrics for a generation across platforms
  const sumViews = (g: GenerationMetrics) =>
    Object.values(g.platforms).reduce((s, p) => s + p.views, 0)

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-medium text-gray-900">Analytics</h3>
          {lastRefreshedAt && (
            <span className="text-xs text-gray-400">Updated {timeAgo(lastRefreshedAt)}</span>
          )}
          {refreshError && (
            <span className="text-xs text-red-400">{refreshError}</span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing || cooldownActive}
          className={`p-1.5 transition ${
            cooldownActive
              ? 'text-gray-300 cursor-not-allowed'
              : 'text-gray-400 hover:text-gray-600'
          }`}
          title={cooldownTooltip}
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <Eye className="w-4 h-4" />
            <span className="text-xs">Total Views</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatNumber(totals.total_views)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <TrendingUp className="w-4 h-4" />
            <span className="text-xs">Avg Engagement</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatRate(totals.avg_engagement_rate)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <Share2 className="w-4 h-4" />
            <span className="text-xs">Avg Virality</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatRate(totals.avg_virality_rate)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center gap-2 text-gray-500 mb-1">
            <Bookmark className="w-4 h-4" />
            <span className="text-xs">Published</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{totals.total_published}</div>
        </div>
      </div>

      {/* Period Selector */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-gray-500">Period:</span>
        <button
          onClick={() => setPeriod(undefined)}
          className={`px-3 py-1 text-xs rounded-full transition ${
            !period ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          Latest
        </button>
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 text-xs rounded-full transition ${
              period === p ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="py-2 px-2 w-12"></th>
              <th
                className="py-2 px-2 cursor-pointer hover:text-gray-700"
                onClick={() => handleSort('published_at')}
              >
                <span className="flex items-center gap-1">
                  Published
                  {sortBy === 'published_at' && <ArrowUpDown className="w-3 h-3" />}
                </span>
              </th>
              <th className="py-2 px-2">Platforms</th>
              <th
                className="py-2 px-2 text-right cursor-pointer hover:text-gray-700"
                onClick={() => handleSort('views')}
              >
                <span className="flex items-center justify-end gap-1">
                  Views
                  {sortBy === 'views' && <ArrowUpDown className="w-3 h-3" />}
                </span>
              </th>
              <th
                className="py-2 px-2 text-right cursor-pointer hover:text-gray-700"
                onClick={() => handleSort('engagement_rate')}
              >
                <span className="flex items-center justify-end gap-1">
                  Engage%
                  {sortBy === 'engagement_rate' && <ArrowUpDown className="w-3 h-3" />}
                </span>
              </th>
              <th
                className="py-2 px-2 text-right cursor-pointer hover:text-gray-700"
                onClick={() => handleSort('virality_rate')}
              >
                <span className="flex items-center justify-end gap-1">
                  Viral%
                  {sortBy === 'virality_rate' && <ArrowUpDown className="w-3 h-3" />}
                </span>
              </th>
              <th
                className="py-2 px-2 text-right cursor-pointer hover:text-gray-700"
                onClick={() => handleSort('saves')}
              >
                <span className="flex items-center justify-end gap-1">
                  Saves
                  {sortBy === 'saves' && <ArrowUpDown className="w-3 h-3" />}
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {generations.map((gen) => {
              const isExpanded = expandedRows.has(gen.approved_generation_id)
              const platformEntries = Object.entries(gen.platforms)
              const hasMetrics = gen.metrics_status === 'complete' && platformEntries.length > 0

              // Aggregate across platforms for the row
              const totalViews = sumViews(gen)
              const maxEngagement = hasMetrics
                ? Math.max(...platformEntries.map(([, p]) => p.engagement_rate ?? 0))
                : null
              const maxVirality = hasMetrics
                ? Math.max(...platformEntries.map(([, p]) => p.virality_rate ?? 0))
                : null
              const totalSaves = hasMetrics
                ? platformEntries.reduce((s, [, p]) => s + p.saves, 0)
                : 0

              return (
                <Fragment key={gen.approved_generation_id}>
                  <tr
                    className="border-b hover:bg-gray-50 cursor-pointer"
                    onClick={() => hasMetrics && platformEntries.length > 1 && toggleRow(gen.approved_generation_id)}
                  >
                    <td className="py-2 px-2">
                      {gen.thumbnail_url ? (
                        <img
                          src={gen.thumbnail_url}
                          alt=""
                          className="w-10 h-10 rounded object-cover"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded bg-gray-100" />
                      )}
                    </td>
                    <td className="py-2 px-2 text-gray-700">
                      {gen.published_at
                        ? formatDate(gen.published_at, 'date')
                        : '--'}
                    </td>
                    <td className="py-2 px-2">
                      <div className="flex gap-1">
                        {Object.keys(gen.platforms).length > 0
                          ? Object.keys(gen.platforms).map((p) => (
                              <span
                                key={p}
                                className="text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-600"
                              >
                                {PLATFORM_ICONS[p] || p}
                              </span>
                            ))
                          : <StatusBadge status={gen.metrics_status} />}
                      </div>
                    </td>
                    {hasMetrics ? (
                      <>
                        <td className="py-2 px-2 text-right font-medium">
                          {formatNumber(totalViews)}
                        </td>
                        <td className="py-2 px-2 text-right">{formatRate(maxEngagement)}</td>
                        <td className="py-2 px-2 text-right">{formatRate(maxVirality)}</td>
                        <td className="py-2 px-2 text-right">{formatNumber(totalSaves)}</td>
                      </>
                    ) : (
                      <td colSpan={4} className="py-2 px-2 text-center">
                        <StatusBadge status={gen.metrics_status} />
                      </td>
                    )}
                  </tr>
                  {/* Expanded per-platform breakdown */}
                  {isExpanded && platformEntries.length > 1 && (
                    <tr>
                      <td colSpan={7} className="bg-gray-50 px-4 py-2">
                        <div className="flex items-center gap-4 text-xs text-gray-400 mb-1">
                          <span className="w-6">Plt</span>
                          <span className="w-16 text-right">Views</span>
                          <span className="w-14 text-right">Engage%</span>
                          <span className="w-14 text-right">Viral%</span>
                          <span className="w-14 text-right">Saves</span>
                          <span className="w-14 text-right">Reach</span>
                        </div>
                        {platformEntries.map(([platform, metrics]) => (
                          <PlatformMetricsRow
                            key={platform}
                            platform={platform}
                            metrics={metrics}
                          />
                        ))}
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
