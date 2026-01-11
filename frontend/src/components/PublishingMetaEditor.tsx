import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from 'react-query'
import { Loader2, Sparkles, Save } from 'lucide-react'
import { workflowApi } from '@/services/api'

interface PlatformMeta {
  title: string
  description: string
  hashtags: string
}

interface PublishingMetaEditorProps {
  videoId: number
  platforms: string[]
  initialMeta: Record<string, PlatformMeta> | null
}

export default function PublishingMetaEditor({
  videoId,
  platforms,
  initialMeta
}: PublishingMetaEditorProps) {
  const queryClient = useQueryClient()
  const [meta, setMeta] = useState<Record<string, PlatformMeta>>({})
  const [activePlatform, setActivePlatform] = useState<string>(platforms[0] || 'youtube')
  const [hasChanges, setHasChanges] = useState(false)

  // Initialize meta from props
  useEffect(() => {
    if (initialMeta) {
      setMeta(initialMeta)
    }
  }, [initialMeta])

  // Generate meta mutation
  const generateMutation = useMutation(
    () => workflowApi.generateMeta(videoId),
    {
      onSuccess: (response) => {
        const newMeta = (response.data.publishing_meta || {}) as Record<string, PlatformMeta>
        setMeta(newMeta)
        queryClient.invalidateQueries(['video', videoId])
      },
      onError: (error) => {
        console.error('Failed to generate meta:', error)
      }
    }
  )

  // Save meta mutation
  const saveMutation = useMutation(
    (metaToSave: Record<string, PlatformMeta>) => workflowApi.updateMeta(videoId, metaToSave),
    {
      onSuccess: () => {
        setHasChanges(false)
        queryClient.invalidateQueries(['video', videoId])
      }
    }
  )

  const updateField = (platform: string, field: keyof PlatformMeta, value: string) => {
    setMeta(prev => ({
      ...prev,
      [platform]: {
        title: prev[platform]?.title || '',
        description: prev[platform]?.description || '',
        hashtags: prev[platform]?.hashtags || '',
        [field]: value
      }
    }))
    setHasChanges(true)
  }

  const platformMeta = meta[activePlatform]
  const currentMeta = {
    title: platformMeta?.title || '',
    description: platformMeta?.description || '',
    hashtags: platformMeta?.hashtags || ''
  }
  const hasMeta = Object.keys(meta).length > 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Publishing Metadata</h3>
        <div className="flex gap-2">
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isLoading}
            className="flex items-center px-3 py-1.5 text-sm bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition disabled:opacity-50"
          >
            {generateMutation.isLoading ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-1" />
            )}
            {hasMeta ? 'Regenerate' : 'Generate'}
          </button>
          {hasChanges && (
            <button
              onClick={() => saveMutation.mutate(meta)}
              disabled={saveMutation.isLoading}
              className="flex items-center px-3 py-1.5 text-sm bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition disabled:opacity-50"
            >
              {saveMutation.isLoading ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-1" />
              )}
              Save
            </button>
          )}
        </div>
      </div>

      {/* Platform tabs */}
      {platforms.length > 1 && (
        <div className="flex gap-2 border-b">
          {platforms.map(platform => (
            <button
              key={platform}
              onClick={() => setActivePlatform(platform)}
              className={`px-3 py-2 text-sm font-medium border-b-2 transition ${
                activePlatform === platform
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {platform === 'instagram' ? 'Instagram' :
               platform === 'tiktok' ? 'TikTok' : 'YouTube'}
            </button>
          ))}
        </div>
      )}

      {/* Meta fields */}
      {hasMeta ? (
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              type="text"
              value={currentMeta.title}
              onChange={(e) => updateField(activePlatform, 'title', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Enter title..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={currentMeta.description}
              onChange={(e) => updateField(activePlatform, 'description', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              placeholder="Enter description..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hashtags</label>
            <input
              type="text"
              value={currentMeta.hashtags}
              onChange={(e) => updateField(activePlatform, 'hashtags', e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              placeholder="#hashtag1 #hashtag2..."
            />
          </div>
        </div>
      ) : (
        <div className="text-center py-6 text-gray-500">
          <p className="mb-2">No metadata generated yet</p>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isLoading}
            className="inline-flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50"
          >
            {generateMutation.isLoading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-2" />
            )}
            Generate Metadata
          </button>
        </div>
      )}
    </div>
  )
}
