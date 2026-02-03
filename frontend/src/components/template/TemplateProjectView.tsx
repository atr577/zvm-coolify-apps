import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Settings, Loader2 } from 'lucide-react'
import { DashboardScreen } from './DashboardScreen'
import { ReviewScreen } from './ReviewScreen'
import { PipelineScreen } from './PipelineScreen'
import {
  publishingScheduleApi,
  type PublishingConfig,
  type PublishingScheduleResponse,
  type PipelineStats,
} from '@/services/api'
import type { CSVUploadResponse, Generation } from '@/types'

interface TemplateProjectViewProps {
  projectId: number
  projectName: string
  projectTimezone?: string
}

type ScreenType = 'dashboard' | 'review' | 'pipeline'

const VALID_SCREENS: ScreenType[] = ['dashboard', 'review', 'pipeline']

// Map old tab params to new screens for backward compatibility
const TAB_TO_SCREEN: Record<string, ScreenType> = {
  generate: 'pipeline',
  variants: 'pipeline',
  templates: 'pipeline',
  moderation: 'review',
  publishing: 'dashboard',
}

export function TemplateProjectView({
  projectId,
  projectName,
}: TemplateProjectViewProps) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [generationsRefresh, setGenerationsRefresh] = useState(0)

  // Data state
  const [config, setConfig] = useState<PublishingConfig | null>(null)
  const [schedule, setSchedule] = useState<PublishingScheduleResponse | null>(null)
  const [stats, setStats] = useState<PipelineStats | null>(null)
  const [initialLoading, setInitialLoading] = useState(true)

  // Determine current screen from URL
  const getScreenFromUrl = (): ScreenType | null => {
    const screenParam = searchParams.get('screen')
    if (screenParam && VALID_SCREENS.includes(screenParam as ScreenType)) {
      return screenParam as ScreenType
    }
    // Backward compatibility: old ?tab= params
    const tabParam = searchParams.get('tab')
    if (tabParam && tabParam in TAB_TO_SCREEN) {
      return TAB_TO_SCREEN[tabParam]
    }
    return null
  }

  const [currentScreen, setCurrentScreen] = useState<ScreenType>(
    getScreenFromUrl() || 'dashboard'
  )

  // Fetch publishing data
  const fetchPublishingData = useCallback(async () => {
    try {
      const [configRes, scheduleRes] = await Promise.all([
        publishingScheduleApi.getConfig(projectId),
        publishingScheduleApi.getSchedule(projectId),
      ])
      setConfig(configRes.data)
      setSchedule(scheduleRes.data)
    } catch (err) {
      console.error('Failed to load publishing data:', err)
    }
  }, [projectId])

  // Smart default screen logic + initial data load
  useEffect(() => {
    const init = async () => {
      try {
        const [statsRes] = await Promise.all([
          publishingScheduleApi.getPipelineStats(projectId),
          fetchPublishingData(),
        ])
        const statsData = statsRes.data
        setStats(statsData)

        // Only apply smart default if no explicit screen in URL
        const urlScreen = getScreenFromUrl()
        if (!urlScreen) {
          let defaultScreen: ScreenType = 'dashboard'

          // No variants or templates → pipeline (setup)
          if (statsData.variants_count === 0 || statsData.templates_count === 0) {
            defaultScreen = 'pipeline'
          } else if (statsData.review_count > 0) {
            // Items pending review → review
            defaultScreen = 'review'
          }

          setCurrentScreen(defaultScreen)
          setSearchParams(prev => {
            prev.set('screen', defaultScreen)
            prev.delete('tab')
            return prev
          }, { replace: true })
        } else {
          setCurrentScreen(urlScreen)
          // Normalize URL: replace ?tab= with ?screen=
          if (searchParams.get('tab')) {
            setSearchParams(prev => {
              prev.set('screen', urlScreen)
              prev.delete('tab')
              return prev
            }, { replace: true })
          }
        }
      } catch (err) {
        console.error('Failed to initialize:', err)
      } finally {
        setInitialLoading(false)
      }
    }
    init()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const handleNavigate = (screen: ScreenType) => {
    setCurrentScreen(screen)
    setSearchParams(prev => {
      prev.set('screen', screen)
      return prev
    })
  }

  const handleCsvUploadSuccess = (_response: CSVUploadResponse) => {
    setRefreshTrigger((prev) => prev + 1)
  }

  const handleGenerationStarted = (_generation: Generation) => {
    setGenerationsRefresh((prev) => prev + 1)
  }

  const handleTogglePause = async () => {
    if (!config) return
    const updated = {
      enabled: config.enabled,
      is_paused: !config.is_paused,
      days: config.days,
      preferred_times: config.preferred_times,
      depth_days: config.depth_days,
    }
    const res = await publishingScheduleApi.updateConfig(projectId, updated)
    setConfig(res.data)
    // Refresh schedule too
    const scheduleRes = await publishingScheduleApi.getSchedule(projectId)
    setSchedule(scheduleRes.data)
  }

  if (initialLoading) {
    return (
      <div className="flex-1 h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="flex-1 h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">{projectName}</h1>
          <button
            onClick={() => navigate(`/project/${projectId}/edit`)}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            <Settings className="h-5 w-5" />
          </button>
        </div>

        {/* Screen Switcher */}
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => handleNavigate('dashboard')}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition ${
              currentScreen === 'dashboard'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => handleNavigate('review')}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition relative ${
              currentScreen === 'review'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Review
            {stats && stats.review_count > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                {stats.review_count}
              </span>
            )}
          </button>
          <button
            onClick={() => handleNavigate('pipeline')}
            className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition ${
              currentScreen === 'pipeline'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Pipeline
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {currentScreen === 'dashboard' && (
          <DashboardScreen
            projectId={projectId}
            onNavigate={handleNavigate}
            config={config}
            schedule={schedule}
            onRefresh={fetchPublishingData}
            onTogglePause={handleTogglePause}
          />
        )}

        {currentScreen === 'review' && (
          <ReviewScreen
            projectId={projectId}
            pendingCount={stats?.review_count || 0}
            onNavigate={handleNavigate}
          />
        )}

        {currentScreen === 'pipeline' && (
          <PipelineScreen
            projectId={projectId}
            refreshTrigger={refreshTrigger}
            generationsRefresh={generationsRefresh}
            onCsvUploadSuccess={handleCsvUploadSuccess}
            onGenerationStarted={handleGenerationStarted}
          />
        )}
      </div>
    </div>
  )
}
