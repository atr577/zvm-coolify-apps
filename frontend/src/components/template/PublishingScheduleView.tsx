import { useState } from 'react'
import { Calendar, CheckCircle, XCircle, AlertCircle, Loader2, X, Play } from 'lucide-react'
import type { PublishingScheduleResponse, ScheduleSlot } from '@/services/api'
import { formatDate } from '@/utils/date'
import VideoPreview from '@/components/video/VideoPreview'

interface PublishingScheduleViewProps {
  schedule: PublishingScheduleResponse
  onRefresh: () => void
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'published':
      return <CheckCircle className="w-4 h-4 text-green-500" />
    case 'publishing':
      return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
    case 'partially_published':
      return <AlertCircle className="w-4 h-4 text-yellow-500" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />
    default:
      return null
  }
}

interface SlotCardProps {
  slot: ScheduleSlot
  onClick?: () => void
}

function SlotCard({ slot, onClick }: SlotCardProps) {
  const hasItem = slot.item !== null
  const isClickable = hasItem && onClick

  return (
    <div
      onClick={isClickable ? onClick : undefined}
      className={`rounded-lg border overflow-hidden ${
        hasItem ? 'bg-white border-gray-200' : 'bg-gray-50 border-dashed border-gray-300'
      } ${isClickable ? 'cursor-pointer hover:border-purple-400 hover:shadow-md transition-all' : ''}`}
    >
      {/* Thumbnail or empty placeholder */}
      <div className="aspect-[9/16] bg-gray-100 relative group">
        {hasItem && slot.item!.thumbnail_url ? (
          <>
            <img
              src={slot.item!.thumbnail_url}
              alt="Thumbnail"
              className="w-full h-full object-cover"
            />
            {/* Play icon overlay on hover */}
            {isClickable && (
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                <div className="w-10 h-10 bg-white/90 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg">
                  <Play className="w-5 h-5 text-purple-600 ml-0.5" />
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-300">
            <Calendar className="w-8 h-8" />
          </div>
        )}

        {/* Status badge overlay */}
        {hasItem && (
          <div className="absolute top-2 right-2">
            {getStatusBadge(slot.item!.status)}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-gray-900">{formatDate(slot.scheduled_at, 'weekday')}</span>
          <span className="text-gray-500">{formatDate(slot.scheduled_at, 'time')}</span>
        </div>

        {hasItem ? (
          <>
            {/* Title preview */}
            {slot.item!.publishing_metadata && Object.values(slot.item!.publishing_metadata)[0]?.title && (
              <p className="text-xs text-gray-600 line-clamp-2">
                {Object.values(slot.item!.publishing_metadata)[0].title}
              </p>
            )}
          </>
        ) : (
          <p className="text-xs text-gray-400">Пустой слот</p>
        )}
      </div>
    </div>
  )
}

// Modal for video preview
interface VideoPreviewModalProps {
  slot: ScheduleSlot
  onClose: () => void
}

function VideoPreviewModal({ slot, onClose }: VideoPreviewModalProps) {
  const item = slot.item!
  const metadata = item.publishing_metadata
  const firstPlatform = metadata ? Object.entries(metadata)[0] : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />

      {/* Modal content */}
      <div className="relative bg-white rounded-xl shadow-2xl max-w-lg w-full max-h-[90vh] flex flex-col">
        {/* Header - fixed */}
        <div className="flex items-center justify-between p-4 border-b flex-shrink-0">
          <div>
            <h3 className="font-semibold text-gray-900">
              {formatDate(slot.scheduled_at)}
            </h3>
            <p className="text-sm text-gray-500">
              Запланированная публикация
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto flex-1">
          {/* Video */}
          <div className="p-4">
            <div className="max-w-xs mx-auto">
              <VideoPreview
                videoUrl={item.video_url}
                thumbnailUrl={item.thumbnail_url}
                className="w-full"
                aspectRatio="9/16"
              />
            </div>
          </div>

          {/* Metadata */}
          {firstPlatform && (
            <div className="px-4 pb-4 space-y-2">
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase">
                  {firstPlatform[0]}
                </span>
              </div>
              {firstPlatform[1].title && (
                <h4 className="font-medium text-gray-900">
                  {firstPlatform[1].title}
                </h4>
              )}
              {firstPlatform[1].description && (
                <p className="text-sm text-gray-600">
                  {firstPlatform[1].description}
                </p>
              )}
              {firstPlatform[1].hashtags && (
                <p className="text-sm text-purple-600">
                  {firstPlatform[1].hashtags}
                </p>
              )}
            </div>
          )}

          {/* Status - only show if not just "approved" */}
          {item.status !== 'approved' && (
            <div className="px-4 pb-4">
              <div className="flex items-center gap-2 text-sm">
                {getStatusBadge(item.status)}
                <span className="text-gray-600 capitalize">{item.status}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function PublishingScheduleView({ schedule, onRefresh }: PublishingScheduleViewProps) {
  const [selectedSlot, setSelectedSlot] = useState<ScheduleSlot | null>(null)

  if (schedule.slots.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <Calendar className="w-12 h-12 mx-auto mb-4 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">Расписание не настроено</h3>
        <p className="text-sm text-gray-500">
          Выберите дни и время публикации выше.
        </p>
      </div>
    )
  }

  const filledSlots = schedule.slots.filter(s => s.item).length
  const totalSlots = schedule.slots.length

  return (
    <>
      <div className="bg-white rounded-lg border p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900">Расписание</h3>
            <p className="text-sm text-gray-500">
              {filledSlots} из {totalSlots} слотов заполнено
            </p>
          </div>
          <button
            onClick={onRefresh}
            className="text-sm text-blue-600 hover:underline"
          >
            Обновить
          </button>
        </div>

        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-3">
          {schedule.slots.map((slot, idx) => (
            <SlotCard
              key={idx}
              slot={slot}
              onClick={slot.item ? () => setSelectedSlot(slot) : undefined}
            />
          ))}
        </div>
      </div>

      {/* Video Preview Modal */}
      {selectedSlot && selectedSlot.item && (
        <VideoPreviewModal
          slot={selectedSlot}
          onClose={() => setSelectedSlot(null)}
        />
      )}
    </>
  )
}
