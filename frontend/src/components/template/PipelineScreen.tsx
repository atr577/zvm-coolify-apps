import { AlertCircle } from 'lucide-react'
import { CsvUpload } from './CsvUpload'
import { VariantsList } from './VariantsList'
import { VideoTemplatesList } from './VideoTemplatesList'
import { GenerationPanel } from './GenerationPanel'
import { GenerationsList } from './GenerationsList'
import type { CSVUploadResponse, Generation } from '@/types'

interface PipelineScreenProps {
  projectId: number
  refreshTrigger: number
  generationsRefresh: number
  onCsvUploadSuccess: (response: CSVUploadResponse) => void
  onGenerationStarted: (generation: Generation) => void
}

export function PipelineScreen({
  projectId,
  refreshTrigger,
  generationsRefresh,
  onCsvUploadSuccess,
  onGenerationStarted,
}: PipelineScreenProps) {
  return (
    <div className="space-y-6">
      {/* Phase 3 notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-blue-900 mb-1">
              Unified pipeline coming in Phase 3
            </h3>
            <p className="text-sm text-blue-700">
              The new accordion-based pipeline configuration is under development. For now, use
              the sections below.
            </p>
          </div>
        </div>
      </div>

      {/* Generate section */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Generate</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <GenerationPanel
              projectId={projectId}
              onGenerationStarted={onGenerationStarted}
            />
          </div>
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg border p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Generations</h3>
              <GenerationsList projectId={projectId} refreshTrigger={generationsRefresh} />
            </div>
          </div>
        </div>
      </div>

      {/* Variants section */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Variants</h2>
        <div className="space-y-4">
          <CsvUpload projectId={projectId} onUploadSuccess={onCsvUploadSuccess} />
          <VariantsList projectId={projectId} refreshTrigger={refreshTrigger} />
        </div>
      </div>

      {/* Templates section */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Templates</h2>
        <VideoTemplatesList projectId={projectId} />
      </div>
    </div>
  )
}
