import { GenerationPanel } from './GenerationPanel'
import { BatchProgress } from './BatchProgress'
import type { BatchGenerateResponse } from '@/types'

interface GenerateScreenProps {
  projectId: number
  refreshTrigger: number
  onBatchStarted: (response: BatchGenerateResponse) => void
}

export function GenerateScreen({
  projectId,
  refreshTrigger,
  onBatchStarted,
}: GenerateScreenProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <GenerationPanel
          projectId={projectId}
          onBatchStarted={onBatchStarted}
        />
      </div>
      <div className="lg:col-span-2">
        <div className="bg-white rounded-lg border p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Progress</h3>
          <BatchProgress projectId={projectId} refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </div>
  )
}
