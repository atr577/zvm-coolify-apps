import VideoPreview from '@/components/video/VideoPreview'
import { ReviewActions } from './ReviewActions'
import { ReviewMetadata } from './ReviewMetadata'
import { Calendar, ExternalLink } from 'lucide-react'
import type { ModerationQueueItem, PlatformMetadata, ScheduleSlot } from '@/services/api'

interface ReviewFocusedViewProps {
  item: ModerationQueueItem
  targetSlot: ScheduleSlot | null
  slotsInfo: string | null
  metadata: Record<string, PlatformMetadata> | null
  metadataLoading: boolean
  metadataError: string | null
  onMetadataChange: (metadata: Record<string, PlatformMetadata>) => void
  onMetadataRetry: () => void
  onApprove: () => void
  onReject: (reason: string, comment?: string) => void
  onRedo: (feedback?: string) => void
  actionLoading: boolean
}

export function ReviewFocusedView({
  item,
  targetSlot,
  slotsInfo,
  metadata,
  metadataLoading,
  metadataError,
  onMetadataChange,
  onMetadataRetry,
  onApprove,
  onReject,
  onRedo,
  actionLoading,
}: ReviewFocusedViewProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Video Preview */}
      <div className="flex flex-col items-center">
        <VideoPreview
          videoUrl={item.video_url}
          thumbnailUrl={item.image_url}
          aspectRatio="9/16"
          className="w-full max-w-sm"
        />
        {item.image_url && (
          <a
            href={item.image_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-blue-600 hover:underline mt-2"
          >
            <ExternalLink className="w-3 h-3" />
            View source image
          </a>
        )}
      </div>

      {/* Right: Data + Actions + Metadata */}
      <div className="space-y-5">
        {/* Variant data */}
        {item.variant && item.variant.data && (
          <div>
            <h4 className="text-sm font-medium text-gray-500 mb-2">Variant data</h4>
            <div className="bg-gray-50 rounded-lg p-3 space-y-1">
              {Object.entries(item.variant.data).map(([key, value]) => (
                <div key={key} className="flex text-sm">
                  <span className="text-gray-400 w-28 flex-shrink-0">{key}:</span>
                  <span className="text-gray-900">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Template name */}
        {item.video_template && (
          <div className="text-sm">
            <span className="text-gray-500">Template:</span>{' '}
            <span className="font-medium text-gray-900">{item.video_template.name}</span>
          </div>
        )}

        {/* Target slot */}
        <div className="flex items-center gap-2 text-sm">
          <Calendar className="w-4 h-4 text-gray-400" />
          {targetSlot ? (
            <span className="text-gray-700">
              Publish to:{' '}
              <span className="font-medium">
                {new Date(targetSlot.scheduled_at).toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                })}{' '}
                {new Date(targetSlot.scheduled_at).toLocaleTimeString('en-US', {
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                })}
              </span>
              {slotsInfo && <span className="text-gray-400 ml-1">({slotsInfo})</span>}
            </span>
          ) : (
            <span className="text-gray-500">
              All slots filled. Video will queue for next available slot.
            </span>
          )}
        </div>

        {/* Actions */}
        <ReviewActions
          onApprove={onApprove}
          onReject={onReject}
          onRedo={onRedo}
          targetSlot={targetSlot}
          disabled={actionLoading}
        />

        {/* Metadata */}
        <ReviewMetadata
          metadata={metadata}
          loading={metadataLoading}
          error={metadataError}
          onChange={onMetadataChange}
          onRetry={onMetadataRetry}
        />
      </div>
    </div>
  )
}
