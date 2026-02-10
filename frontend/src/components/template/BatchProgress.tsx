import { useState, useEffect, useCallback } from 'react'
import { templateApi } from '@/services/api'
import type { Generation } from '@/types'
import {
  Loader2, RotateCcw, CheckCircle2, XCircle, AlertTriangle,
  Clock, ChevronDown, ChevronRight, ThumbsUp, ThumbsDown, RefreshCw,
  Ban,
} from 'lucide-react'

interface BatchProgressProps {
  projectId: number
  refreshTrigger?: number
}

interface BatchInfo {
  batch_id: string | null
  generations: Generation[]
  created_at: string
}

const IN_PROGRESS_STATUSES = ['pending', 'preprocessing', 'generating_image', 'generating_video', 'generating_audio', 'merging_audio']

function groupByBatch(generations: Generation[]): BatchInfo[] {
  const batchMap = new Map<string, Generation[]>()
  const singles: BatchInfo[] = []

  for (const gen of generations) {
    if (gen.batch_id) {
      const existing = batchMap.get(gen.batch_id)
      if (existing) existing.push(gen)
      else batchMap.set(gen.batch_id, [gen])
    } else {
      singles.push({ batch_id: null, generations: [gen], created_at: gen.created_at })
    }
  }

  const groups: BatchInfo[] = []
  for (const [batchId, gens] of batchMap) {
    groups.push({ batch_id: batchId, generations: gens, created_at: gens[0].created_at })
  }

  groups.push(...singles)

  groups.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  return groups
}

function isBatchActive(batch: BatchInfo): boolean {
  return batch.generations.some(g =>
    IN_PROGRESS_STATUSES.includes(g.status) || g.status === 'failed'
  )
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  if (diffDay === 1) return 'yesterday'
  if (diffDay < 7) return `${diffDay}d ago`
  return date.toLocaleDateString()
}

function getModerationStats(generations: Generation[]) {
  const completed = generations.filter(g => g.status === 'completed')
  const failed = generations.filter(g => g.status === 'failed')
  const cancelled = generations.filter(g => g.status === 'cancelled')
  const approved = completed.filter(g => g.moderation_status === 'approved')
  const rejected = completed.filter(g => g.moderation_status === 'rejected')
  const regenerated = completed.filter(g => g.moderation_status === 'regenerated')
  const pendingReview = completed.filter(g => !g.moderation_status)

  return {
    total: generations.length,
    completed: completed.length,
    failed: failed.length,
    cancelled: cancelled.length,
    approved: approved.length,
    rejected: rejected.length,
    regenerated: regenerated.length,
    pendingReview: pendingReview.length,
  }
}

const MODERATION_LABEL: Record<string, { text: string; className: string }> = {
  approved: { text: 'Approved', className: 'text-green-600' },
  rejected: { text: 'Rejected', className: 'text-red-500' },
  regenerated: { text: 'Regen', className: 'text-orange-500' },
}

function CancelConfirmModal({
  batch,
  onConfirm,
  onClose,
  cancelling,
}: {
  batch: BatchInfo
  onConfirm: () => void
  onClose: () => void
  cancelling: boolean
}) {
  const completed = batch.generations.filter(g => g.status === 'completed').length
  const willCancel = batch.generations.filter(g => IN_PROGRESS_STATUSES.includes(g.status)).length
  const total = batch.generations.length

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-sm w-full mx-4 p-5">
        <h3 className="text-base font-semibold text-gray-900 mb-2">Cancel batch?</h3>
        <p className="text-sm text-gray-600 mb-4">
          {completed > 0
            ? `${completed} of ${total} videos are ready and will be kept. `
            : ''}
          {willCancel > 0
            ? `${willCancel} in progress or pending will be cancelled.`
            : 'All videos have already finished.'}
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={cancelling}
            className="px-3 py-1.5 text-sm text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition disabled:opacity-50"
          >
            Keep running
          </button>
          <button
            onClick={onConfirm}
            disabled={cancelling}
            className="px-3 py-1.5 text-sm text-white bg-red-600 hover:bg-red-700 rounded-md transition disabled:opacity-50 flex items-center gap-1.5"
          >
            {cancelling && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Cancel batch
          </button>
        </div>
      </div>
    </div>
  )
}

