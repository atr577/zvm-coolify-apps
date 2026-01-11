/**
 * VideoDetail - Main video page using Workflow V3
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from 'react-query'
import { Loader2, Trash2, ArrowLeft, Settings, CheckCircle } from 'lucide-react'
import { videosApi, metricsApi } from '@/services/api'
import { WorkflowRunner } from '@/components/workflow'
import { CompletedVideoView } from '@/components/video'
import type { Video } from '@/types'

export default function VideoDetail() {
  const { id } = useParams<{ id: string }>()
  const videoId = parseInt(id || '0')
  const navigate = useNavigate()

  // Fetch video with polling during generation
  const { data: video, isLoading } = useQuery(
    ['video', videoId],
    () => videosApi.get(videoId).then(res => res.data),
    {
      refetchInterval: (data) => {
        const status = data?.status?.toLowerCase()
        return status === 'in_progress' || status === 'pending' ? 2000 : false
      }
    }
  )

  // Fetch metrics for completed videos
  const { data: metricsSummary, refetch: refetchMetrics } = useQuery(
    ['metrics', videoId],
    () => metricsApi.getSummary(videoId).then(res => res.data),
    {
      enabled: video?.status === 'completed',
      refetchInterval: 60000
    }
  )

  // Set author rating mutation
  const setRatingMutation = useMutation(
    (rating: number) => metricsApi.setRating(videoId, rating),
    { onSuccess: () => refetchMetrics() }
  )

  // Delete mutation
  const deleteMutation = useMutation(
    () => videosApi.delete(videoId),
    {
      onSuccess: () => {
        navigate(video?.project_id ? `/?project=${video.project_id}` : '/')
      }
    }
  )

  // Toggle workflow mode mutation
  const toggleModeMutation = useMutation(
    () => videosApi.update(videoId, {
      workflow_mode: video?.workflow_mode === 'MANUAL' ? 'AUTO' : 'MANUAL'
    }),
    {
      onSuccess: () => {
        // Invalidate will be handled by react-query
      }
    }
  )

  if (isLoading || !video) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
      </div>
    )
  }

  const isRemix = video.project?.project_type === 'remix'
  const includeAudio = video.project?.audio_mode !== 'none'
  // NEW: Discover now has 4 steps (scenario, image, video, audio), Remix has 3 (image, video, audio)
  const totalSteps = isRemix ? (includeAudio ? 3 : 2) : (includeAudio ? 4 : 3)
  const completedCount = getCompletedCount(video, isRemix, includeAudio)
  const isCompleted = video.status?.toLowerCase() === 'completed'

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <VideoHeader
        video={video}
        completedCount={completedCount}
        totalSteps={totalSteps}
        isCompleted={isCompleted}
        onToggleMode={() => toggleModeMutation.mutate()}
        onDelete={() => confirm('Delete video?') && deleteMutation.mutate()}
        onBack={() => navigate(video.project_id ? `/?project=${video.project_id}` : '/')}
      />

      {/* Content */}
      {isCompleted ? (
        <CompletedVideoView
          video={video}
          videoId={videoId}
          metricsSummary={metricsSummary}
          onRefetchMetrics={() => refetchMetrics()}
          onSetRating={(rating) => setRatingMutation.mutate(rating)}
        />
      ) : (
        <WorkflowRunner video={video} videoId={videoId} />
      )}
    </div>
  )
}

// Header component
interface VideoHeaderProps {
  video: Video
  completedCount: number
  totalSteps: number
  isCompleted: boolean
  onToggleMode: () => void
  onDelete: () => void
  onBack: () => void
}

function VideoHeader({
  video,
  completedCount,
  totalSteps,
  isCompleted,
  onToggleMode,
  onDelete,
  onBack,
}: VideoHeaderProps) {
  const isRemix = video.project?.project_type === 'remix'

  return (
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center space-x-4">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
        >
          <ArrowLeft className="h-5 w-5 text-gray-600" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-gray-900 line-clamp-1">{video.title}</h1>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            {isCompleted ? (
              <span className="flex items-center text-green-600">
                <CheckCircle className="h-4 w-4 mr-1" />
                Completed
              </span>
            ) : (
              <span>Step {completedCount + 1} of {totalSteps}</span>
            )}
            {video.workflow_mode === 'MANUAL' && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">Manual</span>
            )}
            {isRemix && (
              <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded">Remix</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <button
          onClick={onToggleMode}
          className="p-2 hover:bg-gray-100 rounded-lg transition"
          title={video.workflow_mode === 'MANUAL' ? 'Switch to Auto mode' : 'Switch to Manual mode'}
        >
          <Settings className="h-5 w-5 text-gray-500" />
        </button>
        <button
          onClick={onDelete}
          className="p-2 hover:bg-red-50 rounded-lg transition"
        >
          <Trash2 className="h-5 w-5 text-red-500" />
        </button>
      </div>
    </div>
  )
}

// Helper: Count completed steps from video data
function getCompletedCount(video: Video, isRemix: boolean, includeAudio: boolean = true): number {
  // NEW: simplified Discover workflow - scenario generates image_prompt + motion_prompt
  let steps = isRemix
    ? ['image', 'video', 'audio']
    : ['scenario', 'image', 'video', 'audio']

  if (!includeAudio) {
    steps = steps.filter(s => s !== 'audio')
  }

  let count = 0
  for (const step of steps) {
    if (hasStepData(video, step)) {
      count++
    } else {
      break
    }
  }
  return count
}

// Helper: Check if step has data
function hasStepData(video: Video, step: string): boolean {
  switch (step) {
    case 'story':
      return !!video.story_data
    case 'description':
      return !!video.description_data
    case 'prompt':
      return !!video.prompt_data
    case 'image':
      return !!video.image_url
    case 'scenario':
      return !!video.scenario_data
    case 'video':
      return !!video.video_url
    case 'audio':
      return !!video.video_with_audio_url
    default:
      return false
  }
}
