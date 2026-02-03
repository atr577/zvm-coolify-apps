import { useState, useEffect, useCallback, useMemo } from 'react'
import { CheckCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import {
  moderationApi,
  publishingScheduleApi,
  type ModerationQueueItem,
  type PlatformMetadata,
  type PublishingScheduleResponse,
} from '@/services/api'
import { ReviewFocusedView } from './ReviewFocusedView'
import { ReviewFilmstrip } from './ReviewFilmstrip'
import { RejectionArchive } from './RejectionArchive'

type FilterType = 'all' | 'pending' | 'approved' | 'rejected'
type ItemStatus = 'pending' | 'approved' | 'rejected' | 'redo'

type ScreenType = 'dashboard' | 'review' | 'pipeline'

interface ReviewScreenProps {
  projectId: number
  pendingCount: number
  onNavigate?: (screen: ScreenType) => void
}

export function ReviewScreen({ projectId, onNavigate }: ReviewScreenProps) {
  // Data state
  const [items, setItems] = useState<ModerationQueueItem[]>([])
  const [schedule, setSchedule] = useState<PublishingScheduleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Navigation state
  const [filter, setFilter] = useState<FilterType>('pending')
  const [currentIndex, setCurrentIndex] = useState(0)

  // Local status tracking
  const [approvedIds, setApprovedIds] = useState<Set<number>>(new Set())
  const [rejectedIds, setRejectedIds] = useState<Set<number>>(new Set())
  const [redoIds, setRedoIds] = useState<Set<number>>(new Set())

  // Metadata state
  const [metadata, setMetadata] = useState<Record<string, PlatformMetadata> | null>(null)
  const [metadataLoading, setMetadataLoading] = useState(false)
  const [metadataError, setMetadataError] = useState<string | null>(null)

  // Action state
  const [actionLoading, setActionLoading] = useState(false)

  // Rejection archive
  const [archiveOpen, setArchiveOpen] = useState(false)

  // Get item status
  const getStatus = useCallback((itemId: number): ItemStatus => {
    if (approvedIds.has(itemId)) return 'approved'
    if (rejectedIds.has(itemId)) return 'rejected'
    if (redoIds.has(itemId)) return 'redo'
    return 'pending'
  }, [approvedIds, rejectedIds, redoIds])

  // Filtered items
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      const status = getStatus(item.id)
      if (filter === 'all') return status !== 'redo'
      if (filter === 'pending') return status === 'pending'
      if (filter === 'approved') return status === 'approved'
      if (filter === 'rejected') return status === 'rejected'
      return true
    })
  }, [items, filter, getStatus])

  // Current item
  const currentItem = filteredItems[currentIndex] || null

  // Filter counts
  const counts = useMemo(() => {
    const all = items.filter((i) => getStatus(i.id) !== 'redo').length
    const pending = items.filter((i) => getStatus(i.id) === 'pending').length
    const approved = items.filter((i) => getStatus(i.id) === 'approved').length
    const rejected = items.filter((i) => getStatus(i.id) === 'rejected').length
    return { all, pending, approved, rejected }
  }, [items, getStatus])

  // Target slot calculation
  const { targetSlot, slotsInfo } = useMemo(() => {
    if (!schedule) return { targetSlot: null, slotsInfo: null }
    const filledSlots = schedule.slots.filter((s) => s.item).length
    const nextSlotIndex = filledSlots + approvedIds.size
    const slot = schedule.slots[nextSlotIndex] || null
    const info = slot
      ? `Slot ${nextSlotIndex + 1} of ${schedule.slots.length}`
      : null
    return { targetSlot: slot, slotsInfo: info }
  }, [schedule, approvedIds.size])

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [queueRes, scheduleRes] = await Promise.all([
        moderationApi.getQueue(projectId),
        publishingScheduleApi.getSchedule(projectId),
      ])
      setItems(queueRes.data.items)
      setSchedule(scheduleRes.data)
    } catch (err) {
      console.error('Failed to load review data:', err)
      setError('Failed to load review data')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Pre-generate metadata when current item changes
  const loadMetadata = useCallback(async (generationId: number) => {
    setMetadata(null)
    setMetadataError(null)
    setMetadataLoading(true)
    try {
      const res = await moderationApi.preGenerateMetadata(projectId, generationId)
      setMetadata(res.data.metadata)
    } catch (err) {
      console.error('Failed to pre-generate metadata:', err)
      setMetadataError('Failed to generate metadata')
    } finally {
      setMetadataLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (currentItem && getStatus(currentItem.id) === 'pending') {
      loadMetadata(currentItem.id)
    } else {
      setMetadata(null)
      setMetadataLoading(false)
      setMetadataError(null)
    }
  }, [currentItem?.id, getStatus, loadMetadata, currentItem])

  // Navigate to next pending item
  const advanceToNextPending = useCallback((excludeId: number) => {
    const pendingItems = items.filter(
      (i) => getStatus(i.id) === 'pending' && i.id !== excludeId
    )
    if (pendingItems.length === 0) {
      setCurrentIndex(0)
      return
    }
    // Find the next pending item in filteredItems
    const currentFilteredIndex = filteredItems.findIndex((i) => i.id === excludeId)
    // Look forward first
    for (let i = currentFilteredIndex + 1; i < filteredItems.length; i++) {
      if (getStatus(filteredItems[i].id) === 'pending') {
        setCurrentIndex(i > 0 ? i - 1 : 0) // Will shift because item is removed
        return
      }
    }
    // Then look backward
    setCurrentIndex(Math.max(0, currentIndex - 1))
  }, [items, filteredItems, getStatus, currentIndex])

  // Action handlers
  const handleApprove = async () => {
    if (!currentItem || actionLoading) return
    try {
      setActionLoading(true)
      await moderationApi.approve(projectId, currentItem.id, metadata || undefined)
      setApprovedIds((prev) => new Set(prev).add(currentItem.id))
      if (filter === 'pending') {
        advanceToNextPending(currentItem.id)
      }
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } }
      if (error.response?.status === 409) {
        // Already approved — treat as success
        setApprovedIds((prev) => new Set(prev).add(currentItem.id))
      } else {
        console.error('Failed to approve:', err)
        setMetadataError(error.response?.data?.detail || 'Failed to approve')
      }
    } finally {
      setActionLoading(false)
    }
  }

  const handleReject = async (reason: string, comment?: string) => {
    if (!currentItem || actionLoading) return
    try {
      setActionLoading(true)
      await moderationApi.reject(projectId, currentItem.id, { reason, comment })
      setRejectedIds((prev) => new Set(prev).add(currentItem.id))
      if (filter === 'pending') {
        advanceToNextPending(currentItem.id)
      }
    } catch (err) {
      console.error('Failed to reject:', err)
    } finally {
      setActionLoading(false)
    }
  }

  const handleRedo = async (feedback?: string) => {
    if (!currentItem || actionLoading) return
    try {
      setActionLoading(true)
      await moderationApi.regenerate(projectId, currentItem.id, feedback ? { feedback } : undefined)
      setRedoIds((prev) => new Set(prev).add(currentItem.id))
      if (filter === 'pending') {
        advanceToNextPending(currentItem.id)
      }
    } catch (err) {
      console.error('Failed to regenerate:', err)
    } finally {
      setActionLoading(false)
    }
  }

  // Handle filter change
  const handleFilterChange = (newFilter: FilterType) => {
    setFilter(newFilter)
    setCurrentIndex(0)
  }

  // Handle filmstrip navigation
  const handleNavigate = (index: number) => {
    setCurrentIndex(index)
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <button onClick={fetchData} className="text-sm text-blue-600 hover:underline">
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Empty state (no pending items at all)
  if (filteredItems.length === 0) {
    return (
      <div className="space-y-6">
        {/* Filters — still show them */}
        <FilterTabs filter={filter} counts={counts} onChange={handleFilterChange} />

        <div className="text-center py-12">
          <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {filter === 'pending' ? 'All caught up!' : `No ${filter} videos`}
          </h3>
          <p className="text-gray-500 mb-6">
            {filter === 'pending'
              ? 'No videos pending review.'
              : `Switch to another filter to see videos.`}
          </p>
          {filter === 'pending' && onNavigate && (
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => onNavigate!('pipeline')}
                className="px-4 py-2 text-sm font-medium bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Run pipeline
              </button>
              <button
                onClick={() => onNavigate!('dashboard')}
                className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Dashboard
              </button>
            </div>
          )}
        </div>

        {/* Rejection Archive */}
        <ArchiveSection
          open={archiveOpen}
          onToggle={() => setArchiveOpen(!archiveOpen)}
          projectId={projectId}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header: Filters + Counter */}
      <div className="flex items-center justify-between">
        <FilterTabs filter={filter} counts={counts} onChange={handleFilterChange} />
        <span className="text-sm text-gray-500">
          {currentIndex + 1} of {filteredItems.length}
        </span>
      </div>

      {/* Focused view */}
      {currentItem && (
        <ReviewFocusedView
          item={currentItem}
          targetSlot={targetSlot}
          slotsInfo={slotsInfo}
          metadata={metadata}
          metadataLoading={metadataLoading}
          metadataError={metadataError}
          onMetadataChange={setMetadata}
          onMetadataRetry={() => currentItem && loadMetadata(currentItem.id)}
          onApprove={handleApprove}
          onReject={handleReject}
          onRedo={handleRedo}
          actionLoading={actionLoading}
        />
      )}

      {/* Filmstrip */}
      <ReviewFilmstrip
        items={filteredItems}
        currentIndex={currentIndex}
        getStatus={getStatus}
        onNavigate={handleNavigate}
      />

      {/* Rejection Archive */}
      <ArchiveSection
        open={archiveOpen}
        onToggle={() => setArchiveOpen(!archiveOpen)}
        projectId={projectId}
      />
    </div>
  )
}


