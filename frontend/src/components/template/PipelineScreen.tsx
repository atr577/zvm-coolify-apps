import { ConfigureSection } from './ConfigureSection'
import { GenerationPanel } from './GenerationPanel'
import { GenerationsList } from './GenerationsList'
import type { Generation } from '@/types'

interface PipelineScreenProps {
  projectId: number
  generationsRefresh: number
  onGenerationStarted: (generation: Generation) => void
}

export function PipelineScreen({
  projectId,
  generationsRefresh,
  onGenerationStarted,
}: PipelineScreenProps) {
  return (
    <div className="space-y-6">
      {/* Configure section */}
      <ConfigureSection projectId={projectId} />

      {/* Run section */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 mb-4">Run</h2>
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
    </div>
  )
}
