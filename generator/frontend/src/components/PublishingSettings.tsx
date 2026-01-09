import { useState } from 'react'
import { useQuery, useQueryClient } from 'react-query'
import { CheckCircle, Instagram, Youtube, AlertCircle, Loader2 } from 'lucide-react'
import { workflowApi, publishingApi, socialAccountsApi, SocialAccount } from '@/services/api'
import type { AdaptationData, PlatformAdaptation } from '@/types'
import { getErrorMessage } from '@/types'

interface PublishingSettingsProps {
  videoId: number
  publishingStepId: number
  adaptationData: AdaptationData | null
  platforms: string[]
  videoUrl: string
}

interface PublishResult {
  platform: string
  success: boolean
  post_url?: string
  error?: string
}

export default function PublishingSettings({
  videoId,
  publishingStepId,
  adaptationData,
  platforms,
  videoUrl
}: PublishingSettingsProps) {
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(platforms || [])
  const [publishResults, setPublishResults] = useState<PublishResult[]>([])
  const [isPublishing, setIsPublishing] = useState(false)
  const [youtubePrivacy, setYoutubePrivacy] = useState<'public' | 'private' | 'unlisted'>('private')
  const queryClient = useQueryClient()

  // Fetch connected social accounts
  const { data: socialAccounts, isLoading: loadingAccounts } = useQuery(
    'socialAccounts',
    () => socialAccountsApi.list().then(res => res.data),
    { staleTime: 30000 }
  )

  const togglePlatform = (platform: string) => {
    setSelectedPlatforms(prev =>
      prev.includes(platform)
        ? prev.filter(p => p !== platform)
        : [...prev, platform]
    )
  }

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'instagram':
        return <Instagram className="h-5 w-5" />
      case 'youtube':
        return <Youtube className="h-5 w-5" />
      case 'tiktok':
        return <span className="text-lg font-bold">TT</span>
      default:
        return null
    }
  }

  const getPlatformLabel = (platform: string) => {
    const labels: Record<string, string> = {
      instagram: 'Instagram Reels',
      tiktok: 'TikTok',
      youtube: 'YouTube Shorts'
    }
    return labels[platform] || platform
  }

  const getPlatformMeta = (platform: string): PlatformAdaptation => {
    return adaptationData?.[platform] || {}
  }

  const getConnectedAccount = (platform: string): SocialAccount | undefined => {
    return socialAccounts?.find(acc => acc.platform === platform && acc.is_active)
  }

  const publishToPlatform = async (platform: string): Promise<PublishResult> => {
    const account = getConnectedAccount(platform)
    if (!account) {
      return { platform, success: false, error: 'Аккаунт не подключен' }
    }

    const meta = getPlatformMeta(platform)
    const title = meta.title || 'Video'
    const description = meta.description || ''
    const hashtags = meta.hashtags?.join(' ') || ''

    try {
      let response
      switch (platform) {
        case 'youtube':
          response = await publishingApi.toYouTube(videoId, account.id, videoUrl, title, description, hashtags, youtubePrivacy)
          break
        case 'instagram':
          response = await publishingApi.toInstagram(videoId, account.id, videoUrl, title, description, hashtags)
          break
        case 'tiktok':
          response = await publishingApi.toTikTok(videoId, account.id, videoUrl, title, description, hashtags)
          break
        default:
          return { platform, success: false, error: 'Неподдерживаемая платформа' }
      }

      const data = response.data
      if (data.success) {
        return { platform, success: true, post_url: data.post_url }
      } else {
        return { platform, success: false, error: data.error_message || 'Ошибка публикации' }
      }
    } catch (err: unknown) {
      return { platform, success: false, error: getErrorMessage(err) }
    }
  }

  const handlePublish = async () => {
    if (selectedPlatforms.length === 0) return
    if (!videoUrl) {
      setPublishResults([{ platform: 'all', success: false, error: 'URL видео отсутствует' }])
      return
    }

    setIsPublishing(true)
    setPublishResults([])

    const results: PublishResult[] = []

    // Publish to each selected platform
    for (const platform of selectedPlatforms) {
      const result = await publishToPlatform(platform)
      results.push(result)
      setPublishResults([...results])
    }

    // If all successful, approve the step
    const allSuccess = results.every(r => r.success)
    if (allSuccess) {
      try {
        await workflowApi.approveStep(publishingStepId, true, 'Published to all platforms')
        queryClient.invalidateQueries(['video', videoId])
      } catch (err) {
        console.error('Failed to approve step:', err)
      }
    }

    setIsPublishing(false)
  }

  const hasUnconnectedPlatforms = selectedPlatforms.some(p => !getConnectedAccount(p))

  return (
    <div className="bg-gradient-to-br from-purple-50 to-blue-50 border-2 border-purple-300 p-6 rounded-lg shadow-lg">
      <div className="flex items-center mb-6">
        <div className="bg-purple-600 p-3 rounded-lg mr-4">
          <CheckCircle className="h-6 w-6 text-white" />
        </div>
        <div>
          <h3 className="text-xl font-bold text-gray-900">Настройки публикации</h3>
          <p className="text-sm text-gray-600">Выберите платформы для публикации видео</p>
        </div>
      </div>

      {loadingAccounts ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
          <span className="ml-2 text-gray-600">Загрузка аккаунтов...</span>
        </div>
      ) : (
        <>
          <div className="space-y-4 mb-6">
            {platforms.map(platform => {
              const isSelected = selectedPlatforms.includes(platform)
              const meta = getPlatformMeta(platform)
              const account = getConnectedAccount(platform)
              const result = publishResults.find(r => r.platform === platform)

              return (
                <div
                  key={platform}
                  className={`border-2 rounded-lg p-4 cursor-pointer transition ${
                    isSelected
                      ? 'border-purple-500 bg-white shadow-md'
                      : 'border-gray-300 bg-white hover:border-gray-400'
                  }`}
                  onClick={() => togglePlatform(platform)}
                >
                  <div className="flex items-start">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => togglePlatform(platform)}
                      className="mt-1 mr-3 h-5 w-5 text-purple-600 rounded focus:ring-purple-500"
                      onClick={e => e.stopPropagation()}
                    />

                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center">
                          <span className="mr-2">{getPlatformIcon(platform)}</span>
                          <span className="font-semibold text-gray-900">
                            {getPlatformLabel(platform)}
                          </span>
                        </div>

                        {/* Account status */}
                        {account ? (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                            @{account.username || account.display_name || 'Connected'}
                          </span>
                        ) : (
                          <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                            Не подключен
                          </span>
                        )}
                      </div>

                      {/* Publish result */}
                      {result && (
                        <div className={`mt-2 p-2 rounded ${result.success ? 'bg-green-50' : 'bg-red-50'}`}>
                          {result.success ? (
                            <div className="flex items-center text-green-700 text-sm">
                              <CheckCircle className="h-4 w-4 mr-2" />
                              <span>Опубликовано</span>
                              {result.post_url && (
                                <a
                                  href={result.post_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="ml-2 underline"
                                  onClick={e => e.stopPropagation()}
                                >
                                  Открыть
                                </a>
                              )}
                            </div>
                          ) : (
                            <div className="flex items-center text-red-700 text-sm">
                              <AlertCircle className="h-4 w-4 mr-2" />
                              <span>{result.error}</span>
                            </div>
                          )}
                        </div>
                      )}

                      {isSelected && meta && !result && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          {/* YouTube Privacy Selector */}
                          {platform === 'youtube' && (
                            <div className="mb-3">
                              <p className="text-xs font-medium text-gray-500 mb-1">Приватность:</p>
                              <select
                                value={youtubePrivacy}
                                onChange={(e) => setYoutubePrivacy(e.target.value as 'public' | 'private' | 'unlisted')}
                                onClick={(e) => e.stopPropagation()}
                                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                              >
                                <option value="private">Приватное (только вы)</option>
                                <option value="unlisted">По ссылке (не в поиске)</option>
                                <option value="public">Публичное (все видят)</option>
                              </select>
                            </div>
                          )}
                          {meta.title && (
                            <div className="mb-2">
                              <p className="text-xs font-medium text-gray-500 mb-1">Заголовок:</p>
                              <p className="text-sm text-gray-800">{meta.title}</p>
                            </div>
                          )}
                          {meta.description && (
                            <div className="mb-2">
                              <p className="text-xs font-medium text-gray-500 mb-1">Описание:</p>
                              <p className="text-sm text-gray-800">{meta.description}</p>
                            </div>
                          )}
                          {meta.hashtags && meta.hashtags.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-gray-500 mb-1">Хэштеги:</p>
                              <p className="text-sm text-purple-600">
                                {meta.hashtags.join(' ')}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {selectedPlatforms.length === 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-yellow-800">
                Выберите хотя бы одну платформу для публикации
              </p>
            </div>
          )}

          {hasUnconnectedPlatforms && selectedPlatforms.length > 0 && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-orange-800">
                Некоторые выбранные платформы не подключены. Подключите аккаунты в настройках профиля.
              </p>
            </div>
          )}

          {!videoUrl && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-red-800">
                URL видео отсутствует. Убедитесь, что видео сгенерировано.
              </p>
            </div>
          )}

          <div className="flex space-x-3">
            <button
              onClick={handlePublish}
              disabled={selectedPlatforms.length === 0 || isPublishing || hasUnconnectedPlatforms || !videoUrl}
              className="flex-1 flex items-center justify-center px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isPublishing ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  Публикация...
                </>
              ) : (
                <>
                  <CheckCircle className="h-5 w-5 mr-2" />
                  Опубликовать на {selectedPlatforms.length} {
                    selectedPlatforms.length === 1 ? 'платформе' : 'платформах'
                  }
                </>
              )}
            </button>
          </div>

          <p className="text-xs text-gray-500 text-center mt-4">
            После подтверждения видео будет опубликовано на выбранных платформах
          </p>
        </>
      )}
    </div>
  )
}
