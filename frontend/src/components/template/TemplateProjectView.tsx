import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Settings } from 'lucide-react'
import { CsvUpload } from './CsvUpload'
import { VariantsList } from './VariantsList'
import { VideoTemplatesList } from './VideoTemplatesList'
import { GenerationPanel } from './GenerationPanel'
import { GenerationsList } from './GenerationsList'
import { ModerationQueue } from './ModerationQueue'
import { RejectionArchive } from './RejectionArchive'
import type { CSVUploadResponse, Generation } from '@/types'

interface TemplateProjectViewProps {
  projectId: number
  projectName: string
}

type TabType = 'generate' | 'variants' | 'templates' | 'moderation'

export function TemplateProjectView({ projectId, projectName }: TemplateProjectViewProps) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [generationsRefresh, setGenerationsRefresh] = useState(0)

  // Get tab from URL or default to 'generate'
  const tabParam = searchParams.get('tab')
  const validTabs: TabType[] = ['generate', 'moderation', 'variants', 'templates']
  const activeTab: TabType = validTabs.includes(tabParam as TabType) ? (tabParam as TabType) : 'generate'

  const handleTabChange = (tab: TabType) => {
    setSearchParams(prev => {
      prev.set('tab', tab)
      return prev
    })
  }

  const handleCsvUploadSuccess = (_response: CSVUploadResponse) => {
    setRefreshTrigger(prev => prev + 1)
  }

  const handleGenerationStarted = (_generation: Generation) => {
    setGenerationsRefresh(prev => prev + 1)
  }

  const tabs: { key: TabType; label: string }[] = [
    { key: 'generate', label: 'Generate' },
    { key: 'moderation', label: 'Moderation' },
    { key: 'variants', label: 'Variants' },
    { key: 'templates', label: 'Templates' },
  ]

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
        {/* Tabs */}
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key)}
              className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition ${
                activeTab === tab.key
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'generate' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <GenerationPanel
                projectId={projectId}
                onGenerationStarted={handleGenerationStarted}
              />
            </div>
            <div className="lg:col-span-2">
              <div className="bg-white rounded-lg border p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Generations</h3>
                <GenerationsList
                  projectId={projectId}
                  refreshTrigger={generationsRefresh}
                />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'moderation' && (
          <div className="space-y-8">
            <div className="bg-white rounded-lg border p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Moderation Queue</h3>
              <ModerationQueue projectId={projectId} />
            </div>

            <div className="bg-white rounded-lg border p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Rejection Archive</h3>
              <RejectionArchive projectId={projectId} />
            </div>
          </div>
        )}

        {activeTab === 'variants' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-4">Upload CSV</h2>
              <CsvUpload
                projectId={projectId}
                onUploadSuccess={handleCsvUploadSuccess}
              />
            </div>

            <div>
              <h2 className="text-lg font-medium text-gray-900 mb-4">Variants</h2>
              <VariantsList
                projectId={projectId}
                refreshTrigger={refreshTrigger}
              />
            </div>
          </div>
        )}

        {activeTab === 'templates' && (
          <VideoTemplatesList projectId={projectId} />
        )}
      </div>
    </div>
  )
}
