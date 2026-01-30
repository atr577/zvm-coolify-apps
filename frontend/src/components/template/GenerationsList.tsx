import { useState, useEffect, useCallback } from 'react'
import { templateApi } from '@/services/api'
import type { Generation } from '@/types'

interface GenerationsListProps {
  projectId: number
  refreshTrigger?: number
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  preprocessing: 'bg-blue-100 text-blue-700',
  generating_image: 'bg-purple-100 text-purple-700',
  generating_video: 'bg-indigo-100 text-indigo-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  preprocessing: 'Processing...',
  generating_image: 'Image...',
  generating_video: 'Video...',
  completed: 'Completed',
  failed: 'Failed',
}

// Rating component
function RatingInput({
  label,
  value,
  comment,
  onRatingChange,
  onCommentChange,
}: {
  label: string
  value: number | null
  comment: string | null
  onRatingChange: (rating: number) => void
  onCommentChange: (comment: string) => void
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 w-12">{label}:</span>
        <div className="flex gap-1">
          {[0, 1, 2, 3, 4, 5].map((rating) => (
            <button
              key={rating}
              onClick={() => onRatingChange(rating)}
              className={`w-7 h-7 text-xs rounded border transition-colors ${
                value === rating
                  ? 'bg-purple-600 text-white border-purple-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-purple-400'
              }`}
            >
              {rating}
            </button>
          ))}
        </div>
        {value !== null && (
          <span className="text-xs text-gray-400 ml-2">({value}/5)</span>
        )}
      </div>
      <input
        type="text"
        value={comment || ''}
        onChange={(e) => onCommentChange(e.target.value)}
        placeholder="Comment..."
        className="w-full text-xs px-2 py-1 border border-gray-200 rounded focus:ring-1 focus:ring-purple-500 focus:border-purple-500"
      />
    </div>
  )
}

