import { AlertCircle, CheckCircle, Clock, Eye, Heart, Image, MessageCircle, Share2 } from 'lucide-react'
import { InstagramIcon, TikTokIcon, YouTubeIcon } from '@/components/icons/PlatformIcons'
import { getImageUrl } from '@/utils/video'
import type { Video, StepType } from '@/types'

const STEP_ORDER: StepType[] = ['scenario', 'image', 'video', 'audio']

const STEP_LABELS: Record<StepType, string> = {
  scenario: 'Scenario',
  image: 'Image',
  video: 'Video',
  audio: 'Audio',
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const datePart = date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
  const timePart = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false })
  return `${datePart} ${timePart}`
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'K'
  return num.toString()
}

function getLatestMetrics(video: Video) {
  if (!video.metrics || video.metrics.length === 0) return null

  const periodPriority = ['7d', '24h', '6h', '30m']
  let totalViews = 0, totalLikes = 0, totalComments = 0, totalShares = 0

  const platforms = new Set(video.metrics.map(m => m.platform))
  for (const platform of platforms) {
    const platformMetrics = video.metrics.filter(m => m.platform === platform)
    for (const period of periodPriority) {
      const metric = platformMetrics.find(m => m.period === period)
      if (metric) {
        totalViews += metric.views
        totalLikes += metric.likes
        totalComments += metric.comments
        totalShares += metric.shares
        break
      }
    }
  }

  if (totalViews === 0 && totalLikes === 0) return null
  return { views: totalViews, likes: totalLikes, comments: totalComments, shares: totalShares }
}

interface VideoGridCardProps {
  video: Video
  onClick: () => void
  showProjectName?: boolean
  projectName?: string
}

export default function VideoGridCard({ video, onClick, showProjectName, projectName }: VideoGridCardProps) {
  // Filter steps based on project type and audio_mode
  const isRemix = video.project?.project_type === 'remix'
  const includeAudio = video.project?.audio_mode !== 'none'
  const baseSteps = isRemix
    ? ['image', 'video', 'audio'] as StepType[]
    : STEP_ORDER
  const activeSteps = includeAudio ? baseSteps : baseSteps.filter(s => s !== 'audio')

  const stepIndex = activeSteps.indexOf(video.current_step)
  const statusLower = video.status?.toLowerCase() || ''
  const isInProgress = ['pending', 'in_progress', 'awaiting_approval', 'validating'].includes(statusLower)
  const isCompleted = statusLower === 'completed'
  const isPublished = video.is_published === true
  const isError = statusLower === 'failed' || statusLower === 'validation_failed'
  const metrics = getLatestMetrics(video)

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl shadow-sm hover:shadow-md transition cursor-pointer overflow-hidden border border-gray-100"
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-gray-100 relative">
        {getImageUrl(video) ? (
          <img src={getImageUrl(video)!} alt={video.title} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Image className="h-12 w-12 text-gray-300" />
          </div>
        )}

        {/* Status badge */}
        <div className="absolute top-2 right-2">
          {isPublished && (
            <span className="px-2 py-1 bg-green-500 text-white text-xs font-medium rounded-full flex items-center">
              <CheckCircle className="h-3 w-3 mr-1" /> Published
            </span>
          )}
          {isCompleted && !isPublished && (
            <span className="px-2 py-1 bg-blue-500 text-white text-xs font-medium rounded-full flex items-center">
              <CheckCircle className="h-3 w-3 mr-1" /> Ready
            </span>
          )}
          {isError && (
            <span className="px-2 py-1 bg-red-500 text-white text-xs font-medium rounded-full flex items-center">
              <AlertCircle className="h-3 w-3 mr-1" /> Error
            </span>
          )}
          {isInProgress && (
            <span className="px-2 py-1 bg-yellow-500 text-white text-xs font-medium rounded-full flex items-center">
              <Clock className="h-3 w-3 mr-1" /> {STEP_LABELS[video.current_step] || video.current_step}
            </span>
          )}
        </div>

        {/* Workflow mode badge */}
        {video.workflow_mode === 'MANUAL' && (
          <div className="absolute top-2 left-2">
            <span className="px-2 py-1 bg-blue-500 text-white text-xs font-medium rounded-full">Manual</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-medium text-gray-900 truncate mb-1">{video.title}</h3>

        {showProjectName && projectName && (
          <p className="text-xs text-gray-500 mb-2">{projectName}</p>
        )}

        {/* Progress indicator for in-progress videos */}
        {isInProgress && (
          <div className="flex items-center gap-1 mb-2">
            {activeSteps.map((_, i) => (
              <span
                key={i}
                className={`w-2 h-2 rounded-full ${
                  i < stepIndex ? 'bg-purple-600' :
                  i === stepIndex ? 'bg-purple-400' :
                  'bg-gray-300'
                }`}
              />
            ))}
          </div>
        )}

        {/* Key dates */}
        <div className="text-xs text-gray-400 space-y-0.5">
          <p>Created: {formatDate(video.created_at)}</p>
          {video.updated_at !== video.created_at && !isCompleted && <p>Updated: {formatDate(video.updated_at)}</p>}
          {isCompleted && !isPublished && <p className="text-blue-600">Completed: {formatDate(video.updated_at)}</p>}
          {isPublished && video.published_at && <p className="text-green-600">Published: {formatDate(video.published_at)}</p>}
        </div>

        {/* Platform icons (if published) */}
        {isPublished && video.project?.platforms && (
          <div className="flex items-center gap-2 mt-2">
            {video.project.platforms.includes('instagram') && <InstagramIcon className="w-4 h-4 text-pink-500" />}
            {video.project.platforms.includes('tiktok') && <TikTokIcon className="w-4 h-4 text-gray-900" />}
            {video.project.platforms.includes('youtube') && <YouTubeIcon className="w-4 h-4 text-red-500" />}
          </div>
        )}

        {/* Metrics (if published and has data) */}
        {isPublished && metrics && (
          <div className="flex items-center gap-3 mt-2 pt-2 border-t border-gray-100 text-xs text-gray-500">
            <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{formatNumber(metrics.views)}</span>
            <span className="flex items-center gap-1"><Heart className="w-3 h-3" />{formatNumber(metrics.likes)}</span>
            <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" />{formatNumber(metrics.comments)}</span>
            {metrics.shares > 0 && (
              <span className="flex items-center gap-1"><Share2 className="w-3 h-3" />{formatNumber(metrics.shares)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