// --- Filter Tabs ---

function FilterTabs({
  filter,
  counts,
  onChange,
}: {
  filter: FilterType
  counts: { all: number; pending: number; approved: number; rejected: number }
  onChange: (f: FilterType) => void
}) {
  const tabs: { key: FilterType; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: counts.all },
    { key: 'pending', label: 'Pending', count: counts.pending },
    { key: 'approved', label: 'Approved', count: counts.approved },
    { key: 'rejected', label: 'Rejected', count: counts.rejected },
  ]

  return (
    <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`px-3 py-1.5 text-sm font-medium rounded-md transition ${
            filter === tab.key
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {tab.label}
          {tab.count > 0 && (
            <span className={`ml-1.5 text-xs ${
              filter === tab.key ? 'text-gray-500' : 'text-gray-400'
            }`}>
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}


// --- Archive Section ---

function ArchiveSection({
  open,
  onToggle,
  projectId,
}: {
  open: boolean
  onToggle: () => void
  projectId: number
}) {
  return (
    <div className="border-t pt-4">
      <button
        onClick={onToggle}
        className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900"
      >
        {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        Rejection Archive
      </button>
      {open && (
        <div className="mt-4">
          <RejectionArchive projectId={projectId} />
        </div>
      )}
    </div>
  )
}
