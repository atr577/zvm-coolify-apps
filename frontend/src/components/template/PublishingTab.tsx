import { useState, useEffect } from 'react'
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { publishingScheduleApi, type PublishingScheduleResponse, type PublishingConfig as PublishingConfigType } from '@/services/api'
import { PublishingConfigForm } from './PublishingConfigForm'
import { PublishingScheduleView } from './PublishingScheduleView'
import { PublishingQueueView } from './PublishingQueueView'

interface PublishingTabProps {
  projectId: number
  projectTimezone: string
}

export function PublishingTab({ projectId, projectTimezone }: PublishingTabProps) {
  const [config, setConfig] = useState<PublishingConfigType | null>(null)
  const [schedule, setSchedule] = useState<PublishingScheduleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<'schedule' | 'queue'>('schedule')

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [configRes, scheduleRes] = await Promise.all([
        publishingScheduleApi.getConfig(projectId),
        publishingScheduleApi.getSchedule(projectId)
      ])

      setConfig(configRes.data)
      setSchedule(scheduleRes.data)
    } catch (err) {
      console.error('Failed to load publishing data:', err)
      setError('Failed to load publishing data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [projectId])

  const handleConfigUpdate = async (data: {
    enabled: boolean
    days: string[]
    preferred_times: string[]
    depth_days: number
  }) => {
    try {
      const response = await publishingScheduleApi.updateConfig(projectId, {
        ...data,
        is_paused: config?.is_paused ?? false,
      })
      setConfig(response.data)
      // Refetch schedule to get updated slots
      const scheduleRes = await publishingScheduleApi.getSchedule(projectId)
      setSchedule(scheduleRes.data)
    } catch (err) {
      console.error('Failed to update config:', err)
      throw err
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={fetchData}
            className="mt-2 text-sm text-blue-600 hover:underline flex items-center gap-1 mx-auto"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Warnings */}
      {schedule?.warnings && schedule.warnings.length > 0 && (
        <div className="space-y-2">
          {schedule.warnings.map((warning, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg text-sm ${
                warning.type === 'config_disabled'
                  ? 'bg-gray-100 text-gray-700'
                  : warning.type === 'no_platforms'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-yellow-50 text-yellow-700'
              }`}
            >
              {warning.message}
            </div>
          ))}
        </div>
      )}

      {/* Config Form */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Schedule Settings</h3>
        {config && (
          <PublishingConfigForm
            config={config}
            timezone={projectTimezone}
            onUpdate={handleConfigUpdate}
          />
        )}
      </div>

      {/* Section Toggle */}
      <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveSection('schedule')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition ${
            activeSection === 'schedule'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Schedule View
        </button>
        <button
          onClick={() => setActiveSection('queue')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition ${
            activeSection === 'queue'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Queue ({schedule?.slots.filter(s => s.item).length || 0})
        </button>
      </div>

      {/* Content */}
      {activeSection === 'schedule' && schedule && (
        <PublishingScheduleView
          schedule={schedule}
          onRefresh={fetchData}
        />
      )}

      {activeSection === 'queue' && (
        <PublishingQueueView
          projectId={projectId}
          onRefresh={fetchData}
        />
      )}
    </div>
  )
}
