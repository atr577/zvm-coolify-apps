import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { PipelineFunnel } from './PipelineFunnel'
import { PublishingScheduleView } from './PublishingScheduleView'
import { PublishingQueueView } from './PublishingQueueView'
import type { PublishingScheduleResponse, PublishingConfig } from '@/services/api'

interface DashboardScreenProps {
  projectId: number
  onNavigate: (screen: 'review' | 'generate' | 'details', options?: { section?: string }) => void
  config: PublishingConfig | null
  schedule: PublishingScheduleResponse | null
  onRefresh: () => void
  onTogglePause: () => Promise<void>
}

export function DashboardScreen({
  projectId,
  onNavigate,
  config,
  schedule,
  onRefresh,
  onTogglePause,
}: DashboardScreenProps) {
  const [view, setView] = useState<'calendar' | 'queue'>('calendar')
  const [isPauseToggling, setIsPauseToggling] = useState(false)

  const handleFunnelNavigate = (target: 'review' | 'generate' | 'queue' | 'calendar') => {
    if (target === 'review') {
      onNavigate('review')
    } else if (target === 'generate') {
      onNavigate('generate')
    } else if (target === 'queue') {
      setView('queue')
      document.getElementById('schedule-section')?.scrollIntoView({ behavior: 'smooth' })
    } else if (target === 'calendar') {
      setView('calendar')
      document.getElementById('schedule-section')?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const handlePauseToggle = async () => {
    if (!config) return
    try {
      setIsPauseToggling(true)
      await onTogglePause()
    } catch (err) {
      console.error('Failed to toggle pause:', err)
    } finally {
      setIsPauseToggling(false)
    }
  }

  const isConfigured = config && config.days.length > 0 && config.preferred_times.length > 0

  return (
    <div className="space-y-6">
      {/* Pipeline Funnel */}
      <PipelineFunnel projectId={projectId} onNavigate={handleFunnelNavigate} />

      {/* Status + Quick Actions */}
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            {config?.is_paused && (
              <div className="flex items-center gap-2 text-yellow-700 bg-yellow-50 px-3 py-2 rounded">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">Publishing inactive</span>
              </div>
            )}
            {schedule && schedule.slots.length > 0 && !config?.is_paused && (
              <p className="text-sm text-gray-600">
                Next publish:{' '}
                {new Date(schedule.slots[0]?.scheduled_at).toLocaleString()}
              </p>
            )}
            {schedule &&
              schedule.warnings
                .filter((w) => w.type !== 'config_disabled' || !config?.is_paused)
                .map((w, idx) => (
                  <p key={idx} className="text-sm text-yellow-600">
                    {w.message}
                  </p>
                ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => onNavigate('review')}
              className="px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
            >
              Review videos
            </button>
            <button
              onClick={() => onNavigate('generate')}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Generate
            </button>
          </div>
        </div>
      </div>

      {/* Schedule Section */}
      <div id="schedule-section">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Schedule</h3>
          <div className="flex items-center gap-4">
            {/* Active Toggle */}
            {isConfigured && (
              <label className="flex items-center gap-2 cursor-pointer">
                <span className="text-sm text-gray-600">Active</span>
                <button
                  onClick={handlePauseToggle}
                  disabled={isPauseToggling}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                    !config?.is_paused ? 'bg-green-500' : 'bg-gray-300'
                  } ${isPauseToggling ? 'opacity-50' : ''}`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                      !config?.is_paused ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </label>
            )}

            {/* Calendar/Queue Toggle */}
            <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setView('calendar')}
                className={`px-4 py-1 text-sm font-medium rounded-md transition ${
                  view === 'calendar'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Calendar
              </button>
              <button
                onClick={() => setView('queue')}
                className={`px-4 py-1 text-sm font-medium rounded-md transition ${
                  view === 'queue'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Queue
              </button>
            </div>
          </div>
        </div>

        {view === 'calendar' && schedule && (
          <PublishingScheduleView schedule={schedule} onRefresh={onRefresh} />
        )}
        {view === 'queue' && <PublishingQueueView projectId={projectId} onRefresh={onRefresh} />}

        {!isConfigured && (
          <div className="bg-white rounded-lg border p-8 text-center">
            <p className="text-sm text-gray-500">
              No schedule configured. Set up days and times in{' '}
              <button
                onClick={() => onNavigate('details')}
                className="text-purple-600 hover:underline"
              >
                Details &rarr; Distribution
              </button>
              .
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
