import { useState, useEffect, useCallback } from 'react'
import { templateApi } from '@/services/api'
import { formatDate } from '@/utils/date'
import type { Generation } from '@/types'
import VideoPreview from '@/components/video/VideoPreview'
import { ChevronDown, ChevronRight, Loader2 } from 'lucide-react'

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

interface BatchGroup {
  batch_id: string | null
  generations: Generation[]
  created_at: string
}

function groupByBatch(generations: Generation[]): BatchGroup[] {
  const groups: BatchGroup[] = []
  const batchMap = new Map<string, Generation[]>()

  for (const gen of generations) {
    if (gen.batch_id) {
      const existing = batchMap.get(gen.batch_id)
      if (existing) {
        existing.push(gen)
      } else {
        batchMap.set(gen.batch_id, [gen])
      }
    } else {
      // Individual generation (no batch)
      groups.push({
        batch_id: null,
        generations: [gen],
        created_at: gen.created_at,
      })
    }
  }

  // Convert batch map to groups
  for (const [batchId, gens] of batchMap) {
    groups.push({
      batch_id: batchId,
      generations: gens,
      created_at: gens[0].created_at,
    })
  }

  // Sort by most recent first
  groups.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  return groups
}

function getBatchStatus(generations: Generation[]): { label: string; color: string } {
  const total = generations.length
  const completed = generations.filter(g => g.status === 'completed').length
  const failed = generations.filter(g => g.status === 'failed').length
  const inProgress = generations.some(g =>
    ['pending', 'preprocessing', 'generating_image', 'generating_video'].includes(g.status)
  )

  if (inProgress) {
    return { label: `${completed}/${total} in progress`, color: 'text-blue-600' }
  }
  if (failed > 0 && completed > 0) {
    return { label: `${completed}/${total} completed, ${failed} failed`, color: 'text-yellow-600' }
  }
  if (failed === total) {
    return { label: `${total} failed`, color: 'text-red-600' }
  }
  return { label: `${completed}/${total} completed`, color: 'text-green-600' }
}

function GenerationCard({
  gen,
  onRetry,
  onDelete,
}: {
  gen: Generation
  onRetry: (id: number) => void
  onDelete: (id: number) => void
}) {
  return (
    <div className="border rounded-lg p-4 hover:bg-gray-50">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${STATUS_COLORS[gen.status] || 'bg-gray-100'}`}>
            {STATUS_LABELS[gen.status] || gen.status}
          </span>
          <span className="text-xs text-gray-500">#{gen.id}</span>
          <span className="text-xs text-gray-400">
            {formatDate(gen.created_at)}
          </span>
        </div>

        <div className="flex gap-2">
          {gen.status === 'failed' && (
            <>
              <button onClick={() => onRetry(gen.id)} className="text-sm text-blue-600 hover:text-blue-800">
                Retry
              </button>
              <button onClick={() => onDelete(gen.id)} className="text-sm text-red-600 hover:text-red-800">
                Delete
              </button>
            </>
          )}
          {gen.status === 'completed' && (
            <button onClick={() => onDelete(gen.id)} className="text-sm text-gray-400 hover:text-red-600">
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

      {/* Results — no ratings */}
      {gen.status === 'completed' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {gen.image_path && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-500 uppercase">Image</div>
              <a href={`/api/files/${gen.image_path}`} target="_blank" rel="noopener noreferrer" className="block">
                <img
                  src={`/api/files/${gen.image_path}`}
                  alt="Generated"
                  className="w-full max-h-64 object-contain rounded border border-gray-200 hover:border-purple-400 transition-colors"
                />
              </a>
            </div>
          )}
          {(gen.video_with_audio_path || gen.video_path) && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-500 uppercase">
                Video{gen.video_with_audio_path ? ' + Music' : ''}
              </div>
              <VideoPreview
                videoUrl={`/api/files/${gen.video_with_audio_path || gen.video_path}`}
                thumbnailUrl={gen.image_path ? `/api/files/${gen.image_path}` : null}
                className="w-full max-h-64"
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
    </div>
  )
}

function BatchGroupView({
  group,
  onRetry,
  onDelete,
}: {
  group: BatchGroup
  onRetry: (id: number) => void
  onDelete: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(false)

  // Individual generation (no batch) — render directly
  if (!group.batch_id) {
    return <GenerationCard gen={group.generations[0]} onRetry={onRetry} onDelete={onDelete} />
  }

  const status = getBatchStatus(group.generations)
  const isInProgress = group.generations.some(g =>
    ['pending', 'preprocessing', 'generating_image', 'generating_video'].includes(g.status)
  )

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Batch header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition"
      >
        <div className="flex items-center gap-3">
          {expanded ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )}
          <span className="text-sm font-medium text-gray-900">
            Batch — {group.generations.length} videos
          </span>
          {isInProgress && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm ${status.color}`}>{status.label}</span>
          <span className="text-xs text-gray-400">
            {formatDate(group.created_at)}
          </span>
        </div>
      </button>

      {/* Expanded generations */}
      {expanded && (
        <div className="border-t p-4 space-y-3 bg-gray-50/50">
          {group.generations.map((gen) => (
            <GenerationCard key={gen.id} gen={gen} onRetry={onRetry} onDelete={onDelete} />
          ))}
        </div>
      )}
    </div>
  )
}

export function GenerationsList({ projectId, refreshTrigger }: GenerationsListProps) {
  const [generations, setGenerations] = useState<Generation[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const limit = 20

  // Polling for in-progress generations
  const [polling, setPolling] = useState(false)

  const loadGenerations = useCallback(async () => {
    try {
      const response = await templateApi.listGenerations(projectId, { offset, limit })
      setGenerations(response.data.generations)
      setTotal(response.data.total)

      // Check if any are in progress
      const hasInProgress = response.data.generations.some((g: Generation) =>
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

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  if (loading && generations.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  if (generations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No generations yet. Use the panel to start a batch run.
      </div>
    )
  }

  const groups = groupByBatch(generations)

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        {total} generation{total !== 1 ? 's' : ''} total
        {polling && <span className="ml-2 text-blue-600">(updating...)</span>}
      </div>

      <div className="space-y-3">
        {groups.map((group, i) => (
          <BatchGroupView
            key={group.batch_id || `single-${i}`}
            group={group}
            onRetry={handleRetry}
            onDelete={handleDelete}
          />
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
