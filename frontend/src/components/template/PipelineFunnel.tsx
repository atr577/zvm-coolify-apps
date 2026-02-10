import { useState, useEffect, useCallback } from 'react'
import { Loader2, PlayCircle, Eye, CheckCircle, Calendar, Send } from 'lucide-react'
import { publishingScheduleApi, type PipelineStats } from '@/services/api'

interface PipelineFunnelProps {
  projectId: number
  onNavigate: (target: 'review' | 'generate' | 'queue' | 'calendar') => void
}

export function PipelineFunnel({ projectId, onNavigate }: PipelineFunnelProps) {
  const [stats, setStats] = useState<PipelineStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      const { data } = await publishingScheduleApi.getPipelineStats(projectId)
      setStats(data)
    } catch (err) {
      console.error('Failed to load pipeline stats:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [fetchStats])

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!stats) return null

  const counters = [
    {
      label: 'Generating',
      count: stats.generating_count,
      icon: PlayCircle,
      onClick: () => onNavigate('generate'),
      highlight: stats.generating_count > 0,
    },
    {
      label: 'Review',
      count: stats.review_count,
      icon: Eye,
      onClick: () => onNavigate('review'),
      highlight: stats.review_count > 0,
    },
    {
      label: 'Approved',
      count: stats.approved_count,
      icon: CheckCircle,
      onClick: () => onNavigate('queue'),
      highlight: false,
    },
    {
      label: 'Schedule',
      count: `${stats.scheduled_count}/${stats.total_schedule_slots}`,
      icon: Calendar,
      onClick: () => onNavigate('calendar'),
      highlight: stats.total_schedule_slots > 0 && stats.scheduled_count < stats.total_schedule_slots,
    },
    {
      label: 'Published',
      count: stats.published_count,
      icon: Send,
      onClick: () => onNavigate('queue'),
      highlight: false,
    },
  ]

  return (
    <div className="bg-white rounded-lg border p-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">Pipeline Status</h3>
      <div className="grid grid-cols-5 gap-4">
        {counters.map((c) => (
          <button
            key={c.label}
            onClick={c.onClick}
            className={`flex flex-col items-center p-4 rounded-lg border transition-all ${
              c.highlight
                ? 'bg-purple-50 border-purple-300 hover:bg-purple-100'
                : 'hover:bg-gray-50 border-gray-200'
            }`}
          >
            <c.icon
              className={`w-6 h-6 mb-2 ${c.highlight ? 'text-purple-600' : 'text-gray-400'}`}
            />
            <div
              className={`text-2xl font-bold ${c.highlight ? 'text-purple-700' : 'text-gray-900'}`}
            >
              {c.count}
            </div>
            <div className="text-xs text-gray-500 mt-1">{c.label}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
