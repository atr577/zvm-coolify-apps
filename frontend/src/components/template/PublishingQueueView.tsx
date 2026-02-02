import { useState, useEffect } from 'react'
import { Loader2, Trash2, Edit2, Save, X, AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { publishingScheduleApi, type PublishingQueueItem, type PublishingQueueResponse } from '@/services/api'

interface PublishingQueueViewProps {
  projectId: number
  onRefresh: () => void
}

function getStatusIcon(status: string) {
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
      return <div className="w-4 h-4 rounded-full bg-gray-300" />
  }
}

interface QueueItemCardProps {
  item: PublishingQueueItem
  projectId: number
  onDelete: () => void
  onUpdate: () => void
}

function QueueItemCard({ item, projectId, onDelete, onUpdate }: QueueItemCardProps) {
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [metadata, setMetadata] = useState(item.publishing_metadata || {})

  const handleDelete = async () => {
    if (!confirm('Remove this video from publishing queue?')) return

    try {
      setDeleting(true)
      await publishingScheduleApi.deleteQueueItem(projectId, item.id)
      onDelete()
    } catch (err) {
      console.error('Failed to delete:', err)
      alert('Failed to remove from queue')
    } finally {
      setDeleting(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      await publishingScheduleApi.updateQueueItem(projectId, item.id, {
        publishing_metadata: metadata as Record<string, { title: string; description: string; hashtags: string }>
      })
      setEditing(false)
      onUpdate()
    } catch (err) {
      console.error('Failed to save:', err)
      alert('Failed to save changes')
    } finally {
      setSaving(false)
    }
  }

  const updatePlatformMeta = (platform: string, field: string, value: string) => {
    setMetadata(prev => {
      const current = prev[platform] || { title: '', description: '', hashtags: '' }
      return {
        ...prev,
        [platform]: {
          title: current.title,
          description: current.description,
          hashtags: current.hashtags,
          [field]: value
        }
      }
    })
  }

  const platforms = Object.keys(metadata)

  return (
    <div className="border rounded-lg p-4 bg-white">
      <div className="flex gap-4">
        {/* Thumbnail */}
        <div className="flex-shrink-0">
          {item.thumbnail_url ? (
            <img
              src={item.thumbnail_url}
              alt="Thumbnail"
              className="w-20 h-32 object-cover rounded"
            />
          ) : (
            <div className="w-20 h-32 bg-gray-100 rounded flex items-center justify-center text-gray-400">
              No image
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2">
              {getStatusIcon(item.status)}
              <span className="text-sm font-medium capitalize">{item.status}</span>
              <span className="text-xs text-gray-400">#{item.id} • Position {item.position}</span>
            </div>
            <div className="flex items-center gap-1">
              {item.status === 'approved' && (
                <>
                  <button
                    onClick={() => setEditing(!editing)}
                    className="p-1 text-gray-400 hover:text-blue-600"
                    title="Edit metadata"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleDelete}
                    disabled={deleting}
                    className="p-1 text-gray-400 hover:text-red-600"
                    title="Remove from queue"
                  >
                    {deleting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Error message */}
          {item.last_error && (
            <div className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded mb-2">
              {item.last_error}
            </div>
          )}

          {/* Platform statuses */}
          {item.platform_statuses && (
            <div className="flex flex-wrap gap-1 mb-2">
              {Object.entries(item.platform_statuses).map(([platform, status]) => (
                <span
                  key={platform}
                  className={`text-xs px-2 py-0.5 rounded ${
                    status === 'published'
                      ? 'bg-green-100 text-green-700'
                      : status === 'failed' || status === 'failed_retriable'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {platform}: {status}
                </span>
              ))}
            </div>
          )}

          {/* Metadata View/Edit */}
          {editing ? (
            <div className="space-y-4 mt-3">
              {platforms.map(platform => {
                const meta = metadata[platform] as { title: string; description: string; hashtags: string } | undefined
                return (
                  <div key={platform} className="space-y-2">
                    <h4 className="text-xs font-medium text-gray-500 uppercase">{platform}</h4>
                    <input
                      type="text"
                      value={meta?.title || ''}
                      onChange={e => updatePlatformMeta(platform, 'title', e.target.value)}
                      placeholder="Title"
                      className="w-full px-2 py-1 text-sm border rounded"
                    />
                    <textarea
                      value={meta?.description || ''}
                      onChange={e => updatePlatformMeta(platform, 'description', e.target.value)}
                      placeholder="Description"
                      rows={2}
                      className="w-full px-2 py-1 text-sm border rounded"
                    />
                    <input
                      type="text"
                      value={meta?.hashtags || ''}
                      onChange={e => updatePlatformMeta(platform, 'hashtags', e.target.value)}
                      placeholder="#hashtags"
                      className="w-full px-2 py-1 text-sm border rounded"
                    />
                  </div>
                )
              })}

              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  Save
                </button>
                <button
                  onClick={() => {
                    setMetadata(item.publishing_metadata || {})
                    setEditing(false)
                  }}
                  className="flex items-center gap-1 px-3 py-1 text-sm border rounded hover:bg-gray-50"
                >
                  <X className="w-3 h-3" />
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {platforms.slice(0, 1).map(platform => {
                const meta = metadata[platform] as { title: string; description: string; hashtags: string } | undefined
                return (
                  <div key={platform}>
                    {meta?.title && (
                      <p className="text-sm text-gray-900 font-medium line-clamp-1">{meta.title}</p>
                    )}
                    {meta?.description && (
                      <p className="text-xs text-gray-500 line-clamp-2">{meta.description}</p>
                    )}
                  </div>
                )
              })}
              {platforms.length > 1 && (
                <p className="text-xs text-gray-400">+{platforms.length - 1} more platforms</p>
              )}
            </div>
          )}

          {/* Timestamps */}
          <div className="text-xs text-gray-400 mt-2">
            Approved: {new Date(item.approved_at).toLocaleString()}
            {item.published_at && (
              <> • Published: {new Date(item.published_at).toLocaleString()}</>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function PublishingQueueView({ projectId, onRefresh }: PublishingQueueViewProps) {
  const [queue, setQueue] = useState<PublishingQueueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchQueue = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await publishingScheduleApi.getQueue(projectId)
      setQueue(response.data)
    } catch (err) {
      console.error('Failed to load queue:', err)
      setError('Failed to load queue')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchQueue()
  }, [projectId])

  const handleItemChange = () => {
    fetchQueue()
    onRefresh()
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
            onClick={fetchQueue}
            className="mt-2 text-sm text-blue-600 hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!queue || queue.items.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-8 text-center">
        <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
          <AlertCircle className="w-6 h-6 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">Queue is Empty</h3>
        <p className="text-sm text-gray-500">
          Approve videos in Moderation to add them to the publishing queue.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900">
            Publishing Queue
          </h3>
          <p className="text-sm text-gray-500">
            {queue.total} videos waiting to be published (FIFO order)
          </p>
        </div>
        <button
          onClick={fetchQueue}
          className="text-sm text-blue-600 hover:underline"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {queue.items.map(item => (
          <QueueItemCard
            key={item.id}
            item={item}
            projectId={projectId}
            onDelete={handleItemChange}
            onUpdate={handleItemChange}
          />
        ))}
      </div>
    </div>
  )
}
