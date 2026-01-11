import { useMutation, useQueryClient } from 'react-query'
import { videosApi, workflowApi, StepType } from '@/services/api'
import type { Video } from '@/types'

/**
 * Hook for managing 4-step workflow: SCENARIO → IMAGE → VIDEO → AUDIO
 */
export function useVideoWorkflow(videoId: number, video: Video | undefined) {
  const queryClient = useQueryClient()

  // Invalidate video query to refresh data
  const invalidateVideo = () => {
    queryClient.invalidateQueries(['video', videoId])
  }

  // Run all steps automatically (AUTO mode)
  const runAutoMutation = useMutation(
    () => workflowApi.runAuto(videoId),
    {
      onSuccess: invalidateVideo,
      onError: (error) => console.error('Workflow run failed:', error)
    }
  )

  // Generate a single step (MANUAL mode)
  const generateStepMutation = useMutation(
    (step: StepType) => workflowApi.generateStep(videoId, step),
    {
      onSuccess: invalidateVideo,
      onError: (error) => console.error('Generate step failed:', error)
    }
  )

  // Select a variant (triggers auto-continue to next step)
  const selectVariantMutation = useMutation(
    (variantId: number) => workflowApi.selectVariant(videoId, variantId),
    {
      onSuccess: invalidateVideo,
      onError: (error) => console.error('Select variant failed:', error)
    }
  )

  // Delete video
  const deleteMutation = useMutation(
    () => videosApi.delete(videoId),
    { onSuccess: () => {} } // Navigation handled in component
  )

  // Toggle workflow mode
  const toggleWorkflowModeMutation = useMutation(
    () => videosApi.update(videoId, {
      workflow_mode: video?.workflow_mode === 'MANUAL' ? 'AUTO' : 'MANUAL'
    }),
    { onSuccess: invalidateVideo }
  )

  // Get current step from video status
  const getCurrentStep = (): StepType | null => {
    if (!video?.current_step) return null
    return video.current_step as StepType
  }

  // Get workflow steps for this project
  const getWorkflowSteps = (): StepType[] => {
    const steps: StepType[] = ['scenario', 'image', 'video', 'audio']
    if (video?.project?.audio_mode === 'none') {
      return steps.filter(s => s !== 'audio')
    }
    return steps
  }

  // Check if step is completed (has content in video)
  const isStepCompleted = (step: StepType): boolean => {
    if (!video) return false
    switch (step) {
      case 'scenario':
        return !!video.scenario_data
      case 'image':
        return !!video.image_url
      case 'video':
        return !!video.video_url
      case 'audio':
        return !!video.video_with_audio_url
      default:
        return false
    }
  }

  return {
    // Mutations
    runAutoMutation,
    generateStepMutation,
    selectVariantMutation,
    deleteMutation,
    toggleWorkflowModeMutation,

    // Helpers
    getCurrentStep,
    getWorkflowSteps,
    isStepCompleted,
  }
}
