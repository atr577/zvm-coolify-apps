import { useState } from 'react'
import { CheckCircle, Loader2, AlertCircle, ExternalLink, Upload } from 'lucide-react'
import type { AdaptationData, PlatformAdaptation } from '@/types'

interface PublishData {
  video_url: string
  title: string
  description: string
  hashtags: string
}

interface PublishingStepProps {
  projectId: number
  adaptedPlatforms: string[]
  adaptationData: AdaptationData | null
  videoUrl: string
  onPublish: (platform: string, data: PublishData) => void
  publishingStatus: Record<string, { status: string; postUrl?: string; error?: string }>
}

const getPlatformData = (adaptationData: AdaptationData | null, platform: string): PlatformAdaptation | undefined => {
  return adaptationData?.[platform]
}

export default function PublishingStep({
  adaptedPlatforms,
  adaptationData,
  videoUrl,
  onPublish,
  publishingStatus
}: PublishingStepProps) {
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([])

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'instagram':
        return '📸'
      case 'tiktok':
        return '🎵'
      case 'youtube':
        return '📹'
      default:
        return '📱'
    }
  }

  const getPlatformName = (platform: string) => {
    switch (platform) {
      case 'instagram':
        return 'Instagram Reels'
      case 'tiktok':
        return 'TikTok'
      case 'youtube':
        return 'YouTube Shorts'
      default:
        return platform
    }
  }

  const getPublishStatus = (platform: string) => {
    const status = publishingStatus[platform]
    if (!status) return 'ready'
    return status.status
  }

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    )
  }

  const handlePublish = (platform: string) => {
    const platformData = getPlatformData(adaptationData, platform)
    if (!platformData) return

    onPublish(platform, {
      video_url: videoUrl,
      title: platformData.title || platformData.caption?.split('\n')[0] || 'Untitled',
      description: platformData.description || platformData.caption || '',
      hashtags: platformData.hashtags?.join(' ') || ''
    })
  }

  const handlePublishSelected = () => {
    selectedPlatforms.forEach(platform => {
      if (getPublishStatus(platform) === 'ready') {
        handlePublish(platform)
      }
    })
  }

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border-l-4 border-blue-400 p-4">
        <p className="text-blue-800 text-sm">
          <strong>📢 Ready to publish!</strong> Your content has been adapted for{' '}
          {adaptedPlatforms.length} platform{adaptedPlatforms.length > 1 ? 's' : ''}.
          Select platforms and publish when ready.
        </p>
      </div>

      {/* Platform cards */}
      <div className="space-y-4">
        {adaptedPlatforms.map(platform => {
          const platformData = getPlatformData(adaptationData, platform)
          const status = getPublishStatus(platform)
          const isSelected = selectedPlatforms.includes(platform)
          const isPublishing = status === 'pending' || status === 'processing'
          const isPublished = status === 'published'
          const isFailed = status === 'failed'

          return (
            <div
              key={platform}
              className={`border-2 rounded-lg p-5 transition-all ${
                isPublished
                  ? 'bg-green-50 border-green-300'
                  : isFailed
                  ? 'bg-red-50 border-red-300'
                  : isSelected
                  ? 'bg-primary-50 border-primary-400 shadow-md'
                  : 'bg-white border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-4 flex-1">
                  {/* Checkbox */}
                  {!isPublished && status !== 'processing' && (
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => togglePlatform(platform)}
                      disabled={isPublishing}
                      className="mt-1 h-5 w-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  )}

                  {/* Platform info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      <span className="text-3xl">{getPlatformIcon(platform)}</span>
                      <div>
                        <h4 className="text-lg font-bold text-gray-900">
                          {getPlatformName(platform)}
                        </h4>
                        {platformData?.format && (
                          <p className="text-xs text-gray-500">{platformData.format}</p>
                        )}
                      </div>
                    </div>

                    {/* Content preview */}
                    <div className="bg-white bg-opacity-50 rounded p-3 space-y-2 text-sm">
                      {platformData?.title && (
                        <div>
                          <span className="font-semibold text-gray-700">Title:</span>
                          <p className="text-gray-900 line-clamp-1">{platformData.title}</p>
                        </div>
                      )}
                      {platformData?.caption && (
                        <div>
                          <span className="font-semibold text-gray-700">Caption:</span>
                          <p className="text-gray-900 line-clamp-2">{platformData.caption}</p>
                        </div>
                      )}
                      {platformData?.hashtags && platformData.hashtags.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {platformData.hashtags.slice(0, 5).map((tag: string) => (
                            <span key={tag} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                              #{tag}
                            </span>
                          ))}
                          {platformData.hashtags.length > 5 && (
                            <span className="text-xs text-gray-500">+{platformData.hashtags.length - 5} more</span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Status messages */}
                    {isPublished && publishingStatus[platform]?.postUrl && (
                      <a
                        href={publishingStatus[platform].postUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-3 inline-flex items-center text-green-700 hover:text-green-800 font-medium text-sm"
                      >
                        <ExternalLink className="h-4 w-4 mr-1" />
                        View published post
                      </a>
                    )}

                    {isFailed && publishingStatus[platform]?.error && (
                      <div className="mt-3 text-red-700 text-sm">
                        <strong>Error:</strong> {publishingStatus[platform].error}
                      </div>
                    )}
                  </div>
                </div>

                {/* Action button */}
                <div className="ml-4">
                  {isPublishing ? (
                    <div className="flex items-center text-primary-600">
                      <Loader2 className="h-5 w-5 animate-spin mr-2" />
                      <span className="text-sm font-medium">Publishing...</span>
                    </div>
                  ) : isPublished ? (
                    <div className="flex items-center text-green-600">
                      <CheckCircle className="h-5 w-5 mr-2" />
                      <span className="text-sm font-medium">Published</span>
                    </div>
                  ) : isFailed ? (
                    <button
                      onClick={() => handlePublish(platform)}
                      className="flex items-center px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
                    >
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Retry
                    </button>
                  ) : (
                    <button
                      onClick={() => handlePublish(platform)}
                      disabled={isPublishing}
                      className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 text-sm"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Publish Now
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Bulk publish button */}
      {selectedPlatforms.length > 0 && (
        <div className="bg-gradient-to-r from-primary-50 to-primary-100 border-2 border-primary-300 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-primary-900">
                {selectedPlatforms.length} platform{selectedPlatforms.length > 1 ? 's' : ''} selected
              </p>
              <p className="text-sm text-primary-700">Publish to all selected platforms at once</p>
            </div>
            <button
              onClick={handlePublishSelected}
              className="flex items-center px-6 py-3 bg-primary-600 text-white rounded-md hover:bg-primary-700 font-medium shadow-md"
            >
              <Upload className="h-5 w-5 mr-2" />
              Publish to {selectedPlatforms.length} Platform{selectedPlatforms.length > 1 ? 's' : ''}
            </button>
          </div>
        </div>
      )}

      {/* Info note */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
        <p className="font-semibold text-gray-800 mb-2">📝 Publishing Notes:</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>Make sure you have authorized access to each platform</li>
          <li>Published content will use the adapted captions and hashtags</li>
          <li>Publishing may take a few moments to complete</li>
          <li>You can retry failed publications</li>
        </ul>
      </div>
    </div>
  )
}
