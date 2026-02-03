import { Loader2, RefreshCw } from 'lucide-react'
import type { PlatformMetadata } from '@/services/api'

interface ReviewMetadataProps {
  metadata: Record<string, PlatformMetadata> | null
  loading: boolean
  error: string | null
  onChange: (metadata: Record<string, PlatformMetadata>) => void
  onRetry: () => void
}

export function ReviewMetadata({ metadata, loading, error, onChange, onRetry }: ReviewMetadataProps) {
  if (loading) {
    return (
      <div className="border rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">Publishing Metadata</h4>
        <div className="flex items-center gap-2 text-sm text-gray-500 py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          Generating metadata...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="border border-red-200 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">Publishing Metadata</h4>
        <div className="text-sm text-red-600 mb-2">{error}</div>
        <button
          onClick={onRetry}
          className="flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <RefreshCw className="w-3 h-3" />
          Retry
        </button>
      </div>
    )
  }

  if (!metadata) return null

  const updateField = (platform: string, field: keyof PlatformMetadata, value: string) => {
    onChange({
      ...metadata,
      [platform]: { ...metadata[platform], [field]: value },
    })
  }

  return (
    <div className="border rounded-lg p-4">
      <h4 className="font-medium text-gray-900 mb-3">Publishing Metadata</h4>
      <div className="space-y-4">
        {Object.entries(metadata).map(([platform, data]) => (
          <div key={platform} className="space-y-2">
            <h5 className="text-sm font-medium text-gray-600 capitalize">{platform}</h5>
            <input
              type="text"
              value={data.title}
              onChange={(e) => updateField(platform, 'title', e.target.value)}
              placeholder="Title"
              className="w-full px-3 py-1.5 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
            <textarea
              value={data.description}
              onChange={(e) => updateField(platform, 'description', e.target.value)}
              placeholder="Description"
              rows={2}
              className="w-full px-3 py-1.5 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
            <input
              type="text"
              value={data.hashtags || ''}
              onChange={(e) => updateField(platform, 'hashtags', e.target.value)}
              placeholder="Hashtags"
              className="w-full px-3 py-1.5 text-sm border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            />
          </div>
        ))}
      </div>
    </div>
  )
}
