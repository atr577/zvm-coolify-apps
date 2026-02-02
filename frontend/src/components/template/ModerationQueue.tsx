import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, RefreshCw, Loader2, AlertCircle } from 'lucide-react'
import { moderationApi, type ModerationQueueItem } from '@/services/api'
import VideoPreview from '@/components/video/VideoPreview'

interface ModerationQueueProps {
  projectId: number
  onApproved?: () => void
}

export function ModerationQueue({ projectId, onApproved }: ModerationQueueProps) {
  const [items, setItems] = useState<ModerationQueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<number | null>(null)
  const [rejectModal, setRejectModal] = useState<{ id: number; open: boolean }>({ id: 0, open: false })
  const [rejectReason, setRejectReason] = useState('')
  const [rejectComment, setRejectComment] = useState('')
  const [regenerateModal, setRegenerateModal] = useState<{ id: number; open: boolean }>({ id: 0, open: false })
  const [regenerateFeedback, setRegenerateFeedback] = useState('')

  const fetchQueue = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await moderationApi.getQueue(projectId)
      setItems(response.data.items)
    } catch (err) {
      setError('Failed to load moderation queue')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
  }, [projectId])

  const handleApprove = async (id: number) => {
    try {
      setActionLoading(id)
      await moderationApi.approve(projectId, id)
      setItems(prev => prev.filter(item => item.id !== id))
      onApproved?.()
    } catch (err: unknown) {
      const error = err as { response?: { status?: number; data?: { detail?: string } } }
      if (error.response?.status === 503) {
        setError('Metadata generation failed. Please retry.')
      } else if (error.response?.status === 409) {
        setError('Already approved')
        fetchQueue()
      } else {
        setError(error.response?.data?.detail || 'Failed to approve')
      }
    } finally {
      setActionLoading(null)
    }
  }

  const handleReject = async () => {
    if (!rejectReason.trim()) return

    try {
      setActionLoading(rejectModal.id)
      await moderationApi.reject(projectId, rejectModal.id, {
        reason: rejectReason.trim(),
        comment: rejectComment.trim() || undefined
      })
      setItems(prev => prev.filter(item => item.id !== rejectModal.id))
      setRejectModal({ id: 0, open: false })
      setRejectReason('')
      setRejectComment('')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to reject')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRegenerate = async () => {
    try {
      setActionLoading(regenerateModal.id)
      await moderationApi.regenerate(projectId, regenerateModal.id, {
        feedback: regenerateFeedback.trim() || undefined
      })
      setItems(prev => prev.filter(item => item.id !== regenerateModal.id))
      setRegenerateModal({ id: 0, open: false })
      setRegenerateFeedback('')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      setError(error.response?.data?.detail || 'Failed to regenerate')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => { setError(null); fetchQueue() }}
            className="mt-2 text-sm text-blue-600 hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-300" />
        <p>No videos pending moderation</p>
        <p className="text-sm mt-1">Generate more videos to see them here</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-gray-500">
        {items.length} video{items.length !== 1 ? 's' : ''} pending moderation
      </div>

      <div className="space-y-4">
        {items.map(item => (
          <div
            key={item.id}
            className="relative border rounded-lg p-4 hover:bg-gray-50"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">
                  Pending Review
                </span>
                <span className="text-xs text-gray-500">#{item.id}</span>
                <span className="text-xs text-gray-400">
                  {item.completed_at ? new Date(item.completed_at).toLocaleString() : 'Processing'}
                </span>
              </div>

              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleApprove(item.id)}
                  disabled={actionLoading === item.id}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {actionLoading === item.id ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <CheckCircle className="w-3 h-3" />
                  )}
                  Approve
                </button>
                <button
                  onClick={() => setRegenerateModal({ id: item.id, open: true })}
                  disabled={actionLoading === item.id}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
                >
                  <RefreshCw className="w-3 h-3" />
                  Regenerate
                </button>
                <button
                  onClick={() => setRejectModal({ id: item.id, open: true })}
                  disabled={actionLoading === item.id}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                >
                  <XCircle className="w-3 h-3" />
                  Reject
                </button>
              </div>
            </div>

            {/* Two-column layout: Video left, Text right */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Left: Video */}
              <div>
                <VideoPreview
                  videoUrl={item.video_url}
                  thumbnailUrl={item.image_url}
                  className="w-full max-h-[28rem]"
                />
              </div>

              {/* Right: Text info */}
              <div className="space-y-3">
                {/* Variant data */}
                {item.variant && item.variant.data && (
                  <div className="text-sm text-gray-700 space-y-1">
                    {Object.entries(item.variant.data).map(([k, v]) => (
                      <div key={k}>
                        <span className="text-gray-400">{k}:</span> {String(v)}
                      </div>
                    ))}
                  </div>
                )}

                {/* Template info */}
                {item.video_template && (
                  <div className="text-xs text-gray-500">
                    Template: <span className="font-medium">{item.video_template.name}</span>
                  </div>
                )}

                {/* Image link */}
                {item.image_url && (
                  <div className="text-xs">
                    <a
                      href={item.image_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      Open source image →
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Loading overlay */}
            {actionLoading === item.id && (
              <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-lg">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Reject Modal */}
      {rejectModal.open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Reject Video</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={rejectReason}
                  onChange={e => setRejectReason(e.target.value)}
                  placeholder="e.g., Poor video quality"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Comment (optional)
                </label>
                <textarea
                  value={rejectComment}
                  onChange={e => setRejectComment(e.target.value)}
                  placeholder="Additional details..."
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setRejectModal({ id: 0, open: false })
                  setRejectReason('')
                  setRejectComment('')
                }}
                className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectReason.trim() || actionLoading === rejectModal.id}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading === rejectModal.id ? (
                  <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                ) : (
                  'Reject'
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Regenerate Modal */}
      {regenerateModal.open && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Regenerate Video</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Feedback (optional)
                </label>
                <textarea
                  value={regenerateFeedback}
                  onChange={e => setRegenerateFeedback(e.target.value)}
                  placeholder="What would you like to change? e.g., darker background, model closer to camera, more dynamic pose..."
                  rows={4}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Leave empty to regenerate with original prompts
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setRegenerateModal({ id: 0, open: false })
                  setRegenerateFeedback('')
                }}
                className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleRegenerate}
                disabled={actionLoading === regenerateModal.id}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {actionLoading === regenerateModal.id ? (
                  <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                ) : (
                  'Regenerate'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
