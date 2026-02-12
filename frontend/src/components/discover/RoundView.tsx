import { useState, useCallback, useEffect } from 'react'
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import type { DiscoverRound, DiscoverRoundType } from '@/types'
import { discoverApi } from '@/services/api'
import { getErrorMessage } from '@/types'
import { ItemGrid } from './ItemGrid'
import { getModelDisplayName } from '@/constants/models'

interface RoundViewProps {
  projectId: number
  round: DiscoverRound
  isLatestRound: boolean
  onRefresh: () => void
  onSelectionsChange?: (roundId: number, selections: Record<string, 'selected' | 'rejected'>) => void
  finalistItemId?: number | null
  onCrownClick?: (itemId: number) => void
  readOnly?: boolean
}

export function RoundView({ projectId, round, isLatestRound, onRefresh, onSelectionsChange, finalistItemId, onCrownClick, readOnly }: RoundViewProps) {
  const [selections, setSelections] = useState<Record<string, 'selected' | 'rejected'>>(() => {
    const init: Record<string, 'selected' | 'rejected'> = {}
    for (const item of round.items) {
      if (item.selection === 'selected' || item.selection === 'rejected') {
        init[String(item.id)] = item.selection
      }
    }
    return init
  })
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)

  const isSelectable = round.status === 'completed' && !readOnly
  const hasFailedItems = round.items.some(i => i.status === 'failed')
  const allItemsDone = round.items.every(i => i.status === 'completed' || i.status === 'failed')
  const isGenerating = round.status === 'generating' || round.items.some(i => i.status === 'generating' || i.status === 'pending')

  const selectedCount = Object.values(selections).filter(v => v === 'selected').length
  const rejectedCount = Object.values(selections).filter(v => v === 'rejected').length
  const completedItems = round.items.filter(i => i.status === 'completed')

  const handleSelectionChange = useCallback((itemId: number, value: 'selected' | 'rejected' | null) => {
    setSelections(prev => {
      const next = { ...prev }
      if (value === null) {
        delete next[String(itemId)]
      } else {
        next[String(itemId)] = value
      }
      return next
    })
  }, [])

  // Notify parent of selection changes
  useEffect(() => {
    onSelectionsChange?.(round.id, selections)
  }, [selections, round.id, onSelectionsChange])

  const handleRetry = async () => {
    setRetrying(true)
    setError(null)
    try {
      await discoverApi.retryFailed(projectId, round.id)
      onRefresh()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRetrying(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Round header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          Round {round.round_number}
          <span className="ml-2 text-sm font-normal text-gray-500">
            {round.round_type === 'image' ? 'Images' : 'Videos'}
          </span>
          {round.model_used && (
            <span className="ml-2 text-xs font-normal text-gray-400">
              {getModelDisplayName(round.model_used)}
            </span>
          )}
          {isGenerating && (
            <span className="ml-2 inline-flex items-center gap-1 text-sm text-blue-600">
              <Loader2 className="h-3 w-3 animate-spin" />
              Generating...
            </span>
          )}
        </h3>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          {completedItems.length}/{round.total_items} ready
          {selectedCount > 0 && (
            <span className="text-green-600">{selectedCount} selected</span>
          )}
          {rejectedCount > 0 && (
            <span className="text-red-500">{rejectedCount} rejected</span>
          )}
        </div>
      </div>

      {/* Error */}
      {(error || round.error_message) && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
          <span className="text-sm text-red-700">{error || round.error_message}</span>
        </div>
      )}

      {/* Item grid */}
      <ItemGrid
        items={round.items}
        roundType={round.round_type as DiscoverRoundType}
        selectable={isSelectable}
        selections={selections}
        onSelectionChange={handleSelectionChange}
        finalistItemId={finalistItemId}
        onCrownClick={onCrownClick}
      />

      {/* Retry failed */}
      {hasFailedItems && isLatestRound && allItemsDone && !readOnly && (
        <button
          onClick={handleRetry}
          disabled={retrying}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 disabled:opacity-50"
        >
          {retrying ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Retry failed items
        </button>
      )}
    </div>
  )
}