function BatchHistoryAccordion({ batch }: { batch: BatchInfo }) {
  const [open, setOpen] = useState(false)
  const stats = getModerationStats(batch.generations)
  const isSingle = !batch.batch_id

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      {/* Header — clickable */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-gray-50 transition text-sm"
      >
        <div className="flex items-center gap-2">
          {open
            ? <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
            : <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
          }
          {stats.cancelled === stats.total && <Ban className="h-3.5 w-3.5 text-gray-400" />}
          {stats.cancelled < stats.total && stats.failed === 0 && <CheckCircle2 className="h-3.5 w-3.5 text-green-400" />}
          {stats.cancelled < stats.total && stats.failed > 0 && stats.failed < stats.total && <AlertTriangle className="h-3.5 w-3.5 text-yellow-400" />}
          {stats.cancelled < stats.total && stats.failed === stats.total && <XCircle className="h-3.5 w-3.5 text-red-400" />}
          <span className="text-gray-700 font-medium">
            {isSingle ? '1 video' : `${stats.total} videos`}
          </span>

          {/* Compact moderation badges */}
          <div className="flex items-center gap-2 ml-1">
            {stats.approved > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-green-600">
                <ThumbsUp className="h-3 w-3" />{stats.approved}
              </span>
            )}
            {stats.rejected > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-red-500">
                <ThumbsDown className="h-3 w-3" />{stats.rejected}
              </span>
            )}
            {stats.regenerated > 0 && (
              <span className="flex items-center gap-0.5 text-xs text-orange-500">
                <RefreshCw className="h-3 w-3" />{stats.regenerated}
              </span>
            )}
            {stats.pendingReview > 0 && (
              <span className="text-xs text-gray-400">{stats.pendingReview} pending</span>
            )}
            {stats.failed > 0 && (
              <span className="text-xs text-red-400">{stats.failed} failed</span>
            )}
            {stats.cancelled > 0 && (
              <span className="text-xs text-gray-400">{stats.cancelled} cancelled</span>
            )}
          </div>
        </div>
        <span className="text-xs text-gray-400 flex-shrink-0 ml-3">
          {formatRelativeDate(batch.created_at)}
        </span>
      </button>

      {/* Expanded — generation list */}
      {open && (
        <div className="border-t border-gray-100 bg-gray-50/50 px-3 py-2 space-y-1">
          {batch.generations.map(gen => {
            const mod = gen.moderation_status
            const modStyle = mod ? MODERATION_LABEL[mod] : null

            return (
              <div key={gen.id} className="flex items-center justify-between text-xs py-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-gray-400">#{gen.id}</span>
                  {gen.variant_data && (
                    <span className="text-gray-500 truncate">
                      {Object.values(gen.variant_data).slice(0, 2).join(', ')}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                  {gen.status === 'failed' && (
                    <span className="text-red-500">failed</span>
                  )}
                  {gen.status === 'cancelled' && (
                    <span className="text-gray-400">cancelled</span>
                  )}
                  {gen.status === 'completed' && modStyle && (
                    <span className={modStyle.className}>{modStyle.text}</span>
                  )}
                  {gen.status === 'completed' && !modStyle && (
                    <span className="text-gray-400">review</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function BatchProgressBar({
  batch,
  projectId,
  onCancelled,
}: {
  batch: BatchInfo
  projectId: number
  onCancelled: () => void
}) {
  const [showCancelModal, setShowCancelModal] = useState(false)
  const [cancelling, setCancelling] = useState(false)

  const total = batch.generations.length
  const completed = batch.generations.filter(g => g.status === 'completed').length
  const failed = batch.generations.filter(g => g.status === 'failed').length
  const cancelled = batch.generations.filter(g => g.status === 'cancelled').length
  const inProgress = batch.generations.filter(g => IN_PROGRESS_STATUSES.includes(g.status)).length
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  const canCancel = batch.batch_id && inProgress > 0

  const handleCancel = async () => {
    if (!batch.batch_id) return
    setCancelling(true)
    try {
      await templateApi.cancelBatch(projectId, batch.batch_id)
      setShowCancelModal(false)
      onCancelled()
    } catch (err) {
      console.error('Failed to cancel batch:', err)
    } finally {
      setCancelling(false)
    }
  }

  // Single generation (no batch)
  if (!batch.batch_id) {
    const gen = batch.generations[0]
    const isActive = IN_PROGRESS_STATUSES.includes(gen.status)
    return (
      <div className="flex items-center gap-3 text-sm">
        {isActive && <Loader2 className="h-4 w-4 animate-spin text-blue-500 flex-shrink-0" />}
        {gen.status === 'failed' && <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />}
        <span className="text-gray-600">
          #{gen.id} — {gen.status === 'failed' ? 'Failed' : 'Processing...'}
        </span>
      </div>
    )
  }

  const allDone = inProgress === 0

  return (
    <>
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            {!allDone && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
            {allDone && failed === 0 && cancelled === 0 && <CheckCircle2 className="h-4 w-4 text-green-500" />}
            {allDone && (failed > 0 || cancelled > 0) && <AlertTriangle className="h-4 w-4 text-yellow-500" />}
            <span className="text-gray-700 font-medium">
              Batch — {total} video{total !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {canCancel && (
              <button
                onClick={() => setShowCancelModal(true)}
                className="text-xs text-red-500 hover:text-red-700 font-medium transition"
              >
                Cancel
              </button>
            )}
            <span className="text-xs text-gray-400">
              {new Date(batch.created_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full flex">
            {completed > 0 && (
              <div
                className="bg-green-500 transition-all duration-500"
                style={{ width: `${(completed / total) * 100}%` }}
              />
            )}
            {failed > 0 && (
              <div
                className="bg-red-400 transition-all duration-500"
                style={{ width: `${(failed / total) * 100}%` }}
              />
            )}
            {cancelled > 0 && (
              <div
                className="bg-gray-300 transition-all duration-500"
                style={{ width: `${(cancelled / total) * 100}%` }}
              />
            )}
            {inProgress > 0 && (
              <div
                className="bg-blue-400 animate-pulse transition-all duration-500"
                style={{ width: `${(inProgress / total) * 100}%` }}
              />
            )}
          </div>
        </div>

        {/* Status text */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>
            {completed > 0 && <span className="text-green-600">{completed} done</span>}
            {failed > 0 && <span className="text-red-500 ml-2">{failed} failed</span>}
            {cancelled > 0 && <span className="text-gray-400 ml-2">{cancelled} cancelled</span>}
            {inProgress > 0 && <span className="text-blue-500 ml-2">{inProgress} in progress</span>}
          </span>
          <span>{pct}%</span>
        </div>
      </div>

      {showCancelModal && (
        <CancelConfirmModal
          batch={batch}
          onConfirm={handleCancel}
          onClose={() => setShowCancelModal(false)}
          cancelling={cancelling}
        />
      )}
    </>
  )
}

function FailedItem({ gen, onRetry }: { gen: Generation; onRetry: (id: number) => void }) {
  return (
    <div className="flex items-center justify-between text-sm py-1.5 px-3 bg-red-50 rounded">
      <div className="flex items-center gap-2 min-w-0">
        <XCircle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
        <span className="text-gray-600 truncate">
          #{gen.id}
          {gen.variant_data && (
            <span className="text-gray-400 ml-1">
              — {Object.values(gen.variant_data).slice(0, 2).join(', ')}
            </span>
          )}
        </span>
        <span className="text-red-500 text-xs truncate">
          {gen.error_message}
        </span>
      </div>
      <button
        onClick={() => onRetry(gen.id)}
        className="flex items-center gap-1 text-blue-600 hover:text-blue-800 flex-shrink-0 ml-2"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Retry
      </button>
    </div>
  )
}

export function BatchProgress({ projectId, refreshTrigger }: BatchProgressProps) {
  const [generations, setGenerations] = useState<Generation[]>([])
  const [loading, setLoading] = useState(true)
  const [polling, setPolling] = useState(false)

  const loadGenerations = useCallback(async () => {
    try {
      const response = await templateApi.listGenerations(projectId, { offset: 0, limit: 100 })
      setGenerations(response.data.generations)

      const hasInProgress = response.data.generations.some((g: Generation) =>
        IN_PROGRESS_STATUSES.includes(g.status)
      )
      setPolling(hasInProgress)
    } catch (err) {
      console.error('Failed to load generations:', err)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadGenerations()
  }, [loadGenerations, refreshTrigger])

  // Polling
  useEffect(() => {
    if (!polling) return
    const interval = setInterval(loadGenerations, 3000)
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
      </div>
    )
  }

  const batches = groupByBatch(generations)
  const activeBatches = batches.filter(b =>
    isBatchActive(b) &&
    // Exclude failed singles — they show in FAILED section only
    !(b.generations.length === 1 && !b.batch_id && b.generations[0].status === 'failed')
  )
  const completedBatches = batches.filter(b => !isBatchActive(b))

  // All failed generations across all batches (for retry section)
  const failedGenerations = generations.filter(g => g.status === 'failed')

  const hasActive = activeBatches.length > 0 || failedGenerations.length > 0

  if (!hasActive && completedBatches.length === 0) {
    return (
      <div className="text-center py-6 text-sm text-gray-500">
        No generations yet. Start a batch to begin.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Active batches */}
      {hasActive && (
        <div className="space-y-4">
          {activeBatches.map((batch, i) => (
            <BatchProgressBar
              key={batch.batch_id || `single-${i}`}
              batch={batch}
              projectId={projectId}
              onCancelled={loadGenerations}
            />
          ))}

          {/* Failed items with retry */}
          {failedGenerations.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-xs font-medium text-gray-500 uppercase">
                Failed ({failedGenerations.length})
              </div>
              {failedGenerations.map(gen => (
                <FailedItem key={gen.id} gen={gen} onRetry={handleRetry} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Batch history */}
      {completedBatches.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-xs font-medium text-gray-500 uppercase">History</span>
          </div>
          <div className="space-y-1.5">
            {completedBatches.map((batch, i) => (
              <BatchHistoryAccordion
                key={batch.batch_id || `hist-${i}`}
                batch={batch}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
