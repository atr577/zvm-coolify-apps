import { useState, useRef, useEffect } from 'react'
import { Check, X, Loader2, AlertCircle, Play, Trophy, Crown } from 'lucide-react'
import type { DiscoverItem, DiscoverRoundType } from '@/types'
import { getMediaUrl } from '@/utils/video'

interface ItemGridProps {
  items: DiscoverItem[]
  roundType: DiscoverRoundType
  selectable: boolean
  selections: Record<string, 'selected' | 'rejected'>
  onSelectionChange: (itemId: number, value: 'selected' | 'rejected' | null) => void
  finalistItemId?: number | null
  onCrownClick?: (itemId: number) => void
}

export function ItemGrid({ items, roundType, selectable, selections, onSelectionChange, finalistItemId, onCrownClick }: ItemGridProps) {
  return (
    <div className={`grid gap-3 ${
      roundType === 'video'
        ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
        : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5'
    }`}>
      {items.map(item => (
        <ItemCard
          key={item.id}
          item={item}
          roundType={roundType}
          selectable={selectable}
          selection={selections[String(item.id)] || null}
          onSelectionChange={(value) => onSelectionChange(item.id, value)}
          isFinalist={item.id === finalistItemId}
          onCrownClick={onCrownClick ? () => onCrownClick(item.id) : undefined}
        />
      ))}
    </div>
  )
}

interface ItemCardProps {
  item: DiscoverItem
  roundType: DiscoverRoundType
  selectable: boolean
  selection: 'selected' | 'rejected' | null
  onSelectionChange: (value: 'selected' | 'rejected' | null) => void
  isFinalist?: boolean
  onCrownClick?: () => void
}

function ItemCard({ item, roundType, selectable, selection, onSelectionChange, isFinalist, onCrownClick }: ItemCardProps) {
  const [showPrompt, setShowPrompt] = useState(false)
  const mediaUrl = getMediaUrl(item.local_path, item.result_url)

  const borderClass = isFinalist
    ? 'ring-2 ring-amber-400'
    : selection === 'selected'
    ? 'ring-2 ring-green-500'
    : selection === 'rejected'
    ? 'ring-2 ring-red-400 opacity-60'
    : ''

  const mediaContent = (
    <>
      {/* Selection buttons */}
      {selectable && item.status === 'completed' && (
        <div className="absolute bottom-2 left-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onSelectionChange(selection === 'selected' ? null : 'selected')
            }}
            className={`flex-1 py-1.5 rounded text-xs font-medium flex items-center justify-center gap-1 transition ${
              selection === 'selected'
                ? 'bg-green-500 text-white'
                : 'bg-white/90 text-gray-700 hover:bg-green-100'
            }`}
          >
            <Check className="h-3 w-3" />
          </button>
          {/* Crown button — pick finalist */}
          {onCrownClick && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onCrownClick()
              }}
              className={`flex-1 py-1.5 rounded text-xs font-medium flex items-center justify-center gap-1 transition ${
                isFinalist
                  ? 'bg-amber-500 text-white'
                  : 'bg-white/90 text-gray-700 hover:bg-amber-100'
              }`}
            >
              <Crown className="h-3 w-3" />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation()
              onSelectionChange(selection === 'rejected' ? null : 'rejected')
            }}
            className={`flex-1 py-1.5 rounded text-xs font-medium flex items-center justify-center gap-1 transition ${
              selection === 'rejected'
                ? 'bg-red-500 text-white'
                : 'bg-white/90 text-gray-700 hover:bg-red-100'
            }`}
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* Selection badge */}
      {selection && (
        <div className={`absolute top-2 right-2 w-6 h-6 rounded-full flex items-center justify-center z-10 ${
          selection === 'selected' ? 'bg-green-500' : 'bg-red-500'
        }`}>
          {selection === 'selected' ? <Check className="h-3 w-3 text-white" /> : <X className="h-3 w-3 text-white" />}
        </div>
      )}

      {/* Position number + finalist badge */}
      <div className="absolute top-2 left-2 flex items-center gap-1 z-10">
        <div className="w-5 h-5 rounded-full bg-black/50 text-white text-xs flex items-center justify-center">
          {item.position}
        </div>
        {isFinalist && (
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-amber-400 text-amber-900 text-[10px] font-bold">
            {roundType === 'video' ? <Crown className="h-3 w-3" /> : <Trophy className="h-3 w-3" />}
            Winner
          </div>
        )}
      </div>

      {/* Prompt overlay on hover (images only) */}
      {item.status === 'completed' && roundType !== 'video' && (
        <div className={`absolute inset-0 bg-black/70 text-white text-xs p-2 overflow-y-auto transition-opacity ${
          showPrompt ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
        }`}>
          <p>{item.prompt}</p>
        </div>
      )}
    </>
  )

  return (
    <div className={`group rounded-lg overflow-hidden bg-gray-100 ${borderClass}`}>
      {/* Media + overlays */}
      {item.status === 'completed' && mediaUrl ? (
        roundType === 'video' ? (
          <>
            <div className="relative">
              <VideoPreview url={mediaUrl} />
              {mediaContent}
            </div>
            <div
              className="px-2 py-1.5 bg-gray-900 text-gray-300 text-[11px] leading-tight cursor-pointer"
              onClick={() => setShowPrompt(!showPrompt)}
            >
              <p className={showPrompt ? '' : 'line-clamp-6'}>{item.prompt}</p>
            </div>
          </>
        ) : (
          <div className="relative">
            <img
              src={mediaUrl}
              alt={`Item ${item.position}`}
              className="w-full aspect-[9/16] object-cover cursor-pointer"
              onClick={() => setShowPrompt(!showPrompt)}
            />
            {mediaContent}
          </div>
        )
      ) : item.status === 'generating' || item.status === 'pending' ? (
        <div className="w-full aspect-[9/16] flex flex-col items-center justify-center text-gray-400">
          <Loader2 className="h-8 w-8 animate-spin mb-2" />
          <span className="text-xs">Generating...</span>
        </div>
      ) : item.status === 'failed' ? (
        <div className="w-full aspect-[9/16] flex flex-col items-center justify-center text-red-400 px-3">
          <AlertCircle className="h-8 w-8 mb-2" />
          <span className="text-xs text-center">{item.error_message || 'Failed'}</span>
        </div>
      ) : null}
    </div>
  )
}

function VideoPreview({ url }: { url: string }) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    if (!videoRef.current) return
    if (playing) {
      videoRef.current.play().catch(() => setPlaying(false))
    } else {
      videoRef.current.pause()
    }
  }, [playing])

  return (
    <div className="relative w-full aspect-[9/16]">
      <video
        ref={videoRef}
        src={url}
        className="w-full h-full object-cover cursor-pointer"
        loop
        muted
        playsInline
        onClick={() => setPlaying(p => !p)}
      />
      {!playing && (
        <div
          className="absolute inset-0 flex items-center justify-center cursor-pointer"
          onClick={(e) => { e.stopPropagation(); setPlaying(true) }}
        >
          <div className="w-12 h-12 rounded-full bg-black/50 flex items-center justify-center">
            <Play className="h-6 w-6 text-white ml-1" />
          </div>
        </div>
      )}
    </div>
  )
}
