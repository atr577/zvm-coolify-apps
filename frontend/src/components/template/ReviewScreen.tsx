import { AlertCircle } from 'lucide-react'
import { ModerationQueue } from './ModerationQueue'
import { RejectionArchive } from './RejectionArchive'

interface ReviewScreenProps {
  projectId: number
  pendingCount: number
}

export function ReviewScreen({ projectId, pendingCount }: ReviewScreenProps) {
  return (
    <div className="space-y-6">
      {/* Phase 2 notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-blue-900 mb-1">
              Focused review coming in Phase 2
            </h3>
            <p className="text-sm text-blue-700">
              The new one-at-a-time review experience is under development. For now, use the
              moderation queue below.
            </p>
            {pendingCount > 0 && (
              <p className="text-sm font-medium text-blue-900 mt-2">
                {pendingCount} video{pendingCount !== 1 ? 's' : ''} pending review
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Fallback: existing moderation components */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Moderation Queue</h3>
        <ModerationQueue projectId={projectId} />
      </div>

      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Rejection Archive</h3>
        <RejectionArchive projectId={projectId} />
      </div>
    </div>
  )
}
