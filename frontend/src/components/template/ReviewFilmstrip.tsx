import { useEffect, useRef } from 'react'
import { ImageOff } from 'lucide-react'
import type { ModerationQueueItem } from '@/services/api'

type ItemStatus = 'pending' | 'approved' | 'rejected' | 'redo'

interface ReviewFilmstripProps {
  items: ModerationQueueItem[]
  currentIndex: number
  getStatus: (itemId: number) => ItemStatus
  onNavigate: (index: number) => void
}

const STATUS_BORDER: Record<ItemStatus, string> = {
  pending: 'border-gray-300',
  approved: 'border-green-500',
  rejected: 'border-red-500',
  redo: 'border-blue-400',
}

export function ReviewFilmstrip({ items, currentIndex, getStatus, onNavigate }: ReviewFilmstripProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLDivElement>(null)

  // Scroll active item into view
  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
  }, [currentIndex])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyboard = (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input/textarea
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return

      if (e.key === 'ArrowLeft' && currentIndex > 0) {
        e.preventDefault()
        onNavigate(currentIndex - 1)
      } else if (e.key === 'ArrowRight' && currentIndex < items.length - 1) {
        e.preventDefault()
        onNavigate(currentIndex + 1)
      }
    }
    window.addEventListener('keydown', handleKeyboard)
    return () => window.removeEventListener('keydown', handleKeyboard)
  }, [currentIndex, items.length, onNavigate])

  if (items.length === 0) return null

  return (
    <div className="border-t pt-4">
      <div ref={containerRef} className="overflow-x-auto pb-2">
        <div className="flex gap-2">
          {items.map((item, index) => {
            const status = getStatus(item.id)
            const isCurrent = index === currentIndex

            return (
              <div
                key={item.id}
                ref={isCurrent ? activeRef : undefined}
                onClick={() => onNavigate(index)}
                className={`
                  flex-shrink-0 w-16 h-24 cursor-pointer rounded overflow-hidden
                  border-2 ${STATUS_BORDER[status]}
                  ${isCurrent ? 'ring-2 ring-purple-600 ring-offset-1' : 'hover:opacity-80'}
                  transition
                `}
              >
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={`#${item.id}`}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                    <ImageOff className="w-4 h-4 text-gray-400" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