export function GenerationsList({ projectId, refreshTrigger }: GenerationsListProps) {
  const [generations, setGenerations] = useState<Generation[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const limit = 10

  // Polling for in-progress generations
  const [polling, setPolling] = useState(false)

  // Track pending rating updates
  const [savingRatings, setSavingRatings] = useState<Set<number>>(new Set())

  const loadGenerations = useCallback(async () => {
    try {
      const response = await templateApi.listGenerations(projectId, { offset, limit })
      setGenerations(response.data.generations)
      setTotal(response.data.total)

      // Check if any are in progress
      const hasInProgress = response.data.generations.some(g =>
        ['pending', 'preprocessing', 'generating_image', 'generating_video'].includes(g.status)
      )
      setPolling(hasInProgress)
    } catch (err) {
      console.error('Failed to load generations:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId, offset, limit])

  useEffect(() => {
    loadGenerations()
  }, [loadGenerations, refreshTrigger])

  // Polling effect
  useEffect(() => {
    if (!polling) return

    const interval = setInterval(() => {
      loadGenerations()
    }, 3000)

    return () => clearInterval(interval)
  }, [polling, loadGenerations])

  const handleRetry = async (generationId: number) => {
    try {
      await templateApi.retryGeneration(projectId, generationId)
      loadGenerations()
    } catch (err: unknown) {
      const errorMsg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Retry failed'
        : 'Retry failed'
      alert(errorMsg)
    }
  }

  const handleDelete = async (generationId: number) => {
    if (!confirm('Delete this generation?')) return
    try {
      await templateApi.deleteGeneration(projectId, generationId)
      loadGenerations()
    } catch (err) {
      console.error('Delete failed:', err)
      alert('Delete failed')
    }
  }

  const handleRatingUpdate = async (
    generationId: number,
    field: 'image_rating' | 'image_comment' | 'video_rating' | 'video_comment',
    value: number | string
  ) => {
    // Update local state immediately for responsiveness
    setGenerations(prev => prev.map(g =>
      g.id === generationId ? { ...g, [field]: value } : g
    ))

    // Debounce API call for comments
    if (field.includes('comment')) {
      // For comments, save after a short delay
      setSavingRatings(prev => new Set(prev).add(generationId))
      setTimeout(async () => {
        try {
          await templateApi.updateGenerationRating(projectId, generationId, { [field]: value })
        } catch (err) {
          console.error('Failed to save rating:', err)
        } finally {
          setSavingRatings(prev => {
            const next = new Set(prev)
            next.delete(generationId)
            return next
          })
        }
      }, 500)
    } else {
      // For ratings, save immediately
      try {
        await templateApi.updateGenerationRating(projectId, generationId, { [field]: value })
      } catch (err) {
        console.error('Failed to save rating:', err)
      }
    }
  }

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  if (loading && generations.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <svg className="animate-spin h-6 w-6 text-gray-400" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      </div>
    )
  }

  if (generations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No generations yet. Click "Generate Video" to start.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        {total} generation{total !== 1 ? 's' : ''} total
        {polling && <span className="ml-2 text-blue-600">(updating...)</span>}
      </div>

      <div className="space-y-4">
        {generations.map((gen) => (
          <div
            key={gen.id}
            className="border rounded-lg p-4 hover:bg-gray-50"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[gen.status] || 'bg-gray-100'}`}>
                  {STATUS_LABELS[gen.status] || gen.status}
                </span>
                <span className="text-xs text-gray-500">#{gen.id}</span>
                <span className="text-xs text-gray-400">
                  {new Date(gen.created_at).toLocaleString()}
                </span>
              </div>

              <div className="flex gap-2">
                {gen.status === 'failed' && (
                  <>
                    <button
                      onClick={() => handleRetry(gen.id)}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Retry
                    </button>
                    <button
                      onClick={() => handleDelete(gen.id)}
                      className="text-sm text-red-600 hover:text-red-800"
                    >
                      Delete
                    </button>
                  </>
                )}
                {gen.status === 'completed' && (
                  <button
                    onClick={() => handleDelete(gen.id)}
                    className="text-sm text-gray-400 hover:text-red-600"
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>

            {/* Variant data preview */}
            {gen.variant_data && (
              <div className="text-xs text-gray-600 mb-3 bg-gray-50 rounded p-2">
                {Object.entries(gen.variant_data).map(([k, v]) => (
                  <span key={k} className="mr-3">
                    <span className="text-gray-400">{k}:</span> {String(v)}
                  </span>
                ))}
              </div>
            )}

            {/* Error message */}
            {gen.status === 'failed' && gen.error_message && (
              <p className="text-sm text-red-600 mb-3">
                Failed at {gen.failed_at_step}: {gen.error_message}
              </p>
            )}

            {/* Results with inline preview and ratings */}
            {gen.status === 'completed' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Image */}
                {gen.image_path && (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-gray-500 uppercase">Image</div>
                    <a
                      href={`/api/files/${gen.image_path}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block"
                    >
                      <img
                        src={`/api/files/${gen.image_path}`}
                        alt="Generated"
                        className="w-full max-h-64 object-contain rounded border border-gray-200 hover:border-purple-400 transition-colors"
                      />
                    </a>
                    <RatingInput
                      label="Rating"
                      value={gen.image_rating}
                      comment={gen.image_comment}
                      onRatingChange={(rating) => handleRatingUpdate(gen.id, 'image_rating', rating)}
                      onCommentChange={(comment) => handleRatingUpdate(gen.id, 'image_comment', comment)}
                    />
                  </div>
                )}

                {/* Video */}
                {gen.video_path && (
                  <div className="space-y-2">
                    <div className="text-xs font-medium text-gray-500 uppercase">Video</div>
                    <video
                      src={`/api/files/${gen.video_path}`}
                      controls
                      className="w-full max-h-64 rounded border border-gray-200"
                    />
                    <RatingInput
                      label="Rating"
                      value={gen.video_rating}
                      comment={gen.video_comment}
                      onRatingChange={(rating) => handleRatingUpdate(gen.id, 'video_rating', rating)}
                      onCommentChange={(comment) => handleRatingUpdate(gen.id, 'video_comment', comment)}
                    />
                  </div>
                )}
              </div>
            )}

            {/* In-progress image preview */}
            {gen.status === 'generating_video' && gen.image_path && (
              <div className="mt-3">
                <div className="text-xs font-medium text-gray-500 uppercase mb-2">Image (video generating...)</div>
                <img
                  src={`/api/files/${gen.image_path}`}
                  alt="Generated"
                  className="max-h-48 object-contain rounded border border-gray-200"
                />
              </div>
            )}

            {/* Saving indicator */}
            {savingRatings.has(gen.id) && (
              <div className="text-xs text-gray-400 mt-2">Saving...</div>
            )}
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4">
          <button
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={offset === 0}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setOffset(offset + limit)}
            disabled={currentPage >= totalPages}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
