import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from 'react-query'
import { Loader2 } from 'lucide-react'
import { videosApi, metricsApi } from '@/services/api'
import { useVideoWorkflow } from '@/hooks/useVideoWorkflow'
import {
  VideoHeader,
  CompletedVideoView,
  InProgressView
} from '@/components/video'

export default function VideoDetail() {
  const { id } = useParams<{ id: string }>()
  const videoId = parseInt(id || '0')
  const navigate = useNavigate()

  const { data: video, isLoading } = useQuery(
    ['video', videoId],
    () => videosApi.get(videoId).then(res => res.data),
    { refetchInterval: 5000 }
  )

  const workflow = useVideoWorkflow(videoId, video)

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

  // Auto-start generation (only for AUTO mode)
  const hasNoWorkflow = !video?.workflow_steps || video?.workflow_steps.length === 0
  const shouldAutoStart = video?.status === 'pending' && hasNoWorkflow && video?.workflow_mode !== 'MANUAL'

  useEffect(() => {
    if (shouldAutoStart && !workflow.autoGenerateMutation.isLoading) {
      workflow.autoGenerateMutation.mutate()
    }
  }, [shouldAutoStart])

  // Handle navigation after delete
  useEffect(() => {
    if (workflow.deleteMutation.isSuccess) {
      navigate(video?.project_id ? `/?project=${video.project_id}` : '/')
    }
  }, [workflow.deleteMutation.isSuccess])

  if (isLoading || !video) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-12 w-12 animate-spin text-purple-600" />
      </div>
    )
  }

  // Current step data
  const steps = video.workflow_steps || []
  const currentStep = steps.find(s => {
    const st = s.status?.toLowerCase()
    return st === 'awaiting_approval' || st === 'in_progress'
  })
  const pendingSteps = steps.filter(s => s.status?.toLowerCase() === 'pending')
  const failedStep = steps.find(s => {
    if (s.status?.toLowerCase() !== 'failed') return false
    const hasPendingOfSameType = pendingSteps.some(p => p.step_type === s.step_type)
    return !hasPendingOfSameType
  })
  const completedSteps = steps.filter(s => {
    const st = s.status?.toLowerCase()
    return st === 'approved' || st === 'completed'
  })

  const isRemix = video.project?.project_type === 'remix'
  const totalSteps = isRemix ? 3 : 9
  const completedCount = completedSteps.length
  const isCompleted = video.status?.toLowerCase() === 'completed'
  const isPublishing = video.current_step?.toLowerCase() === 'publishing'

  return (
    <div className="max-w-4xl mx-auto">
      <VideoHeader
        title={video.title}
        completedCount={completedCount}
        totalSteps={totalSteps}
        isCompleted={isCompleted}
        workflowMode={video.workflow_mode}
        isRemix={isRemix}
        onToggleMode={() => workflow.toggleWorkflowModeMutation.mutate()}
        onDelete={() => confirm('Delete video?') && workflow.deleteMutation.mutate()}
      />

      {isCompleted ? (
        <CompletedVideoView
          video={video}
          videoId={videoId}
          steps={steps}
          completedCount={completedCount}
          totalSteps={totalSteps}
          metricsSummary={metricsSummary}
          onRefetchMetrics={() => refetchMetrics()}
          onSetRating={(rating) => setRatingMutation.mutate(rating)}
        />
      ) : (
        <InProgressView
          video={video}
          videoId={videoId}
          steps={steps}
          currentStep={currentStep}
          pendingSteps={pendingSteps}
          failedStep={failedStep}
          completedCount={completedCount}
          totalSteps={totalSteps}
          isPublishing={isPublishing}
          workflow={workflow}
        />
      )}
    </div>
  )
}
